FOLDER: 04_billing_cash_flow
=============================
Tracks whether money is flowing as it should: are GCs paying on time, are invoices
stuck unpaid, and is retention being released after project completion?

Key terms:
  Retention    = 10% of every invoice withheld by the GC as a performance guarantee.
                 Should be released after the project reaches substantial completion.
  Net 30       = Standard payment terms: GC must pay within 30 days of invoice.
  Payment lag  = Days between when an invoice was submitted and when payment arrived.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: cash_flow_summary.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one project's overall cash flow summary.
405 rows.

  project_id              The project.

  total_applications      How many billing applications (invoices) were submitted
                          over the life of this project.
                          Example: 12 = 12 monthly invoices.

  max_cumulative_billed   Total amount billed to date across all applications.
                          Example: 38,022,400 = $38M billed total.

  total_retention_held    10% of max_cumulative_billed, currently withheld.
                          Example: 3,802,240 = $3.8M in retention held by the GC.

  late_payments           Number of invoices on this project that were paid after
                          the 30-day contract deadline.
                          Example: 5 = 5 invoices paid late.
                          Portfolio average: 62.5% of all invoices are paid late.

  avg_days_to_payment     Average number of days between invoice submission and payment.
                          Example: 31.6 days (vs. 30-day contract terms = slightly late).
                          Portfolio average: 32.5 days.

  gc_name                 The General Contractor.
                          Example: "JE Dunn"

  original_contract_value The signed contract price.

  project_type            Small / Medium / Large / Mega.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: overdue_applications.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one invoice that was submitted but never paid, and is past its due date.
Sorted from most overdue to least.
1,279 rows total. Total overdue amount: ~$11.3B.

Note: The large dollar total reflects that many of these "overdue" invoices are from
older completed projects where the billing_history status is simply "Pending" —
they may be settled in the contracts system but not marked Paid in this dataset.

  project_id              The project with the unpaid invoice.

  gc_name                 Which GC hasn't paid.
                          Example: "DPR Construction"

  application_number      Which invoice cycle is overdue.
                          Example: 2 = the second invoice was never marked Paid.

  period_end              The date this invoice covered work through.
                          Example: "2018-03-03" (a 2018 project — extremely overdue).

  days_overdue            How many days past the 30-day payment deadline this invoice is.
                          = (today - period_end) - 30 days
                          Example: 2,931 days overdue = over 8 years past due.

  net_payment_due         The dollar amount owed on this invoice (after 10% retention).
                          Example: 313,110 = $313K owed.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: retention_analysis.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One row = one project where retention money is still being held after the
scheduled completion date has passed. This money should have been released.
405 rows. Total unreleased retention: $635,473,120.

  project_id                  The project.

  gc_name                     Which GC is holding the retention.
                              Example: "JE Dunn"

  project_type                Small / Medium / Large / Mega.

  retention_held              Dollar amount currently withheld as retention.
                              = cumulative_billed × 10%
                              Example: 5,848,870 = $5.8M held on a Mega project.

  cumulative_billed           Total amount billed on this project to date.
                              Example: 58,488,700 = $58.5M billed.

  substantial_completion_date The date the project was supposed to be done.
                              Example: "2021-11-22"

  days_past_completion        How many days past the completion date retention is still held.
                              Example: 1,601 days = over 4 years past due.
                              This is money the subcontractor is owed but hasn't received.
