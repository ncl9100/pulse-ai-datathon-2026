CLEANED DATA
=============
Standardized raw files from Step 1.

Key changes vs. raw files:
  - labor_logs:          30+ role name variants → 8 canonical; cost_code column dropped (redundant)
  - material_deliveries: 25+ category variants → 5 canonical
  - change_orders:       affected_sov_lines parsed from string list; exploded version = one row per SOV line
  - field_notes:         note_type and weather_conditions standardized
  - billing_line_items:  balance_to_finish, total_billed, scheduled_value, description dropped (redundant);
                         pct_manually_adjusted flag added where pct differs from derived value --> It's a flag (True/False) on each billing line that marks whether a project manager manually typed in a different pct_complete value than what the math would give.

Example:
The math gives: (35,000 / 100,000) × 100 = 35%
But the recorded pct_complete = 40%
That 5% gap means a PM looked at the job site and said "we're actually 40% done with this scope, even though we've only billed 35% of the money." Maybe materials are on site but not yet billed, or the physical installation is ahead of the paperwork.
So pct_manually_adjusted = True on that row.
The flag matters because in Step 5, pct_complete drives the Earned Value calculation (EV = BAC × pct_complete). A manually-adjusted row means the EV is based on a human judgment call, not just billing math — which is actually more accurate, but worth knowing when you're auditing results.

  - billing_history:     retention_held, net_payment_due dropped (perfectly derived from cumulative_billed)
