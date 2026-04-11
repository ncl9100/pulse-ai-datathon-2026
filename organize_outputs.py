"""
organize_outputs.py
====================
Moves all output CSVs from outputs/ into named subfolders with README files.
"""

import os
import shutil

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")

FOLDERS = {
    "01_cleaned_data": {
        "files": [
            "labor_logs_clean.csv",
            "material_deliveries_clean.csv",
            "change_orders_clean.csv",
            "change_orders_exploded.csv",
            "field_notes_clean.csv",
            "billing_line_items_clean.csv",
            "billing_history_clean.csv",
            "step1_cleaning_report.csv",
        ],
        "readme": (
            "CLEANED DATA\n"
            "=============\n"
            "Standardized raw files from Step 1.\n\n"
            "Key changes vs. raw files:\n"
            "  - labor_logs:          30+ role name variants → 8 canonical; cost_code column dropped (redundant)\n"
            "  - material_deliveries: 25+ category variants → 5 canonical\n"
            "  - change_orders:       affected_sov_lines parsed from string list; exploded version = one row per SOV line\n"
            "  - field_notes:         note_type and weather_conditions standardized\n"
            "  - billing_line_items:  balance_to_finish, total_billed, scheduled_value, description dropped (redundant);\n"
            "                         pct_manually_adjusted flag added where pct differs from derived value\n"
            "  - billing_history:     retention_held, net_payment_due dropped (perfectly derived from cumulative_billed)\n"
        ),
    },
    "02_project_baseline": {
        "files": ["project_master.csv"],
        "readme": (
            "PROJECT BASELINE\n"
            "=================\n"
            "One row per project. Built from contracts + SOV budget + change orders.\n\n"
            "Key columns:\n"
            "  original_contract_value  : signed contract price\n"
            "  total_estimated_cost     : sum of all estimated labor + material\n"
            "  builtin_margin_usd/pct   : how much profit margin was in the original price\n"
            "  revised_contract_value   : original + all approved change orders\n"
            "  co_rejection_rate_pct    : % of change orders rejected by the GC\n"
            "  project_type             : Small / Medium / Large / Mega\n"
        ),
    },
    "03_cost_performance": {
        "files": [
            "actual_cost_per_line.csv",
            "billing_progress.csv",
            "billing_timeline.csv",
            "cpi_per_line.csv",
            "cpi_per_project.csv",
        ],
        "readme": (
            "COST PERFORMANCE\n"
            "=================\n"
            "Earned Value Management metrics per SOV line and per project.\n\n"
            "  actual_cost_per_line : labor + material actual cost vs. budget per scope\n"
            "  billing_progress     : latest % complete per scope (from most recent billing app)\n"
            "  billing_timeline     : all billing applications per project over time\n"
            "  cpi_per_line         : CPI, EAC, VAC per scope\n"
            "  cpi_per_project      : rolled-up project CPI; status = Efficient/On Track/Watch/At Risk/Critical\n\n"
            "Note: retention_held and net_payment_due in billing_timeline are recomputed\n"
            "from cumulative_billed × 10% (authoritative formula).\n"
        ),
    },
    "04_billing_cash_flow": {
        "files": [
            "cash_flow_summary.csv",
            "overdue_applications.csv",
            "retention_analysis.csv",
        ],
        "readme": (
            "BILLING & CASH FLOW\n"
            "====================\n"
            "Payment timing, overdue invoices, and unreleased retention.\n\n"
            "  cash_flow_summary    : per-project billing totals and payment lag stats\n"
            "  overdue_applications : invoices past due date, sorted by days overdue\n"
            "  retention_analysis   : projects with retention still held past completion date\n"
        ),
    },
    "05_change_orders": {
        "files": [
            "co_analysis_by_project.csv",
            "co_analysis_by_gc.csv",
            "co_rfi_recovery.csv",
            "co_timing.csv",
        ],
        "readme": (
            "CHANGE ORDER ANALYSIS\n"
            "======================\n"
            "  co_analysis_by_project : approved/rejected CO totals and recovery rate per project\n"
            "  co_analysis_by_gc      : which GCs reject most, and their top rejection reasons\n"
            "  co_rfi_recovery        : cost-flagged RFIs and how many became approved COs\n"
            "  co_timing              : when in the project lifecycle COs were filed\n"
        ),
    },
    "06_root_cause": {
        "files": [
            "cause_effect_diagnosis.csv",
            "chain_a_design_rework.csv",
            "chain_b_material_shortage.csv",
            "chain_c_rfi_standby.csv",
            "chain_d_rejected_co.csv",
            "chain_e_early_co_volume.csv",
        ],
        "readme": (
            "ROOT CAUSE DIAGNOSIS\n"
            "=====================\n"
            "For the 85+ worst-performing projects, identifies the primary cause of loss.\n\n"
            "  cause_effect_diagnosis : one row per poor performer; primary_cause label + cost overrun\n"
            "  chain_a_*              : projects hit by design rework losses\n"
            "  chain_b_*              : projects hit by material shortage / OT standby\n"
            "  chain_c_*              : projects where RFI cost impacts went unrecovered\n"
            "  chain_d_*              : projects with large rejected CO values\n"
            "  chain_e_*              : projects with high early-phase CO volume (leading indicator)\n"
        ),
    },
    "07_early_warning": {
        "files": [
            "early_warning_scores.csv",
            "early_warning_thresholds.csv",
            "early_warning_validation.csv",
        ],
        "readme": (
            "EARLY WARNING MODEL\n"
            "====================\n"
            "Risk scores for every project using only data from the first 20% of the timeline.\n\n"
            "  early_warning_scores     : 0–100 risk score + High/Moderate/Low label per project\n"
            "  early_warning_thresholds : the 7 signal thresholds derived from historical data\n"
            "  early_warning_validation : accuracy/precision/recall on completed projects\n"
        ),
    },
}

print("Organizing outputs into subfolders …\n")

for folder, config in FOLDERS.items():
    folder_path = os.path.join(OUT_DIR, folder)
    os.makedirs(folder_path, exist_ok=True)

    moved = 0
    for fname in config["files"]:
        src = os.path.join(OUT_DIR, fname)
        dst = os.path.join(folder_path, fname)
        if os.path.exists(src):
            shutil.move(src, dst)
            moved += 1
        elif os.path.exists(dst):
            pass  # already there
        else:
            print(f"   [MISSING] {fname}")

    with open(os.path.join(folder_path, "README.txt"), "w") as f:
        f.write(config["readme"])

    print(f"   {folder}/ — {moved} files moved")

print("\n✓ Outputs organized.")
