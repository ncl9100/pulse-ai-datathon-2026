"""
Step 5 — Score Project Efficiency (CPI / Earned Value)
========================================================
Earned Value formulas:
  EV  = BAC × (pct_complete / 100)
  CPI = EV / Actual Cost
  EAC = Actual Cost / (pct_complete / 100)
  VAC = BAC − EAC

CPI status bands:
  ≥ 1.15   Efficient
  1.0–1.15 On Track
  0.85–1.0 Watch
  0.75–0.85 At Risk
  < 0.75   Critical

Outputs
-------
cpi_per_line.csv
cpi_per_project.csv
"""

import pandas as pd
import numpy as np
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

print("Loading inputs …")
actual   = pd.read_csv(os.path.join(OUT_DIR, "actual_cost_per_line.csv"),  low_memory=False)
progress = pd.read_csv(os.path.join(OUT_DIR, "billing_progress.csv"),      low_memory=False)
sov      = pd.read_csv(os.path.join(DATA_DIR, "sov_all.csv"),              low_memory=False)

# BAC per line = scheduled_value from sov_all (authoritative source)
bac = sov[["project_id", "sov_line_id", "scheduled_value"]].rename(
    columns={"scheduled_value": "bac"}
)

# ── Line-level EV ────────────────────────────────────────────────
print("Computing line-level earned value …")
ev = bac.merge(
    progress[["project_id", "sov_line_id", "pct_complete"]
             + (["pct_manually_adjusted"] if "pct_manually_adjusted" in progress.columns else [])],
    on=["project_id", "sov_line_id"], how="left"
)
ev = ev.merge(
    actual[["project_id", "sov_line_id", "total_actual_cost",
            "actual_labor_cost", "actual_material_cost",
            "ot_ratio_pct", "cost_variance_usd"]],
    on=["project_id", "sov_line_id"], how="left"
)

ev["pct_complete"]      = ev["pct_complete"].fillna(0)
ev["total_actual_cost"] = ev["total_actual_cost"].fillna(0)
ev["earned_value"]      = ev["bac"] * (ev["pct_complete"] / 100)

with np.errstate(divide="ignore", invalid="ignore"):
    ev["cpi"] = np.where(
        ev["total_actual_cost"] > 0,
        ev["earned_value"] / ev["total_actual_cost"],
        np.nan
    )
    ev["eac"] = np.where(
        ev["pct_complete"] > 0,
        ev["total_actual_cost"] / (ev["pct_complete"] / 100),
        np.nan
    )

ev["vac"] = ev["bac"] - ev["eac"]

def cpi_status(cpi):
    if pd.isna(cpi):    return "No Cost Yet"
    elif cpi >= 1.15:   return "Efficient"
    elif cpi >= 1.0:    return "On Track"
    elif cpi >= 0.85:   return "Watch"
    elif cpi >= 0.75:   return "At Risk"
    else:               return "Critical"

ev["cpi_status"] = ev["cpi"].apply(cpi_status)
ev.to_csv(os.path.join(OUT_DIR, "cpi_per_line.csv"), index=False)

# ── Project-level rollup (weighted by BAC) ───────────────────────
print("Rolling up to project level …")
proj_ev = ev.groupby("project_id").agg(
    total_bac=("bac", "sum"),
    total_earned_value=("earned_value", "sum"),
    total_actual_cost=("total_actual_cost", "sum"),
    lines_total=("sov_line_id", "count"),
    lines_complete=("pct_complete", lambda x: (x >= 99.5).sum()),
    avg_pct_complete=("pct_complete", "mean"),
).reset_index()

with np.errstate(divide="ignore", invalid="ignore"):
    proj_ev["project_cpi"] = np.where(
        proj_ev["total_actual_cost"] > 0,
        proj_ev["total_earned_value"] / proj_ev["total_actual_cost"],
        np.nan
    )
    proj_ev["project_eac"] = np.where(
        proj_ev["avg_pct_complete"] > 0,
        proj_ev["total_actual_cost"] / (proj_ev["avg_pct_complete"] / 100),
        np.nan
    )

proj_ev["project_vac"]    = proj_ev["total_bac"] - proj_ev["project_eac"]
proj_ev["project_status"] = proj_ev["project_cpi"].apply(cpi_status)

proj_ev.to_csv(os.path.join(OUT_DIR, "cpi_per_project.csv"), index=False)

status_counts = proj_ev["project_status"].value_counts()
print(f"\n   Projects: {len(proj_ev)}")
print("   Status breakdown:")
print(status_counts.to_string())
print(f"\n   Portfolio avg CPI:  {proj_ev['project_cpi'].mean():.3f}")
print(f"   Total BAC:          ${proj_ev['total_bac'].sum():,.0f}")
print(f"   Total actual cost:  ${proj_ev['total_actual_cost'].sum():,.0f}")

print("\n✓ Step 5 complete → cpi_per_line.csv, cpi_per_project.csv")
