"""
STEP 2 — PROJECT MASTER TABLE
==============================
Purpose:
    Build one definitive row per project that combines the most important
    summary figures from contracts, sov_budget, and change_orders. Every
    subsequent step joins back to this table.

    The master table answers two questions at a glance:
      1. What did we promise? (contract value, duration, estimated cost, built-in margin)
      2. What changed? (approved COs, revised contract value, schedule growth)

Depends on:
    ../contracts_all.csv
    ../sov_all.csv
    ../sov_budget_all.csv
    outputs/change_orders_clean.csv   ← from Step 1

Output:
    outputs/project_master.csv
"""

import pandas as pd
import ast
import os

BASE = os.path.join(os.path.dirname(__file__), "..")
OUT  = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUT, exist_ok=True)

# ── Load inputs ───────────────────────────────────────────────────────────────
print("Loading data ...")
contracts = pd.read_csv(os.path.join(BASE, "contracts_all.csv"), parse_dates=["contract_date","substantial_completion_date"])
sov       = pd.read_csv(os.path.join(BASE, "sov_all.csv"))
budget    = pd.read_csv(os.path.join(BASE, "sov_budget_all.csv"))

# Use change_orders_clean from Step 1 if available, else fall back to raw
co_path = os.path.join(OUT, "change_orders_clean.csv")
if os.path.exists(co_path):
    cos = pd.read_csv(co_path)
    # re-parse the affected_sov_lines column if it's still a string
    if cos["affected_sov_lines"].dtype == object:
        cos["affected_sov_lines"] = cos["affected_sov_lines"].apply(
            lambda v: ast.literal_eval(v) if isinstance(v, str) and v.startswith("[") else []
        )
else:
    print("  WARNING: run Step 1 first. Falling back to raw change_orders_all.csv")
    cos = pd.read_csv(os.path.join(BASE, "change_orders_all.csv"))

# ── 2A: Contract base values ──────────────────────────────────────────────────
print("Building contract base ...")
master = contracts.copy()
master["original_duration_days"] = (
    master["substantial_completion_date"] - master["contract_date"]
).dt.days

# Extract project type from name
def classify_project(name):
    name = str(name)
    if any(k in name for k in ["Hospital","Medical","Clinic","Health"]):
        return "Healthcare"
    if "Data Center" in name:
        return "Data Center"
    if any(k in name for k in ["School","Elementary","High School","University","Campus","College"]):
        return "Education"
    if any(k in name for k in ["Office","Corporate","Tower","Park"]):
        return "Commercial/Office"
    if any(k in name for k in ["Condo","Residential","Living","Apartment","Senior"]):
        return "Residential"
    return "Other"

master["project_type"] = master["project_name"].apply(classify_project)

# ── 2B: Budget totals per project ────────────────────────────────────────────
print("Summing SOV budgets ...")
budget_totals = budget.groupby("project_id").agg(
    total_estimated_labor_hours = ("estimated_labor_hours", "sum"),
    total_estimated_labor_cost  = ("estimated_labor_cost",  "sum"),
    total_estimated_material_cost = ("estimated_material_cost", "sum"),
    total_estimated_equipment_cost = ("estimated_equipment_cost", "sum"),
    total_estimated_sub_cost    = ("estimated_sub_cost",    "sum"),
).reset_index()

budget_totals["total_estimated_cost"] = (
    budget_totals["total_estimated_labor_cost"]
  + budget_totals["total_estimated_material_cost"]
  + budget_totals["total_estimated_equipment_cost"]
  + budget_totals["total_estimated_sub_cost"]
)

# Scheduled value (contract total from SOV — should match original_contract_value)
sov_totals = sov.groupby("project_id").agg(
    sov_total_scheduled_value = ("scheduled_value", "sum")
).reset_index()

# ── 2C: Change order summaries ───────────────────────────────────────────────
print("Summarising change orders ...")

def safe_float(v):
    try: return float(v)
    except: return 0.0

cos["amount_float"] = cos["amount"].apply(safe_float)
cos["schedule_impact_days_float"] = cos["schedule_impact_days"].apply(safe_float)

