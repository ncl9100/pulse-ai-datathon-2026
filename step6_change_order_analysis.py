"""
Step 6 — Analyze Contract Changes
====================================
Real CO column names: co_number, date_submitted, reason_category,
                      description, amount, status, related_rfi,
                      affected_sov_lines_parsed (after Step 1 clean)

Real RFI column names: project_id, rfi_number, date_submitted,
                       subject, submitted_by, assigned_to, priority,
                       status, date_required, date_responded,
                       response_summary, cost_impact, schedule_impact
  cost_impact is boolean (True/False) in raw data

Outputs
-------
co_analysis_by_project.csv
co_analysis_by_gc.csv
co_rfi_recovery.csv
co_timing.csv
"""

import pandas as pd
import numpy as np
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

print("Loading files …")
co     = pd.read_csv(os.path.join(OUT_DIR, "change_orders_clean.csv"),  low_memory=False)
master = pd.read_csv(os.path.join(OUT_DIR, "project_master.csv"),       low_memory=False)
rfis   = pd.read_csv(os.path.join(DATA_DIR, "rfis_all.csv"),            low_memory=False)

# ── A  Revenue recovery by project ──────────────────────────────
print("\nA: Revenue recovery by project …")
approved_mask = co["status"] == "Approved"
rejected_mask = co["status"] == "Rejected"

co_proj = co.groupby("project_id").agg(
    total_cos=("co_number", "count"),
    approved_cos=("status", lambda x: (x == "Approved").sum()),
    rejected_cos=("status", lambda x: (x == "Rejected").sum()),
    pending_cos=("status", lambda x: (x == "Pending").sum()),
    total_co_value_usd=("amount", "sum"),
).reset_index()

approved_vals = (co[approved_mask].groupby("project_id")["amount"].sum()
                 .reset_index().rename(columns={"amount": "approved_value_usd"}))
rejected_vals = (co[rejected_mask].groupby("project_id")["amount"].sum()
                 .reset_index().rename(columns={"amount": "rejected_value_usd"}))

co_proj = co_proj.merge(approved_vals, on="project_id", how="left")
co_proj = co_proj.merge(rejected_vals, on="project_id", how="left")

co_proj["recovery_rate_pct"] = (
    co_proj["approved_value_usd"] / co_proj["total_co_value_usd"].replace(0, np.nan) * 100
).round(1)
co_proj["rejection_rate_pct"] = (
    co_proj["rejected_cos"] / co_proj["total_cos"].replace(0, np.nan) * 100
).round(1)

co_proj = co_proj.merge(
    master[["project_id", "gc_name", "original_contract_value", "project_type"]],
    on="project_id", how="left"
)
co_proj.to_csv(os.path.join(OUT_DIR, "co_analysis_by_project.csv"), index=False)
print(f"   {len(co_proj)} projects | avg recovery rate: {co_proj['recovery_rate_pct'].mean():.1f}%")

# ── B  GC rejection patterns ─────────────────────────────────────
print("\nB: GC rejection patterns …")
co_with_gc = co.merge(master[["project_id", "gc_name"]], on="project_id", how="left")

gc_summary = co_with_gc.groupby("gc_name").agg(
    total_cos=("co_number", "count"),
    rejected_cos=("status", lambda x: (x == "Rejected").sum()),
    total_value_usd=("amount", "sum"),
).reset_index()

rej_vals_gc = (
    co_with_gc[co_with_gc["status"] == "Rejected"]
    .groupby("gc_name")["amount"].sum()
    .reset_index().rename(columns={"amount": "rejected_value_usd"})
)
gc_summary = gc_summary.merge(rej_vals_gc, on="gc_name", how="left")
gc_summary["rejection_rate_pct"] = (
    gc_summary["rejected_cos"] / gc_summary["total_cos"].replace(0, np.nan) * 100
).round(1)

