"""
Step 1 — Fix the Raw Data + Remove Redundant Columns
=====================================================
Standardizes messy text entries and removes columns that are either
perfectly derived from other columns or duplicated across files.

Outputs
-------
labor_logs_clean.csv
material_deliveries_clean.csv
change_orders_clean.csv
change_orders_exploded.csv
field_notes_clean.csv
billing_line_items_clean.csv
billing_history_clean.csv
step1_cleaning_report.csv
"""

import pandas as pd
import numpy as np
import re
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

report_rows = []

# ──────────────────────────────────────────────────────────────
# 1A  Labor logs — normalize role names, drop cost_code
# ──────────────────────────────────────────────────────────────
print("1A  Cleaning labor_logs …")
ll = pd.read_csv(os.path.join(DATA_DIR, "labor_logs_all.csv"), low_memory=False)

def normalize_role(raw):
    if pd.isna(raw): return raw
    rl = str(raw).strip().lower()
    if re.search(r'foreperson|foreman|forewoman|frm\b', rl):       return "Foreman"
    if re.search(r'journeyperson|journeywoman|journeyman|jman|j-man|\bjour\b', rl): return "Journeyman"
    if re.search(r'apprentice|appr?\b', rl):                       return "Apprentice"
    if re.search(r'helper|hlpr?', rl):                             return "Helper"
    if re.search(r'superintendent|supt\b|super\b', rl):            return "Superintendent"
    if re.search(r'project.?manager|proj.?mgr|\bpm\b', rl):        return "Project Manager"
    if re.search(r'engineer|\beng\b', rl):                         return "Engineer"
    if re.search(r'technician|\btech\b', rl):                      return "Technician"
    return str(raw).strip()

before = ll["role"].nunique()
ll["role"] = ll["role"].apply(normalize_role)
after = ll["role"].nunique()
report_rows.append({"file": "labor_logs", "action": "role standardization",
                    "before": before, "after": after})

# cost_code is 100% redundant with the line number in sov_line_id
if "cost_code" in ll.columns:
    ll = ll.drop(columns=["cost_code"])
    report_rows.append({"file": "labor_logs", "action": "drop cost_code (redundant with sov_line_id)",
                        "before": "present", "after": "dropped"})

ll.to_csv(os.path.join(OUT_DIR, "labor_logs_clean.csv"), index=False)
print(f"   Roles: {before} variants → {after} canonical | Rows: {len(ll):,}")

# ──────────────────────────────────────────────────────────────
# 1B  Material deliveries — normalize material_category
# ──────────────────────────────────────────────────────────────
print("1B  Cleaning material_deliveries …")
md = pd.read_csv(os.path.join(DATA_DIR, "material_deliveries_all.csv"), low_memory=False)

def normalize_category(raw):
    if pd.isna(raw): return raw
    rl = str(raw).strip().lower()
    if "duct" in rl:                    return "Ductwork"
    if "pip" in rl:                     return "Piping"
    if "equip" in rl:                   return "Equipment"
    if "control" in rl or "ctrl" in rl: return "Controls"
    if "insul" in rl:                   return "Insulation"
    return str(raw).strip()

before = md["material_category"].nunique()
md["material_category"] = md["material_category"].apply(normalize_category)
after = md["material_category"].nunique()
report_rows.append({"file": "material_deliveries", "action": "material_category standardization",
                    "before": before, "after": after})

md.to_csv(os.path.join(OUT_DIR, "material_deliveries_clean.csv"), index=False)
print(f"   Categories: {before} variants → {after} canonical | Rows: {len(md):,}")

# ──────────────────────────────────────────────────────────────
# 1C  Change orders — parse list column, explode to one row per SOV line
#     Real column names: co_number, date_submitted, reason_category, affected_sov_lines
# ──────────────────────────────────────────────────────────────
print("1C  Cleaning change_orders …")
co = pd.read_csv(os.path.join(DATA_DIR, "change_orders_all.csv"), low_memory=False)

def parse_sov_list(val):
    if pd.isna(val): return []
    val = str(val).strip().strip("[]\"'")
    if not val: return []
    parts = [p.strip().strip("\"'") for p in val.split(",")]
    return [p for p in parts if p]

co["affected_sov_lines_parsed"] = co["affected_sov_lines"].apply(parse_sov_list)
co_clean = co.drop(columns=["affected_sov_lines"])
co_clean.to_csv(os.path.join(OUT_DIR, "change_orders_clean.csv"), index=False)

co_exploded = co_clean.explode("affected_sov_lines_parsed").rename(
    columns={"affected_sov_lines_parsed": "sov_line_id"}
)
co_exploded = co_exploded[
    co_exploded["sov_line_id"].notna() & (co_exploded["sov_line_id"] != "")
]
co_exploded.to_csv(os.path.join(OUT_DIR, "change_orders_exploded.csv"), index=False)

report_rows.append({"file": "change_orders", "action": "parse + explode affected_sov_lines",
                    "before": len(co), "after": len(co_exploded)})
print(f"   {len(co):,} orders → {len(co_exploded):,} exploded rows")

# ──────────────────────────────────────────────────────────────
# 1D  Field notes — normalize note_type and weather
#     Real columns: note_type, weather (not weather_conditions)
# ──────────────────────────────────────────────────────────────
print("1D  Cleaning field_notes …")
fn = pd.read_csv(os.path.join(DATA_DIR, "field_notes_all.csv"), low_memory=False)

