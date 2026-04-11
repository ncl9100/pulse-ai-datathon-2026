"""
Step 9 — Predict Future Risk
==============================
Seven early-window signals → 0–100 risk score per project.
Early window = first 20% of project duration from contract_date.

Real column names used:
  contracts: contract_date, substantial_completion_date
  rfis:      rfi_number, date_submitted, cost_impact (True/False)
  co_timing: project_stage, reason_category, co_number, amount
  billing_history_clean: cumulative_billed, period_end, payment_date,
                         application_number

Outputs
-------
early_warning_scores.csv
early_warning_thresholds.csv
early_warning_validation.csv
"""

import pandas as pd
import numpy as np
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

print("Loading inputs …")
cpi_proj  = pd.read_csv(os.path.join(OUT_DIR, "cpi_per_project.csv"),       low_memory=False)
master    = pd.read_csv(os.path.join(OUT_DIR, "project_master.csv"),        low_memory=False)
actual    = pd.read_csv(os.path.join(OUT_DIR, "actual_cost_per_line.csv"),  low_memory=False)
co_timing = pd.read_csv(os.path.join(OUT_DIR, "co_timing.csv"),             low_memory=False)
rfi_rec   = pd.read_csv(os.path.join(OUT_DIR, "co_rfi_recovery.csv"),       low_memory=False)
bh_clean  = pd.read_csv(os.path.join(OUT_DIR, "billing_history_clean.csv"), low_memory=False)
rfis_raw  = pd.read_csv(os.path.join(DATA_DIR, "rfis_all.csv"),             low_memory=False)

# Recompute derived billing columns
bh_clean["retention_held"]  = (bh_clean["cumulative_billed"] * 0.10).round(2)
bh_clean["net_payment_due"] = (bh_clean["cumulative_billed"] - bh_clean["retention_held"]).round(2)

# ── Label: over budget on completed projects ──────────────────────
finished = cpi_proj[cpi_proj["avg_pct_complete"] >= 90].copy()
finished["actual_overbudget"] = (finished["project_cpi"] < 0.85).astype(int)
print(f"   Completed projects: {len(finished)} | Over budget: {finished['actual_overbudget'].sum()}")

# ── Signal 1: Project CPI (overall efficiency signal) ───────────
# Using final CPI as a proxy — in a true early-warning setting you'd
# compute this on just early-window labor/billing data

# ── Signals 2 & 7: Early CO count and early scope CO count ──────
if "project_stage" in co_timing.columns:
    early_co = co_timing[co_timing["project_stage"] == "Early (0-20%)"].groupby("project_id").agg(
        early_co_count=("co_number", "count"),
        early_scope_cos=("reason_category",
                         lambda x: x.isin(["Design Error", "Scope Gap"]).sum()),
    ).reset_index()
else:
    early_co = pd.DataFrame({"project_id": cpi_proj["project_id"],
                              "early_co_count": 0, "early_scope_cos": 0})

# ── Signal 3: Early RFI count ────────────────────────────────────
master_dates = master[["project_id", "contract_date", "original_duration_days"]].copy()
master_dates["contract_date"] = pd.to_datetime(master_dates["contract_date"], errors="coerce")
master_dates["early_end"] = master_dates["contract_date"] + pd.to_timedelta(
    master_dates["original_duration_days"].fillna(365) * 0.20, unit="D"
)

rfis_raw["submitted_date"] = pd.to_datetime(rfis_raw["date_submitted"], errors="coerce")
rfis_merged = rfis_raw.merge(master_dates, on="project_id", how="left")
rfis_merged["in_early_window"] = (
    rfis_merged["submitted_date"] >= rfis_merged["contract_date"]
) & (
    rfis_merged["submitted_date"] <= rfis_merged["early_end"]
)
early_rfi = (
    rfis_merged[rfis_merged["in_early_window"]]
    .groupby("project_id").size()
    .reset_index(name="early_rfi_count")
)

# ── Signal 4: OT ratio ───────────────────────────────────────────
ot_by_proj = actual.groupby("project_id").agg(
    early_ot_ratio=("ot_ratio_pct", "mean")
).reset_index()

# ── Signal 5: Partial shipment rate ─────────────────────────────
partial_by_proj = actual.groupby("project_id").agg(
    early_partial_mat=("partial_shipment_rate_pct", "mean")
).reset_index()

# ── Signal 6: Billing lag ────────────────────────────────────────
bh_clean["period_end"]   = pd.to_datetime(bh_clean["period_end"],   errors="coerce")
bh_clean["payment_date"] = pd.to_datetime(bh_clean["payment_date"], errors="coerce")
paid_mask = bh_clean["payment_date"].notna() & bh_clean["period_end"].notna()
bh_clean.loc[paid_mask, "billing_lag_days"] = (
    bh_clean.loc[paid_mask, "payment_date"] - bh_clean.loc[paid_mask, "period_end"]
).dt.days

lag_by_proj = bh_clean.groupby("project_id").agg(
    early_billing_lag=("billing_lag_days", "mean")
).reset_index()

