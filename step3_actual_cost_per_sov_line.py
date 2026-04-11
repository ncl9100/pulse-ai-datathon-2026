"""
Step 3 — Calculate What It Actually Cost
==========================================
labor_logs real columns:
  project_id, log_id, date, employee_id, role, sov_line_id,
  hours_st, hours_ot, hourly_rate, burden_multiplier, work_area
  (cost_code was dropped in Step 1)

material_deliveries real columns:
  project_id, delivery_id, date, sov_line_id, material_category,
  item_description, quantity, unit, unit_cost, total_cost,
  po_number, vendor, received_by, condition_notes

Outputs
-------
actual_cost_per_line.csv
"""

import pandas as pd
import numpy as np
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Labor ────────────────────────────────────────────────────────
print("Loading labor_logs_clean …")
ll = pd.read_csv(os.path.join(OUT_DIR, "labor_logs_clean.csv"), low_memory=False)
print(f"   {len(ll):,} rows")

# burden_multiplier is already in the raw data per row
ll["st_cost"]          = ll["hours_st"] * ll["hourly_rate"] * ll["burden_multiplier"]
ll["ot_cost"]          = ll["hours_ot"] * ll["hourly_rate"] * 1.5 * ll["burden_multiplier"]
ll["total_labor_cost"] = ll["st_cost"] + ll["ot_cost"]
ll["total_hours"]      = ll["hours_st"] + ll["hours_ot"]

labor_agg = ll.groupby(["project_id", "sov_line_id"]).agg(
    actual_labor_cost=("total_labor_cost", "sum"),
    total_hours=("total_hours", "sum"),
    total_ot_hours=("hours_ot", "sum"),
    worker_count=("employee_id", "nunique"),
).reset_index()

labor_agg["ot_ratio_pct"] = (
    labor_agg["total_ot_hours"] / labor_agg["total_hours"].replace(0, np.nan) * 100
).round(2)

print(f"   → {len(labor_agg):,} project/line combinations")

# ── Materials ────────────────────────────────────────────────────
print("Loading material_deliveries_clean …")
md = pd.read_csv(os.path.join(OUT_DIR, "material_deliveries_clean.csv"), low_memory=False)
print(f"   {len(md):,} rows")

# Detect partial shipments from condition_notes
if "condition_notes" in md.columns:
    md["is_partial"] = (
        md["condition_notes"].str.lower().str.contains("partial", na=False)
    )
else:
    md["is_partial"] = False

mat_agg = md.groupby(["project_id", "sov_line_id"]).agg(
    actual_material_cost=("total_cost", "sum"),
    delivery_count=("delivery_id", "count"),
    partial_deliveries=("is_partial", "sum"),
).reset_index()

mat_agg["partial_shipment_rate_pct"] = (
    mat_agg["partial_deliveries"] / mat_agg["delivery_count"].replace(0, np.nan) * 100
).round(2)

print(f"   → {len(mat_agg):,} project/line combinations")

# ── Budget per line ──────────────────────────────────────────────
print("Loading SOV budget …")
sov_budget = pd.read_csv(os.path.join(DATA_DIR, "sov_budget_all.csv"), low_memory=False)
budget_per_line = sov_budget[
    ["project_id", "sov_line_id", "estimated_labor_cost", "estimated_material_cost"]
].copy()
budget_per_line["total_budget"] = (
    budget_per_line["estimated_labor_cost"] + budget_per_line["estimated_material_cost"]
)

# ── Merge ────────────────────────────────────────────────────────
print("Merging …")
actual = labor_agg.merge(mat_agg, on=["project_id", "sov_line_id"], how="outer")
actual["actual_labor_cost"]    = actual["actual_labor_cost"].fillna(0)
actual["actual_material_cost"] = actual["actual_material_cost"].fillna(0)
actual["total_actual_cost"]    = actual["actual_labor_cost"] + actual["actual_material_cost"]

actual = actual.merge(budget_per_line, on=["project_id", "sov_line_id"], how="left")

actual["cost_variance_usd"] = actual["total_budget"] - actual["total_actual_cost"]
actual["cost_variance_pct"] = (
    actual["cost_variance_usd"] / actual["total_budget"].replace(0, np.nan) * 100
).round(2)

print(f"\n   Final: {len(actual):,} project/line rows")
print(f"   Over-budget lines: {(actual['cost_variance_usd'] < 0).sum():,}")
print(f"   Total actual cost: ${actual['total_actual_cost'].sum():,.0f}")

actual.to_csv(os.path.join(OUT_DIR, "actual_cost_per_line.csv"), index=False)
print("\n✓ Step 3 complete → outputs/actual_cost_per_line.csv")
