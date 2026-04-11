FOLDER: 01_cleaned_data
========================
These are the standardized versions of the 7 raw data files. Messy text entries have been
normalized to consistent categories, redundant columns have been removed, and a new flag
has been added where important manual overrides were detected.

Key: SOV = Schedule of Values — the breakdown of a project into 15 standard scopes of work
     (e.g. Ductwork, Piping, Controls). Every cost, billing, and labor entry links back to one.
     GC  = General Contractor — the main contractor who hired this HVAC subcontractor.
     CO  = Change Order — a formal request to change the contract price or scope.
     RFI = Request for Information — a formal question sent to the architect/engineer.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: labor_logs_clean.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one worker's time entry for one day on one scope of work.
1,202,039 rows total.

  project_id        Which project this work belongs to.
                    Example: "PRJ-2024-001" = Mercy General Hospital HVAC job.

  log_id            Unique ID for this specific time entry.
                    Example: "11a98032"

  date              The date work was performed.
                    Example: "2024-03-27"

  employee_id       Anonymized unique code for the worker.
                    Example: "EMP-4598"

  role              The worker's job classification. Normalized from 33 raw variants
                    down to 8 standard types:
                      Foreman         — leads a crew on site
                      Journeyman      — fully qualified tradesperson (e.g. pipefitter)
                      Apprentice      — worker in training, lower pay rate
                      Helper          — general labor support
                      Superintendent  — oversees all field operations for the company
                      Project Manager — manages schedule, budget, and paperwork
                      Engineer        — handles technical/design coordination
                      Technician      — specialized equipment work
                    Example: "Journeyman" (raw data had "Journeyman Pipefitter", "jman",
                    "JOURNEYMAN" — all now standardized to "Journeyman").

  sov_line_id       Which scope of work this labor was charged to.
                    Format: [project_id]-SOV-[line number]
                    Example: "PRJ-2024-001-SOV-01" = Line 1 (General Conditions) on that project.

  hours_st          Straight-time hours worked at regular pay rate.
                    Example: 8 = one standard 8-hour workday.

  hours_ot          Overtime hours worked, paid at 1.5× the regular rate.
                    Example: 0 = no overtime. 2 = two hours of overtime that day.

  hourly_rate       The worker's base wage in dollars per hour.
                    Example: 74.5 = $74.50/hr for a Journeyman.
                             38.0 = $38.00/hr for an Apprentice.

  burden_multiplier A factor applied on top of the hourly rate to cover payroll taxes,
                    workers' compensation insurance, health benefits, and union dues.
                    Example: 1.42 means the true cost is 42% more than the raw wage.
                    A Journeyman at $74.50/hr actually costs $74.50 × 1.42 = $105.79/hr.
                    Range in this dataset: 1.38 – 1.42.

  work_area         Physical location on site where the work was performed.
                    Example: "Floor 6"

  [REMOVED] cost_code — contained only the SOV line number (1, 2, 3...), which is already
                    embedded at the end of sov_line_id. 100% redundant, dropped.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: material_deliveries_clean.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one material delivery received on a job site.
22,438 rows total.

  project_id        Which project received this delivery.

  delivery_id       Unique ID for this delivery.
                    Example: "DEL-001-7b34a2"

  date              Date the delivery arrived on site.
                    Example: "2024-04-13"

  sov_line_id       Which scope of work this material is being used for.
                    Example: "PRJ-2024-001-SOV-03" = Ductwork scope.

  material_category Type of material. Normalized from 25 raw variants to 5 standard types:
                      Ductwork    — sheet metal ducts that carry conditioned air
                      Piping      — pipes for hot/chilled water or refrigerant
                      Equipment   — major HVAC units (air handlers, chillers, boilers)
                      Controls    — thermostats, sensors, building automation wiring
                      Insulation  — foam/wrap material around ducts and pipes
                    Example: "Ductwork"

  item_description  Specific description of the item delivered.
                    Example: 'Spiral Duct 16"' = 16-inch diameter spiral ductwork.

  quantity          How many units were delivered.
                    Example: 263

  unit              Unit of measurement for the quantity.
                    Example: "LF" = linear feet.

  unit_cost         Cost per unit in dollars.
                    Example: 176.84 = $176.84 per linear foot.

  total_cost        Total dollar value of this delivery (quantity × unit_cost).
                    Example: 263 LF × $176.84 = $46,509.65

  po_number         Purchase order number that authorized this purchase.
                    Example: "PO-62186"

  vendor            The supplier company.
                    Example: "Ferguson Supply"

  received_by       Who accepted the delivery on site.
                    Example: "M. Chen"

  condition_notes   Notes on the condition or completeness of the shipment.
                    "Partial shipment - backorder pending" = only part of the order
                    arrived; the rest is delayed. This triggers the partial shipment flag
                    used in Steps 3 and 9.
                    "Good condition" = complete and undamaged delivery.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: change_orders_clean.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one formal request to change the contract scope or price.
