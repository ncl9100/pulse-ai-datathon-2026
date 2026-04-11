"""
Step 7 — Track Cash Movement
==============================
billing_history_clean real columns (after dropping derived cols in Step 1):
  project_id, application_number, period_end, period_total,
  cumulative_billed, status, payment_date, line_item_count

retention_held  = cumulative_billed × 0.10  (recomputed here)
net_payment_due = cumulative_billed − retention_held  (recomputed here)

contracts real columns:
  project_id, project_name, original_contract_value, contract_date,
  substantial_completion_date, retention_pct, payment_terms,
  gc_name, architect, engineer_of_record

Outputs
-------
cash_flow_summary.csv
overdue_applications.csv
retention_analysis.csv
"""

import pandas as pd
import numpy as np
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

RETENTION_RATE = 0.10
PAYMENT_TERMS  = 30   # days

print("Loading files …")
bh     = pd.read_csv(os.path.join(OUT_DIR, "billing_history_clean.csv"), low_memory=False)
master = pd.read_csv(os.path.join(OUT_DIR, "project_master.csv"),        low_memory=False)
print(f"   billing_history: {len(bh):,} rows, columns: {list(bh.columns)}")

# ── Recompute derived columns from authoritative formula ─────────
bh["retention_held"]  = (bh["cumulative_billed"] * RETENTION_RATE).round(2)
bh["net_payment_due"] = (bh["cumulative_billed"] - bh["retention_held"]).round(2)

# ── Parse dates ──────────────────────────────────────────────────
# billing_history has: period_end, payment_date
bh["period_end"]    = pd.to_datetime(bh["period_end"],    errors="coerce")
bh["payment_date"]  = pd.to_datetime(bh["payment_date"],  errors="coerce")

# Use period_end as the application/invoice date
bh["application_date"] = bh["period_end"]

# ── Payment lag ──────────────────────────────────────────────────
print("\nAnalyzing payment lag …")
paid_mask = bh["payment_date"].notna() & bh["application_date"].notna()
if paid_mask.sum() > 0:
    bh.loc[paid_mask, "days_to_payment"] = (
        bh.loc[paid_mask, "payment_date"] - bh.loc[paid_mask, "application_date"]
    ).dt.days
    bh["is_late"] = bh["days_to_payment"] > PAYMENT_TERMS

    avg_lag  = bh.loc[paid_mask, "days_to_payment"].mean()
    late_pct = bh.loc[paid_mask, "is_late"].mean() * 100
    print(f"   Avg days to payment: {avg_lag:.1f}  (contract terms: {PAYMENT_TERMS})")
    print(f"   Late payment rate:   {late_pct:.1f}%")
else:
    bh["days_to_payment"] = np.nan
    bh["is_late"] = False
    print("   No payment date data available")

# ── Overdue applications ─────────────────────────────────────────
today = pd.Timestamp.today()
bh["due_date"] = bh["application_date"] + pd.Timedelta(days=PAYMENT_TERMS)

unpaid_mask = bh["payment_date"].isna() & bh["application_date"].notna()
bh.loc[unpaid_mask, "days_overdue"] = (
    (today - bh.loc[unpaid_mask, "application_date"]).dt.days - PAYMENT_TERMS
).clip(lower=0)

overdue = bh[unpaid_mask & (bh.get("days_overdue", pd.Series(0, index=bh.index)) > 0)].copy()
overdue = overdue.merge(master[["project_id", "gc_name"]], on="project_id", how="left")

overdue_out = overdue[[
    "project_id", "gc_name", "application_number",
    "period_end", "days_overdue", "net_payment_due"
]].sort_values("days_overdue", ascending=False)
overdue_out.to_csv(os.path.join(OUT_DIR, "overdue_applications.csv"), index=False)
print(f"\n   Overdue applications: {len(overdue):,}")
print(f"   Total overdue amount: ${overdue['net_payment_due'].sum():,.0f}")

# ── Retention analysis ────────────────────────────────────────────
print("\nAnalyzing unreleased retention …")
latest = (
    bh.sort_values("application_number", ascending=False)
      .groupby("project_id", as_index=False)
      .first()
)
latest = latest.merge(
    master[["project_id", "gc_name", "substantial_completion_date", "project_type"]],
    on="project_id", how="left"
)
latest["substantial_completion_date"] = pd.to_datetime(
    latest["substantial_completion_date"], errors="coerce"
)
latest["days_past_completion"] = (
    (today - latest["substantial_completion_date"]).dt.days
).clip(lower=0)

retention_due = latest[
    (latest["retention_held"] > 0) & (latest["days_past_completion"] > 0)
].copy()

retention_out = retention_due[[
    "project_id", "gc_name", "project_type",
    "retention_held", "cumulative_billed",
    "substantial_completion_date", "days_past_completion"
]].sort_values("retention_held", ascending=False)

retention_out.to_csv(os.path.join(OUT_DIR, "retention_analysis.csv"), index=False)
print(f"   Projects with unreleased retention: {len(retention_out):,}")
print(f"   Total retention held:               ${retention_out['retention_held'].sum():,.0f}")

# ── Cash flow summary per project ────────────────────────────────
cf_summary = bh.groupby("project_id").agg(
    total_applications=("application_number", "count"),
    max_cumulative_billed=("cumulative_billed", "max"),
    total_retention_held=("retention_held", "max"),
    late_payments=("is_late", lambda x: x.sum() if hasattr(x, "sum") else 0),
    avg_days_to_payment=("days_to_payment", "mean"),
).reset_index()

cf_summary = cf_summary.merge(
    master[["project_id", "gc_name", "original_contract_value", "project_type"]],
    on="project_id", how="left"
)
cf_summary.to_csv(os.path.join(OUT_DIR, "cash_flow_summary.csv"), index=False)

print(f"\n✓ Step 7 complete → cash_flow_summary.csv, overdue_applications.csv, retention_analysis.csv")
