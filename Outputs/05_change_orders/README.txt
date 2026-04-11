FOLDER: 05_change_orders
=========================
Analyzes how well the company recovered extra costs through change orders, which GCs
push back most, and how many RFIs turned into paid COs.

Key terms:
  CO  = Change Order — formal request to add money to the contract for extra/changed work
  RFI = Request for Information — a written question sent to the architect or engineer
        asking for a design clarification. When the answer reveals extra work is needed,
        an RFI often becomes a CO. If the CO gets rejected, the cost is unrecovered.
  Recovery rate = approved CO value / total CO value submitted. How much of claimed
                  extra cost was actually paid by the GC.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: co_analysis_by_project.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one project's CO summary. 405 rows.

  total_cos             Total COs submitted on this project.
                        Example: 10

  approved_cos          COs the GC agreed to pay.
                        Example: 8

  rejected_cos          COs the GC refused. This cost falls on the subcontractor.
                        Example: 2

  pending_cos           COs still under review.

  total_co_value_usd    Dollar amount of all COs submitted.
                        Example: $5,456,000

  approved_value_usd    Dollar amount approved and paid.
                        Example: $4,293,800

  rejected_value_usd    Dollar amount rejected — unrecovered money.
                        Example: $1,162,200

  recovery_rate_pct     Approved value / total value × 100.
                        Example: 78.7% — GC paid 79 cents of every dollar claimed.
                        Portfolio average: 75.9%.

  rejection_rate_pct    Rejected COs / total COs × 100.
                        Example: 20.0% — 1 in 5 COs rejected.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: co_analysis_by_gc.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one GC across all their projects. 5 rows (one per GC).

  gc_name               The General Contractor company.
                        Example: "Skanska USA"

  total_cos             Total COs submitted across all their projects.
                        Example: 767

  rejected_cos          Total they refused to pay.
                        Example: 197

  total_value_usd       Total dollar value of all COs submitted to this GC.

  rejected_value_usd    Total dollar value rejected.

  rejection_rate_pct    Their rejection rate. Sorted highest to lowest.
                        Example: 25.7% — Skanska rejects the most COs in the portfolio.
                        All 5 GCs cluster between 23.8%–25.7%.

  top_rejection_reason  The most common reason_category they reject.
                        Example: "Design Error" — they push back hardest when told the
                        subcontractor's extra work was caused by a design mistake.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: co_rfi_recovery.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one project's RFI-to-CO recovery summary.

  cost_impact_rfis      RFIs where cost_impact = True (the clarification revealed
                        extra work would be needed).
                        Example: 6 — 6 RFIs on this project had a cost impact.

  recovered_rfis        How many of those RFIs resulted in an approved CO (matched
                        via the related_rfi field in change orders).
                        Example: 3

  recovery_rate_pct     recovered / cost_impact_rfis × 100.
                        Example: 50.0% — only half of cost-impacting RFIs became paid COs.
                        Portfolio total: 5,565 cost RFIs, 3,053 recovered (54.9%).
                        The unrecovered 45% represents cost the company absorbed.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: co_timing.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one CO, with context about when in the project it was filed.

  co_number             The CO identifier. Example: "CO-012"

  status                Approved / Rejected / Pending.

  amount                Dollar amount of this CO. Example: 390,900

  reason_category       Why it was needed. Example: "Acceleration"

  project_stage         Which phase of the project this CO was filed in:
                          Early (0-20%)      — first fifth of the project timeline
                          Mid (20-50%)       — middle portion
                          Late (50-80%)      — final push
                          Closeout (80-100%) — near or at completion
                        Example: "Early (0-20%)" — this CO was filed in the first 6% of
                        the project timeline.

  project_stage_pct     Exact % into the project when this CO was filed.
                        Example: 6.31% — filed very early in the project.
                        Portfolio finding: rejection rates are consistent across all stages
                        (~24%), meaning GCs don't get easier or harder as projects progress.
