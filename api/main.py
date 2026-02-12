"""
main.py — FastAPI backend for the MRR Dashboard.

Thin API layer that queries BigQuery views and returns JSON.
Run: uv run uvicorn api.main:app --port 8888 --reload
"""

import os
import logging
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

app = FastAPI(title="MRR Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET = os.getenv("BQ_DATASET", "stripe_mrr")

# Lazy-initialized BigQuery client
_bq_client = None


def get_bq_client() -> bigquery.Client:
    """Lazy-initialize BigQuery client on first use."""
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(project=PROJECT_ID)
    return _bq_client


def query_bq(sql: str) -> list[dict]:
    """Run a BigQuery query and return results as list of dicts."""
    try:
        client = get_bq_client()
        results = client.query(sql).result()
        return [dict(row) for row in results]
    except Exception:
        logger.exception("BigQuery query failed")
        raise HTTPException(status_code=500, detail="BigQuery query failed")


@app.get("/api/mrr")
def get_mrr():
    """Monthly MRR time series."""
    data = query_bq(f"""
        SELECT
            month,
            mrr_amount,
            paying_customers,
            total_customers,
            active_subscriptions
        FROM `{PROJECT_ID}.{DATASET}.mrr_monthly`
        ORDER BY month ASC
    """)
    return {"data": data}


@app.get("/api/mrr-by-plan")
def get_mrr_by_plan():
    """MRR broken down by plan tier per month."""
    data = query_bq(f"""
        SELECT
            month,
            plan_name,
            mrr_amount
        FROM `{PROJECT_ID}.{DATASET}.mrr_by_plan`
        ORDER BY month ASC, plan_name ASC
    """)
    return {"data": data}


@app.get("/api/arpu")
def get_arpu():
    """ARPPU (Average Revenue Per Paying User) time series."""
    data = query_bq(f"""
        SELECT
            month,
            arppu
        FROM `{PROJECT_ID}.{DATASET}.arppu_monthly`
        ORDER BY month ASC
    """)
    return {"data": data}


@app.get("/api/customers-by-plan")
def get_customers_by_plan():
    """Customer count broken down by plan tier per month."""
    data = query_bq(f"""
        SELECT
            month,
            plan_name,
            customer_count
        FROM `{PROJECT_ID}.{DATASET}.customers_by_plan`
        ORDER BY month ASC, plan_name ASC
    """)
    return {"data": data}


@app.get("/api/health")
def health(response: Response):
    """Health check. Tests BigQuery connectivity."""
    try:
        client = get_bq_client()
        client.query("SELECT 1").result()
        return {"status": "ok", "bigquery": "connected"}
    except Exception:
        logger.exception("BigQuery connectivity check failed")
        response.status_code = 503
        return {"status": "degraded", "bigquery": "unavailable"}
