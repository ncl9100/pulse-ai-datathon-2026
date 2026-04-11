"""
STEP 9 — EARLY WARNING MODEL
==============================
Purpose:
    Use completed projects as training data to identify which signals, observable
    in the first 20% of a project's duration, most strongly predict whether
    the project will finish with a poor CPI (below 0.85).

    This converts all previous retrospective analysis into a forward-looking tool.
    When a new project starts, you can score it against these early signals and
    flag it for proactive intervention before significant losses accumulate.

    Signals tested (all measured in weeks 1 through ~20% of planned duration):
        1. Early CO count and rejection rate
        2. RFI volume and cost-impact rate
        3. Overtime ratio in labor logs
        4. Partial shipment rate in material deliveries
        5. Upstream design CO percentage (Scope Gap + Design Error as % of all COs)

    Method:
        Step 1 — Split projects into "poor" (CPI < 0.85) vs "healthy" (CPI ≥ 0.85)
        Step 2 — Compute each signal for each project using only early-period data
        Step 3 — Compare signal distributions between the two groups
        Step 4 — Assign a 0–100 risk score to each project based on thresholds
        Step 5 — Validate: for completed projects, check how often a high risk score
                 predicted the actual outcome

    Note: this is a rule-based scoring model (not machine learning) so it is
    fully interpretable — every point in the score can be explained to a client.

Depends on:
    outputs/cpi_per_project.csv          ← from Step 5
    outputs/project_master.csv           ← from Step 2
    outputs/change_orders_clean.csv      ← from Step 1
    ../rfis_all.csv
    outputs/labor_logs_clean.csv         ← from Step 1 (or raw)
    outputs/material_deliveries_clean.csv ← from Step 1

Output:
    outputs/early_warning_scores.csv     — risk score for every project
    outputs/early_warning_thresholds.csv — the signal thresholds derived from data
    outputs/early_warning_validation.csv — accuracy of the model on completed projects
"""

import pandas as pd
import numpy as np
import os

BASE = os.path.join(os.path.dirname(__file__), "..")
OUT  = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUT, exist_ok=True)

# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading data ...")
cpi_proj = pd.read_csv(os.path.join(OUT, "cpi_per_project.csv"))
master   = pd.read_csv(os.path.join(OUT, "project_master.csv"),
                       parse_dates=["contract_date","substantial_completion_date"])
cos      = pd.read_csv(os.path.join(OUT, "change_orders_clean.csv"), parse_dates=["date_submitted"])
rfis     = pd.read_csv(os.path.join(BASE, "rfis_all.csv"), parse_dates=["date_submitted","date_required"])

labor_path = os.path.join(OUT, "labor_logs_clean.csv")
if not os.path.exists(labor_path):
    labor_path = os.path.join(BASE, "labor_logs_all.csv")
labor = pd.read_csv(labor_path, parse_dates=["date"],
                    dtype={"hours_st":float,"hours_ot":float})

mats_path = os.path.join(OUT, "material_deliveries_clean.csv")
if not os.path.exists(mats_path):
    mats_path = os.path.join(BASE, "material_deliveries_all.csv")
mats = pd.read_csv(mats_path, parse_dates=["date"])

cos["amount_float"] = pd.to_numeric(cos["amount"], errors="coerce").fillna(0)

# ── 9A: Define early-period cutoff per project (first 20% of duration) ────────
print("Defining early-period windows ...")
master["early_period_end"] = master["contract_date"] + pd.to_timedelta(
    master["original_duration_days"] * 0.20, unit="D"
)

# ── 9B: Compute early-period signals for each project ─────────────────────────
print("Computing early-period signals (this may take ~30 seconds) ...")

# Signal 1: Early CO count, rejection rate, upstream design %
cos_with_dates = cos.merge(
    master[["project_id","contract_date","early_period_end","original_duration_days"]],
    on="project_id", how="left"
)
cos_with_dates["is_early"] = cos_with_dates["date_submitted"] <= cos_with_dates["early_period_end"]
early_cos = cos_with_dates[cos_with_dates["is_early"]]

