"""
STEP 4 — BILLING PROGRESS
===========================
Purpose:
    Pull the most recent "official" percentage complete for every SOV line on
    every project, as agreed between the subcontractor and the GC.

    The billing_line_items file has one row per SOV line per billing application.
    We want only the LATEST application number for each (project, SOV line) pair,
    because that contains the cumulative progress to date.

    This pct_complete figure is what Step 5 divides actual cost by to compute
    the Cost Performance Index. Getting it right matters: using an intermediate
    billing period would understate progress and make a project look worse than it is.

Depends on:
    ../billing_line_items_all.csv
    ../billing_history_all.csv
    ../sov_all.csv

Output:
    outputs/billing_progress.csv       — latest pct_complete per (project, SOV line)
    outputs/billing_timeline.csv       — all billing periods kept (for trend charts)
"""

import pandas as pd
import os

BASE = os.path.join(os.path.dirname(__file__), "..")
OUT  = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUT, exist_ok=True)

# ── Load ───────────────────────────────────────────────────────────────────────
print("Loading billing data ...")
line_items = pd.read_csv(os.path.join(BASE, "billing_line_items_all.csv"))
history    = pd.read_csv(os.path.join(BASE, "billing_history_all.csv"),
                         parse_dates=["period_end", "payment_date"])
sov        = pd.read_csv(os.path.join(BASE, "sov_all.csv"))

# ── 4A: Validate that scheduled_value in billing matches sov_all ─────────────
# (tiny discrepancies can exist from rounding; flag if >1%)
merged_check = line_items.merge(
    sov[["sov_line_id","scheduled_value"]].rename(columns={"scheduled_value":"sov_sv"}),
    on="sov_line_id", how="left"
)
merged_check["sv_diff_%"] = abs(merged_check["scheduled_value"] - merged_check["sov_sv"]) \
                             / merged_check["sov_sv"].replace(0,1) * 100
discrepancies = merged_check[merged_check["sv_diff_%"] > 1]
if len(discrepancies) > 0:
    print(f"  WARNING: {len(discrepancies)} billing line items have scheduled_value "
          f"differing >1% from sov_all. Investigate before relying on pct_complete.")
else:
    print("  Scheduled value consistency check: PASSED")

# ── 4B: Keep only the latest billing application per (project, SOV line) ──────
print("Extracting latest billing period per SOV line ...")

# Sort by application_number descending, then keep first occurrence of each (project, line)
line_items_sorted = line_items.sort_values("application_number", ascending=False)
latest = line_items_sorted.drop_duplicates(subset=["project_id","sov_line_id"], keep="first")

# Bring in the billing period date from history
latest = latest.merge(
    history[["project_id","application_number","period_end","status"]],
    on=["project_id","application_number"], how="left"
)

# ── 4C: Add SOV metadata (line_number only — description already in billing_line_items) ──
latest = latest.merge(
    sov[["sov_line_id","line_number"]].drop_duplicates("sov_line_id"),
    on="sov_line_id", how="left"
)
# billing_line_items already has a description column; rename for clarity
latest = latest.rename(columns={"description": "sov_description"})

# ── 4D: Classify completion stage ─────────────────────────────────────────────
def completion_stage(pct):
    if pct == 0:      return "Not started"
    elif pct < 25:    return "Early (0–25%)"
    elif pct < 50:    return "Progressing (25–50%)"
    elif pct < 75:    return "Midway (50–75%)"
    elif pct < 100:   return "Near complete (75–99%)"
    else:             return "Complete (100%)"

latest["completion_stage"] = latest["pct_complete"].apply(completion_stage)

# ── 4E: Flag overbilling risk ──────────────────────────────────────────────────
# If total_billed > scheduled_value (pct_complete > 100), that is overbilling —
# the sub billed more than the contract value for that line.
latest["overbilled_flag"] = latest["pct_complete"] > 100

# ── 4F: Balance to finish ──────────────────────────────────────────────────────
# Cross-check: balance_to_finish should equal scheduled_value - total_billed
latest["balance_check"] = (
    latest["scheduled_value"] - latest["total_billed"] - latest["balance_to_finish"]
).abs()
if latest["balance_check"].max() > 1:
    print(f"  WARNING: balance_to_finish inconsistency detected in {(latest['balance_check']>1).sum()} rows")

# ── 4G: Keep full timeline for trend analysis ──────────────────────────────────
print("Saving full billing timeline ...")
timeline = line_items.merge(
    history[["project_id","application_number","period_end","status","period_total","cumulative_billed"]],
    on=["project_id","application_number"], how="left"
)
timeline = timeline.merge(
    sov[["project_id","sov_line_id","description"]],
    on=["project_id","sov_line_id"], how="left"
)
timeline.to_csv(os.path.join(OUT, "billing_timeline.csv"), index=False)

# ── Save ───────────────────────────────────────────────────────────────────────
out_cols = [
    "project_id", "sov_line_id", "line_number", "sov_description",
    "scheduled_value", "total_billed", "pct_complete", "balance_to_finish",
    "application_number", "period_end", "completion_stage", "overbilled_flag"
]
latest[out_cols].to_csv(os.path.join(OUT, "billing_progress.csv"), index=False)

# Summary
print(f"\n✓ Step 4 complete.")
print(f"  outputs/billing_progress.csv  — {len(latest):,} rows (latest snapshot per SOV line)")
print(f"  outputs/billing_timeline.csv  — {len(timeline):,} rows (all billing periods)")

print(f"\n  Completion stage breakdown (across all SOV lines, all projects):")
stage_counts = latest["completion_stage"].value_counts()
for stage, cnt in stage_counts.items():
    print(f"    {stage:<30} {cnt:>6,} lines ({cnt/len(latest)*100:.1f}%)")

print(f"\n  Lines flagged as overbilled (pct_complete > 100%): {latest['overbilled_flag'].sum()}")

print(f"\n  Average pct_complete by SOV line description:")
avg_pct = latest.groupby("sov_description")["pct_complete"].mean().sort_values()
for desc, pct in avg_pct.items():
    bar = "█" * int(pct / 5)
    print(f"    {desc:<45} {pct:>6.1f}%  {bar}")
