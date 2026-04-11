# Full Analysis Workflow — HVAC Mechanical Subcontractor Portfolio
### 405 Projects | $6.4B Total Contract Value | 2018–2024

---

## Who We Are and What This Data Represents

This dataset belongs to a **mechanical subcontractor** — the company physically installing HVAC systems (ductwork, piping, equipment, controls) across construction sites. The General Contractors (Turner Construction, DPR Construction, Skanska USA, JE Dunn, Mortenson) hire this company and govern payment. Every analysis must be read from the subcontractor's perspective: **our contract value vs. our actual cost = our margin.**

---

## Part 1 — The 10 Files: What Each One Is and What It Tells You

### 1. `contracts_all.csv` — The Commitment Layer
**What it is:** One row per project. The legal agreement between the subcontractor and the GC.

| Column | What It Means |
|---|---|
| `project_id` | Master key. Every other file joins here. |
| `project_name` | Reveals project type (Hospital, Data Center, School, etc.) — used for segment benchmarking |
| `original_contract_value` | What the subcontractor was hired to do the job for. This is revenue ceiling before change orders. |
| `contract_date` | When the clock started. Use against `substantial_completion_date` for planned duration. |
| `substantial_completion_date` | The contractual deadline. Miss it and the GC can claim liquidated damages. |
| `retention_pct` | Always 0.10 (10%) in this dataset. Meaning: for every dollar billed, 10 cents is held back until the job is complete and accepted. |
| `payment_terms` | Always "Net 30" — the GC must pay within 30 days of a billing application being approved. |
| `gc_name` | Which GC runs the site. Some GCs pay faster, dispute more COs, or have tighter schedule management — this becomes a comparison axis. |

**What it indicates:** The baseline promise. You compare every other number in the dataset against what this file established at the start.

---

### 2. `sov_all.csv` — The Work Breakdown
**What it is:** One row per work category per project. 15 categories × 405 projects = 6,075 rows. The Schedule of Values (SOV) is the contract broken into specific scopes.

| Column | What It Means |
|---|---|
| `sov_line_id` | The granular key. Format: `PRJ-2024-001-SOV-04`. Every labor log, material delivery, billing line item, and change order links to this. |
| `line_number` | 1–15, always in the same order (see below) |
| `description` | The 15 standard work categories |
| `scheduled_value` | The dollar value of that scope in the contract — what the subcontractor will bill for completing it |
| `labor_pct` | What fraction of `scheduled_value` represents labor revenue |
| `material_pct` | What fraction represents material revenue |

**The 15 Work Categories in Execution Order:**
1. General Conditions & Project Management
2. Submittals & Engineering
3. Ductwork – Fabrication
4. Ductwork – Installation
5. Piping – Hydronic Systems
6. Piping – Refrigerant
7. Equipment – RTUs/AHUs *(rooftop units, air handlers)*
8. Equipment – Chillers/Boilers
9. Equipment – Terminal Units (VAV/FCU) *(zone-level control devices)*
10. Controls – DDC/BAS Installation *(digital controls hardware)*
11. Controls – Programming & Commissioning
12. Insulation
13. Testing, Adjusting & Balancing (TAB)
14. Startup & Commissioning Support
15. Closeout Documentation & Training

**What it indicates:** The sequence matters. Lines 1–2 are administrative overhead. Lines 3–9 are physical installation (most labor and material). Lines 10–15 are the finishing and verification work that unlocks final payment. Projects that get stuck in Lines 10–15 often have retention sitting unpaid for months while the subcontractor waits for the owner to sign off.

---

### 3. `sov_budget_all.csv` — The Cost Estimate Behind Each Line
**What it is:** One row per SOV line per project. The internal cost estimate — what the subcontractor's estimator said it would cost to execute each scope.

