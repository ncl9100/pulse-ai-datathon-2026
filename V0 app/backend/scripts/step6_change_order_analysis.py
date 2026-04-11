"""
STEP 6 — CHANGE ORDER ANALYSIS
================================
Purpose:
    Change orders are where the contract diverges from the original plan.
    This step examines:
      1. Revenue recovery: how much additional revenue was approved vs. lost to rejection
      2. GC behavior: which General Contractors reject the most COs (adversarial clients)
      3. Root cause patterns: which reason categories drive the most cost impact
      4. RFI-to-CO conversion: of all RFIs flagged as cost_impact=True, how many
         became approved COs vs. going unrecovered
      5. Timing: how many COs were submitted early (first 20% of project duration),
         which is an early warning signal for design completeness problems

Depends on:
    outputs/change_orders_clean.csv    ← from Step 1
    outputs/change_orders_exploded.csv ← from Step 1
    ../rfis_all.csv
    outputs/project_master.csv         ← from Step 2

Output:
    outputs/co_analysis_by_project.csv   — project-level CO summary
    outputs/co_analysis_by_gc.csv        — GC-level rejection and loss patterns
    outputs/co_rfi_recovery.csv          — RFI cost-impact vs. CO approval matching
    outputs/co_timing.csv                — early vs. late CO submission analysis
"""

import pandas as pd
import ast
import os
from datetime import timedelta

BASE = os.path.join(os.path.dirname(__file__), "..")
OUT  = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUT, exist_ok=True)

# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading data ...")
cos    = pd.read_csv(os.path.join(OUT, "change_orders_clean.csv"), parse_dates=["date_submitted"])
rfis   = pd.read_csv(os.path.join(BASE, "rfis_all.csv"), parse_dates=["date_submitted","date_required","date_responded"])
master = pd.read_csv(os.path.join(OUT, "project_master.csv"), parse_dates=["contract_date","substantial_completion_date"])

cos["amount_float"] = pd.to_numeric(cos["amount"], errors="coerce").fillna(0)
cos["schedule_impact_days_float"] = pd.to_numeric(cos["schedule_impact_days"], errors="coerce").fillna(0)

# ── 6A: Revenue recovery by project ──────────────────────────────────────────
print("Computing CO revenue recovery ...")
proj_co = cos.merge(
    master[["project_id","project_type","gc_name","original_contract_value","original_duration_days","contract_date"]],
    on="project_id", how="left"
)

# CO value as % of original contract
proj_co["co_as_pct_of_contract"] = (
    proj_co["amount_float"] / proj_co["original_contract_value"] * 100
)

# For each project: approved revenue, rejected loss, rejection rate, schedule growth
co_by_project = proj_co.groupby("project_id").apply(lambda df: pd.Series({
    "total_co_count":            len(df),
    "approved_co_count":         (df["status"] == "Approved").sum(),
    "rejected_co_count":         (df["status"] == "Rejected").sum(),
    "approved_co_revenue_$":     df.loc[df["status"] == "Approved",  "amount_float"].sum(),
    "rejected_co_loss_$":        df.loc[(df["status"] == "Rejected") & (df["amount_float"] > 0), "amount_float"].sum(),
    "ve_reduction_$":            abs(df.loc[df["reason_category"] == "Value Engineering", "amount_float"].sum()),
    "total_approved_schedule_days": df.loc[df["status"] == "Approved", "schedule_impact_days_float"].sum(),
    "co_rejection_rate_%":       (df["status"] == "Rejected").sum() / len(df) * 100,
})).reset_index()

co_by_project = co_by_project.merge(
    master[["project_id","project_name","project_type","gc_name",
            "original_contract_value","original_duration_days"]],
    on="project_id", how="left"
)

co_by_project["co_loss_rate_%"] = (
    co_by_project["rejected_co_loss_$"]
  / (co_by_project["approved_co_revenue_$"] + co_by_project["rejected_co_loss_$"]).replace(0,1)
  * 100
).round(2)

# ── 6B: GC-level rejection analysis ──────────────────────────────────────────
print("Analysing GC rejection patterns ...")
gc_analysis = proj_co.groupby("gc_name").apply(lambda df: pd.Series({
    "total_cos":             len(df),
    "approved":              (df["status"] == "Approved").sum(),
    "rejected":              (df["status"] == "Rejected").sum(),
    "total_approved_$":      df.loc[df["status"] == "Approved", "amount_float"].sum(),
    "total_rejected_$":      df.loc[(df["status"] == "Rejected") & (df["amount_float"] > 0), "amount_float"].sum(),
    "rejection_rate_%":      (df["status"] == "Rejected").sum() / len(df) * 100,
    "avg_approval_amount_$": df.loc[df["status"] == "Approved", "amount_float"].mean(),
    "avg_rejection_amount_$":df.loc[(df["status"] == "Rejected") & (df["amount_float"] > 0), "amount_float"].mean(),
})).reset_index().round(2)

