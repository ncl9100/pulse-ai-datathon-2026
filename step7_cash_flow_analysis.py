"""
STEP 7 — CASH FLOW ANALYSIS
=============================
Purpose:
    From the CFO's perspective, revenue earned is meaningless until it becomes
    cash in the bank. This step tracks three cash flow problems:

    1. PAYMENT LAG: The contract says Net 30. How many invoices are being paid
       late, by how many days, and which GCs are the worst offenders?

    2. STUCK BILLING: Applications in "Pending" or "Approved" status are invoices
       the GC has either not approved yet or approved but not paid. Quantify
       the total dollar value sitting in limbo and how long it's been stuck.

    3. RETENTION TRAP: 10% of every dollar billed is held back. For projects
       past their substantial completion date, that retention is legally earned
       and should be released — but often isn't. This is idle cash the company
       is owed right now.

Depends on:
    ../billing_history_all.csv
    outputs/project_master.csv  ← from Step 2

Output:
    outputs/cash_flow_summary.csv        — project-level cash flow health
    outputs/overdue_applications.csv     — every overdue or stuck billing application
    outputs/retention_analysis.csv       — retention held, releasable, and unreleased
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, date

BASE = os.path.join(os.path.dirname(__file__), "..")
OUT  = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUT, exist_ok=True)

# Use today's date as the reference point for "days overdue"
TODAY = pd.Timestamp(date.today())

# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading billing history ...")
billing = pd.read_csv(os.path.join(BASE, "billing_history_all.csv"),
                      parse_dates=["period_end","payment_date"])
master  = pd.read_csv(os.path.join(OUT,  "project_master.csv"),
                      parse_dates=["contract_date","substantial_completion_date"])

billing["net_payment_due_f"] = pd.to_numeric(billing["net_payment_due"], errors="coerce").fillna(0)
billing["retention_held_f"]  = pd.to_numeric(billing["retention_held"],  errors="coerce").fillna(0)
billing["period_total_f"]    = pd.to_numeric(billing["period_total"],     errors="coerce").fillna(0)
billing["cumulative_billed_f"]= pd.to_numeric(billing["cumulative_billed"],errors="coerce").fillna(0)

# ── 7A: Payment lag (Paid applications only) ──────────────────────────────────
print("Computing payment lag ...")
paid = billing[billing["status"] == "Paid"].copy()
paid["payment_lag_days"] = (paid["payment_date"] - paid["period_end"]).dt.days
paid["paid_late_flag"]   = paid["payment_lag_days"] > 30
paid["days_overdue"]     = (paid["payment_lag_days"] - 30).clip(lower=0)

# Merge GC name
paid = paid.merge(master[["project_id","gc_name","project_type"]], on="project_id", how="left")

lag_by_gc = paid.groupby("gc_name").agg(
    total_paid_apps       = ("project_id",        "count"),
    late_paid_apps        = ("paid_late_flag",     "sum"),
    avg_payment_lag_days  = ("payment_lag_days",   "mean"),
    max_payment_lag_days  = ("payment_lag_days",   "max"),
    avg_days_overdue      = ("days_overdue",        "mean"),
    total_late_amount_usd = ("net_payment_due_f",  lambda x: x[paid.loc[x.index,"paid_late_flag"]].sum()),
).reset_index().round(2)
lag_by_gc["late_rate_%"] = (lag_by_gc["late_paid_apps"] / lag_by_gc["total_paid_apps"] * 100).round(1)

# ── 7B: Stuck billing (Pending and Approved-but-not-paid) ─────────────────────
print("Identifying stuck billing applications ...")
stuck = billing[billing["status"].isin(["Pending","Approved"])].copy()
stuck = stuck.merge(master[["project_id","gc_name","project_type","project_name"]], on="project_id", how="left")
stuck["days_since_period_end"] = (TODAY - stuck["period_end"]).dt.days
stuck["days_overdue"] = (stuck["days_since_period_end"] - 30).clip(lower=0)
stuck["is_overdue_flag"] = stuck["days_since_period_end"] > 30

overdue = stuck[stuck["is_overdue_flag"]].copy()
overdue = overdue.sort_values("days_overdue", ascending=False)
overdue.to_csv(os.path.join(OUT, "overdue_applications.csv"), index=False)

print(f"  Total stuck applications: {len(stuck):,}")
print(f"  Overdue (>30 days): {len(overdue):,} | Total overdue value: ${overdue['net_payment_due_f'].sum():,.0f}")

# ── 7C: Retention analysis ────────────────────────────────────────────────────
print("Analysing retention ...")

# For each project, get the latest (maximum) cumulative retention held
latest_billing = billing.sort_values("application_number", ascending=False).drop_duplicates("project_id", keep="first")
retention_df = latest_billing[["project_id","cumulative_billed_f","retention_held_f"]].copy()
retention_df = retention_df.merge(
    master[["project_id","project_name","project_type","gc_name",
            "substantial_completion_date","original_contract_value"]],
    on="project_id", how="left"
)

# Flag projects that are past substantial completion (retention should be releasable)
retention_df["past_completion_date"] = retention_df["substantial_completion_date"] < TODAY
retention_df["days_past_completion"] = (
    TODAY - retention_df["substantial_completion_date"]
).dt.days.clip(lower=0)

# Retention is releasable if project is past completion AND retention > 0
retention_df["retention_releasable"] = (
    retention_df["past_completion_date"] & (retention_df["retention_held_f"] > 0)
)

retention_df.to_csv(os.path.join(OUT, "retention_analysis.csv"), index=False)

# ── 7D: Project-level cash flow health score ──────────────────────────────────
print("Building cash flow health summary ...")

# Combine all signals per project
cf_project = billing.groupby("project_id").agg(
    total_cumulative_billed  = ("cumulative_billed_f", "max"),
    total_retention_held     = ("retention_held_f",    "max"),
    paid_app_count           = ("status",              lambda x: (x == "Paid").sum()),
    pending_app_count        = ("status",              lambda x: (x == "Pending").sum()),
    approved_app_count       = ("status",              lambda x: (x == "Approved").sum()),
).reset_index()

# Add payment lag stats for paid apps
paid_summary = paid.groupby("project_id").agg(
    avg_payment_lag        = ("payment_lag_days", "mean"),
    late_payment_count     = ("paid_late_flag",   "sum"),
    total_paid_amount      = ("net_payment_due_f","sum"),
).reset_index().round(2)

# Add stuck amounts
stuck_summary = stuck.groupby("project_id").agg(
    total_stuck_amount     = ("net_payment_due_f", "sum"),
    total_overdue_amount   = ("net_payment_due_f", lambda x: x[stuck.loc[x.index,"is_overdue_flag"]].sum()),
    overdue_app_count      = ("is_overdue_flag",   "sum"),
).reset_index()

cf = (cf_project
      .merge(paid_summary,   on="project_id", how="left")
      .merge(stuck_summary,  on="project_id", how="left")
      .merge(retention_df[["project_id","past_completion_date","days_past_completion","retention_releasable"]],
             on="project_id", how="left")
      .merge(master[["project_id","project_name","project_type","gc_name"]], on="project_id", how="left")
)

cf = cf.fillna(0)

# Cash flow health: penalise for overdue invoices and unreleased retention
cf["cash_tied_up_$"] = cf["total_overdue_amount"] + cf.apply(
    lambda r: r["total_retention_held"] if r["retention_releasable"] else 0, axis=1
)

cf.to_csv(os.path.join(OUT, "cash_flow_summary.csv"), index=False)

# Summary
total_retention   = retention_df["retention_held_f"].sum()
releasable        = retention_df.loc[retention_df["retention_releasable"], "retention_held_f"].sum()
total_overdue_val = overdue["net_payment_due_f"].sum()

print(f"\n✓ Step 7 complete.")
print(f"  outputs/cash_flow_summary.csv      — {len(cf)} projects")
print(f"  outputs/overdue_applications.csv   — {len(overdue):,} overdue applications")
print(f"  outputs/retention_analysis.csv     — {len(retention_df)} projects")
print(f"\n  Cash flow summary:")
print(f"    Total retention held across all projects:  ${total_retention:>15,.0f}")
print(f"    Retention on projects past completion:     ${releasable:>15,.0f}")
print(f"    Projects past completion with retention:   {retention_df['retention_releasable'].sum()}")
print(f"    Total overdue invoice value (>30 days):    ${total_overdue_val:>15,.0f}")
print(f"\n  Payment lag by GC:")
print(lag_by_gc[["gc_name","late_rate_%","avg_payment_lag_days","max_payment_lag_days"]].to_string(index=False))