| Column | What It Means |
|---|---|
| `estimated_labor_hours` | How many man-hours to complete this line item |
| `estimated_labor_cost` | Hours × average blended rate. The ceiling for labor spending on this scope. |
| `estimated_material_cost` | Material purchasing budget for this scope |
| `estimated_equipment_cost` | Rental equipment (lifts, cranes). Note: Equipment lines (SOV-07, 08, 09) have $0 here — those are purchased equipment tracked as material deliveries, not cost. |
| `estimated_sub_cost` | Any work sub-contracted out by the mechanical sub |
| `productivity_factor` | A multiplier below 1.0 signals the estimator built in difficulty. Ductwork Fabrication (SOV-03) is set to 0.85, meaning 15% harder than baseline. |
| `key_assumptions` | Text field. Critical — if actual conditions violate these assumptions (e.g., "clear site access"), the estimate is invalid and a change order may be warranted. |

**What it indicates:** The gap between `scheduled_value` (from `sov_all`) and `estimated_labor_cost + estimated_material_cost + estimated_equipment_cost + estimated_sub_cost` is the **built-in margin per line item before work starts.** Negative gaps mean the line was bid at a loss.

---

### 4. `labor_logs_all.csv` — Every Hour Worked (1.2M Rows)
**What it is:** One row per employee per day per project per SOV line. The most granular dataset.

| Column | What It Means |
|---|---|
| `employee_id` | Worker identifier. Tracks individuals across projects. |
| `role` | Job classification. Note: the same role appears under multiple name variants ("Journeyman Pipefitter", "JM Pipefitter", "J. Pipefitter", "Pipefitter JM") — these must be standardized before any analysis. |
| `sov_line_id` | Which scope this worker's hours are charged to |
| `hours_st` | Standard time hours (paid at `hourly_rate × burden_multiplier`) |
| `hours_ot` | Overtime hours (paid at `hourly_rate × 1.5 × burden_multiplier`). 15% of all log entries contain OT. |
| `hourly_rate` | Base hourly wage |
| `burden_multiplier` | Total employment cost multiplier (1.38–1.42). Covers benefits, payroll taxes, workers' comp, union dues. A $74.50/hr pipefitter actually costs $74.50 × 1.42 = **$105.79/hr** to employ. |
| `work_area` | Floor, zone, or section of the building. Used for spatial productivity analysis. |
| `cost_code` | Numeric code 1–15, maps directly to SOV line number |

**What it indicates:** Actual labor cost per scope, per day, per person. The primary driver of cost overruns on labor-intensive scopes (Ductwork Installation, Piping, Controls).

---

### 5. `material_deliveries_all.csv` — Physical Materials Received
**What it is:** One row per delivery event. Records what arrived on site, when, at what cost.

| Column | What It Means |
|---|---|
| `sov_line_id` | Which scope this material supports |
| `material_category` | Category name — heavily inconsistent (25+ variants for the same 6 categories). Must be standardized: Ductwork, Piping, Equipment, Controls, Insulation are the real categories. |
| `unit_cost` | Cost per unit. Compare to estimated unit rates to spot vendor overcharges or favorable buys. |
| `total_cost` | Actual spend on this delivery |
| `vendor` | 6 vendors: ACR Group, Johnstone Supply, RE Michel, Ferguson Supply, Winsupply, Carrier Enterprise |
| `condition_notes` | Three values: "Good condition" (66%), "Minor packaging damage – product OK" (17%), "Partial shipment – backorder pending" (17%) |

**What it indicates:** Actual material cost per scope. The 17% partial shipment rate is a supply chain signal — nearly 1 in 5 deliveries is incomplete, which can idle workers waiting for materials. Cross-reference delivery dates against labor logs to quantify idle time caused by material shortages.

---

### 6. `change_orders_all.csv` — Every Contract Modification
**What it is:** One row per change order. A change order is a formal request to adjust the contract price, scope, or schedule.

| Column | What It Means |
|---|---|
| `co_number` | Sequential within a project. High CO numbers late in a project signal scope instability. |
| `reason_category` | The cause: Scope Gap, Design Error, Acceleration, Unforeseen Condition, Code Compliance, Value Engineering, Owner Request, Coordination |
| `amount` | Dollar value. Value Engineering COs are **negative** (they reduce the contract — the owner swaps something for a cheaper alternative). |
| `status` | Approved (75.4%) or Rejected (24.6%). Rejected COs represent work done with no payment. |
| `related_rfi` | If an RFI triggered this CO, the RFI number appears here. Blank = CO arose without a preceding RFI. |
| `affected_sov_lines` | List of SOV lines impacted. Use this to allocate CO cost/revenue back to specific scopes. |
| `labor_hours_impact` | Additional hours required by this CO. Approved COs with high `labor_hours_impact` inflate actual labor cost on those SOV lines. |
| `schedule_impact_days` | Days added to the schedule. Values cluster at 0, 2, 5, 7, 14. A project with multiple 7- and 14-day COs may have its completion date quietly extended by months. |

