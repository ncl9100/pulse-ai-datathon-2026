"""
run_all.py — Master Pipeline Runner
=====================================
Runs all 9 analysis steps in order, then organizes the outputs into folders.
"""

import subprocess
import sys
import time
import os

STEPS = [
    ("Step 1",  "step1_data_cleaning.py"),
    ("Step 2",  "step2_project_master_table.py"),
    ("Step 3",  "step3_actual_cost_per_sov_line.py"),
    ("Step 4",  "step4_billing_progress.py"),
    ("Step 5",  "step5_cost_performance_index.py"),
    ("Step 6",  "step6_change_order_analysis.py"),
    ("Step 7",  "step7_cash_flow_analysis.py"),
    ("Step 8",  "step8_cause_effect_chains.py"),
    ("Step 9",  "step9_early_warning_model.py"),
    ("Organize", "organize_outputs.py"),
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
results = []
total_start = time.time()

print("=" * 60)
print("  DATATHON ANALYSIS PIPELINE")
print("=" * 60)

for label, script in STEPS:
    script_path = os.path.join(SCRIPT_DIR, script)
    print(f"\n{'─'*60}")
    print(f"  Running {label}: {script}")
    print(f"{'─'*60}")

    step_start = time.time()
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=False,
        text=True,
    )
    elapsed = time.time() - step_start

    status = "✓ PASS" if result.returncode == 0 else "✗ FAIL"
    results.append((label, script, status, f"{elapsed:.1f}s"))

    if result.returncode != 0:
        print(f"\n  {status} — {elapsed:.1f}s")
        print("  Pipeline stopped due to error.")
        break
    else:
        print(f"\n  {status} — {elapsed:.1f}s")

total_elapsed = time.time() - total_start

print(f"\n{'='*60}")
print("  PIPELINE SUMMARY")
print(f"{'='*60}")
for label, script, status, t in results:
    print(f"  {status}  {label:<12} {script:<45} {t:>8}")
print(f"\n  Total time: {total_elapsed:.1f}s")
print("=" * 60)
