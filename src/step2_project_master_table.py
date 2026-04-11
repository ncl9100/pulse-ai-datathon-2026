"""
Step 2 — Build the Project Master Table
========================================
One row per project. Real column names:
  contracts:   project_id, project_name, original_contract_value,
               contract_date, substantial_completion_date,
               retention_pct, payment_terms, gc_name, architect, engineer_of_record
  sov_all:     project_id, sov_line_id, line_number, description,
               scheduled_value, labor_pct, material_pct
  sov_budget:  project_id, sov_line_id, estimated_labor_hours,
               estimated_labor_cost, estimated_material_cost,
               estimated_equipment_cost, estimated_sub_cost
  change_orders_clean: project_id, co_number, date_submitted,
               reason_category, description, amount, status, ...

Outputs
-------
project_master.csv
"""

import pandas as pd
import numpy as np
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

print("Loading files …")
contracts  = pd.read_csv(os.path.join(DATA_DIR, "contracts_all.csv"),      low_memory=False)
sov        = pd.read_csv(os.path.join(DATA_DIR, "sov_all.csv"),            low_memory=False)
sov_budget = pd.read_csv(os.path.join(DATA_DIR, "sov_budget_all.csv"),     low_memory=False)
co_clean   = pd.read_csv(os.path.join(OUT_DIR,  "change_orders_clean.csv"),low_memory=False)

# ── Contract base ───────────────────────────────────────────────
print("Processing contracts …")
contracts["contract_date"] = pd.to_datetime(contracts["contract_date"], errors="coerce")
contracts["substantial_completion_date"] = pd.to_datetime(
    contracts["substantial_completion_date"], errors="coerce"
)
contracts["original_duration_days"] = (
    contracts["substantial_completion_date"] - contracts["contract_date"]
).dt.days

def classify_project(val):
    if val < 5_000_000:    return "Small"
    elif val < 20_000_000: return "Medium"
    elif val < 50_000_000: return "Large"
    else:                  return "Mega"

contracts["project_type"] = contracts["original_contract_value"].apply(classify_project)

# ── SOV totals — scheduled_value is the authoritative budget ────
print("Aggregating SOV …")
sov_totals = sov.groupby("project_id")["scheduled_value"].sum().reset_index()
sov_totals.columns = ["project_id", "sov_total_scheduled_value"]

# ── SOV budget — estimated costs ────────────────────────────────
print("Aggregating SOV budget …")
budget_totals = sov_budget.groupby("project_id").agg(
    estimated_labor_cost=("estimated_labor_cost", "sum"),
    estimated_material_cost=("estimated_material_cost", "sum"),
    estimated_equipment_cost=("estimated_equipment_cost", "sum"),
    estimated_sub_cost=("estimated_sub_cost", "sum"),
).reset_index()
budget_totals["total_estimated_cost"] = (
    budget_totals["estimated_labor_cost"]
    + budget_totals["estimated_material_cost"]
    + budget_totals["estimated_equipment_cost"]
    + budget_totals["estimated_sub_cost"]
)

# ── Change order summary ─────────────────────────────────────────
print("Summarizing change orders …")
# co_number is the ID, reason_category is the reason column
approved_mask = co_clean["status"] == "Approved"
rejected_mask = co_clean["status"] == "Rejected"

co_summary = co_clean.groupby("project_id").agg(
    total_cos=("co_number", "count"),
    approved_cos=("status", lambda x: (x == "Approved").sum()),
    rejected_cos=("status", lambda x: (x == "Rejected").sum()),
    total_co_value=("amount", "sum"),
).reset_index()

approved_vals = (
    co_clean[approved_mask]
    .groupby("project_id")["amount"].sum()
    .reset_index()
    .rename(columns={"amount": "approved_co_value"})
)
rejected_vals = (
    co_clean[rejected_mask]
    .groupby("project_id")["amount"].sum()
    .reset_index()
    .rename(columns={"amount": "rejected_co_value"})
)
design_cos = (
    co_clean[co_clean["reason_category"].isin(["Design Error", "Scope Gap"])]
    .groupby("project_id").size()
    .reset_index(name="upstream_design_cos")
)

co_summary = (co_summary
              .merge(approved_vals, on="project_id", how="left")
              .merge(rejected_vals, on="project_id", how="left")
              .merge(design_cos,    on="project_id", how="left"))

co_summary["co_rejection_rate_pct"] = (
    co_summary["rejected_cos"] / co_summary["total_cos"].replace(0, np.nan) * 100
).round(1)
co_summary["upstream_design_co_pct"] = (
    co_summary["upstream_design_cos"].fillna(0)
    / co_summary["total_cos"].replace(0, np.nan) * 100
).round(1)

# ── Join everything ─────────────────────────────────────────────
print("Joining …")
master = (contracts
          .merge(sov_totals,    on="project_id", how="left")
          .merge(budget_totals, on="project_id", how="left")
          .merge(co_summary,    on="project_id", how="left"))

# ── Derived metrics ──────────────────────────────────────────────
master["revised_contract_value"] = (
    master["original_contract_value"] + master["approved_co_value"].fillna(0)
)
master["builtin_margin_usd"] = (
    master["original_contract_value"] - master["total_estimated_cost"]
)
master["builtin_margin_pct"] = (
    master["builtin_margin_usd"]
    / master["original_contract_value"].replace(0, np.nan) * 100
).round(2)

print(f"\n✓ Project master: {len(master)} projects, {master.shape[1]} columns")
print(f"   Avg built-in margin:      {master['builtin_margin_pct'].mean():.1f}%")
print(f"   Projects under 5% margin: {(master['builtin_margin_pct'] < 5).sum()}")
print("\n   Project type breakdown:")
print(master["project_type"].value_counts().to_string())

master.to_csv(os.path.join(OUT_DIR, "project_master.csv"), index=False)
print("\n✓ Step 2 complete → outputs/project_master.csv")
