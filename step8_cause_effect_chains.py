"""
STEP 8 — CAUSE-AND-EFFECT CHAINS
==================================
Purpose:
    The worst-performing projects (by CPI from Step 5) need a specific explanation
    for why they went over budget. This step tests five causal chains against every
    project in the bottom 20% of CPI and produces a per-project diagnosis.

    The five chains are:
      A. Design Incomplete at Bid   → Scope Gap / Design Error COs → rework labor
      B. Material Shortage           → Idle Labor → Acceleration CO → OT premium
      C. Slow RFI Response           → Standby labor → Unrecovered schedule impact
      D. Rejected Change Order       → Unrecovered labor cost
      E. High Early CO Volume        → Leading indicator of project-wide distress

    For each chain, the script quantifies the estimated financial impact in dollars
    so findings can be ranked by severity.

Depends on:
    outputs/cpi_per_project.csv          ← from Step 5
    outputs/actual_cost_per_line.csv     ← from Step 3
    outputs/change_orders_clean.csv      ← from Step 1
    outputs/change_orders_exploded.csv   ← from Step 1
    ../rfis_all.csv
    outputs/material_deliveries_clean.csv ← from Step 1
    ../labor_logs_all.csv                (uses clean if available)
    outputs/project_master.csv           ← from Step 2

Output:
    outputs/cause_effect_diagnosis.csv   — per-project chain scores and estimated impacts
    outputs/chain_A_design_rework.csv
    outputs/chain_B_material_idle.csv
    outputs/chain_C_rfi_standby.csv
    outputs/chain_D_rejected_co_loss.csv
    outputs/chain_E_early_cos.csv
"""

import pandas as pd
import numpy as np
import ast
import os

BASE = os.path.join(os.path.dirname(__file__), "..")
OUT  = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUT, exist_ok=True)

# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading data ...")
cpi_proj  = pd.read_csv(os.path.join(OUT, "cpi_per_project.csv"))
act_cost  = pd.read_csv(os.path.join(OUT, "actual_cost_per_line.csv"))
master    = pd.read_csv(os.path.join(OUT, "project_master.csv"),
                        parse_dates=["contract_date","substantial_completion_date"])
rfis      = pd.read_csv(os.path.join(BASE, "rfis_all.csv"),
                        parse_dates=["date_submitted","date_required","date_responded"])

cos_path  = os.path.join(OUT, "change_orders_clean.csv")
cos       = pd.read_csv(cos_path, parse_dates=["date_submitted"])
cos["amount_float"] = pd.to_numeric(cos["amount"], errors="coerce").fillna(0)
cos["labor_hours_impact_f"] = pd.to_numeric(cos["labor_hours_impact"], errors="coerce").fillna(0)
cos["schedule_impact_days_f"] = pd.to_numeric(cos["schedule_impact_days"], errors="coerce").fillna(0)

mats_path = os.path.join(OUT, "material_deliveries_clean.csv")
mats      = pd.read_csv(mats_path)

# Use bottom 30% of projects by CPI as the focus set (include all if preferred)
# Set to None to run on all projects
cpi_threshold = cpi_proj["project_cpi"].quantile(0.30)
focus_projects = cpi_proj[cpi_proj["project_cpi"] <= cpi_threshold]["project_id"].tolist()
print(f"  Focus: bottom 30% of projects by CPI ({len(focus_projects)} projects, CPI ≤ {cpi_threshold:.3f})")

# ── CHAIN A: Design Incomplete → Rework Labor ─────────────────────────────────
print("\nChain A: Design rework from Scope Gap / Design Error COs ...")
chain_a_cos = cos[
    cos["reason_category"].isin(["Scope Gap","Design Error"])
].copy()

chain_a = chain_a_cos.groupby("project_id").agg(
    design_co_count         = ("co_number",    "count"),
    approved_design_co_usd    = ("amount_float", lambda x: x[cos.loc[x.index,"status"] == "Approved"].sum()),
    rejected_design_co_usd    = ("amount_float", lambda x: x[(cos.loc[x.index,"status"] == "Rejected") & (x > 0)].sum()),
    design_co_labor_hours   = ("labor_hours_impact_f", "sum"),
).reset_index()

