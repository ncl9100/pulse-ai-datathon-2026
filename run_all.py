"""
RUN ALL — Master Pipeline Runner
==================================
Purpose:
    Executes all 9 analysis steps in the correct dependency order.
    Each step's outputs are consumed by later steps, so the sequence matters.

    Run this file from the analysis/ folder to execute the full pipeline:
        python run_all.py

    Or run individual steps:
        python step1_data_cleaning.py
        python step3_actual_cost_per_sov_line.py
        etc.

    Steps and their outputs:
        Step 1  → outputs/labor_logs_clean.csv
                  outputs/material_deliveries_clean.csv
                  outputs/change_orders_clean.csv
                  outputs/change_orders_exploded.csv
                  outputs/field_notes_clean.csv
                  outputs/step1_cleaning_report.csv

        Step 2  → outputs/project_master.csv

        Step 3  → outputs/actual_cost_per_line.csv       [heavy: 1.2M rows]

        Step 4  → outputs/billing_progress.csv
                  outputs/billing_timeline.csv

        Step 5  → outputs/cpi_per_line.csv
                  outputs/cpi_per_project.csv

        Step 6  → outputs/co_analysis_by_project.csv
                  outputs/co_analysis_by_gc.csv
                  outputs/co_rfi_recovery.csv
                  outputs/co_timing.csv

        Step 7  → outputs/cash_flow_summary.csv
                  outputs/overdue_applications.csv
                  outputs/retention_analysis.csv

        Step 8  → outputs/cause_effect_diagnosis.csv
                  outputs/chain_A_design_rework.csv
                  outputs/chain_B_material_idle.csv
                  outputs/chain_C_rfi_standby.csv
                  outputs/chain_D_rejected_co_loss.csv
                  outputs/chain_E_early_cos.csv

        Step 9  → outputs/early_warning_scores.csv
                  outputs/early_warning_thresholds.csv
                  outputs/early_warning_validation.csv

    Expected runtime: 3–7 minutes (Step 3 and Step 9 are the slowest due to
    the 1.2M-row labor log file).
"""

import subprocess
import sys
import os
import time

STEPS = [
    ("Step 1 — Data Cleaning",            "step1_data_cleaning.py"),
    ("Step 2 — Project Master Table",      "step2_project_master_table.py"),
    ("Step 3 — Actual Cost Per SOV Line",  "step3_actual_cost_per_sov_line.py"),
    ("Step 4 — Billing Progress",          "step4_billing_progress.py"),
    ("Step 5 — Cost Performance Index",    "step5_cost_performance_index.py"),
    ("Step 6 — Change Order Analysis",     "step6_change_order_analysis.py"),
    ("Step 7 — Cash Flow Analysis",        "step7_cash_flow_analysis.py"),
    ("Step 8 — Cause-and-Effect Chains",   "step8_cause_effect_chains.py"),
    ("Step 9 — Early Warning Model",       "step9_early_warning_model.py"),
]

script_dir = os.path.dirname(os.path.abspath(__file__))
results = []
pipeline_start = time.time()

print("=" * 60)
print("  DATATHON ANALYSIS PIPELINE")
print("=" * 60)

for label, script in STEPS:
    print(f"\n{'─'*60}")
    print(f"  Running: {label}")
    print(f"{'─'*60}")
    start = time.time()

    result = subprocess.run(
        [sys.executable, os.path.join(script_dir, script)],
        cwd=script_dir,
        capture_output=False,
    )

    elapsed = time.time() - start
    status  = "✓ PASSED" if result.returncode == 0 else "✗ FAILED"
    results.append((label, status, f"{elapsed:.1f}s"))
    print(f"\n  {status}  ({elapsed:.1f}s)")

total = time.time() - pipeline_start
print(f"\n{'='*60}")
print(f"  PIPELINE COMPLETE — {total:.0f}s total")
print(f"{'='*60}")
for label, status, t in results:
    print(f"  {status}  {t:>7}   {label}")

failed = [r for r in results if "FAILED" in r[1]]
if failed:
    print(f"\n  {len(failed)} step(s) failed. Check output above for error details.")
    sys.exit(1)
else:
    print(f"\n  All steps passed. Outputs are in: analysis/outputs/")
