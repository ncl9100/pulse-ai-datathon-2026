"""
STEP 5 — COST PERFORMANCE INDEX (CPI)
=======================================
Purpose:
    The CPI answers: "For every dollar of budget, how much actual work did we get?"
    A CPI below 1.0 means we're spending more than planned relative to progress.
    A CPI above 1.0 means we're running efficiently.

    CPI formula per SOV line:
        budgeted_cost_of_work_performed = estimated_total_cost × pct_complete
        CPI = budgeted_cost_of_work_performed / actual_cost_to_date

    We also compute:
        Estimate At Completion (EAC) = actual_cost_to_date / pct_complete
            → Projects what the final cost will be if the current burn rate continues
        Variance At Completion (VAC) = budget_at_completion - EAC
            → How much over or under budget the line will finish

    Results are computed at both line-item level and rolled-up project level.

Depends on:
    outputs/actual_cost_per_line.csv   ← from Step 3
    outputs/billing_progress.csv       ← from Step 4
    outputs/project_master.csv         ← from Step 2

Output:
    outputs/cpi_per_line.csv           — CPI for every (project, SOV line)
    outputs/cpi_per_project.csv        — rolled-up project-level CPI
"""

import pandas as pd
import numpy as np
import os

OUT = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUT, exist_ok=True)

# ── Load ───────────────────────────────────────────────────────────────────────
print("Loading Step 3 and Step 4 outputs ...")
cost     = pd.read_csv(os.path.join(OUT, "actual_cost_per_line.csv"))
progress = pd.read_csv(os.path.join(OUT, "billing_progress.csv"))
master   = pd.read_csv(os.path.join(OUT, "project_master.csv"))

# ── 5A: Merge cost and progress ───────────────────────────────────────────────
print("Merging cost and billing progress ...")
df = cost.merge(
    progress[["project_id","sov_line_id","pct_complete","total_billed","completion_stage"]],
    on=["project_id","sov_line_id"], how="left"
)
df["pct_complete"] = df["pct_complete"].fillna(0)

# ── 5B: Core EVM calculations ─────────────────────────────────────────────────
print("Computing EVM metrics ...")

# Budget At Completion (BAC): total planned cost for this line
df["bac"] = df["estimated_total_cost"]

# Budgeted Cost of Work Performed (BCWP / Earned Value):
# How much cost should have been spent given the % complete achieved
df["earned_value"] = df["bac"] * (df["pct_complete"] / 100)

# Actual Cost of Work Performed (ACWP)
df["actual_cost"] = df["actual_total_cost"]

# Cost Performance Index: earned / actual
# CPI = 1.0 → on budget   |   CPI < 1.0 → over budget   |   CPI > 1.0 → under budget
df["cpi"] = np.where(
    df["actual_cost"] > 0,
    df["earned_value"] / df["actual_cost"],
    np.nan   # no work done yet
)

# Estimate At Completion: if burn rate continues, what will it cost to finish?
df["eac"] = np.where(
    df["pct_complete"] > 0,
    df["actual_cost"] / (df["pct_complete"] / 100),
    df["bac"]   # not started → assume on budget
)

# Variance At Completion: how much over/under budget will the line finish?
df["vac"] = df["bac"] - df["eac"]
df["vac_%"] = (df["vac"] / df["bac"].replace(0, 1) * 100).round(2)

# Labor-specific productivity ratio (hours burn vs progress)
df["labor_productivity_ratio"] = np.where(
    df["actual_labor_hours_total"] > 0,
    (df["pct_complete"] / 100) / (df["actual_labor_hours_total"] / df["estimated_labor_hours"].replace(0, 1)),
    np.nan
)

# ── 5C: Risk flags ─────────────────────────────────────────────────────────────
df["cpi_flag"] = pd.cut(
    df["cpi"].fillna(1.0),
    bins=[-np.inf, 0.70, 0.85, 0.95, 1.05, np.inf],
    labels=["Critical (<0.70)", "At Risk (0.70–0.85)", "Watch (0.85–0.95)",
            "On Track (0.95–1.05)", "Efficient (>1.05)"]
)

