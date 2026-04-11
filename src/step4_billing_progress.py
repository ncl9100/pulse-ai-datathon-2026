"""
Step 4 — Calculate How Much Is Done
=====================================
billing_line_items_clean now has NO scheduled_value or description
(dropped in Step 1 as cross-file duplicates from sov_all).
So the join to sov_all is clean — no collision.

We recompute:
  total_billed      = previous_billed + this_period
  balance_to_finish = scheduled_value - total_billed

Outputs
-------
billing_progress.csv   — latest pct_complete per project/line
billing_timeline.csv   — per-project billing history by application
"""

import pandas as pd
import numpy as np
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

print("Loading billing_line_items_clean …")
bl = pd.read_csv(os.path.join(OUT_DIR, "billing_line_items_clean.csv"), low_memory=False)
print(f"   {len(bl):,} rows, columns: {list(bl.columns)}")

# Recompute total_billed from source columns (dropped as redundant in Step 1)
bl["total_billed"] = bl["previous_billed"] + bl["this_period"]

# ── Join sov_all — clean merge, no collision ─────────────────────
print("Joining sov_all …")
sov = pd.read_csv(os.path.join(DATA_DIR, "sov_all.csv"), low_memory=False)
sov_lookup = sov[["project_id", "sov_line_id", "line_number",
                   "scheduled_value", "description"]].copy()

bl = bl.merge(sov_lookup, on=["project_id", "sov_line_id"], how="left")

# Recompute balance_to_finish
bl["balance_to_finish"] = bl["scheduled_value"] - bl["total_billed"]

# ── Latest application per project/line ─────────────────────────
print("Extracting latest application per project/line …")
billing_progress = (
    bl.sort_values("application_number", ascending=False)
      .groupby(["project_id", "sov_line_id"], as_index=False)
      .first()
)

progress_cols = [
    "project_id", "sov_line_id", "line_number", "description",
    "application_number", "scheduled_value",
    "previous_billed", "this_period", "total_billed",
    "pct_complete", "pct_manually_adjusted", "balance_to_finish",
]
progress_cols = [c for c in progress_cols if c in billing_progress.columns]
billing_progress = billing_progress[progress_cols]

print(f"   {len(billing_progress):,} project/line progress records")
print(f"   Avg % complete: {billing_progress['pct_complete'].mean():.1f}%")
if "pct_manually_adjusted" in billing_progress.columns:
    print(f"   Manually adjusted entries: {billing_progress['pct_manually_adjusted'].sum():,}")

billing_progress.to_csv(os.path.join(OUT_DIR, "billing_progress.csv"), index=False)

# ── Billing timeline — all applications per project ─────────────
print("\nBuilding billing timeline …")
timeline = bl.groupby(["project_id", "application_number"]).agg(
    total_billed_this_app=("this_period", "sum"),
    cumulative_billed=("total_billed", "sum"),
    lines_count=("sov_line_id", "count"),
).reset_index()

# Recompute retention and net payment (authoritative formula)
timeline["retention_held"]  = (timeline["cumulative_billed"] * 0.10).round(2)
timeline["net_payment_due"] = (timeline["cumulative_billed"] - timeline["retention_held"]).round(2)

timeline = timeline.sort_values(["project_id", "application_number"])
timeline.to_csv(os.path.join(OUT_DIR, "billing_timeline.csv"), index=False)

print(f"   {len(timeline):,} billing applications across {timeline['project_id'].nunique()} projects")
print("\n✓ Step 4 complete → billing_progress.csv, billing_timeline.csv")
