"""
STEP 3 — ACTUAL COST PER SOV LINE
===================================
Purpose:
    For every (project, SOV line) pair, compute what the work actually cost:
      - Labor cost broken down by straight-time and overtime
      - Material cost from deliveries received
      - Rolled-up totals

    This is the most computationally heavy step because labor_logs has 1.2M rows.
    Output is the foundation for Step 5 (Cost Performance Index).

Depends on:
    outputs/labor_logs_clean.csv        ← from Step 1
    outputs/material_deliveries_clean.csv ← from Step 1
    ../sov_all.csv                       (for SOV line descriptions)
    ../sov_budget_all.csv                (for budget benchmarks)

Output:
    outputs/actual_cost_per_line.csv    — one row per (project_id, sov_line_id)
"""

import pandas as pd
import os

BASE = os.path.join(os.path.dirname(__file__), "..")
OUT  = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUT, exist_ok=True)

# ── Load data ─────────────────────────────────────────────────────────────────
print("Loading labor logs (1.2M rows — this takes ~10 seconds) ...")

labor_path = os.path.join(OUT, "labor_logs_clean.csv")
if not os.path.exists(labor_path):
    print("  WARNING: labor_logs_clean.csv not found. Run Step 1 first.")
    print("  Falling back to raw labor_logs_all.csv")
    labor_path = os.path.join(BASE, "labor_logs_all.csv")

labor = pd.read_csv(labor_path, dtype={
    "hours_st": float, "hours_ot": float,
    "hourly_rate": float, "burden_multiplier": float
})

mats_path = os.path.join(OUT, "material_deliveries_clean.csv")
if not os.path.exists(mats_path):
    mats_path = os.path.join(BASE, "material_deliveries_all.csv")
mats = pd.read_csv(mats_path, dtype={"total_cost": float})

sov    = pd.read_csv(os.path.join(BASE, "sov_all.csv"))
budget = pd.read_csv(os.path.join(BASE, "sov_budget_all.csv"))

# ── 3A: Actual labor cost per (project, line) ────────────────────────────────
print("Computing actual labor costs ...")

labor["st_cost"] = labor["hours_st"] * labor["hourly_rate"] * labor["burden_multiplier"]
labor["ot_cost"] = labor["hours_ot"] * labor["hourly_rate"] * 1.5 * labor["burden_multiplier"]
labor["total_labor_cost"] = labor["st_cost"] + labor["ot_cost"]
labor["total_hours"] = labor["hours_st"] + labor["hours_ot"]

labor_agg = labor.groupby(["project_id", "sov_line_id"]).agg(
    actual_labor_hours_st   = ("hours_st",          "sum"),
    actual_labor_hours_ot   = ("hours_ot",           "sum"),
    actual_labor_hours_total = ("total_hours",       "sum"),
    actual_labor_cost_st    = ("st_cost",            "sum"),
    actual_labor_cost_ot    = ("ot_cost",            "sum"),
    actual_labor_cost_total = ("total_labor_cost",   "sum"),
    unique_workers          = ("employee_id",        "nunique"),
).reset_index()

labor_agg["ot_ratio_%"] = (
    labor_agg["actual_labor_hours_ot"]
  / labor_agg["actual_labor_hours_total"].replace(0, 1) * 100
).round(2)

# ── 3B: Actual material cost per (project, line) ─────────────────────────────
print("Computing actual material costs ...")

mats_agg = mats.groupby(["project_id", "sov_line_id"]).agg(
    actual_material_cost       = ("total_cost",   "sum"),
    material_delivery_count    = ("delivery_id",  "count"),
    partial_shipment_count     = ("condition_notes", lambda x: (x == "Partial shipment - backorder pending").sum()),
    damaged_delivery_count     = ("condition_notes", lambda x: (x == "Minor packaging damage - product OK").sum()),
).reset_index()