# ── 6C: RFI → CO recovery gap ─────────────────────────────────────────────────
print("Matching RFIs to change orders ...")

# RFIs that flagged cost impact
cost_rfis = rfis[rfis["cost_impact"] == True].copy()

# COs that reference an RFI
cos_with_rfi = cos[cos["related_rfi"].notna() & (cos["related_rfi"] != "")].copy()
cos_with_rfi["rfi_ref"] = cos_with_rfi["related_rfi"].str.strip()

# Merge to find which cost-impact RFIs have a matching approved CO
cost_rfis["rfi_has_approved_co"] = cost_rfis.apply(
    lambda row: any(
        (cos_with_rfi["project_id"] == row["project_id"]) &
        (cos_with_rfi["rfi_ref"] == row["rfi_number"]) &
        (cos_with_rfi["status"] == "Approved")
    ), axis=1
)

rfi_recovery = cost_rfis.groupby("project_id").agg(
    cost_impact_rfi_count        = ("rfi_number",         "count"),
    rfi_with_approved_co         = ("rfi_has_approved_co", "sum"),
).reset_index()
rfi_recovery["rfi_unrecovered_count"] = (
    rfi_recovery["cost_impact_rfi_count"] - rfi_recovery["rfi_with_approved_co"]
)
rfi_recovery["recovery_rate_%"] = (
    rfi_recovery["rfi_with_approved_co"] / rfi_recovery["cost_impact_rfi_count"] * 100
).round(2)

rfi_recovery = rfi_recovery.merge(
    master[["project_id","project_name","gc_name","project_type"]],
    on="project_id", how="left"
)

# ── 6D: CO timing analysis (early vs. late) ───────────────────────────────────
print("Analysing CO submission timing ...")
proj_co["days_from_start"] = (
    proj_co["date_submitted"] - proj_co["contract_date"]
).dt.days

proj_co["project_stage"] = pd.cut(
    proj_co["days_from_start"] / proj_co["original_duration_days"].replace(0, 1),
    bins=[0, 0.20, 0.50, 0.80, float("inf")],
    labels=["Early (0–20%)", "Mid (20–50%)", "Late (50–80%)", "Closeout (80%+)"]
)

timing = proj_co.groupby(["project_id","project_stage"], observed=True).agg(
    co_count           = ("co_number",    "count"),
    approved_count     = ("status",       lambda x: (x == "Approved").sum()),
    rejected_count     = ("status",       lambda x: (x == "Rejected").sum()),
    total_amount_usd   = ("amount_float", "sum"),
).reset_index()

# ── Save ──────────────────────────────────────────────────────────────────────
co_by_project.to_csv(os.path.join(OUT, "co_analysis_by_project.csv"), index=False)
gc_analysis.to_csv(  os.path.join(OUT, "co_analysis_by_gc.csv"),      index=False)
rfi_recovery.to_csv( os.path.join(OUT, "co_rfi_recovery.csv"),        index=False)
timing.to_csv(        os.path.join(OUT, "co_timing.csv"),              index=False)

# Summary
print(f"\n✓ Step 6 complete.")
print(f"  outputs/co_analysis_by_project.csv  — {len(co_by_project)} projects")
print(f"  outputs/co_analysis_by_gc.csv        — {len(gc_analysis)} GCs")
print(f"  outputs/co_rfi_recovery.csv          — {len(rfi_recovery)} projects")
print(f"  outputs/co_timing.csv               — {len(timing)} stage breakdowns")

print(f"\n  GC rejection rates:")
print(gc_analysis[["gc_name","total_cos","rejection_rate_%","total_rejected_$"]].to_string(index=False))

print(f"\n  RFI cost recovery:")
total_cost_rfis   = rfi_recovery["cost_impact_rfi_count"].sum()
total_recovered   = rfi_recovery["rfi_with_approved_co"].sum()
total_unrecovered = rfi_recovery["rfi_unrecovered_count"].sum()
print(f"    Total RFIs with cost_impact=True:        {total_cost_rfis:,}")
print(f"    RFIs matched to approved CO:             {total_recovered:,} ({total_recovered/total_cost_rfis*100:.1f}%)")
print(f"    Unrecovered cost-impact RFIs:            {total_unrecovered:,} ({total_unrecovered/total_cost_rfis*100:.1f}%)")

print(f"\n  CO stage distribution:")
stage_total = timing.groupby("project_stage", observed=True)["co_count"].sum()
print(stage_total)