**What it indicates:**
- **Scope Gap + Design Error** = design wasn't complete at bid. The subcontractor bid on an incomplete design and is now recovering costs for work that should have been included originally.
- **Acceleration** = the schedule slipped (for any reason) and the GC is paying a premium to recover it. Average approved Acceleration CO: $201,615.
- **Owner Request** = the highest-value category. Average $341,937 per CO, but 20 were rejected totaling $6.28M in unrecovered cost. These often involve late-stage scope additions.
- **Value Engineering** = negative revenue. Average -$140,318 per approved CO. These subtract from contract value.

---

### 7. `rfis_all.csv` — Field Questions and Design Clarifications
**What it is:** One row per Request for Information. When field workers encounter something not addressed (or wrong) in the design drawings, they stop and formally ask for direction.

| Column | What It Means |
|---|---|
| `date_submitted` | When the field raised the question |
| `date_required` | When the field needs an answer to avoid stopping work |
| `date_responded` | When the design team actually answered |
| `priority` | Low / Medium / High. High-priority RFIs on critical path scopes are schedule bombs. |
| `cost_impact` | Boolean. True for 25.2% of all RFIs. |
| `schedule_impact` | Boolean. True for 20.0% of all RFIs. |
| `related_rfi` | Referenced in `change_orders_all` — traces which RFIs became change orders. |

**What it indicates:** Response lag = `date_responded - date_required`. Average across the dataset: **-6.2 days** (responses come before the deadline on average). However, **13% of RFIs get late responses** — and late-response RFIs have a cost impact rate of 27.0% vs. 25.0% for on-time responses. The gap is modest here, but at the individual project level, a string of late RFIs on a critical scope is a schedule and cost event.

---

### 8. `billing_history_all.csv` — Payment Applications
**What it is:** One row per billing application per project. The subcontractor submits these monthly to request payment.

| Column | What It Means |
|---|---|
| `application_number` | Sequential. The number of billings tells you how long the project has been running. |
| `period_end` | The billing cutoff date |
| `period_total` | New amount billed this period |
| `cumulative_billed` | Running total billed to date |
| `retention_held` | Cumulative retention withheld (always 10% of `cumulative_billed`) |
| `net_payment_due` | `cumulative_billed × 0.90` — what actually gets paid (excluding retention) |
| `status` | Paid (53.8%), Pending (28.7%), Approved (17.5%) |
| `payment_date` | When money actually arrived. Only populated for Paid status. |

**What it indicates:** Average payment lag for Paid applications: **32.5 days** against a Net 30 contract. 62% of all paid invoices were paid late. This is a cash flow problem — the subcontractor is funding the job for 32+ days before receiving payment, while also having 10% permanently withheld.

---

### 9. `billing_line_items_all.csv` — Progress Per Work Category
**What it is:** One row per SOV line per billing application. The detailed breakdown of every billing submission.

| Column | What It Means |
|---|---|
| `scheduled_value` | Contract value of this SOV line (same as `sov_all`) |
| `previous_billed` | What was billed on this line through all prior applications |
| `this_period` | New amount billed this application |
| `total_billed` | Running billed-to-date on this line |
| `pct_complete` | `total_billed / scheduled_value`. This is the **official progress percentage** as agreed between the sub and GC. |
| `balance_to_finish` | `scheduled_value - total_billed` — remaining revenue to be earned |

**What it indicates:** `pct_complete` is the single most important number in this file. Compare it against the labor burn rate (actual hours ÷ estimated hours) to detect whether the project is on track or burning cost ahead of progress.

---

