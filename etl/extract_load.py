"""
extract_load.py — Batch ETL pipeline: Stripe -> BigQuery.

Extracts all invoices and subscriptions from Stripe API,
loads them into BigQuery raw tables using WRITE_TRUNCATE (idempotent),
then creates/updates the BigQuery views for MRR, MRR by plan, and ARPPU.

Run: uv run python etl/extract_load.py
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import stripe
import pandas as pd
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET = os.getenv("BQ_DATASET", "stripe_mrr")

bq_client = bigquery.Client(project=PROJECT_ID)

# Load price-to-plan mapping from config
CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "stripe_prices.json"

if not CONFIG_FILE.exists():
    print(f"ERROR: {CONFIG_FILE} not found.")
    print("Run seed_prices.py first:  uv run python scripts/seed_prices.py")
    exit(1)

with open(CONFIG_FILE) as f:
    _config = json.load(f)

PRICE_TO_PLAN = _config["price_to_plan"]


def ensure_dataset():
    """Create BigQuery dataset if it doesn't exist."""
    dataset_ref = bigquery.DatasetReference(PROJECT_ID, DATASET)
    try:
        bq_client.get_dataset(dataset_ref)
        print(f"Dataset {DATASET} already exists.")
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        bq_client.create_dataset(dataset)
        print(f"Created dataset {DATASET}.")


def extract_invoices():
    """Extract all invoices from Stripe, return list of dicts.

    Uses Search API because test clock objects are hidden from list endpoints.
    Line items are fetched per invoice since search doesn't support expand.
    """
    print("Extracting invoices from Stripe...")
    rows = []
    invoices = stripe.Invoice.search(
        query="status:'paid' OR status:'open' OR status:'void' OR status:'uncollectible'",
        limit=100,
    )

    for inv in invoices.auto_paging_iter():
        price_id = None
        # Fetch line items separately (search doesn't support expand)
        lines = stripe.Invoice.list_lines(inv.id, limit=1)
        if lines.data:
            first_line = lines.data[0]
            pricing = getattr(first_line, "pricing", None)
            if pricing and pricing.get("price_details"):
                price_id = pricing["price_details"].get("price")

        # subscription_id is nested under parent.subscription_details
        subscription_id = None
        parent = getattr(inv, "parent", None)
        if parent and parent.get("subscription_details"):
            subscription_id = parent["subscription_details"].get("subscription")

        rows.append({
            "invoice_id": inv.id,
            "customer_id": inv.customer,
            "subscription_id": subscription_id,
            "status": inv.status,
            "amount_paid": inv.amount_paid,
            "currency": inv.currency,
            "price_id": price_id,
            "period_start": datetime.fromtimestamp(inv.period_start, tz=timezone.utc) if inv.period_start else None,
            "period_end": datetime.fromtimestamp(inv.period_end, tz=timezone.utc) if inv.period_end else None,
            "created": datetime.fromtimestamp(inv.created, tz=timezone.utc),
        })

    print(f"Extracted {len(rows)} invoices.")
    return rows


def extract_subscriptions():
    """Extract all subscriptions from Stripe, return list of dicts.

    Uses Search API because test clock objects are hidden from list endpoints.
    """
    print("Extracting subscriptions from Stripe...")
    rows = []
    subs = stripe.Subscription.search(
        query="status:'active' OR status:'canceled' OR status:'past_due' OR status:'incomplete'",
        limit=100,
    )

    for sub in subs.auto_paging_iter():
        item = sub["items"]["data"][0]
        rows.append({
            "subscription_id": sub.id,
            "customer_id": sub.customer,
            "status": sub.status,
            "price_id": item.price.id,
            "price_amount": item.price.unit_amount,
            "price_interval": item.price.recurring.interval if item.price.recurring else None,
            "quantity": item.quantity,
            "current_period_start": datetime.fromtimestamp(item.current_period_start, tz=timezone.utc),
            "current_period_end": datetime.fromtimestamp(item.current_period_end, tz=timezone.utc),
            "created": datetime.fromtimestamp(sub.created, tz=timezone.utc),
            "canceled_at": (
                datetime.fromtimestamp(sub.canceled_at, tz=timezone.utc)
                if sub.canceled_at else None
            ),
        })

    print(f"Extracted {len(rows)} subscriptions.")
    return rows


def load_to_bigquery(rows, table_name, schema):
    """Load list of dicts into a BigQuery table (WRITE_TRUNCATE)."""
    if not rows:
        print(f"No rows to load for {table_name}.")
        return

    table_id = f"{PROJECT_ID}.{DATASET}.{table_name}"
    df = pd.DataFrame(rows)

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    job = bq_client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()
    print(f"Loaded {len(rows)} rows into {table_id}.")


