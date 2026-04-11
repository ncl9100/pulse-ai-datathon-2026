FOLDER: 07_early_warning
=========================
A predictive risk model. Using only information observable in the FIRST 20% of a
project's timeline, it scores every project 0–100 for likelihood of finishing over budget.
The idea: catch problems early enough to intervene, before most of the money is spent.

How it works:
  Seven signals are measured in the early window. Each signal is compared against a
  threshold derived from historical completed projects (midpoint between poor and healthy
  medians). Each triggered threshold adds to the risk score.
  Risk score = (warnings triggered / 7) × 100


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: early_warning_scores.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one project with its risk score and the signals that drove it.
405 rows, sorted from highest risk to lowest.

  project_id            The project.

  gc_name               The GC. Example: "JE Dunn"

  project_type          Small / Medium / Large / Mega.

  risk_score            0–100 score. Higher = more warning signals triggered.
                        Example: 100.0 = all 7 signals in warning territory.

  risk_label            Summary label:
                          High Risk     — score ≥ 70 (60 projects)
                          Moderate Risk — score 40–69 (186 projects)
                          Low Risk      — score < 40 (159 projects)
                        Example: "High Risk"

  project_cpi           The project's actual final CPI (for validation/comparison).
                        Example: 1.06 — a High Risk project that actually finished okay.

  avg_pct_complete      Average % complete across all scopes.
                        Example: 99.0% — fully complete project.

  warn_project_cpi      1 = CPI is below the threshold of 1.251 (lower is worse signal).
                        0 = CPI is healthy. Example: 1

  warn_early_co_count   1 = more than 1.5 early-phase COs filed (higher is worse).
                        Example: 1

  warn_early_scope_cos  1 = at least one Design Error / Scope Gap CO in the early phase.
                        Example: 1

  warn_early_rfi_count  1 = more than 10.5 RFIs filed in the early window.
                        Example: 1

  warn_early_ot_ratio   1 = average OT ratio above 5.35% in the early phase.
                        Example: 1

  warn_early_partial_mat  1 = partial shipment rate above 16.3% in the early phase.
                        Example: 1

  warn_early_billing_lag  1 = average payment lag above 32.2 days.
                        Example: 1

  early_co_count        Raw count of COs filed in first 20% of timeline. Example: 2
  early_scope_cos       Raw count of design/scope COs in early phase. Example: 1
  early_rfi_count       Raw count of RFIs filed in early phase. Example: 13
  early_ot_ratio        Raw average OT ratio in early phase (%). Example: 5.81
  early_partial_mat     Raw average partial shipment rate in early phase (%). Example: 21.9
  early_billing_lag     Raw average days between invoice and payment. Example: 32.75


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: early_warning_thresholds.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one signal, showing how its threshold was derived.
7 rows.

  signal          Name of the signal. Example: "early_rfi_count"

  poor_median     The median value of this signal on projects that finished poorly (CPI < 0.85).
                  Example: 13.0 — poor projects had 13 early-phase RFIs on average.

  healthy_median  The median value on projects that finished well.
                  Example: 8.0 — healthy projects had 8 early-phase RFIs.

  threshold       The cutoff between healthy and warning zones.
                  = (poor_median + healthy_median) / 2
                  Example: 10.5 — more than 10.5 early RFIs triggers a warning.

  direction       Which direction is bad:
                    lower_is_worse  — only applies to project_cpi (low CPI = bad)
                    higher_is_worse — applies to all other signals (more = worse)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: early_warning_validation.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = overall model performance statistics. 1 row.

  projects_validated    How many finished projects were used to test the model.
                        Example: 405

  accuracy_pct          % of projects where the model's prediction matched reality.
                        Example: 67.2% — model was right 2 out of 3 times.

  precision_pct         Of projects the model flagged High Risk, what % were actually bad.
                        Example: 3.7% — most flagged projects turned out fine.
                        Low precision is expected when very few projects actually fail (9/405).

  recall_pct            Of projects that actually failed, what % did the model catch.
                        Example: 55.6% — model caught 5 of the 9 real failures.

  true_positives        Projects correctly predicted as over budget. Example: 5
  false_positives       Projects incorrectly flagged as risky. Example: 130
  false_negatives       Failed projects the model missed. Example: 4