df["ot_flag"] = df["ot_ratio_%"] > 25   # OT above 25% → labor cost risk
df["supply_flag"] = df["partial_shipment_rate_%"] > 20  # supply chain risk

# ── 5D: Project-level rollup ───────────────────────────────────────────────────
print("Rolling up to project level ...")

proj = df.groupby("project_id").agg(
    total_bac              = ("bac",           "sum"),
    total_earned_value     = ("earned_value",  "sum"),
    total_actual_cost      = ("actual_cost",   "sum"),
    total_eac              = ("eac",           "sum"),
    total_vac              = ("vac",           "sum"),
    lines_at_risk          = ("cpi_flag",      lambda x: (x.isin(["At Risk (0.70–0.85)","Critical (<0.70)"])).sum()),
    lines_critical         = ("cpi_flag",      lambda x: (x == "Critical (<0.70)").sum()),
    lines_with_ot_flag     = ("ot_flag",       "sum"),
    lines_with_supply_flag = ("supply_flag",   "sum"),
    weighted_avg_pct_complete = ("pct_complete", lambda x: (x * df.loc[x.index,"bac"]).sum() / df.loc[x.index,"bac"].sum()),
).reset_index()

proj["project_cpi"] = (proj["total_earned_value"] / proj["total_actual_cost"].replace(0, 1)).round(4)
proj["project_eac"] = (proj["total_actual_cost"]  / (proj["weighted_avg_pct_complete"] / 100).replace(0, 1)).round(0)
proj["project_vac"] = proj["total_bac"] - proj["project_eac"]
proj["project_vac_%"] = (proj["project_vac"] / proj["total_bac"].replace(0, 1) * 100).round(2)

proj["project_cpi_flag"] = pd.cut(
    proj["project_cpi"],
    bins=[-np.inf, 0.70, 0.85, 0.95, 1.05, np.inf],
    labels=["Critical","At Risk","Watch","On Track","Efficient"]
)

# Merge with master for project name and type
proj = proj.merge(
    master[["project_id","project_name","project_type","gc_name",
            "original_contract_value","revised_contract_value",
            "total_co_count","co_rejection_rate_%"]],
    on="project_id", how="left"
)

# ── Save ───────────────────────────────────────────────────────────────────────
df.to_csv(os.path.join(OUT, "cpi_per_line.csv"), index=False)
proj.to_csv(os.path.join(OUT, "cpi_per_project.csv"), index=False)

# Summary
print(f"\n✓ Step 5 complete.")
print(f"  outputs/cpi_per_line.csv     — {len(df):,} rows")
print(f"  outputs/cpi_per_project.csv  — {len(proj):,} rows")

print(f"\n  Project-level CPI distribution:")
flag_counts = proj["project_cpi_flag"].value_counts()
for flag, cnt in flag_counts.items():
    print(f"    {str(flag):<25} {cnt:>4} projects ({cnt/len(proj)*100:.1f}%)")

print(f"\n  Projects with any Critical lines: {(proj['lines_critical'] > 0).sum()}")
print(f"  Total projected overrun (negative VAC): ${proj[proj['project_vac']<0]['project_vac'].sum():>15,.0f}")

print(f"\n  Worst 10 projects by CPI:")
worst = proj.nsmallest(10, "project_cpi")[["project_id","project_name","project_cpi","project_vac_%","gc_name"]]
print(worst.to_string(index=False))

print(f"\n  Average CPI by project type:")
type_cpi = proj.groupby("project_type")["project_cpi"].agg(["mean","min","max"]).round(3)
print(type_cpi)

print(f"\n  Average CPI by GC:")
gc_cpi = proj.groupby("gc_name")["project_cpi"].agg(["mean","min","max","count"]).round(3)
print(gc_cpi)
