"""
STEP 1 — DATA CLEANING
======================
Purpose:
    Fix dirty data in labor_logs and material_deliveries before any grouping
    or calculation. The same real-world role (e.g. Journeyman Pipefitter) appears
    under 5–6 different name variants. The same material category (e.g. Equipment)
    appears under 8+ variants. Leaving these unfixed means any GROUP BY on role or
    category silently undercounts.

    Also parses the affected_sov_lines column in change_orders, which is stored as
    a Python-list string (e.g. "['PRJ-2024-001-SOV-04', 'PRJ-2024-001-SOV-14']")
    and must be exploded into one row per affected line before joining.

    Finally flags and removes known data entry errors in field_notes.

Inputs (from ../):
    labor_logs_all.csv
    material_deliveries_all.csv
    change_orders_all.csv
    field_notes_all.csv

Outputs (to outputs/):
    labor_logs_clean.csv           — standardized role names
    material_deliveries_clean.csv  — standardized category names
    change_orders_clean.csv        — affected_sov_lines parsed into individual rows
    change_orders_exploded.csv     — one row per (co_number, affected_sov_line)
    field_notes_clean.csv          — bad weather values and anomalous note_types removed
    step1_cleaning_report.csv      — summary of every fix applied and how many rows it touched
"""

import pandas as pd
import ast
import os

# ── Paths ────────────────────────────────────────────────────────────────────
BASE   = os.path.join(os.path.dirname(__file__), "..")
OUT    = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUT, exist_ok=True)

report_rows = []   # collects one dict per cleaning action for the summary report

# ─────────────────────────────────────────────────────────────────────────────
# 1A — LABOR LOGS: standardize role names
# ─────────────────────────────────────────────────────────────────────────────
print("Cleaning labor_logs_all.csv ...")
labor = pd.read_csv(os.path.join(BASE, "labor_logs_all.csv"))

ROLE_MAP = {
    # Journeyman Pipefitter variants
    "JM Pipefitter":       "Journeyman Pipefitter",
    "J. Pipefitter":       "Journeyman Pipefitter",
    "Pipefitter JM":       "Journeyman Pipefitter",
    "Journeyman P.F.":     "Journeyman Pipefitter",
    # Journeyman Sheet Metal variants
    "Sheet Metal JM":      "Journeyman Sheet Metal",
    "J. Sheet Metal":      "Journeyman Sheet Metal",
    "JM Sheet Metal":      "Journeyman Sheet Metal",
    "Journeyman S.M.":     "Journeyman Sheet Metal",
    "Journeyman S.M":      "Journeyman Sheet Metal",
    # Apprentice 2nd Year variants
    "Apprentice 2nd Yr":   "Apprentice 2nd Year",
    "App 2nd Year":        "Apprentice 2nd Year",
    "Apprentice - 2nd":    "Apprentice 2nd Year",
    # Apprentice 4th Year variants
    "Apprentice 4th Yr":   "Apprentice 4th Year",
    "App 4th Year":        "Apprentice 4th Year",
    "Apprentice - 4th":    "Apprentice 4th Year",
    "4th Yr Apprentice":   "Apprentice 4th Year",
    # Controls Technician variants
    "Controls Tech":       "Controls Technician",
    "DDC Tech":            "Controls Technician",
    "Ctrl Technician":     "Controls Technician",
    "Controls Specialist": "Controls Technician",
    "Apprentice Controls": "Controls Technician",
    # Foreman variants
    "Fmn":                 "Foreman",
    "Lead Foreman":        "Foreman",
    "General Foreman":     "Foreman",
    # Helper variants
    "Helper":              "Helper/Laborer",
}

before_counts = labor["role"].value_counts().to_dict()
labor["role"] = labor["role"].replace(ROLE_MAP)
after_counts  = labor["role"].value_counts().to_dict()

rows_changed = (labor["role"].isin(ROLE_MAP.values())).sum()
report_rows.append({
    "file": "labor_logs_all.csv",
    "column": "role",
    "action": "Standardized role name variants to 8 canonical names",
    "rows_affected": sum(before_counts.get(k, 0) for k in ROLE_MAP),
    "unique_values_before": len(before_counts),
    "unique_values_after": len(after_counts),
})

labor.to_csv(os.path.join(OUT, "labor_logs_clean.csv"), index=False)
print(f"  → {sum(before_counts.get(k,0) for k in ROLE_MAP):,} role name rows standardized")
print(f"  → Saved: outputs/labor_logs_clean.csv")


# ─────────────────────────────────────────────────────────────────────────────
# 1B — MATERIAL DELIVERIES: standardize category names
# ─────────────────────────────────────────────────────────────────────────────
print("\nCleaning material_deliveries_all.csv ...")
mats = pd.read_csv(os.path.join(BASE, "material_deliveries_all.csv"))

def standardize_category(val):
    """Map all variants to one of 5 canonical categories."""
    v = str(val).strip().lower()
    if v in ("ductwork", "duct work", "duct"):
        return "Ductwork"
    if v in ("piping", "pipe", "piping systems"):
        return "Piping"
    if v in ("equipment", "equip.", "equip", "equipmnt"):
        return "Equipment"
    if v in ("controls", "control", "controls/bas", "ddccontrols", "bas"):
        return "Controls"
    if v in ("insulation", "insul.", "insul"):
        return "Insulation"
    return val  # leave unchanged if not recognized (flag for review)

before_unique = mats["material_category"].nunique()
mats["material_category"] = mats["material_category"].apply(standardize_category)
after_unique  = mats["material_category"].nunique()

