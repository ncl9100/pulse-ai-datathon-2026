FOLDER: 03_cost_performance
============================
Earned Value Management (EVM) metrics — the standard method for measuring whether a project
is on track financially. The core question: for every dollar spent, how much work got done?

Key terms:
  BAC = Budget At Completion — the total planned budget for a scope (= scheduled_value)
  EV  = Earned Value — how much budget the completed work is "worth"
        Formula: EV = BAC × (pct_complete / 100)
  CPI = Cost Performance Index — efficiency ratio
        Formula: CPI = EV / Actual Cost
        CPI > 1.0 = spending less than planned (efficient)
        CPI < 1.0 = spending more than planned (over budget)
  EAC = Estimate At Completion — projected final cost if current efficiency continues
        Formula: EAC = Actual Cost / (pct_complete / 100)
  VAC = Variance At Completion — projected profit or loss at end
        Formula: VAC = BAC - EAC  (negative = projected loss)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: actual_cost_per_line.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one scope of work on one project, with its real labor + material costs.
6,275 rows.

  project_id              The project.

  sov_line_id             Which scope of work.
                          Example: "PRJ-2018-001-SOV-01" = General Conditions on that project.

  actual_labor_cost       Total labor dollars spent on this scope.
                          Computed as: hours_st × hourly_rate × burden_multiplier
                                     + hours_ot × hourly_rate × 1.5 × burden_multiplier
                          Example: 252,022 = $252K in labor costs.

  total_hours             Total worker-hours logged to this scope (straight + overtime).
                          Example: 2,914 hours.

  total_ot_hours          Overtime hours only.
                          Example: 156 OT hours out of 2,914 total.

  worker_count            How many unique workers were logged to this scope.
                          Example: 340 unique employees worked on this scope.

  ot_ratio_pct            Overtime as a % of total hours (total_ot / total_hours × 100).
                          High OT ratio = workers being pushed hard, often due to schedule
                          pressure or delays elsewhere forcing catch-up.
                          Example: 5.35% OT ratio.

  actual_material_cost    Total material dollars delivered for this scope.
                          Example: 0 = no material deliveries logged to this line.

  delivery_count          Number of separate deliveries for this scope.

  partial_deliveries      Number of deliveries flagged as partial in condition_notes.

  partial_shipment_rate_pct  Partial deliveries as % of total deliveries.
                          High rate = supply chain problems; workers may be standing by
                          waiting for materials (drives up OT as they catch up later).
                          Example: 0% if no partial deliveries.

  total_actual_cost       Labor + material combined.
                          Example: 252,022 (all labor, no material on this line).

  estimated_labor_cost    What labor was budgeted to cost (from SOV budget).
                          Example: 1,645,600 = $1.6M estimated.

  estimated_material_cost What material was budgeted to cost.
                          Example: 1,084,400 = $1.1M estimated.

  total_budget            estimated_labor + estimated_material combined.
                          Example: 2,730,000 = $2.73M budget for this scope.

  cost_variance_usd       Budget minus actual cost (positive = under budget).
                          Example: 2,477,978 = $2.5M under budget so far (only 9% spent).

  cost_variance_pct       Cost variance as % of budget.
                          Example: 90.77% remaining budget — this scope is barely started.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: billing_progress.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = the LATEST billing status for one scope on one project.