### 10. `field_notes_all.csv` — Daily Site Conditions
**What it is:** One row per field note entry. Multiple entries per project per day across 5 note types: Daily Report, Coordination Note, Issue Log, Safety Log, Inspection Note.

| Column | What It Means |
|---|---|
| `note_type` | All 5 types appear at roughly equal frequency (~20,600–20,860 each) |
| `content` | Free text. Occasionally contains multi-sentence descriptions of scope changes that didn't make it into formal COs — potential uncompensated work. |
| `photos_attached` | 0 or 1. Notes with photos may document damage claims or site conditions. |
| `weather` | Clear, Cloudy, Partly Cloudy, Cold, Rain, Hot |
| `temp_high` / `temp_low` | Daily temperature range. Hot days (weather = "Hot") can reduce outdoor labor productivity. |

**What it indicates:** Context layer for everything else. The `date` field ties notes to specific labor log entries and delivery records. Three field notes in the dataset contain unusually long content strings — these describe multi-month scope disputes (ductwork rerouting conflicts, controls programming revisions, out-of-scope kitchen exhaust work) that are operational alerts for potential unrecovered cost.

---

## Part 2 — How the Files Connect (The Join Map)

```
contracts_all
    └── project_id ──────────────────────────────────────────────────────────┐
                                                                              │
sov_all                                                                       │
    ├── project_id → joins contracts                                          │
    └── sov_line_id ──────────────────────────────────────────────────────┐  │
                                                                          │  │
sov_budget_all                                                            │  │
    ├── project_id → joins contracts                                      │  │
    └── sov_line_id → joins sov_all (1-to-1)                             │  │
                                                                          │  │
labor_logs_all                                                            │  │
    ├── project_id → joins contracts                                      │  │
    └── sov_line_id → joins sov_all (many-to-1)                         ←┘  │
                                                                             │
material_deliveries_all                                                      │
    ├── project_id → joins contracts                                         │
    └── sov_line_id → joins sov_all (many-to-1)                            │
                                                                             │
billing_line_items_all                                                       │
    ├── project_id → joins contracts                                         │
    ├── sov_line_id → joins sov_all (many-to-1)                            │
    └── application_number → joins billing_history_all                      │
                                                                             │
billing_history_all                                                          │
    └── project_id → joins contracts ←──────────────────────────────────────┘

change_orders_all
    ├── project_id → joins contracts
    ├── related_rfi → joins rfis_all (rfi_number)
    └── affected_sov_lines → joins sov_all (list field, requires parsing)

rfis_all
    └── project_id → joins contracts

field_notes_all
    └── project_id → joins contracts
    (date field enables time-based cross-referencing to labor_logs and material_deliveries)
```

**Critical data quality issues to fix before any analysis:**
- `labor_logs`: Role names have 30+ variants for 8 actual roles. Standardize before grouping.
- `material_deliveries`: `material_category` has 25+ variants for 6 actual categories. Standardize.
- `change_orders`: `affected_sov_lines` is a string representation of a Python list — must be parsed.
- `field_notes`: 3 rows have non-standard `note_type` values (long text strings). Flag separately.
- `field_notes`: 1 row has `weather = "RFI-042"` — data entry error, set to null.

---

## Part 3 — The Calculations

### Calculation 1: Built-In Margin Per SOV Line (Pre-Work Baseline)

**Files needed:** `sov_all` + `sov_budget_all`
**Join on:** `sov_line_id`

```
budgeted_total_cost = estimated_labor_cost
                    + estimated_material_cost
                    + estimated_equipment_cost
                    + estimated_sub_cost

line_margin_$ = scheduled_value - budgeted_total_cost
line_margin_% = line_margin_$ / scheduled_value × 100
```

**What it tells you:** Lines with negative margin were bid at a loss from day one. Equipment lines (SOV-07, 08, 09) show `estimated_equipment_cost = 0` — this is because purchased equipment cost appears in `material_deliveries`, not in the budget estimates. Adjust accordingly.

**What good looks like:** Margins of 8–15% per line are healthy for a mechanical sub. Under 5% means there is no room for any overrun.

---

### Calculation 2: Actual Labor Cost Per SOV Line

**Files needed:** `labor_logs_all`
**Group by:** `project_id` + `sov_line_id`