def create_views():
    """Create or replace BigQuery views for MRR, MRR by plan, and ARPPU."""
    print("Creating BigQuery views...")

    # Build the CASE expression for price_id -> plan_name mapping
    case_lines = []
    for price_id, plan_name in PRICE_TO_PLAN.items():
        case_lines.append(f"    WHEN '{price_id}' THEN '{plan_name}'")
    case_expr = "\n".join(case_lines)

    # View 1: mrr_monthly
    mrr_sql = f"""
    CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.mrr_monthly` AS
    WITH paid_invoices AS (
      SELECT
        invoice_id,
        customer_id,
        subscription_id,
        amount_paid,
        DATE_TRUNC(DATE(period_start), MONTH) AS invoice_month
      FROM
        `{PROJECT_ID}.{DATASET}.raw_invoices`
      WHERE
        status = 'paid'
        AND subscription_id IS NOT NULL
        AND amount_paid > 0
    ),
    all_customer_months AS (
      SELECT DISTINCT
        customer_id,
        DATE_TRUNC(DATE(period_start), MONTH) AS invoice_month
      FROM
        `{PROJECT_ID}.{DATASET}.raw_invoices`
      WHERE
        status = 'paid'
        AND subscription_id IS NOT NULL
    )
    SELECT
      p.invoice_month AS month,
      ROUND(SUM(p.amount_paid) / 100.0, 2) AS mrr_amount,
      COUNT(DISTINCT p.customer_id) AS paying_customers,
      (
        SELECT COUNT(DISTINCT a.customer_id)
        FROM all_customer_months a
        WHERE a.invoice_month = p.invoice_month
      ) AS total_customers,
      COUNT(DISTINCT p.subscription_id) AS active_subscriptions
    FROM
      paid_invoices p
    GROUP BY
      p.invoice_month
    ORDER BY
      p.invoice_month ASC
    """
    bq_client.query(mrr_sql).result()
    print(f"  Created view {DATASET}.mrr_monthly")

    # View 2: mrr_by_plan
    mrr_by_plan_sql = f"""
    CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.mrr_by_plan` AS
    SELECT
      DATE_TRUNC(DATE(period_start), MONTH) AS month,
      CASE price_id
{case_expr}
        ELSE 'Unknown'
      END AS plan_name,
      ROUND(SUM(amount_paid) / 100.0, 2) AS mrr_amount
    FROM
      `{PROJECT_ID}.{DATASET}.raw_invoices`
    WHERE
      status = 'paid'
      AND subscription_id IS NOT NULL
    GROUP BY
      month,
      plan_name
    ORDER BY
      month ASC,
      plan_name ASC
    """
    bq_client.query(mrr_by_plan_sql).result()
    print(f"  Created view {DATASET}.mrr_by_plan")

    # View 3: arppu_monthly
    arppu_sql = f"""
    CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.arppu_monthly` AS
    SELECT
      month,
      mrr_amount,
      paying_customers,
      CASE
        WHEN paying_customers > 0 THEN ROUND(mrr_amount / paying_customers, 2)
        ELSE 0
      END AS arppu
    FROM
      `{PROJECT_ID}.{DATASET}.mrr_monthly`
    ORDER BY
      month ASC
    """
    bq_client.query(arppu_sql).result()
    print(f"  Created view {DATASET}.arppu_monthly")


def main():
    print("=" * 60)
    print("Stripe -> BigQuery ETL Pipeline")
    print("=" * 60)
    print()

    ensure_dataset()
    print()

    # Extract
    invoice_rows = extract_invoices()
    subscription_rows = extract_subscriptions()
    print()

    # Load invoices
    print("Loading invoices into BigQuery...")
    load_to_bigquery(invoice_rows, "raw_invoices", [
        bigquery.SchemaField("invoice_id", "STRING"),
        bigquery.SchemaField("customer_id", "STRING"),
        bigquery.SchemaField("subscription_id", "STRING"),
        bigquery.SchemaField("status", "STRING"),
        bigquery.SchemaField("amount_paid", "INTEGER"),
        bigquery.SchemaField("currency", "STRING"),
        bigquery.SchemaField("price_id", "STRING"),
        bigquery.SchemaField("period_start", "TIMESTAMP"),
        bigquery.SchemaField("period_end", "TIMESTAMP"),
        bigquery.SchemaField("created", "TIMESTAMP"),
    ])

    # Load subscriptions
    print("Loading subscriptions into BigQuery...")
    load_to_bigquery(subscription_rows, "raw_subscriptions", [
        bigquery.SchemaField("subscription_id", "STRING"),
        bigquery.SchemaField("customer_id", "STRING"),
        bigquery.SchemaField("status", "STRING"),
        bigquery.SchemaField("price_id", "STRING"),
        bigquery.SchemaField("price_amount", "INTEGER"),
        bigquery.SchemaField("price_interval", "STRING"),
        bigquery.SchemaField("quantity", "INTEGER"),
        bigquery.SchemaField("current_period_start", "TIMESTAMP"),
        bigquery.SchemaField("current_period_end", "TIMESTAMP"),
        bigquery.SchemaField("created", "TIMESTAMP"),
        bigquery.SchemaField("canceled_at", "TIMESTAMP"),
    ])

    print()

    # Create views
    create_views()

    print()
    print("ETL complete. Data loaded and views created.")


if __name__ == "__main__":
    main()