# Top rejection reason_category per GC
top_reason = (
    co_with_gc[co_with_gc["status"] == "Rejected"]
    .groupby("gc_name")["reason_category"]
    .agg(lambda x: x.value_counts().index[0] if len(x) > 0 else "N/A")
    .reset_index()
    .rename(columns={"reason_category": "top_rejection_reason"})
)
gc_summary = gc_summary.merge(top_reason, on="gc_name", how="left")
gc_summary = gc_summary.sort_values("rejection_rate_pct", ascending=False)
gc_summary.to_csv(os.path.join(OUT_DIR, "co_analysis_by_gc.csv"), index=False)
print(f"   {len(gc_summary)} GCs analyzed")
print(gc_summary[["gc_name", "total_cos", "rejection_rate_pct"]].head(10).to_string(index=False))

# ── C  RFI-to-CO recovery gap ────────────────────────────────────
print("\nC: RFI-to-CO recovery gap …")
# cost_impact in rfis is a boolean string (True/False)
rfis["has_cost_impact"] = rfis["cost_impact"].astype(str).str.lower().isin(["true", "1", "yes"])

# Match RFIs to COs via related_rfi column in change_orders
# related_rfi in co_clean contains RFI numbers like "RFI-012"
approved_rfi_links = set(
    co[co["status"] == "Approved"]["related_rfi"].dropna().astype(str).str.strip()
)

cost_rfis = rfis[rfis["has_cost_impact"]].copy()
cost_rfis["rfi_id_str"] = cost_rfis["rfi_number"].astype(str).str.strip()
cost_rfis["approved_recovery"] = cost_rfis["rfi_id_str"].isin(approved_rfi_links)

rfi_recovery = cost_rfis.groupby("project_id").agg(
    cost_impact_rfis=("rfi_number", "count"),
    recovered_rfis=("approved_recovery", "sum"),
).reset_index()

rfi_recovery["recovery_rate_pct"] = (
    rfi_recovery["recovered_rfis"] / rfi_recovery["cost_impact_rfis"].replace(0, np.nan) * 100
).round(1)

rfi_recovery.to_csv(os.path.join(OUT_DIR, "co_rfi_recovery.csv"), index=False)
total_cost_rfis = rfi_recovery["cost_impact_rfis"].sum()
total_recovered = rfi_recovery["recovered_rfis"].sum()
print(f"   Cost-impacting RFIs: {total_cost_rfis:,}")
print(f"   Recovered via approved CO: {total_recovered:,} "
      f"({total_recovered / max(total_cost_rfis, 1) * 100:.1f}%)")

# ── D  CO timing by project stage ────────────────────────────────
print("\nD: CO timing by project stage …")
# contracts uses contract_date and substantial_completion_date
co_timing = co.merge(
    master[["project_id", "contract_date", "substantial_completion_date", "original_duration_days"]],
    on="project_id", how="left"
)
co_timing["contract_date"] = pd.to_datetime(co_timing["contract_date"], errors="coerce")
co_timing["co_date"]       = pd.to_datetime(co_timing["date_submitted"], errors="coerce")

co_timing["days_from_start"] = (co_timing["co_date"] - co_timing["contract_date"]).dt.days
co_timing["project_stage_pct"] = (
    co_timing["days_from_start"]
    / co_timing["original_duration_days"].replace(0, np.nan) * 100
).clip(0, 100)

def stage_label(pct):
    if pd.isna(pct):    return "Unknown"
    elif pct <= 20:     return "Early (0-20%)"
    elif pct <= 50:     return "Mid (20-50%)"
    elif pct <= 80:     return "Late (50-80%)"
    else:               return "Closeout (80-100%)"

co_timing["project_stage"] = co_timing["project_stage_pct"].apply(stage_label)

timing_summary = co_timing.groupby("project_stage").agg(
    co_count=("co_number", "count"),
    approved=("status", lambda x: (x == "Approved").sum()),
    rejected=("status", lambda x: (x == "Rejected").sum()),
    total_value_usd=("amount", "sum"),
).reset_index()
timing_summary["rejection_rate_pct"] = (
    timing_summary["rejected"] / timing_summary["co_count"].replace(0, np.nan) * 100
).round(1)
print(timing_summary.to_string(index=False))

co_timing[["project_id", "co_number", "status", "amount",
           "reason_category", "project_stage", "project_stage_pct"]].to_csv(
    os.path.join(OUT_DIR, "co_timing.csv"), index=False
)

print("\n✓ Step 6 complete → co_analysis_by_project.csv, co_analysis_by_gc.csv, co_rfi_recovery.csv, co_timing.csv")