```
actual_labor_cost = SUM(
    (hours_st × hourly_rate × burden_multiplier)
  + (hours_ot × hourly_rate × 1.5 × burden_multiplier)
)

actual_total_hours = SUM(hours_st + hours_ot)
ot_ratio = SUM(hours_ot) / actual_total_hours
```

**What it tells you:** The true cost of labor for each scope. The 1.5× overtime multiplier on top of burden means overtime hours cost 50% more — an OT ratio above 20% on a labor-intensive line is a meaningful margin risk. Compare `actual_labor_cost` to `estimated_labor_cost` from `sov_budget_all`.

---

### Calculation 3: Labor Productivity Ratio (The Core Performance Metric)

**Files needed:** `labor_logs_all` + `billing_line_items_all` + `sov_budget_all`
**Join on:** `project_id` + `sov_line_id`

```
hours_burn_rate = actual_total_hours / estimated_labor_hours
pct_complete = total_billed / scheduled_value  (from billing_line_items, latest application)

productivity_ratio = pct_complete / hours_burn_rate
```

**What it tells you:**
- `productivity_ratio = 1.0`: Burning hours exactly in line with progress — on track.
- `productivity_ratio < 1.0` (e.g., 0.75): Burned 33% more hours than the work completed warrants — labor is underperforming. The project will finish over budget on labor.
- `productivity_ratio > 1.0`: Ahead of plan — either efficient execution or the billing team is overclaiming progress.

**Example from PRJ-2024-001:** Ductwork Installation (SOV-04) shows actual labor of $265,724 against a $2,457,300 budget. If `pct_complete` on that line is also only ~11%, the ratio is healthy. But if billing shows 40% complete while only $265K has been spent on a $2.46M labor budget, there's a billing overclaim to investigate.

---

### Calculation 4: Cost Variance Per Line (For Active Projects, Normalize by Progress)

**Files needed:** `sov_budget_all` + `labor_logs_all` + `material_deliveries_all` + `billing_line_items_all`

```
budget_at_completion = estimated_labor_cost + estimated_material_cost
                     + estimated_equipment_cost + estimated_sub_cost

actual_cost_to_date = actual_labor_cost + actual_material_cost

estimate_at_completion = actual_cost_to_date / pct_complete
  (projects the final cost based on current spending rate)

cost_variance = budget_at_completion - estimate_at_completion
  (positive = under budget, negative = over budget)

cost_performance_index = budget_at_completion × pct_complete / actual_cost_to_date
  (above 1.0 = efficient, below 1.0 = over-spending relative to progress)
```

**Why not just compare raw actuals to budget:** A project that is 30% complete and has spent 25% of its budget looks fine in absolute terms — but if it's about to enter the most expensive phase, a raw comparison is misleading. Dividing actual cost by `pct_complete` to project final cost is the correct approach.

---

### Calculation 5: Change Order Impact on Revenue

**Files needed:** `change_orders_all`
**Group by:** `project_id`

```
approved_co_revenue = SUM(amount WHERE status = 'Approved')
rejected_co_loss = SUM(amount WHERE status = 'Rejected' AND amount > 0)
  (negative amounts = Value Engineering, excluded from loss calculation)

revised_contract_value = original_contract_value + approved_co_revenue
  (join to contracts_all for original_contract_value)

co_rejection_rate = COUNT(rejected) / COUNT(total)
co_loss_rate = rejected_co_loss / SUM(amount WHERE amount > 0)
```

**What it tells you:** `revised_contract_value` is the true revenue ceiling. `co_loss_rate` tells you what fraction of all submitted additional work was denied — a rate consistently above 30% against a specific GC suggests that GC disputes aggressively. Cross-tab rejection rates by `gc_name` to identify adversarial clients.

---

### Calculation 6: Schedule Impact Accumulation

**Files needed:** `change_orders_all`
**Group by:** `project_id`

```
total_co_schedule_days = SUM(schedule_impact_days WHERE status = 'Approved')

original_duration_days = substantial_completion_date - contract_date
  (join to contracts_all)

schedule_growth_pct = total_co_schedule_days / original_duration_days × 100
```