def normalize_note_type(raw):
    if pd.isna(raw): return raw
    rl = str(raw).strip().lower()
    if "daily"   in rl: return "Daily Report"
    if "safety"  in rl: return "Safety Log"
    if "weather" in rl: return "Weather Delay"
    if "inspect" in rl: return "Inspection"
    if "quality" in rl or rl == "qc": return "Quality Control"
    if "issue"   in rl: return "Issue Log"
    if "rfi"     in rl: return "RFI Log"
    return str(raw).strip()

def normalize_weather(raw):
    if pd.isna(raw): return raw
    rl = str(raw).strip().lower()
    if "clear" in rl or "sun"  in rl:           return "Clear"
    if "rain"  in rl or "shower" in rl:          return "Rain"
    if "snow"  in rl:                            return "Snow"
    if "cloud" in rl or "overcast" in rl:        return "Cloudy"
    if "wind"  in rl:                            return "Wind"
    if "fog"   in rl:                            return "Fog"
    if rl in ("n/a", "na", "none", ""):          return "N/A"
    return str(raw).strip()

if "note_type" in fn.columns:
    before = fn["note_type"].nunique()
    fn["note_type"] = fn["note_type"].apply(normalize_note_type)
    after = fn["note_type"].nunique()
    report_rows.append({"file": "field_notes", "action": "note_type standardization",
                        "before": before, "after": after})

weather_col = next((c for c in ["weather", "weather_conditions"] if c in fn.columns), None)
if weather_col:
    before_w = fn[weather_col].nunique()
    fn[weather_col] = fn[weather_col].apply(normalize_weather)
    after_w = fn[weather_col].nunique()
    report_rows.append({"file": "field_notes", "action": f"{weather_col} standardization",
                        "before": before_w, "after": after_w})

fn.to_csv(os.path.join(OUT_DIR, "field_notes_clean.csv"), index=False)
print(f"   Field notes cleaned: {len(fn):,} rows")

# ──────────────────────────────────────────────────────────────
# 1E  Billing line items — drop derived and cross-file duplicate columns
#     Real columns: sov_line_id, description, scheduled_value,
#                   previous_billed, this_period, total_billed,
#                   pct_complete, balance_to_finish, project_id, application_number
# ──────────────────────────────────────────────────────────────
print("1E  Cleaning billing_line_items — removing redundant columns …")
bl = pd.read_csv(os.path.join(DATA_DIR, "billing_line_items_all.csv"), low_memory=False)

# Flag rows where pct_complete differs from derived value by > 0.01%
# (evidence of a manual override — preserve this signal as a flag)
if all(c in bl.columns for c in ["pct_complete", "total_billed", "scheduled_value"]):
    derived_pct = (bl["total_billed"] / bl["scheduled_value"].replace(0, np.nan)) * 100
    bl["pct_manually_adjusted"] = (bl["pct_complete"] - derived_pct).abs() > 0.01
    n_manual = bl["pct_manually_adjusted"].sum()
    report_rows.append({"file": "billing_line_items", "action": "flag pct_manually_adjusted",
                        "before": "no flag", "after": f"{n_manual} rows flagged"})
    print(f"   {n_manual:,} rows with manually-adjusted pct_complete flagged")

# Drop perfectly derived columns (recomputed on demand from their source columns)
# total_billed        = previous_billed + this_period
# balance_to_finish   = scheduled_value - total_billed
# Drop cross-file duplicates (sov_all.csv is the authoritative source)
# scheduled_value, description
DROP_COLS = [c for c in ["total_billed", "balance_to_finish", "scheduled_value", "description"]
             if c in bl.columns]
if DROP_COLS:
    bl = bl.drop(columns=DROP_COLS)
    report_rows.append({"file": "billing_line_items",
                        "action": f"dropped redundant cols: {DROP_COLS}",
                        "before": "present", "after": "dropped"})
    print(f"   Dropped: {DROP_COLS}")

bl.to_csv(os.path.join(OUT_DIR, "billing_line_items_clean.csv"), index=False)
print(f"   billing_line_items saved: {len(bl):,} rows, {bl.shape[1]} columns")

# ──────────────────────────────────────────────────────────────
# 1F  Billing history — drop perfectly derived columns
#     Real columns: project_id, application_number, period_end,
#                   period_total, cumulative_billed, retention_held,
#                   net_payment_due, status, payment_date, line_item_count
# ──────────────────────────────────────────────────────────────
print("1F  Cleaning billing_history — removing redundant columns …")
bh = pd.read_csv(os.path.join(DATA_DIR, "billing_history_all.csv"), low_memory=False)

# retention_held   = cumulative_billed × 0.10  (100% match)
# net_payment_due  = cumulative_billed − retention_held  (100% match)
BH_DROP = [c for c in ["retention_held", "net_payment_due"] if c in bh.columns]
if BH_DROP:
    bh = bh.drop(columns=BH_DROP)
    report_rows.append({"file": "billing_history",
                        "action": f"dropped derived cols: {BH_DROP}",
                        "before": "present", "after": "dropped"})
    print(f"   Dropped: {BH_DROP}")

bh.to_csv(os.path.join(OUT_DIR, "billing_history_clean.csv"), index=False)
print(f"   billing_history saved: {len(bh):,} rows, {bh.shape[1]} columns")

# ──────────────────────────────────────────────────────────────
# Save cleaning report
# ──────────────────────────────────────────────────────────────
report_df = pd.DataFrame(report_rows)
report_df.to_csv(os.path.join(OUT_DIR, "step1_cleaning_report.csv"), index=False)

print("\n✓ Step 1 complete")
print(report_df.to_string(index=False))