# Estimate labor cost of rework using average burdened rate from act_cost
avg_rate = (
    act_cost[act_cost["actual_labor_hours_total"] > 0]["actual_labor_cost_total"].sum()
  / act_cost[act_cost["actual_labor_hours_total"] > 0]["actual_labor_hours_total"].sum()
)
chain_a["design_rework_estimated_cost_usd"] = chain_a["design_co_labor_hours"] * avg_rate
chain_a["chain_A_net_loss_usd"] = chain_a["rejected_design_co_usd"] + chain_a["design_rework_estimated_cost_usd"]
chain_a.to_csv(os.path.join(OUT, "chain_A_design_rework.csv"), index=False)

# ── CHAIN B: Material Shortages → Idle Labor ─────────────────────────────────
print("Chain B: Material shortage idle labor ...")
partial_deliveries = mats[mats["condition_notes"] == "Partial shipment - backorder pending"].copy()

chain_b = partial_deliveries.groupby("project_id").agg(
    partial_delivery_count  = ("delivery_id",   "count"),
    affected_sov_lines      = ("sov_line_id",   lambda x: list(x.unique())),
).reset_index()

# Acceleration COs are the financial consequence: add their approved values
accel_cos = cos[cos["reason_category"] == "Acceleration"].groupby("project_id").agg(
    acceleration_co_count    = ("co_number",    "count"),
    acceleration_approved_usd  = ("amount_float", lambda x: x[cos.loc[x.index,"status"] == "Approved"].sum()),
    acceleration_rejected_usd  = ("amount_float", lambda x: x[(cos.loc[x.index,"status"] == "Rejected") & (x > 0)].sum()),
    acceleration_ot_hours    = ("labor_hours_impact_f", "sum"),
).reset_index()

chain_b = chain_b.merge(accel_cos, on="project_id", how="left").fillna(0)
chain_b["chain_B_ot_premium_usd"] = chain_b["acceleration_ot_hours"] * avg_rate * 0.50
# 0.50 = the extra 50% cost of OT hours vs standard time
chain_b.to_csv(os.path.join(OUT, "chain_B_material_idle.csv"), index=False)

# ── CHAIN C: Slow RFI Response → Standby Labor Cost ─────────────────────────
print("Chain C: RFI response lag standby cost ...")
rfis["response_lag_days"] = (rfis["date_responded"] - rfis["date_required"]).dt.days
rfis_closed = rfis[rfis["status"] == "Closed"].copy()

# Late = responded after deadline
late_rfis = rfis_closed[rfis_closed["response_lag_days"] > 0].copy()
late_rfis_with_impact = late_rfis[late_rfis["schedule_impact"] == True]

# Estimate standby cost: response_lag_days × typical daily crew cost
# Daily crew cost approximated as avg burdened hourly rate × 8 hours × 5 workers
daily_crew_cost = avg_rate * 8 * 5

chain_c = late_rfis.groupby("project_id").agg(
    late_rfi_count           = ("rfi_number",         "count"),
    late_rfi_with_schedule   = ("schedule_impact",    lambda x: (x == True).sum()),
    late_rfi_with_cost       = ("cost_impact",        lambda x: (x == True).sum()),
    total_excess_lag_days    = ("response_lag_days",  "sum"),
).reset_index()

chain_c["estimated_standby_cost_usd"] = chain_c["total_excess_lag_days"] * daily_crew_cost
chain_c.to_csv(os.path.join(OUT, "chain_C_rfi_standby.csv"), index=False)

# ── CHAIN D: Rejected COs → Unrecovered Labor ────────────────────────────────
print("Chain D: Rejected CO labor loss ...")
rejected_pos = cos[(cos["status"] == "Rejected") & (cos["amount_float"] > 0)].copy()

chain_d = rejected_pos.groupby("project_id").agg(
    rejected_co_count        = ("co_number",            "count"),
    rejected_co_total_usd      = ("amount_float",         "sum"),
    rejected_co_labor_hours  = ("labor_hours_impact_f", "sum"),
    rejected_schedule_days   = ("schedule_impact_days_f","sum"),
).reset_index()