sig1 = early_cos.groupby("project_id").apply(lambda df: pd.Series({
    "early_co_count":           len(df),
    "early_co_rejection_rate_%": (df["status"] == "Rejected").sum() / len(df) * 100 if len(df) > 0 else 0,
    "early_upstream_design_%":  ((df["reason_category"].isin(["Scope Gap","Design Error"])).sum()
                                  / len(df) * 100) if len(df) > 0 else 0,
})).reset_index()

# Signal 2: RFI volume and cost-impact rate in early period
rfis_with_dates = rfis.merge(
    master[["project_id","contract_date","early_period_end"]],
    on="project_id", how="left"
)
rfis_with_dates["is_early"] = rfis_with_dates["date_submitted"] <= rfis_with_dates["early_period_end"]
early_rfis = rfis_with_dates[rfis_with_dates["is_early"]]

sig2 = early_rfis.groupby("project_id").apply(lambda df: pd.Series({
    "early_rfi_count":           len(df),
    "early_rfi_cost_impact_%":  (df["cost_impact"] == True).sum() / len(df) * 100 if len(df) > 0 else 0,
})).reset_index()

# Signal 3: Overtime ratio in early labor logs
labor_with_dates = labor.merge(
    master[["project_id","contract_date","early_period_end"]],
    on="project_id", how="left"
)
labor_with_dates["is_early"] = labor_with_dates["date"] <= labor_with_dates["early_period_end"]
early_labor = labor_with_dates[labor_with_dates["is_early"]]

sig3 = early_labor.groupby("project_id").apply(lambda df: pd.Series({
    "early_ot_ratio_%": df["hours_ot"].sum() / (df["hours_st"] + df["hours_ot"]).sum() * 100
                        if (df["hours_st"] + df["hours_ot"]).sum() > 0 else 0,
})).reset_index()

# Signal 4: Partial shipment rate in early material deliveries
mats_with_dates = mats.merge(
    master[["project_id","contract_date","early_period_end"]],
    on="project_id", how="left"
)
mats_with_dates["is_early"] = mats_with_dates["date"] <= mats_with_dates["early_period_end"]
early_mats = mats_with_dates[mats_with_dates["is_early"]]

sig4 = early_mats.groupby("project_id").apply(lambda df: pd.Series({
    "early_partial_shipment_%": (df["condition_notes"] == "Partial shipment - backorder pending").sum()
                                 / len(df) * 100 if len(df) > 0 else 0,
})).reset_index()

# ── 9C: Combine signals and label outcomes ────────────────────────────────────
print("Combining signals ...")
signals = master[["project_id"]].copy()
for sig in [sig1, sig2, sig3, sig4]:
    signals = signals.merge(sig, on="project_id", how="left")
signals = signals.fillna(0)
signals = signals.merge(
    cpi_proj[["project_id","project_cpi","project_cpi_flag"]],
    on="project_id", how="left"
)

# Outcome label: 1 = poor performer (CPI < 0.85), 0 = healthy
signals["is_poor_performer"] = (signals["project_cpi"] < 0.85).astype(int)

# ── 9D: Find signal thresholds (median split between poor vs healthy) ─────────
print("Finding signal thresholds ...")
poor    = signals[signals["is_poor_performer"] == 1]
healthy = signals[signals["is_poor_performer"] == 0]

signal_cols = [
    "early_co_count", "early_co_rejection_rate_%", "early_upstream_design_%",
    "early_rfi_count", "early_rfi_cost_impact_%",
    "early_ot_ratio_%", "early_partial_shipment_%"
]

thresholds = []
for col in signal_cols:
    poor_median    = poor[col].median()
    healthy_median = healthy[col].median()
    threshold      = (poor_median + healthy_median) / 2
    separation     = abs(poor_median - healthy_median)
    thresholds.append({
        "signal":          col,
        "poor_median":     round(poor_median, 2),
        "healthy_median":  round(healthy_median, 2),
        "threshold":       round(threshold, 2),
        "separation":      round(separation, 2),
        "higher_means_risk": poor_median > healthy_median,
    })

