"""
Step 8 — Explain Why Projects Failed
======================================
CO real column: reason_category (not 'reason'), co_number (not 'change_order_id')
CO timing real column: reason_category, project_stage

Outputs
-------
cause_effect_diagnosis.csv
chain_a_design_rework.csv
chain_b_material_shortage.csv
chain_c_rfi_standby.csv
chain_d_rejected_co.csv
chain_e_early_co_volume.csv
"""

import pandas as pd
import numpy as np
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

print("Loading inputs …")
cpi_proj  = pd.read_csv(os.path.join(OUT_DIR, "cpi_per_project.csv"),        low_memory=False)
actual    = pd.read_csv(os.path.join(OUT_DIR, "actual_cost_per_line.csv"),    low_memory=False)
co_proj   = pd.read_csv(os.path.join(OUT_DIR, "co_analysis_by_project.csv"), low_memory=False)
rfi_rec   = pd.read_csv(os.path.join(OUT_DIR, "co_rfi_recovery.csv"),        low_memory=False)
co_timing = pd.read_csv(os.path.join(OUT_DIR, "co_timing.csv"),              low_memory=False)
master    = pd.read_csv(os.path.join(OUT_DIR, "project_master.csv"),         low_memory=False)

# Poor performers: CPI < 0.85
poor = cpi_proj[cpi_proj["project_cpi"] < 0.85].copy()
poor_ids = set(poor["project_id"])
print(f"   Poor performers (CPI < 0.85): {len(poor)}")

# ── Chain A: Design Rework ────────────────────────────────────────
print("\nChain A: Design Rework …")
# reason_category is the actual column name in co_timing
design_early = co_timing[
    co_timing.get("reason_category", pd.Series(dtype=str)).isin(["Design Error", "Scope Gap"]) &
    co_timing.get("project_stage", pd.Series(dtype=str)).isin(["Early (0-20%)", "Mid (20-50%)"])
] if "reason_category" in co_timing.columns else pd.DataFrame()

if len(design_early) > 0:
    chain_a = design_early.groupby("project_id").agg(
        design_co_count=("co_number", "count"),
        design_co_value_usd=("amount", "sum"),
    ).reset_index()
    chain_a["is_poor_performer"] = chain_a["project_id"].isin(poor_ids)
    chain_a = chain_a.merge(cpi_proj[["project_id", "project_cpi"]], on="project_id", how="left")
    total_a = chain_a.loc[chain_a["is_poor_performer"], "design_co_value_usd"].sum()
else:
    chain_a = pd.DataFrame({"note": ["No design CO data in early/mid stages"]})
    total_a = 0
chain_a.to_csv(os.path.join(OUT_DIR, "chain_a_design_rework.csv"), index=False)
print(f"   Design rework loss in poor performers: ${total_a:,.0f}")

# ── Chain B: Material Shortage ───────────────────────────────────
print("\nChain B: Material Shortage …")
mat_by_proj = actual.groupby("project_id").agg(
    avg_partial_shipment_pct=("partial_shipment_rate_pct", "mean"),
    avg_ot_ratio_pct=("ot_ratio_pct", "mean"),
    total_actual_cost=("total_actual_cost", "sum"),
).reset_index()
mat_by_proj["is_poor_performer"] = mat_by_proj["project_id"].isin(poor_ids)

chain_b = mat_by_proj[mat_by_proj["avg_partial_shipment_pct"] > 40].copy()
# OT standby estimate: portion of OT cost attributable to waiting on materials
chain_b["estimated_standby_cost_usd"] = (
    chain_b["total_actual_cost"] * (chain_b["avg_ot_ratio_pct"] / 100) * 0.5
).round(0)
chain_b.to_csv(os.path.join(OUT_DIR, "chain_b_material_shortage.csv"), index=False)
total_b = chain_b.loc[chain_b["is_poor_performer"], "estimated_standby_cost_usd"].sum()
print(f"   Projects with >40% partial shipments: {len(chain_b)}")
print(f"   Estimated standby loss in poor performers: ${total_b:,.0f}")

# ── Chain C: RFI Standby ─────────────────────────────────────────
print("\nChain C: RFI Standby …")
if "cost_impact_rfis" in rfi_rec.columns:
    chain_c = rfi_rec[
        (rfi_rec["cost_impact_rfis"] > 10) & (rfi_rec["recovery_rate_pct"] < 20)
    ].copy()
    chain_c["is_poor_performer"] = chain_c["project_id"].isin(poor_ids)
    total_c = len(chain_c[chain_c["is_poor_performer"]])