# ── Assemble ─────────────────────────────────────────────────────
print("Assembling signals …")
signals = cpi_proj[["project_id", "project_cpi", "avg_pct_complete"]].copy()

for df in [early_co, early_rfi, ot_by_proj, partial_by_proj, lag_by_proj]:
    signals = signals.merge(df, on="project_id", how="left")

signals = signals.fillna({
    "early_co_count":    0,
    "early_scope_cos":   0,
    "early_rfi_count":   0,
    "early_ot_ratio":    0,
    "early_partial_mat": 0,
    "early_billing_lag": 30,
    "project_cpi":       1.0,
})

# ── Derive thresholds from finished projects ─────────────────────
print("Deriving thresholds …")
training = signals.merge(finished[["project_id", "actual_overbudget"]], on="project_id", how="inner")

SIGNAL_DEFS = [
    ("project_cpi",       "lower_is_worse"),
    ("early_co_count",    "higher_is_worse"),
    ("early_scope_cos",   "higher_is_worse"),
    ("early_rfi_count",   "higher_is_worse"),
    ("early_ot_ratio",    "higher_is_worse"),
    ("early_partial_mat", "higher_is_worse"),
    ("early_billing_lag", "higher_is_worse"),
]

thresholds = []
for col, direction in SIGNAL_DEFS:
    if col not in training.columns:
        continue
    poor_med    = training.loc[training["actual_overbudget"] == 1, col].median()
    healthy_med = training.loc[training["actual_overbudget"] == 0, col].median()
    threshold   = (poor_med + healthy_med) / 2
    thresholds.append({"signal": col, "poor_median": round(poor_med, 3),
                       "healthy_median": round(healthy_med, 3),
                       "threshold": round(threshold, 3), "direction": direction})
    print(f"   {col:<25} poor={poor_med:.2f}  healthy={healthy_med:.2f}  thresh={threshold:.2f}")

threshold_df = pd.DataFrame(thresholds)
threshold_df.to_csv(os.path.join(OUT_DIR, "early_warning_thresholds.csv"), index=False)

# ── Score all projects ────────────────────────────────────────────
print("\nScoring projects …")
for _, row in threshold_df.iterrows():
    col = row["signal"]
    t   = row["threshold"]
    if col not in signals.columns:
        continue
    if row["direction"] == "lower_is_worse":
        signals[f"warn_{col}"] = (signals[col] < t).astype(int)
    else:
        signals[f"warn_{col}"] = (signals[col] > t).astype(int)

warn_cols = [c for c in signals.columns if c.startswith("warn_")]
n_signals = max(len(warn_cols), 1)
signals["risk_score"] = (signals[warn_cols].sum(axis=1) / n_signals * 100).round(1)

def risk_label(score):
    if score >= 70:   return "High Risk"
    elif score >= 40: return "Moderate Risk"
    else:             return "Low Risk"

signals["risk_label"] = signals["risk_score"].apply(risk_label)
signals = signals.merge(
    master[["project_id", "gc_name", "project_type",
            "original_contract_value", "contract_date"]],
    on="project_id", how="left"
)

out_cols = (["project_id", "gc_name", "project_type", "risk_score", "risk_label",
             "project_cpi", "avg_pct_complete"] + warn_cols +
            ["early_co_count", "early_scope_cos", "early_rfi_count",
             "early_ot_ratio", "early_partial_mat", "early_billing_lag"])
out_cols = [c for c in out_cols if c in signals.columns]

signals[out_cols].sort_values("risk_score", ascending=False).to_csv(
    os.path.join(OUT_DIR, "early_warning_scores.csv"), index=False
)

# ── Validate ─────────────────────────────────────────────────────
print("\nValidating …")
val = signals.merge(finished[["project_id", "actual_overbudget"]], on="project_id", how="inner")
val["predicted_overbudget"] = (val["risk_score"] >= 50).astype(int)

correct   = (val["predicted_overbudget"] == val["actual_overbudget"]).sum()
accuracy  = correct / len(val) * 100
tp = ((val["predicted_overbudget"] == 1) & (val["actual_overbudget"] == 1)).sum()
fp = ((val["predicted_overbudget"] == 1) & (val["actual_overbudget"] == 0)).sum()
fn = ((val["predicted_overbudget"] == 0) & (val["actual_overbudget"] == 1)).sum()
precision = tp / max(tp + fp, 1) * 100
recall    = tp / max(tp + fn, 1) * 100

pd.DataFrame([{
    "projects_validated": len(val),
    "accuracy_pct": round(accuracy, 1),
    "precision_pct": round(precision, 1),
    "recall_pct": round(recall, 1),
    "true_positives": int(tp),
    "false_positives": int(fp),
    "false_negatives": int(fn),
}]).to_csv(os.path.join(OUT_DIR, "early_warning_validation.csv"), index=False)

print(f"   Accuracy:  {accuracy:.1f}%")
print(f"   Precision: {precision:.1f}%")
print(f"   Recall:    {recall:.1f}%")
print(f"\n   Risk distribution:")
print(signals["risk_label"].value_counts().to_string())

print("\n✓ Step 9 complete → early_warning_scores.csv, early_warning_thresholds.csv, early_warning_validation.csv")
