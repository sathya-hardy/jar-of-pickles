# Step 2: Batch ETL Pipeline

## Overview

`etl/extract_load.py` loads subscription snapshots into BigQuery and extracts raw invoices/subscriptions from Stripe for reference. MRR calculations are driven by snapshots (not invoices) for accuracy. The pipeline is idempotent — each run truncates and reloads all tables.

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
3. **Extracts invoices** via `stripe.Invoice.search()` with auto-pagination (reference only)
4. **Extracts subscriptions** via `stripe.Subscription.search()` with auto-pagination (reference only)
5. **Filters** all Stripe data to only customers from the current run (reads `config/current_run.json`)
6. **Creates views** for MRR, MRR by plan, ARPPU, and customers by plan

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

### `stripe_mrr.raw_invoices` (reference)

| Column | Type | Source |
|--------|------|--------|
| invoice_id | STRING | `invoice.id` |
| customer_id | STRING | `invoice.customer` |
| subscription_id | STRING | `parent.subscription_details.subscription` |
| status | STRING | `invoice.status` |
| amount_paid | INTEGER | `invoice.amount_paid` (cents) |
| currency | STRING | `invoice.currency` |
| price_id | STRING | `line_item.pricing.price_details.price` |
| period_start | TIMESTAMP | `invoice.period_start` |
| period_end | TIMESTAMP | `invoice.period_end` |
| created | TIMESTAMP | `invoice.created` |

### `stripe_mrr.raw_subscriptions` (reference)

| Column | Type | Source |
|--------|------|--------|
| subscription_id | STRING | `sub.id` |
| customer_id | STRING | `sub.customer` |
| status | STRING | `sub.status` |
| price_id | STRING | `sub.items.data[0].price.id` |
| price_amount | INTEGER | `sub.items.data[0].price.unit_amount` (cents) |
| price_interval | STRING | `sub.items.data[0].price.recurring.interval` |
| quantity | INTEGER | `sub.items.data[0].quantity` (screens) |
| current_period_start | TIMESTAMP | `item.current_period_start` |
| current_period_end | TIMESTAMP | `item.current_period_end` |
| created | TIMESTAMP | `sub.created` |
| canceled_at | TIMESTAMP | `sub.canceled_at` (nullable) |

## BigQuery Views

### `stripe_mrr.mrr_monthly`
Monthly MRR, paying customers, total customers, and active subscriptions. Derived from `sub_snapshots`.

### `stripe_mrr.mrr_by_plan`
MRR broken down by plan tier per month. Derived from `sub_snapshots`.

### `stripe_mrr.arppu_monthly`
Average Revenue Per Paying User per month. Derived from `mrr_monthly`.

### `stripe_mrr.customers_by_plan`
Customer count per plan tier per month. Derived from `sub_snapshots`.

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