**What it tells you:** A project with 30 days of approved schedule-impact COs on a 540-day original timeline has grown 5.6% in duration. This affects staffing plans, retention release timing, and general conditions cost. CO counts of 0, 2, 5, 7, and 14 days dominate — these cluster at weekly intervals, suggesting foremen report impacts in round-week increments.

---

### Calculation 7: RFI Response Lag and Financial Exposure

**Files needed:** `rfis_all`

```
response_lag_days = date_responded - date_required
  (positive = late response)

late_rfis = COUNT WHERE response_lag_days > 0
late_rfi_rate = late_rfis / total_rfis

cost_impact_rfis_with_no_co = COUNT(
  rfis WHERE cost_impact = True
  AND rfi_number NOT IN (change_orders.related_rfi)
)
```

**What it tells you:** `cost_impact_rfis_with_no_co` is the most important number here — RFIs where someone on site acknowledged a cost was incurred, but no change order was ever submitted or approved to recover it. Each one of these is a dollar amount left on the table. To quantify it, compare average approved CO amounts for RFIs that did become COs against the number of unrecovered RFIs.

---

### Calculation 8: Billing Cash Flow Analysis

**Files needed:** `billing_history_all` + `contracts_all`

```
payment_lag_days = payment_date - period_end
  (for Paid applications only)

overdue_applications = billing WHERE status = 'Pending'
                       AND (TODAY - period_end) > 30

total_overdue_balance = SUM(net_payment_due WHERE status = 'Pending'
                           AND (TODAY - period_end) > 30)

total_retention_held = SUM(retention_held) across all projects
  (money earned but contractually withheld)

retention_releasable = SUM(retention_held WHERE project past
                          substantial_completion_date AND status ≠ fully closed)
```

**What it tells you:** 62% of paid invoices arrived late despite Net 30 terms. `total_overdue_balance` is cash the company has earned, invoiced, and is legally owed but hasn't received. `retention_releasable` is equally important — projects past their completion date with retention still held are a working capital drain that should be chased aggressively.

---

### Calculation 9: Vendor Concentration and Unit Cost Tracking

**Files needed:** `material_deliveries_all`

```
vendor_spend_share = SUM(total_cost GROUP BY vendor) / SUM(total_cost)

unit_cost_trend = AVG(unit_cost GROUP BY item_description, vendor, year)
  (requires extracting year from delivery date)

partial_shipment_rate = COUNT(condition_notes = 'Partial shipment - backorder pending')
                       / COUNT(total deliveries)

partial_shipment_labor_cost = SUM(labor_logs.actual_labor_cost
  WHERE date BETWEEN delivery_date AND next_complete_delivery_date
  AND sov_line_id = affected delivery sov_line_id)
```

**What it tells you:** 6 vendors split all $6.4B of material purchasing fairly evenly. `unit_cost_trend` tracks whether you're paying more for the same item over time — useful for renegotiation leverage. The `partial_shipment_labor_cost` calculation attempts to quantify idle labor caused by incomplete deliveries: find all labor log entries on the same SOV line during the gap between a partial delivery and its completion, subtract normal productivity hours, and the residual is delivery-caused waste.

---

### Calculation 10: Weather-Productivity Correlation

**Files needed:** `field_notes_all` + `labor_logs_all`

```
daily_labor_hours = SUM(hours_st + hours_ot GROUP BY project_id, date)
  (from labor_logs)

join to field_notes on project_id + date to get weather condition

avg_hours_by_weather = AVG(daily_labor_hours GROUP BY weather)

productivity_penalty_hot = (avg_hours_on_clear_days - avg_hours_on_hot_days)
                          / avg_hours_on_clear_days
```

**What it tells you:** If crews log an average of 7.2 hours on Clear days vs. 6.4 hours on Hot days, there is an 11% weather productivity penalty. Multiplied across outdoor scopes (Ductwork Installation, Piping) over summer months, this produces a quantifiable labor cost impact that can support future change order claims for extreme weather conditions.

---

## Part 4 — Cause-and-Effect Chains

These are the specific multi-file sequences that explain *why* a project ends up over budget or behind schedule. Each chain starts with a signal in one file and traces through to a financial consequence in another.

