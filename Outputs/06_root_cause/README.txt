FOLDER: 06_root_cause
======================
For the 9 worst-performing projects (CPI < 0.85), identifies the primary chain of events
that caused the cost overrun. Five cause-effect patterns are tested.

Key term:
  CPI = Cost Performance Index. CPI < 0.85 means spending 18%+ more than planned progress.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: cause_effect_diagnosis.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one poor-performing project with its diagnosed primary cause.
9 rows.

  project_cpi           The project's CPI — how bad the overrun is.
                        Example: 0.825 = spending $1.21 for every $1 of work done.

  total_bac             Total contract budget. Example: $3,101,000

  total_actual_cost     What was actually spent. Example: $3,726,606

  cost_overrun_usd      actual_cost - total_bac. How much over budget.
                        Example: $625,606 over budget.

  cost_impact_rfis      Number of RFIs on this project that had a cost impact.
                        Example: 16

  recovery_rate_pct     % of those RFIs that became approved COs.
                        Example: 25.0% — 75% of RFI costs went unrecovered.

  rejected_value_usd    Total dollar value of COs that were rejected.
                        Example: $167,500 in rejected COs.

  rejection_rate_pct    % of COs rejected. Example: 25.0%

  primary_cause         The diagnosed root cause of the overrun:
                          Rejected CO          — large amount of CO value was refused
                          RFI Standby          — many cost-impacting RFIs with low recovery
                          Cost Overrun (Other) — no dominant single cause identified
                        Example: "Rejected CO"
                        Portfolio: 5 of 9 poor performers traced to Rejected CO.

  gc_name               Which GC is on this project. Example: "Skanska USA"

  project_type          Size category. Example: "Small"


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: chain_a_design_rework.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Chain A pattern: Design Error or Scope Gap COs filed in the early/mid phase of a project.
These represent rework — work that had to be redone because the drawings were wrong.

  design_co_count       How many early-phase design/scope COs this project had.
  design_co_value_usd   Total dollar value of those COs.
  is_poor_performer     True if this project has CPI < 0.85.
  project_cpi           The project's CPI score.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: chain_b_material_shortage.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Chain B pattern: High partial shipment rate (>40%) driving high overtime.
Logic: materials arrive incomplete → workers can't finish the scope → they work OT
later to catch up → overtime inflates labor cost.

  avg_partial_shipment_pct    Average % of deliveries that were partial on this project.
                              Example: >40% triggers this chain.
  avg_ot_ratio_pct            Average overtime ratio across all scopes.
  estimated_standby_cost_usd  Estimated OT cost attributable to material delays.
  is_poor_performer           True if CPI < 0.85.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: chain_c_rfi_standby.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Chain C pattern: Many cost-impacting RFIs (>10) but very low CO recovery (<20%).
Logic: architect's answers revealed extra work → subcontractor submitted COs →
GC rejected most of them → costs absorbed with no revenue recovery.

  cost_impact_rfis      RFIs with cost_impact = True. Example: 27
  recovered_rfis        Those that became approved COs. Example: 11
  recovery_rate_pct     % recovered. Example: 40.7% — better than average but still a gap.
  is_poor_performer     True if CPI < 0.85.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: chain_d_rejected_co.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Chain D pattern: Over $500K in rejected CO value on a single project.
The most common cause of poor CPI in this portfolio (5 of 9 poor performers).

  rejected_value_usd    Total CO value the GC refused to pay. Example: $1,162,200
  rejection_rate_pct    % of COs rejected. Example: 20.0%
  is_poor_performer     True if CPI < 0.85.
  155 projects have over $500K in rejected COs, but only 5 of the worst 9 overlap.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: chain_e_early_co_volume.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Chain E: A leading indicator, not a cause. Projects that file more than 5 COs
in the first 20% of their timeline are 20% likely to become poor performers —
vs. only 2.2% overall. Useful for early intervention.

  early_co_count        Number of COs filed in the first 20% of the project.
                        Example: 2 (threshold for flagging is > 5).
  is_poor_performer     True if CPI < 0.85.
  project_cpi           Final CPI for context.