A Change Order (CO) is submitted when something happens that was not covered
in the original contract — extra work, a design mistake, unexpected site conditions, etc.
4,255 rows total.

  project_id        The project this CO belongs to.

  co_number         Unique ID for this change order.
                    Example: "CO-012"

  date_submitted    When the CO was formally submitted to the GC.
                    Example: "2024-04-29"

  reason_category   Why this CO was needed. Categories:
                      Acceleration        — owner demanded faster work than planned,
                                           requiring premium/overtime labor
                      Unforeseen Condition — unexpected discovery on site
                                           (e.g. abandoned pipes not shown on drawings)
                      Design Error        — architect/engineer made a mistake on drawings
                      Scope Gap           — the original contract was missing something required
                      Owner Request       — owner asked for a change or addition
                      Code Compliance     — local building code required something beyond design
                      Coordination        — conflict between different trades on site
                      Value Engineering   — a cheaper alternative proposed and accepted
                    Example: "Unforeseen Condition" — found hidden piping behind a wall.

  description       Plain-English explanation of what the CO covers.
                    Example: "Discovered abandoned piping not shown on documents"

  amount            Dollar amount being requested (positive = more money for the sub).
                    Example: 365700 = $365,700 additional cost claimed.

  status            Whether the GC accepted or rejected this CO.
                      Approved — GC agreed to pay it
                      Rejected — GC refused; subcontractor absorbs the cost
                      Pending  — still under review
                    Example: "Approved"

  related_rfi       If an RFI (Request for Information — a formal question sent to
                    the architect or engineer for a design clarification) triggered this CO,
                    its number appears here. An RFI becomes a CO when the clarification
                    reveals extra work is needed.
                    Example: "RFI-012" — the answer to RFI-012 required $365,700 in extra work.
                    Empty = no RFI was involved.

  labor_hours_impact  Extra labor hours this CO requires.
                    Example: 36 extra worker-hours.

  schedule_impact_days  Extra calendar days this CO adds to the project end date.
                    Example: 0 = no delay.

  submitted_by      Who submitted the CO on the sub's behalf.
                    Example: "K. Thompson"

  approved_by       Who approved it on the GC side.
                    Example: "Project Manager"

  affected_sov_lines_parsed  Which scopes of work this CO touches, as a list.
                    Example: ['PRJ-2024-001-SOV-14'] = only the Piping scope is impacted.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: change_orders_exploded.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Same data as change_orders_clean.csv, but restructured so there is one row
per affected SOV line instead of one row per CO. A CO that affects 2 scopes
becomes 2 rows here. Used for joining CO data to scope-level cost analysis.
8,500 rows (vs. 4,255 original COs).

  sov_line_id       The specific scope this CO row is linked to.
                    Example: "PRJ-2024-001-SOV-04"
  All other columns are the same as change_orders_clean.csv.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: billing_line_items_clean.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one scope of work billed in one billing application.
