# Step 3: BigQuery Views

## Overview

Four views transform the `sub_snapshots` table into dashboard-ready metrics:

1. **`mrr_monthly`** — Monthly MRR with customer and subscription counts
2. **`mrr_by_plan`** — MRR broken down by pricing tier
3. **`arppu_monthly`** — Average Revenue Per Paying User
4. **`customers_by_plan`** — Customer count per plan tier per month

## Prerequisites

- Step 2 completed (`extract_load.py` has run and loaded data into BigQuery)

## Running

Views are created automatically by `extract_load.py` — no manual SQL execution needed. Every time you run the ETL, the views are recreated with `CREATE OR REPLACE VIEW`.

```bash
uv run python etl/extract_load.py
```

## Data Source

All views are derived from the `sub_snapshots` table, which contains monthly point-in-time snapshots of every active subscription. Each row has the customer's plan, screen count, and `mrr_cents` (price per screen × screens) for that month. This gives stable, accurate metrics without relying on Stripe's inconsistent invoice generation.

## View Details

### `mrr_monthly`

Monthly MRR aggregation from subscription snapshots.

| Column | Type | Description |
|--------|------|-------------|
| month | STRING | Month label (e.g., `2025-08`) |
| mrr_amount | FLOAT | Total MRR in dollars (`SUM(mrr_cents) / 100`) |
| paying_customers | INTEGER | Distinct customers with `mrr_cents > 0` |
| total_customers | INTEGER | All active customers including Free tier |
| active_subscriptions | INTEGER | Distinct active subscriptions |

### `mrr_by_plan`

Revenue breakdown by plan tier.

| Column | Type | Description |
|--------|------|-------------|
| month | STRING | Month label |
| plan_name | STRING | Free, Standard, Pro Plus, Engage, Enterprise |
| mrr_amount | FLOAT | MRR for this plan in dollars |

### `arppu_monthly`

Average Revenue Per Paying User. Derived from `mrr_monthly`.

- **Formula**: `mrr_amount / paying_customers`
- **Guards against zero**: Returns 0 if no paying customers

| Column | Type | Description |
|--------|------|-------------|
| month | STRING | Month label |
| mrr_amount | FLOAT | Total MRR (from mrr_monthly) |
| paying_customers | INTEGER | Paying customer count |
| arppu | FLOAT | Average revenue per paying user |

### `customers_by_plan`

Customer count per plan tier per month.

| Column | Type | Description |
|--------|------|-------------|
| month | STRING | Month label |
| plan_name | STRING | Free, Standard, Pro Plus, Engage, Enterprise |
| customer_count | INTEGER | Number of customers on this plan |

## Verification

```sql
-- Check MRR trend (expect 7 rows, gradually growing MRR)
SELECT * FROM stripe_mrr.mrr_monthly ORDER BY month;

-- Check plan breakdown
SELECT * FROM stripe_mrr.mrr_by_plan ORDER BY month, plan_name;

-- Check ARPPU
SELECT * FROM stripe_mrr.arppu_monthly ORDER BY month;

-- Check customer distribution shift over time
SELECT * FROM stripe_mrr.customers_by_plan ORDER BY month, plan_name;
```