chain_d["rejected_labor_cost_usd"] = chain_d["rejected_co_labor_hours"] * avg_rate
chain_d["chain_D_total_loss_usd"]  = chain_d["rejected_co_total_usd"]
chain_d.to_csv(os.path.join(OUT, "chain_D_rejected_co_loss.csv"), index=False)

# ── CHAIN E: High Early CO Volume → Project Distress Signal ──────────────────
print("Chain E: Early CO volume as distress predictor ...")
cos_with_timing = cos.merge(
    master[["project_id","contract_date","original_duration_days"]],
    on="project_id", how="left"
)
cos_with_timing["days_from_start"] = (
    cos_with_timing["date_submitted"] - cos_with_timing["contract_date"]
).dt.days
cos_with_timing["in_first_20pct"] = (
    cos_with_timing["days_from_start"] / cos_with_timing["original_duration_days"].replace(0,1)
) <= 0.20

chain_e = cos_with_timing.groupby("project_id").agg(
    total_co_count           = ("co_number",       "count"),
    early_co_count           = ("in_first_20pct",  "sum"),
    early_co_approved_usd      = ("amount_float",    lambda x: x[(cos_with_timing.loc[x.index,"in_first_20pct"]) & (cos_with_timing.loc[x.index,"status"] == "Approved")].sum()),
    early_co_rejected_usd      = ("amount_float",    lambda x: x[(cos_with_timing.loc[x.index,"in_first_20pct"]) & (cos_with_timing.loc[x.index,"status"] == "Rejected") & (x > 0)].sum()),
).reset_index()
chain_e["early_co_rate_%"] = (
    chain_e["early_co_count"] / chain_e["total_co_count"].replace(0,1) * 100
).round(2)
chain_e.to_csv(os.path.join(OUT, "chain_E_early_cos.csv"), index=False)

# ── Master diagnosis table ────────────────────────────────────────────────────
print("\nBuilding master diagnosis table ...")
diag = cpi_proj[["project_id","project_name","project_type","gc_name","project_cpi","project_cpi_flag","project_vac_%"]].copy()

diag = (diag
    .merge(chain_a[["project_id","design_co_count","chain_A_net_loss_usd"]], on="project_id", how="left")
    .merge(chain_b[["project_id","partial_delivery_count","chain_B_ot_premium_usd"]], on="project_id", how="left")
    .merge(chain_c[["project_id","late_rfi_count","estimated_standby_cost_usd"]], on="project_id", how="left")
    .merge(chain_d[["project_id","rejected_co_count","chain_D_total_loss_usd"]], on="project_id", how="left")
    .merge(chain_e[["project_id","early_co_count","early_co_rate_%"]], on="project_id", how="left")
).fillna(0)

diag["total_estimated_loss_usd"] = (
    diag["chain_A_net_loss_usd"]
  + diag["chain_B_ot_premium_usd"]
  + diag["estimated_standby_cost_usd"]
  + diag["chain_D_total_loss_usd"]
)

# Primary cause: which chain has the highest estimated loss
loss_cols = {
    "chain_A_net_loss_usd":       "A: Design Rework",
    "chain_B_ot_premium_usd":     "B: Material Shortage / OT",
    "estimated_standby_cost_usd": "C: RFI Standby",
    "chain_D_total_loss_usd":     "D: Rejected CO",
}
diag["primary_cause"] = diag[list(loss_cols.keys())].idxmax(axis=1).map(loss_cols)

diag.to_csv(os.path.join(OUT, "cause_effect_diagnosis.csv"), index=False)

# Summary
print(f"\n✓ Step 8 complete.")
print(f"  outputs/cause_effect_diagnosis.csv  — {len(diag)} projects diagnosed")
print(f"\n  Most common primary cause of loss:")
print(diag["primary_cause"].value_counts())
print(f"\n  Total estimated loss breakdown:")
for col, label in loss_cols.items():
    print(f"    {label:<30} ${diag[col].sum():>15,.0f}")
print(f"  {'Total':<30} ${diag['total_estimated_loss_usd'].sum():>15,.0f}")