Projects submit invoices monthly; each invoice includes every active scope.
90,112 rows total.

  sov_line_id         Which scope of work is being billed.
                      Example: "PRJ-2024-001-SOV-01" = General Conditions scope.

  previous_billed     Total dollars billed for this scope in ALL prior applications.
                      Example: 0 = nothing billed yet (this is the first invoice).

  this_period         Dollars billed for this scope in THIS application only.
                      Example: 268,500 = $268,500 billed this month.

  pct_complete        What percentage of this scope the project team says is done.
                      Example: 13.0 = 13% complete as of this invoice.
                      This is a PM's assessment — it may not match the billing math exactly.

  project_id          The project this billing belongs to.

  application_number  Which invoice cycle this entry belongs to (1 = first invoice, etc.).
                      Example: 2 = second billing application.

  pct_manually_adjusted  True/False flag.
                      True  = the PM entered a pct_complete that differs from what the
                              math gives (previous_billed + this_period) / scheduled_value.
                              This means a PM looked at the site and judged that physical
                              progress is ahead of (or behind) what billing numbers show.
                      False = pct_complete matches the billing math exactly.
                      Example: False on the first two rows — billing math and PM judgment agree.
                      Of 90,112 rows, 70,348 were manually adjusted.

  [REMOVED] total_billed       — always equaled previous_billed + this_period (100% derived)
  [REMOVED] balance_to_finish  — always equaled scheduled_value - total_billed (derived)
  [REMOVED] scheduled_value    — duplicate of sov_all.scheduled_value
  [REMOVED] description        — duplicate of sov_all.description


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: billing_history_clean.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one billing application at the whole-project level (summary invoice).
6,479 rows total.

  project_id          The project.

  application_number  Which invoice cycle (1 = first, 2 = second, etc.).
                      Example: 2

  period_end          The cutoff date this invoice covers work through.
                      Example: "2024-05-21" = covers all work completed through May 21.

  period_total        Total dollars billed across ALL scopes in this period only.
                      Example: 2,944,900 = $2.9M billed in this single cycle.

  cumulative_billed   Running total billed across ALL applications to date.
                      Example: Application #2 cumulative = $2,944,900.
                               Application #3 cumulative = $6,573,200.
                      (Grew by $3,628,300 in period 3.)

  status              Payment status of this invoice.
                        Paid    — GC has sent payment
                        Pending — waiting for GC to pay
                      Example: "Paid"

  payment_date        Date the GC's payment actually arrived.
                      Example: "2024-06-30" — period ended May 21, paid June 30.
                      That is 40 days — 10 days past the Net 30 contract terms.

  line_item_count     How many SOV scope lines were included in this invoice.
                      Example: 9

  [REMOVED] retention_held   — always equaled cumulative_billed × 0.10 (100% derived).
                      Retention = 10% withheld from every invoice by the GC as a
                      performance guarantee. Released after project completion.
  [REMOVED] net_payment_due  — always equaled cumulative_billed - retention_held (100% derived).
  Both are recomputed from cumulative_billed wherever needed downstream.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: field_notes_clean.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one note written by a field supervisor on a given day.
103,676 rows total.

  project_id          The project this note is from.

  note_id             Unique ID for this note.
                      Example: "e381c053"

  date                Date the note was written.

  author              Who wrote the note.
                      Example: "R. Williams"

  note_type           Category of the note, normalized to standard types:
                        Daily Report  — routine end-of-day summary
                        Safety Log    — safety meeting or incident documentation
                        Weather Delay — work stopped or slowed due to weather
                        Inspection    — a code or quality inspection occurred
                        Quality Control — QC check on installed work
                        Issue Log     — flagging a problem or conflict on site
                        RFI Log       — note related to a Request for Information
                      Example: "Issue Log"

  content             The full text of the note.
                      Example: "Safety meeting held at start of shift - topic: fall
                      protection. All PPE verified. Completed piping pressure test - passed."

  photos_attached     Number of site photos included with this note.
                      Example: 0 = no photos.

  weather             Weather conditions that day, normalized to:
                      Clear, Rain, Snow, Cloudy, Wind, Fog, N/A.
                      Example: "Rain"

  temp_high           High temperature (°F) that day.
                      Example: 95

  temp_low            Low temperature (°F) that day.
                      Example: 69


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: step1_cleaning_report.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A log of every change made during Step 1 cleaning.

  file     Which file was changed.
  action   What was done.
  before   State before cleaning (e.g. number of unique variants, or "present").
  after    State after cleaning (e.g. reduced count, or "dropped").

Example rows from actual output:
  labor_logs | role standardization | 33 variants | 14 canonical
  billing_line_items | flag pct_manually_adjusted | no flag | 70,348 rows flagged
  billing_history | dropped: retention_held, net_payment_due | present | dropped