Only the most recent application is kept per scope — this shows where things stand today.
6,075 rows.

  project_id              The project.

  sov_line_id             The scope of work.

  line_number             The sequential line number within the project's SOV (1–15).
                          Example: 1 = first scope (usually General Conditions).

  description             Name of this scope.
                          Example: "General Conditions & Project Management"

  application_number      The most recent billing application number for this scope.
                          Example: 12 = 12th invoice cycle.

  scheduled_value         The total contract value for this scope (= BAC).
                          Example: 2,477,800 = $2.48M contracted for this scope.

  previous_billed         Total billed in all applications before the latest one.
                          Example: 2,477,400

  this_period             Amount billed in the most recent application.
                          Example: 400

  total_billed            Cumulative amount billed to date (previous + this_period).
                          Recomputed from source columns; not stored in raw data.
                          Example: 2,477,800

  pct_complete            What % of this scope is done, per the PM's latest assessment.
                          Example: 100.0 = fully complete.

  pct_manually_adjusted   True if the PM's pct_complete differs from billing math.
                          Example: False = billing math and PM agree it's 100%.

  balance_to_finish       Dollars remaining to bill (scheduled_value - total_billed).
                          Example: 0 = nothing left to bill (scope is complete and fully billed).


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: billing_timeline.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one billing application at the whole-project level, showing how billing
progressed over time. All applications are kept here (not just the latest).
6,479 rows across 405 projects.

  project_id              The project.

  application_number      Invoice cycle number (1 = first invoice submitted).

  total_billed_this_app   Total new dollars billed across all scopes in this cycle.
                          Example: Application #2 billed $2,944,900 new.

  cumulative_billed       Running total billed through this application.
                          Example: After app #3: $6,573,200 total billed to date.

  lines_count             How many SOV scopes were included in this application.

  retention_held          10% of cumulative_billed, withheld by the GC.
                          Recomputed here as cumulative_billed × 0.10.
                          Example: $6,573,200 × 10% = $657,320 held back.

  net_payment_due         What the GC actually owes after retention is deducted.
                          = cumulative_billed - retention_held
                          Example: $6,573,200 - $657,320 = $5,915,880 due.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: cpi_per_line.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = EVM metrics for one scope on one project.
Combines actual cost (Step 3) with % complete (Step 4) and budget (SOV).

  project_id / sov_line_id   Scope identifier.

  bac                 Budget At Completion = scheduled_value for this scope.
                      Example: 2,477,800 = $2.48M budgeted.

  pct_complete        % done as of the latest billing application.

  total_actual_cost   What has actually been spent so far on this scope.

  earned_value        EV = BAC × (pct_complete / 100). The dollar value of completed work.
                      Example: $2.48M × 100% = $2,477,800 EV (fully done).

  cpi                 Cost Performance Index = EV / Actual Cost.
                      Example: CPI = 1.64 means for every $1 spent, $1.64 of work was done.
                      CPI < 1.0 means overspending relative to progress.

  eac                 Estimate At Completion = projected final cost.
                      = Actual Cost / (pct_complete / 100)

  vac                 Variance At Completion = BAC - EAC.
                      Positive = projected to finish under budget.
                      Negative = projected loss.

  cpi_status          Performance category:
                        Efficient    — CPI ≥ 1.15
                        On Track     — CPI 1.0–1.15
                        Watch        — CPI 0.85–1.0
                        At Risk      — CPI 0.75–0.85
                        Critical     — CPI < 0.75
                        No Cost Yet  — no spending logged yet


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: cpi_per_project.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = project-level EVM rollup. All scopes combined into one project score.
405 rows.

  project_id          The project.

  total_bac           Sum of all scope budgets for this project.
                      Example: 38,264,000 = $38.3M total budget.

  total_earned_value  Sum of earned value across all scopes.
                      Example: 38,018,593 = $38M worth of work completed.

  total_actual_cost   Total spending across all scopes to date.
                      Example: 17,669,987 = $17.7M spent so far.

  lines_total         Number of SOV scopes on this project.
                      Example: 15

  lines_complete      Number of scopes at 99.5%+ complete.
                      Example: 9

  avg_pct_complete    Average % complete across all scopes.
                      Example: 99.01%

  project_cpi         Project-level CPI = total_earned_value / total_actual_cost.
                      Example: 2.15 = extraordinarily efficient (spending half of budget
                      to achieve the same work — possible on projects with high labor
                      productivity or underspent early phases).
                      Portfolio average CPI: 1.64.

  project_eac         Projected final cost if current pace continues.

  project_vac         Projected profit/loss at completion.
                      Positive = projected to come in under budget.

  project_status      Performance label (same bands as cpi_status above).
                      Portfolio breakdown: 362 Efficient, 22 On Track, 12 Watch,
                      5 At Risk, 4 Critical.