non_standard = mats[~mats["material_category"].isin(
    ["Ductwork","Piping","Equipment","Controls","Insulation"]
)]

report_rows.append({
    "file": "material_deliveries_all.csv",
    "column": "material_category",
    "action": "Standardized category variants to 5 canonical names",
    "rows_affected": len(mats) - len(non_standard),
    "unique_values_before": before_unique,
    "unique_values_after": after_unique,
})

mats.to_csv(os.path.join(OUT, "material_deliveries_clean.csv"), index=False)
print(f"  → {len(mats) - len(non_standard):,} category rows standardized")
if len(non_standard) > 0:
    print(f"  → {len(non_standard)} rows left non-standard (review manually):")
    print(non_standard["material_category"].value_counts())
print(f"  → Saved: outputs/material_deliveries_clean.csv")


# ─────────────────────────────────────────────────────────────────────────────
# 1C — CHANGE ORDERS: parse affected_sov_lines and explode
# ─────────────────────────────────────────────────────────────────────────────
print("\nCleaning change_orders_all.csv ...")
cos = pd.read_csv(os.path.join(BASE, "change_orders_all.csv"))

def parse_sov_list(val):
    """Convert "['SOV-01', 'SOV-02']" string into a Python list."""
    if pd.isna(val) or val == "":
        return []
    try:
        parsed = ast.literal_eval(val)
        return parsed if isinstance(parsed, list) else [str(parsed)]
    except Exception:
        # fallback: strip brackets and split manually
        cleaned = str(val).replace("[","").replace("]","").replace("'","").replace('"',"")
        return [s.strip() for s in cleaned.split(",") if s.strip()]

cos["affected_sov_lines_parsed"] = cos["affected_sov_lines"].apply(parse_sov_list)
cos["affected_sov_line_count"]   = cos["affected_sov_lines_parsed"].apply(len)

# Clean version: keep the list column for reference
cos_clean = cos.drop(columns=["affected_sov_lines"])
cos_clean = cos_clean.rename(columns={"affected_sov_lines_parsed": "affected_sov_lines"})
cos_clean.to_csv(os.path.join(OUT, "change_orders_clean.csv"), index=False)

# Exploded version: one row per (project_id, co_number, sov_line_id)
cos_exploded = cos_clean.explode("affected_sov_lines").rename(
    columns={"affected_sov_lines": "affected_sov_line_id"}
)
cos_exploded = cos_exploded.dropna(subset=["affected_sov_line_id"])
cos_exploded.to_csv(os.path.join(OUT, "change_orders_exploded.csv"), index=False)

report_rows.append({
    "file": "change_orders_all.csv",
    "column": "affected_sov_lines",
    "action": "Parsed list-string into Python list; exploded to one row per SOV line",
    "rows_affected": len(cos),
    "unique_values_before": "N/A (string lists)",
    "unique_values_after": f"{len(cos_exploded)} exploded rows",
})
print(f"  → {len(cos):,} change orders → {len(cos_exploded):,} exploded rows")
print(f"  → Saved: outputs/change_orders_clean.csv")
print(f"  → Saved: outputs/change_orders_exploded.csv")


# ─────────────────────────────────────────────────────────────────────────────
# 1D — FIELD NOTES: fix data entry errors
# ─────────────────────────────────────────────────────────────────────────────
print("\nCleaning field_notes_all.csv ...")
notes = pd.read_csv(os.path.join(BASE, "field_notes_all.csv"))

VALID_WEATHER    = {"Clear","Cloudy","Partly Cloudy","Cold","Rain","Hot"}
VALID_NOTE_TYPES = {"Daily Report","Coordination Note","Issue Log","Safety Log","Inspection Note"}

# Fix weather = "RFI-042" (data entry error — set to null)
bad_weather = ~notes["weather"].isin(VALID_WEATHER) & notes["weather"].notna() & (notes["weather"] != "")
report_rows.append({
    "file": "field_notes_all.csv",
    "column": "weather",
    "action": "Set invalid weather values to NaN",
    "rows_affected": int(bad_weather.sum()),
    "unique_values_before": notes["weather"].nunique(),
    "unique_values_after": notes["weather"].nunique() - int(bad_weather.sum()),
})
notes.loc[bad_weather, "weather"] = None

# Flag anomalous note_type rows (the 3 long-text entries) — keep but tag them
anomalous_types = ~notes["note_type"].isin(VALID_NOTE_TYPES)
notes["note_type_flag"] = anomalous_types
report_rows.append({
    "file": "field_notes_all.csv",
    "column": "note_type",
    "action": "Flagged non-standard note_type rows (kept for manual review)",
    "rows_affected": int(anomalous_types.sum()),
    "unique_values_before": notes["note_type"].nunique(),
    "unique_values_after": f"{notes['note_type'].nunique()} (flagged rows kept)",
})

notes.to_csv(os.path.join(OUT, "field_notes_clean.csv"), index=False)
print(f"  → {int(bad_weather.sum())} bad weather values fixed")
print(f"  → {int(anomalous_types.sum())} anomalous note_type rows flagged")
print(f"  → Saved: outputs/field_notes_clean.csv")


# ─────────────────────────────────────────────────────────────────────────────
# Save cleaning report
# ─────────────────────────────────────────────────────────────────────────────
report = pd.DataFrame(report_rows)
report.to_csv(os.path.join(OUT, "step1_cleaning_report.csv"), index=False)
print("\n✓ Step 1 complete. Cleaning report saved: outputs/step1_cleaning_report.csv")
print(f"  Total cleaning actions: {len(report_rows)}")