mats_agg["partial_shipment_rate_%"] = (
    mats_agg["partial_shipment_count"]
  / mats_agg["material_delivery_count"].replace(0, 1) * 100
).round(2)

# ── 3C: Merge labor + materials + SOV metadata + budget ──────────────────────
print("Merging with SOV and budget ...")

# Start from all SOV lines (some lines may have zero actual labor or zero material)
base = sov[["project_id", "sov_line_id", "line_number", "description", "scheduled_value",
            "labor_pct", "material_pct"]].copy()

result = base.merge(labor_agg, on=["project_id", "sov_line_id"], how="left")
result = result.merge(mats_agg,  on=["project_id", "sov_line_id"], how="left")
result = result.merge(
    budget[["project_id", "sov_line_id",
            "estimated_labor_hours", "estimated_labor_cost",
            "estimated_material_cost", "productivity_factor", "key_assumptions"]],
    on=["project_id", "sov_line_id"], how="left"
)

# Fill NaN for lines with no activity yet
fill_zero = [
    "actual_labor_hours_st", "actual_labor_hours_ot", "actual_labor_hours_total",
    "actual_labor_cost_st",  "actual_labor_cost_ot",  "actual_labor_cost_total",
    "unique_workers", "ot_ratio_%",
    "actual_material_cost", "material_delivery_count",
    "partial_shipment_count", "damaged_delivery_count", "partial_shipment_rate_%"
]
result[fill_zero] = result[fill_zero].fillna(0)

# ── 3D: Variance columns ──────────────────────────────────────────────────────
result["labor_hours_variance"]      = result["actual_labor_hours_total"] - result["estimated_labor_hours"]
result["labor_hours_burn_rate_%"]   = (
    result["actual_labor_hours_total"] / result["estimated_labor_hours"].replace(0, 1) * 100
).round(2)

result["labor_cost_variance_$"]     = result["actual_labor_cost_total"] - result["estimated_labor_cost"]
result["material_cost_variance_$"]  = result["actual_material_cost"]    - result["estimated_material_cost"]

result["actual_total_cost"]         = result["actual_labor_cost_total"] + result["actual_material_cost"]
result["estimated_total_cost"]      = result["estimated_labor_cost"]    + result["estimated_material_cost"]
result["total_cost_variance_$"]     = result["actual_total_cost"]       - result["estimated_total_cost"]

# ── Save ──────────────────────────────────────────────────────────────────────
result.to_csv(os.path.join(OUT, "actual_cost_per_line.csv"), index=False)

# Summary
print(f"\n✓ Step 3 complete. Saved: outputs/actual_cost_per_line.csv")
print(f"  Rows: {len(result):,} (project × SOV line combinations)")
print(f"\n  Labor cost summary:")
print(f"    Total actual labor cost:       ${result['actual_labor_cost_total'].sum():>15,.0f}")
print(f"    Total estimated labor cost:    ${result['estimated_labor_cost'].sum():>15,.0f}")
print(f"    Total OT cost:                 ${result['actual_labor_cost_ot'].sum():>15,.0f}")
print(f"    OT as % of total labor cost:    {result['actual_labor_cost_ot'].sum() / result['actual_labor_cost_total'].sum() * 100:.1f}%")
print(f"\n  Material cost summary:")
print(f"    Total actual material cost:    ${result['actual_material_cost'].sum():>15,.0f}")
print(f"    Total estimated material cost: ${result['estimated_material_cost'].sum():>15,.0f}")
print(f"\n  Lines with OT ratio > 25%: {(result['ot_ratio_%'] > 25).sum()}")
print(f"  Lines with partial shipment rate > 20%: {(result['partial_shipment_rate_%'] > 20).sum()}")
print(f"\n  Top 5 lines by total actual cost:")
top5 = result.groupby("description")["actual_total_cost"].sum().sort_values(ascending=False).head(5)
for desc, cost in top5.items():
    print(f"    {desc:<45} ${cost:>15,.0f}")