else:
    chain_c = pd.DataFrame({"note": ["No RFI cost impact data"]})
    total_c = 0
chain_c.to_csv(os.path.join(OUT_DIR, "chain_c_rfi_standby.csv"), index=False)
print(f"   Projects with RFI standby pattern: {len(chain_c) if 'project_id' in chain_c.columns else 0}")

# ── Chain D: Rejected COs ─────────────────────────────────────────
print("\nChain D: Rejected COs …")
chain_d = co_proj[co_proj.get("rejected_value_usd", pd.Series(0, index=co_proj.index)).fillna(0) > 500_000].copy()
chain_d["is_poor_performer"] = chain_d["project_id"].isin(poor_ids)
chain_d.to_csv(os.path.join(OUT_DIR, "chain_d_rejected_co.csv"), index=False)
total_d = chain_d.loc[chain_d["is_poor_performer"], "rejected_value_usd"].sum() if "rejected_value_usd" in chain_d.columns else 0
print(f"   Projects with >$500K rejected: {len(chain_d)}")
print(f"   Total rejected CO loss (poor performers): ${total_d:,.0f}")

# ── Chain E: Early CO Volume ─────────────────────────────────────
print("\nChain E: Early CO volume (leading indicator) …")
if "project_stage" in co_timing.columns:
    early = co_timing[co_timing["project_stage"] == "Early (0-20%)"]
    chain_e = early.groupby("project_id").size().reset_index(name="early_co_count")
    chain_e["is_poor_performer"] = chain_e["project_id"].isin(poor_ids)
    chain_e = chain_e.merge(cpi_proj[["project_id", "project_cpi"]], on="project_id", how="left")
    chain_e.to_csv(os.path.join(OUT_DIR, "chain_e_early_co_volume.csv"), index=False)
    high_early = chain_e[chain_e["early_co_count"] > 5]
    if len(high_early) > 0:
        poor_rate    = high_early["is_poor_performer"].mean() * 100
        overall_rate = (cpi_proj["project_cpi"] < 0.85).mean() * 100
        print(f"   Projects with >5 early COs: {len(high_early)}")
        print(f"   Poor performer rate in this group: {poor_rate:.1f}% (overall: {overall_rate:.1f}%)")
else:
    pd.DataFrame({"note": ["No project_stage data"]}).to_csv(
        os.path.join(OUT_DIR, "chain_e_early_co_volume.csv"), index=False
    )

# ── Master diagnosis ──────────────────────────────────────────────
print("\nBuilding diagnosis table …")
diag = poor[["project_id", "project_cpi", "total_bac", "total_actual_cost"]].copy()
diag["cost_overrun_usd"] = diag["total_actual_cost"] - diag["total_bac"]

if "cost_impact_rfis" in rfi_rec.columns:
    diag = diag.merge(
        rfi_rec[["project_id", "cost_impact_rfis", "recovery_rate_pct"]],
        on="project_id", how="left"
    )
if "rejected_value_usd" in co_proj.columns:
    diag = diag.merge(
        co_proj[["project_id", "rejected_value_usd", "rejection_rate_pct"]],
        on="project_id", how="left"
    )

def primary_cause(row):
    rejected = row.get("rejected_value_usd") or 0
    rfi_gap  = (row.get("recovery_rate_pct") or 100) < 20 and (row.get("cost_impact_rfis") or 0) > 10
    if rejected > 100_000:  return "Rejected CO"
    elif rfi_gap:           return "RFI Standby"
    else:                   return "Cost Overrun (Other)"

diag["primary_cause"] = diag.apply(primary_cause, axis=1)
diag = diag.merge(master[["project_id", "gc_name", "project_type"]], on="project_id", how="left")
diag.to_csv(os.path.join(OUT_DIR, "cause_effect_diagnosis.csv"), index=False)

print(f"\n   Primary cause breakdown:")
print(diag["primary_cause"].value_counts().to_string())
print(f"\n   Estimated losses (poor performers):")
print(f"     Chain A (Design Rework): ${total_a:>15,.0f}")
print(f"     Chain B (Material):      ${total_b:>15,.0f}")
print(f"     Chain D (Rejected CO):   ${total_d:>15,.0f}")

print("\n✓ Step 8 complete → cause_effect_diagnosis.csv + 5 chain files")
