# Step 2: Batch ETL Pipeline

## Overview

`etl/extract_load.py` extracts all invoices and subscriptions from Stripe's API and loads them into BigQuery raw tables. The pipeline is idempotent — each run truncates and reloads the tables.

## Prerequisites

- Step 1 completed (data exists in Stripe)
- `.env` configured with `STRIPE_SECRET_KEY`, `GCP_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`
- GCP service account has `BigQuery Data Editor` and `BigQuery User` roles
- `uv sync` completed

## Running

```bash
uv run python etl/extract_load.py
```

## What It Does

1. **Creates dataset** `stripe_mrr` in BigQuery if it doesn't exist
2. **Extracts invoices** via `stripe.Invoice.list()` with auto-pagination and line item expansion
3. **Extracts subscriptions** via `stripe.Subscription.list(status="all")`
4. **Loads data** into BigQuery using pandas DataFrames and `WRITE_TRUNCATE`

## BigQuery Tables

### `stripe_mrr.raw_invoices`

| Column | Type | Source |
|--------|------|--------|
| invoice_id | STRING | `invoice.id` |
| customer_id | STRING | `invoice.customer` |
| subscription_id | STRING | `invoice.subscription` |
| status | STRING | `invoice.status` |
| amount_paid | INTEGER | `invoice.amount_paid` (cents) |
| currency | STRING | `invoice.currency` |
| price_id | STRING | `invoice.lines.data[0].price.id` |
| period_start | TIMESTAMP | `invoice.period_start` |
| period_end | TIMESTAMP | `invoice.period_end` |
| created | TIMESTAMP | `invoice.created` |

### `stripe_mrr.raw_subscriptions`

| Column | Type | Source |
|--------|------|--------|
| subscription_id | STRING | `sub.id` |
| customer_id | STRING | `sub.customer` |
| status | STRING | `sub.status` |
| price_id | STRING | `sub.items.data[0].price.id` |
| price_amount | INTEGER | `sub.items.data[0].price.unit_amount` (cents) |
| price_interval | STRING | `sub.items.data[0].price.recurring.interval` |
| quantity | INTEGER | `sub.items.data[0].quantity` (screens) |
| current_period_start | TIMESTAMP | `sub.current_period_start` |
| current_period_end | TIMESTAMP | `sub.current_period_end` |
| created | TIMESTAMP | `sub.created` |
| canceled_at | TIMESTAMP | `sub.canceled_at` (nullable) |

## Load Strategy

- **WRITE_TRUNCATE**: Each run deletes existing data and reloads from scratch
- Idempotent: safe to re-run any number of times
- Uses pandas + pyarrow for type conversion (Python datetime → BigQuery TIMESTAMP)

## Verification

```bash
# Check tables exist
bq ls stripe_mrr

# Check invoice count
bq query "SELECT COUNT(*) FROM stripe_mrr.raw_invoices"

# Check date range
bq query "SELECT MIN(period_start), MAX(period_start) FROM stripe_mrr.raw_invoices"

# Sample rows
bq head stripe_mrr.raw_invoices
```
