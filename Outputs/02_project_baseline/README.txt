FOLDER: 02_project_baseline
============================
One row per project. Built by combining contracts, SOV budget estimates, and change orders.
This is the master reference table that all other analysis joins back to.
405 projects total.

Key terms:
  SOV    = Schedule of Values — the breakdown of a project into ~15 standard work scopes
  GC     = General Contractor — the main contractor who hired this HVAC subcontractor
  CO     = Change Order — a formal request to adjust the contract price


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: project_master.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  project_id                  Unique project identifier.
                              Example: "PRJ-2024-001"

  project_name                Full name of the project.
                              Example: "Mercy General Hospital - HVAC Modernization"

  original_contract_value     The price agreed upon when the contract was signed.
                              This is what the GC agreed to pay before any changes.
                              Example: 35,194,000 = $35.2M

  contract_date               When the contract was officially signed.
                              Example: "2024-03-27"

  substantial_completion_date The planned date when the project is considered done
                              (not necessarily 100% punch-list complete, but usable).
                              Example: "2025-09-01"

  original_duration_days      How many calendar days the project was planned to take
                              (substantial_completion_date - contract_date).
                              Example: 523 days (~17 months).

  retention_pct               The percentage of each invoice withheld by the GC
                              as a performance guarantee until project completion.
                              Example: 0.1 = 10% retention (standard in construction).

  payment_terms               How many days the GC has to pay after receiving an invoice.
                              Example: "Net 30" = must pay within 30 days.

  gc_name                     The General Contractor company on this project.
                              Example: "Turner Construction"
                              The 5 GCs in this portfolio: Turner Construction,
                              DPR Construction, JE Dunn, Skanska USA, Mortenson.

  architect                   Firm that designed the building and produced the drawings.
                              Example: "SmithGroup"

  engineer_of_record          Firm responsible for the mechanical/structural engineering.
                              Example: "Henderson Engineers"

  project_type                Size category based on contract value:
                                Small  — under $5M        (48 projects)
                                Medium — $5M – $20M      (248 projects)
                                Large  — $20M – $50M     (102 projects)
                                Mega   — over $50M       (7 projects)
                              Example: "Large"

  sov_total_scheduled_value   Sum of all SOV line scheduled values for this project.
                              Should equal original_contract_value (confirmed 100% match).
                              Example: 35,194,000

  estimated_labor_cost        Total estimated labor cost from the SOV budget.
                              Example: 17,295,900 = $17.3M in estimated labor.

  estimated_material_cost     Total estimated material cost from the SOV budget.
                              Example: 6,511,900 = $6.5M in estimated materials.

  estimated_equipment_cost    Estimated cost for major equipment (chillers, AHUs, etc.).
                              Example: 8,654,100

  estimated_sub_cost          Estimated cost for sub-subcontractors.
                              Example: 2,059,300

  total_estimated_cost        Sum of all estimated cost categories above.
                              Example: 34,521,200 = $34.5M total cost estimate.

  total_cos                   Total number of change orders submitted on this project.
                              Example: 12

  approved_cos                How many COs the GC accepted.
                              Example: 9

  rejected_cos                How many COs the GC refused to pay.
                              Example: 3

  total_co_value              Total dollar amount across all COs submitted (approved + rejected).
                              Example: 5,487,300 = $5.5M in CO requests.

  approved_co_value           Total dollar amount of COs the GC approved.
                              Example: 4,192,500 = $4.2M recovered through COs.

  rejected_co_value           Dollar value of COs the GC refused. This money was claimed
                              but never paid — it represents unrecovered cost.
                              Example: 1,294,800 = $1.3M rejected.

  upstream_design_cos         Number of COs caused by Design Errors or Scope Gaps —
                              problems that originated with the architect/engineer,
                              not the subcontractor.
                              Example: 3

  co_rejection_rate_pct       Percentage of COs that were rejected (rejected / total × 100).
                              Example: 25.0 = 25% of COs on this project were rejected.
                              Portfolio average: ~24–25%.

  upstream_design_co_pct      Percentage of COs caused by design/scope issues.
                              Example: 25.0 = 25% of COs on this project trace back to
                              architect or engineer mistakes.

  revised_contract_value      The contract value after all approved COs are added.
                              = original_contract_value + approved_co_value
                              Example: 35,194,000 + 4,192,500 = $39,386,500

  builtin_margin_usd          How much dollar profit was built into the original contract
                              price above the estimated cost.
                              = original_contract_value - total_estimated_cost
                              Example: 35,194,000 - 34,521,200 = $672,800 margin.
                              A NEGATIVE number means the project was priced below cost.
                              Portfolio average: -0.8% (353 of 405 projects priced below 5% margin).

  builtin_margin_pct          Built-in margin as a percentage of contract value.
                              Example: 1.91% on PRJ-2024-001.
                              Example: -8.55% on PRJ-2024-002 = priced $2.6M below cost.
                              A project with -8.55% margin needed its change orders to
                              break even — rejections directly cause losses.
