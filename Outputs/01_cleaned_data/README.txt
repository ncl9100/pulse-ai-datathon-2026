CLEANED DATA
=============
Standardized raw files from Step 1.

Key changes vs. raw files:
  - labor_logs:          30+ role name variants → 8 canonical; cost_code column dropped (redundant)
  - material_deliveries: 25+ category variants → 5 canonical
  - change_orders:       affected_sov_lines parsed from string list; exploded version = one row per SOV line
  - field_notes:         note_type and weather_conditions standardized
  - billing_line_items:  balance_to_finish, total_billed, scheduled_value, description dropped (redundant);
                         pct_manually_adjusted flag added where pct differs from derived value --> It's a flag (True/False) on each billing line that marks whether a project manager manually typed in a different pct_complete value than                           what the math would give.

  - billing_history:     retention_held, net_payment_due dropped (perfectly derived from cumulative_billed)