co_summary = cos.groupby("project_id").apply(lambda df: pd.Series({
    "total_co_count":           len(df),
    "approved_co_count":        (df["status"] == "Approved").sum(),
    "rejected_co_count":        (df["status"] == "Rejected").sum(),
    "approved_co_revenue":      df.loc[df["status"] == "Approved", "amount_float"].sum(),
    "rejected_co_loss":         df.loc[(df["status"] == "Rejected") & (df["amount_float"] > 0), "amount_float"].sum(),
    "value_engineering_total":  df.loc[df["reason_category"] == "Value Engineering", "amount_float"].sum(),
    "total_schedule_impact_days": df.loc[df["status"] == "Approved", "schedule_impact_days_float"].sum(),
    "co_count_scope_gap":       (df["reason_category"] == "Scope Gap").sum(),
    "co_count_design_error":    (df["reason_category"] == "Design Error").sum(),
    "co_count_acceleration":    (df["reason_category"] == "Acceleration").sum(),
    "co_count_unforeseen":      (df["reason_category"] == "Unforeseen Condition").sum(),
    "co_count_owner_request":   (df["reason_category"] == "Owner Request").sum(),
    "co_count_code_compliance": (df["reason_category"] == "Code Compliance").sum(),
    "co_count_coordination":    (df["reason_category"] == "Coordination").sum(),
    "co_count_value_engineering": (df["reason_category"] == "Value Engineering").sum(),
})).reset_index()

# ── 2D: Merge everything into master ─────────────────────────────────────────
print("Merging into master table ...")
master = master.merge(budget_totals, on="project_id", how="left")
master = master.merge(sov_totals,   on="project_id", how="left")
master = master.merge(co_summary,   on="project_id", how="left")

# Fill projects with zero change orders
co_cols = [c for c in co_summary.columns if c != "project_id"]
master[co_cols] = master[co_cols].fillna(0)

# ── 2E: Derived metrics ───────────────────────────────────────────────────────
master["revised_contract_value"] = (
    master["original_contract_value"]
  + master["approved_co_revenue"]
  + master["value_engineering_total"]   # already negative
)

master["builtin_margin_$"] = (
    master["original_contract_value"] - master["total_estimated_cost"]
)
master["builtin_margin_%"] = (
    master["builtin_margin_$"] / master["original_contract_value"] * 100
).round(2)

master["co_rejection_rate_%"] = (
    master["rejected_co_count"] / master["total_co_count"].replace(0, 1) * 100
).round(2)

master["schedule_growth_%"] = (
    master["total_schedule_impact_days"] / master["original_duration_days"] * 100
).round(2)

master["upstream_design_co_%"] = (
    (master["co_count_scope_gap"] + master["co_count_design_error"])
  / master["total_co_count"].replace(0, 1) * 100
).round(2)

# ── Save ──────────────────────────────────────────────────────────────────────
out_cols = [
    "project_id", "project_name", "project_type", "gc_name",
    "architect", "engineer_of_record",
    "contract_date", "substantial_completion_date", "original_duration_days",
    "original_contract_value", "retention_pct", "payment_terms",
    "total_estimated_labor_hours", "total_estimated_labor_cost",
    "total_estimated_material_cost", "total_estimated_equipment_cost",
    "total_estimated_sub_cost", "total_estimated_cost",
    "builtin_margin_$", "builtin_margin_%",
    "total_co_count", "approved_co_count", "rejected_co_count",
    "approved_co_revenue", "rejected_co_loss", "value_engineering_total",
    "revised_contract_value",
    "co_rejection_rate_%", "schedule_growth_%", "total_schedule_impact_days",
    "upstream_design_co_%",
    "co_count_scope_gap", "co_count_design_error", "co_count_acceleration",
    "co_count_unforeseen", "co_count_owner_request", "co_count_code_compliance",
    "co_count_coordination", "co_count_value_engineering",
]
master[out_cols].to_csv(os.path.join(OUT, "project_master.csv"), index=False)

# Print summary
print(f"\n✓ Step 2 complete. Project master table saved: outputs/project_master.csv")
print(f"  Rows: {len(master)} projects")
print(f"\n  Built-in margin range:")
print(f"    Min:  {master['builtin_margin_%'].min():.1f}%")
print(f"    Mean: {master['builtin_margin_%'].mean():.1f}%")
print(f"    Max:  {master['builtin_margin_%'].max():.1f}%")
print(f"\n  Projects with built-in margin < 5%: {(master['builtin_margin_%'] < 5).sum()}")
print(f"  Average CO rejection rate: {master['co_rejection_rate_%'].mean():.1f}%")
print(f"  Total approved CO revenue: ${master['approved_co_revenue'].sum():,.0f}")
print(f"  Total rejected CO loss:    ${master['rejected_co_loss'].sum():,.0f}")
print(f"\n  Project type breakdown:")
print(master.groupby("project_type")["original_contract_value"].agg(["count","sum"]).rename(columns={"count":"projects","sum":"total_value"}))
