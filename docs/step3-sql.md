# Step 3: BigQuery SQL Views

## Overview

Three SQL views transform raw tables into dashboard-ready metrics:

1. **`mrr_monthly`** — Monthly MRR with customer and subscription counts
2. **`mrr_by_plan`** — MRR broken down by pricing tier
3. **`arppu_monthly`** — Average Revenue Per Paying User

## Prerequisites

- Step 2 completed (raw tables loaded in BigQuery)
- Replace `PROJECT_ID` in all SQL files with your actual GCP project ID
- Replace `price_XXXXX` in `mrr_by_plan_view.sql` with actual Price IDs from `seed_prices.py` output

## Running

Run each SQL file in the BigQuery Console or via the `bq` CLI:

```bash
# Replace PROJECT_ID first, then run:
bq query --use_legacy_sql=false < sql/mrr_view.sql
bq query --use_legacy_sql=false < sql/mrr_by_plan_view.sql
bq query --use_legacy_sql=false < sql/arpu_view.sql
```

## View Details

### `mrr_monthly`

Monthly MRR aggregation from paid subscription invoices.

- **Filters**: `status = 'paid'`, `subscription_id IS NOT NULL`, `amount_paid > 0`
- **Groups by**: `DATE_TRUNC(period_start, MONTH)` — uses billing period, not invoice creation date
- **Why `period_start`**: With test clocks, all invoices may be created at the same time, but `period_start` correctly reflects the billing month

| Column | Type | Description |
|--------|------|-------------|
| month | DATE | First day of the month |
| mrr_amount | FLOAT | Total MRR in dollars |
| paying_customers | INTEGER | Distinct customers with paid invoices > $0 |
| total_customers | INTEGER | All customers with any paid invoices (including $0) |
| active_subscriptions | INTEGER | Distinct active subscriptions |

### `mrr_by_plan`

Revenue breakdown by plan tier using `price_id` from invoice line items.

- **Plan attribution**: Uses `price_id` extracted during ETL from invoice line items, not subscription current state. This ensures historically accurate attribution even after upgrades/downgrades.
- **CASE mapping**: Maps price IDs to human-readable plan names

| Column | Type | Description |
|--------|------|-------------|
| month | DATE | First day of the month |
| plan_name | STRING | Free, Standard, Pro Plus, Engage, Enterprise |
| mrr_amount | FLOAT | MRR for this plan in dollars |

### `arppu_monthly`

Average Revenue Per Paying User. Based on `mrr_monthly` view.

- **Formula**: `mrr_amount / paying_customers`
- **Excludes free tier**: Only paying customers in denominator for actionable pricing insight

| Column | Type | Description |
|--------|------|-------------|
| month | DATE | First day of the month |
| mrr_amount | FLOAT | Total MRR (from mrr_monthly) |
| paying_customers | INTEGER | Paying customer count |
| arppu | FLOAT | Average revenue per paying user |

## Verification

```sql
-- Check MRR trend (expect ~6 rows, growing MRR)
SELECT * FROM stripe_mrr.mrr_monthly ORDER BY month;

-- Check plan breakdown
SELECT * FROM stripe_mrr.mrr_by_plan ORDER BY month, plan_name;

-- Check ARPPU
SELECT * FROM stripe_mrr.arppu_monthly ORDER BY month;
```