thresh_df = pd.DataFrame(thresholds).sort_values("separation", ascending=False)
thresh_df.to_csv(os.path.join(OUT, "early_warning_thresholds.csv"), index=False)

print("\n  Signal thresholds (ranked by separation power):")
print(thresh_df.to_string(index=False))

# ── 9E: Score each project 0–100 ──────────────────────────────────────────────
print("\nScoring all projects ...")

# Each signal contributes up to (100 / n_signals) points
n_signals  = len(signal_cols)
pts_each   = 100 / n_signals

def score_project(row, thresh_df):
    score = 0
    for _, t in thresh_df.iterrows():
        col = t["signal"]
        val = row.get(col, 0)
        if pd.isna(val): continue
        if t["higher_means_risk"]:
            if val > t["threshold"]:
                score += pts_each
        else:
            if val < t["threshold"]:
                score += pts_each
    return round(score, 1)

signals["risk_score_0_100"] = signals.apply(
    lambda r: score_project(r, thresh_df), axis=1
)

signals["risk_category"] = pd.cut(
    signals["risk_score_0_100"],
    bins=[-1, 30, 55, 75, 101],
    labels=["Low Risk (0–30)", "Moderate (30–55)", "Elevated (55–75)", "High Risk (75–100)"]
)

# ── 9F: Validate on projects where CPI is known ───────────────────────────────
print("Validating model ...")
known = signals[signals["project_cpi"].notna()].copy()
known["predicted_poor"] = known["risk_score_0_100"] >= 55  # threshold for flagging

true_pos  = ((known["predicted_poor"] == True)  & (known["is_poor_performer"] == 1)).sum()
true_neg  = ((known["predicted_poor"] == False) & (known["is_poor_performer"] == 0)).sum()
false_pos = ((known["predicted_poor"] == True)  & (known["is_poor_performer"] == 0)).sum()
false_neg = ((known["predicted_poor"] == False) & (known["is_poor_performer"] == 1)).sum()

precision = true_pos / (true_pos + false_pos) if (true_pos + false_pos) > 0 else 0
recall    = true_pos / (true_pos + false_neg) if (true_pos + false_neg) > 0 else 0
accuracy  = (true_pos + true_neg) / len(known) if len(known) > 0 else 0

validation = pd.DataFrame([{
    "true_positives":  true_pos,  "true_negatives":  true_neg,
    "false_positives": false_pos, "false_negatives": false_neg,
    "precision_%":     round(precision*100, 1),
    "recall_%":        round(recall*100, 1),
    "accuracy_%":      round(accuracy*100, 1),
    "flag_threshold_score": 55,
    "total_projects_evaluated": len(known),
}])
validation.to_csv(os.path.join(OUT, "early_warning_validation.csv"), index=False)

# ── Save final scores ─────────────────────────────────────────────────────────
out_cols = ["project_id"] + signal_cols + [
    "risk_score_0_100", "risk_category", "project_cpi", "is_poor_performer"
]
signals[out_cols].to_csv(os.path.join(OUT, "early_warning_scores.csv"), index=False)

print(f"\n✓ Step 9 complete.")
print(f"  outputs/early_warning_scores.csv      — {len(signals)} projects scored")
print(f"  outputs/early_warning_thresholds.csv  — {len(thresh_df)} signal thresholds")
print(f"  outputs/early_warning_validation.csv  — model accuracy metrics")
print(f"\n  Risk category distribution:")
print(signals["risk_category"].value_counts())
print(f"\n  Model validation (flag threshold = 55 / 100):")
print(f"    Accuracy:  {accuracy*100:.1f}%")
print(f"    Precision: {precision*100:.1f}%  (of flagged projects, % that were actually poor)")
print(f"    Recall:    {recall*100:.1f}%   (of poor projects, % the model caught)")
print(f"\n  High Risk projects (score ≥ 75):")
high_risk = signals[signals["risk_score_0_100"] >= 75].sort_values("risk_score_0_100", ascending=False)
print(f"    Count: {len(high_risk)}")
if len(high_risk) > 0:
    print(high_risk[["project_id","risk_score_0_100","project_cpi"]].head(10).to_string(index=False))