---

### Chain A: Design Incomplete at Bid → Cost Recovery Failure

**Trigger:** `change_orders` with `reason_category = 'Scope Gap'` or `'Design Error'`

**Trace:**
1. A Design Error CO is submitted referencing `related_rfi = RFI-045`
2. Go to `rfis_all`, find RFI-045: submitted April 26, thermostat location conflicts with furniture layout. Flagged `cost_impact = True`
3. Go to `labor_logs_all`: find all entries on `sov_line_id = PRJ-2024-001-SOV-10` (Controls DDC Installation) between April 26 and the CO approval date
4. Those hours represent rework — controls workers installing, then relocating thermostats
5. Check if the approved CO amount covers those labor hours: `approved_co_amount vs. actual_rework_labor_cost`
6. The gap = unrecovered rework cost

**Pattern to find across all 405 projects:** Projects where `(Design Error COs + Scope Gap COs) / original_contract_value > 5%` consistently show lower final margins. The design team failed to complete drawings before the bid, and the subcontractor bid on a fiction.

---

### Chain B: Material Shortage → Idle Labor → Acceleration CO

**Trigger:** `material_deliveries` with `condition_notes = 'Partial shipment - backorder pending'`

**Trace:**
1. Delivery DEL-001-7b34a2 arrives April 13: Spiral Duct 16", 263 LF delivered, backorder pending. SOV line = SOV-03 (Ductwork Fabrication)
2. Go to `labor_logs_all`: find all Journeyman Sheet Metal workers on SOV-03 from April 13 onward
3. If hours are logged but `billing_line_items` shows `pct_complete` on SOV-03 not advancing, those are idle or make-work hours — workers are present but can't install duct that hasn't arrived
4. Check when the backorder was fulfilled (next delivery for same PO number or same item)
5. Go to `change_orders_all`: any Acceleration CO submitted in the weeks following, on SOV-03 or SOV-04? If the delay pushed ductwork installation into overtime to recover schedule, the Acceleration CO is the financial consequence of the original delivery shortage

**Financial measurement:** `cost_of_idle_labor + overtime_premium_for_acceleration - approved_acceleration_CO_amount` = net loss from supply chain failure

---

### Chain C: Slow RFI Response → Unpaid Schedule Impact

**Trigger:** `rfis` where `response_lag_days > 0` AND `schedule_impact = True`

**Trace:**
1. RFI submitted, `date_required = April 30`, `date_responded = May 10` → 10-day late response
2. `schedule_impact = True`, `cost_impact = True`
3. Check `change_orders`: is there an approved CO referencing this RFI? If yes, was the CO amount sufficient?
4. Go to `labor_logs`: pull all entries for this `project_id` across the 10-day lag period
5. If crews were on site but billing progress didn't advance (cross-check `billing_line_items`), those are confirmed standby labor costs
6. If no CO was approved covering this period → all standby labor is unrecovered cost

**The question to answer at portfolio scale:** Do projects with GCs known for slow RFI responses (identify by `assigned_to` in `rfis_all` and cross-reference `gc_name` from `contracts`) also show systematically lower margins?

---

### Chain D: Rejected Change Order → Silent Margin Erosion

**Trigger:** `change_orders` where `status = 'Rejected'` AND `amount > 0`

**Trace:**
1. Identify all rejected COs for a project. Sum their `amount` values and `labor_hours_impact`
2. Cross-reference `affected_sov_lines` — which SOV lines were the work actually performed on?
3. Go to `labor_logs`: the actual labor hours for those SOV lines will exceed `estimated_labor_hours` from `sov_budget_all` by approximately `labor_hours_impact` (the work was done, just not paid for)
4. Calculate: `rejected_labor_cost = labor_hours_impact × average_burdened_rate_for_relevant_roles`
5. This is the direct margin impact of CO rejection

**Pattern across 405 projects:** Owner Request COs have the highest rejection total ($6.28M across this dataset). This suggests that when owners ask for extra work verbally and it gets priced formally, they often dispute the price and reject the CO — but the work was already done. Establish whether specific GCs show disproportionately high Owner Request rejection rates.

