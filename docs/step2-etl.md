# Step 2: Batch ETL Pipeline

## Overview

`etl/extract_load.py` loads subscription snapshots into BigQuery and creates views for MRR, ARPPU, churn, and plan breakdowns. MRR calculations are driven by snapshots (not invoices) for accuracy. The pipeline is idempotent — each run truncates and reloads all tables.

## Prerequisites

- Step 1 completed (`generate_data.py` has run, config files exist)
- `.env` configured with `STRIPE_SECRET_KEY`, `GCP_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`
- GCP service account has `BigQuery Data Editor` and `BigQuery User` roles
- `uv sync` completed

## Running

```bash
uv run python etl/extract_load.py
```

## What It Does

1. **Creates dataset** `stripe_mrr` in BigQuery if it doesn't exist
2. **Loads subscription snapshots** from `config/sub_snapshots.json` into `sub_snapshots` table (source of truth for MRR)
3. **Creates views** for MRR, MRR by plan, ARPPU, customers by plan, and churn

## BigQuery Tables

### `stripe_mrr.sub_snapshots` (source of truth for MRR)

| Column | Type | Description |
|--------|------|-------------|
| month | STRING | Month label (e.g., `2025-08`) |
| customer_id | STRING | Stripe customer ID |
| subscription_id | STRING | Stripe subscription ID |
| plan | STRING | Plan key (e.g., `pro_plus`) |
| price_id | STRING | Stripe price ID |
| price_amount | INTEGER | Price per screen in cents |
| screens | INTEGER | Number of screens |
| mrr_cents | INTEGER | `price_amount × screens` |
| status | STRING | `active` or `past_due` |

## BigQuery Views

### `stripe_mrr.mrr_monthly`
Monthly MRR, paying customers, total customers, and active subscriptions. Derived from `sub_snapshots`.

### `stripe_mrr.mrr_by_plan`
MRR broken down by plan tier per month. Derived from `sub_snapshots`.

### `stripe_mrr.arppu_monthly`
Average Revenue Per Paying User per month. Derived from `mrr_monthly`.

### `stripe_mrr.customers_by_plan`
Customer count per plan tier per month. Derived from `sub_snapshots`.

### `stripe_mrr.churn_monthly`
Monthly customer churn rate. Uses `LAG()` over `mrr_monthly` to compare total customers month-over-month.

## Why Snapshots Instead of Invoices?

Stripe's test clock invoice generation is inconsistent — $0 invoices for Free tier may or may not be created, and proration invoices can spike MRR artificially. Subscription snapshots capture the exact state of each customer at each month, giving perfectly stable and accurate metrics.

## Load Strategy

- **WRITE_TRUNCATE**: Each run deletes existing data and reloads from scratch
- Idempotent: safe to re-run any number of times
- Customer filtering ensures only data from the latest `generate_data.py` run is loaded

## Verification

```bash
# Check tables exist
bq ls stripe_mrr

# Check snapshot count
bq query "SELECT COUNT(*) FROM stripe_mrr.sub_snapshots"

# Check MRR by month
bq query "SELECT * FROM stripe_mrr.mrr_monthly ORDER BY month"

# Check customers by plan
bq query "SELECT * FROM stripe_mrr.customers_by_plan ORDER BY month, plan_name"
```