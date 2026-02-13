"""
extract_load.py — Batch ETL pipeline: Stripe -> BigQuery.

Extracts subscription snapshots (from generate_data.py) and loads them
into BigQuery. MRR views are built from these snapshots, which accurately
reflect the state of each subscription at each month (including upgrades,
downgrades, cancellations, and past_due status at the exact time they happened).

Run: uv run python etl/extract_load.py
"""

import json
import os
from pathlib import Path
import pandas as pd
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET = os.getenv("BQ_DATASET", "stripe_mrr")

bq_client = bigquery.Client(project=PROJECT_ID)

# Load subscription snapshots
SNAPSHOTS_FILE = Path(__file__).resolve().parent.parent / "config" / "sub_snapshots.json"

if not SNAPSHOTS_FILE.exists():
    print(f"ERROR: {SNAPSHOTS_FILE} not found.")
    print("Run generate_data.py first:  uv run python scripts/generate_data.py")
    exit(1)

with open(SNAPSHOTS_FILE) as f:
    SUB_SNAPSHOTS = json.load(f)

print(f"Loaded {len(SUB_SNAPSHOTS)} subscription snapshots.")


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
    """Create or replace BigQuery views for MRR, MRR by plan, ARPPU, and customers by plan."""
    print("Creating BigQuery views...")

    # Build the CASE expression for plan key -> plan display name
    plan_case_lines = [
        "    WHEN 'free' THEN 'Free'",
        "    WHEN 'standard' THEN 'Standard'",
        "    WHEN 'pro_plus' THEN 'Pro Plus'",
        "    WHEN 'engage' THEN 'Engage'",
        "    WHEN 'enterprise' THEN 'Enterprise'",
    ]
    plan_case_expr = "\n".join(plan_case_lines)

    # View 1: mrr_monthly
    mrr_sql = f"""
    CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.mrr_monthly` AS
    SELECT
      month,
      ROUND(SUM(mrr_cents) / 100.0, 2) AS mrr_amount,
      COUNT(DISTINCT CASE WHEN mrr_cents > 0 THEN customer_id END) AS paying_customers,
      COUNT(DISTINCT customer_id) AS total_customers,
      COUNT(DISTINCT subscription_id) AS active_subscriptions,
      COUNT(DISTINCT CASE WHEN status = 'past_due' THEN customer_id END) AS past_due_customers,
      ROUND(SUM(CASE WHEN status = 'past_due' THEN mrr_cents ELSE 0 END) / 100.0, 2) AS at_risk_mrr
    FROM `{PROJECT_ID}.{DATASET}.sub_snapshots`
    GROUP BY month
    ORDER BY month ASC
    """
    bq_client.query(mrr_sql).result()
    print(f"  Created view {DATASET}.mrr_monthly")

    # View 2: mrr_by_plan
    mrr_by_plan_sql = f"""
    CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.mrr_by_plan` AS
    SELECT
      month,
      CASE plan
{plan_case_expr}
        ELSE 'Unknown'
      END AS plan_name,
      ROUND(SUM(mrr_cents) / 100.0, 2) AS mrr_amount
    FROM `{PROJECT_ID}.{DATASET}.sub_snapshots`
    GROUP BY month, plan_name
    ORDER BY month ASC, plan_name ASC
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
    FROM `{PROJECT_ID}.{DATASET}.mrr_monthly`
    ORDER BY month ASC
    """
    bq_client.query(arppu_sql).result()
    print(f"  Created view {DATASET}.arppu_monthly")

    # View 4: customers_by_plan
    customers_by_plan_sql = f"""
    CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.customers_by_plan` AS
    SELECT
      month,
      CASE plan
{plan_case_expr}
        ELSE 'Unknown'
      END AS plan_name,
      COUNT(DISTINCT customer_id) AS customer_count
    FROM `{PROJECT_ID}.{DATASET}.sub_snapshots`
    GROUP BY month, plan_name
    ORDER BY month ASC, plan_name ASC
    """
    bq_client.query(customers_by_plan_sql).result()
    print(f"  Created view {DATASET}.customers_by_plan")

    # View 5: churn_monthly
    churn_sql = f"""
    CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.churn_monthly` AS
    SELECT
      month,
      total_customers,
      LAG(total_customers) OVER (ORDER BY month ASC) AS prev_customers,
      CASE
        WHEN LAG(total_customers) OVER (ORDER BY month ASC) > 0
        THEN ROUND(
          (LAG(total_customers) OVER (ORDER BY month ASC) - total_customers)
          / LAG(total_customers) OVER (ORDER BY month ASC) * 100, 2
        )
        ELSE 0
      END AS churn_rate
    FROM `{PROJECT_ID}.{DATASET}.mrr_monthly`
    ORDER BY month ASC
    """
    bq_client.query(churn_sql).result()
    print(f"  Created view {DATASET}.churn_monthly")


def main():
    print("=" * 60)
    print("Stripe -> BigQuery ETL Pipeline")
    print("=" * 60)
    print()

    ensure_dataset()
    print()

    # Load subscription snapshots
    print("Loading subscription snapshots into BigQuery...")
    load_to_bigquery(SUB_SNAPSHOTS, "sub_snapshots", [
        bigquery.SchemaField("month", "STRING"),
        bigquery.SchemaField("customer_id", "STRING"),
        bigquery.SchemaField("subscription_id", "STRING"),
        bigquery.SchemaField("plan", "STRING"),
        bigquery.SchemaField("price_id", "STRING"),
        bigquery.SchemaField("price_amount", "INTEGER"),
        bigquery.SchemaField("screens", "INTEGER"),
        bigquery.SchemaField("mrr_cents", "INTEGER"),
        bigquery.SchemaField("status", "STRING"),
    ])

    print()

    # Create views
    create_views()

    print()
    print("ETL complete. Data loaded and views created.")


if __name__ == "__main__":
    main()