---

### Chain E: High Early CO Volume → Project Financial Distress

**Trigger:** `change_orders` — compare CO submission timing relative to project start

**Trace:**
1. For each project, calculate `days_since_start = co_date_submitted - contract_date`
2. Count COs submitted in the first 20% of the project duration (`days_since_start / original_duration_days < 0.20`)
3. For completed projects (where `substantial_completion_date` is past), calculate final margin using Cost Variance (Calculation 4)
4. Correlate: do projects with more than X COs in the first 20% of their duration finish with lower margins?

**What this builds toward:** An early-warning scoring model. If you know that projects with 5+ COs in the first 10 weeks historically finish 3 margin points below average, you can flag live projects hitting that threshold and intervene — request acceleration on billing, tighten field cost controls, or proactively pursue CO recovery.

---

## Part 5 — The Analytical Sequence (What to Run First)

The recommended order is not arbitrary — each step produces the numbers needed for the next.

**Step 1: Data Cleaning**
Standardize role names in `labor_logs`. Standardize category names in `material_deliveries`. Parse `affected_sov_lines` list field in `change_orders`. This is table-stakes before any grouping operation.

**Step 2: Build the Project Master Table**
One row per project. Columns: contract value, project type, GC, planned duration, total estimated cost (summed from `sov_budget`), total approved COs, revised contract value. This is the foundation every subsequent analysis joins back to.

**Step 3: Compute Actual Cost Per SOV Line Per Project**
Sum labor cost and material cost from `labor_logs` and `material_deliveries` by `project_id + sov_line_id`. This is the most computationally intensive step given 1.2M labor rows.

**Step 4: Join Billing Progress**
Pull the latest `pct_complete` per SOV line from `billing_line_items` (highest `application_number` per `project_id + sov_line_id`). This gives you current progress for active projects and final progress for completed ones.

**Step 5: Calculate Cost Performance Index Per Line**
Using Calculation 4. Flag any line below 0.85 CPI as a cost risk. This produces a ranked list of troubled scopes across all 405 projects.

**Step 6: Layer in Change Order Revenue and Loss**
Add approved CO totals to revised contract value. Separately tally rejected CO amounts. Cross-tab both by project type and GC to find patterns.

**Step 7: Run the Cash Flow Analysis**
Identify all overdue billing applications and total outstanding retention. These are numbers the CFO needs immediately — they represent earned but uncollected cash.

**Step 8: Build the Cause-and-Effect Chains for the Worst Performers**
Take the bottom 10% of projects by Cost Performance Index and run the 5 causal chains described in Part 4. Identify which chain is most prevalent — that tells you whether the company's biggest margin leak is design quality, supply chain, owner behavior, or execution.

**Step 9: Build the Early Warning Model**
Using completed projects as training data: identify which early-stage metrics (CO volume in first 20% of duration, RFI cost-impact rate, OT ratio in first 8 weeks, partial shipment rate) most strongly predict final CPI. This converts the retrospective analysis into a forward-looking management tool.

---

## Summary Reference: What Each Metric Tells You

| Metric | Source Files | Healthy Range | Red Flag |
|---|---|---|---|
| Line-item built-in margin % | `sov_all` + `sov_budget_all` | 8–15% | < 5% |
| Labor productivity ratio | `labor_logs` + `billing_line_items` + `sov_budget_all` | 0.95–1.10 | < 0.80 |
| Cost Performance Index | Same as above | > 1.0 | < 0.85 |
| OT ratio | `labor_logs` | < 15% | > 25% |
| CO rejection rate | `change_orders_all` | < 20% | > 35% |
| RFI late response rate | `rfis_all` | < 10% | > 20% |
| Cost-impact RFIs with no CO | `rfis_all` + `change_orders_all` | < 5% of all RFIs | > 15% |
| Payment lag vs. Net 30 | `billing_history_all` | ≤ 30 days | > 45 days |
| Pending billing % | `billing_history_all` | < 15% | > 30% |
| Partial shipment rate | `material_deliveries_all` | < 10% | > 20% |
| Schedule growth % from COs | `change_orders_all` + `contracts_all` | < 5% | > 15% |
