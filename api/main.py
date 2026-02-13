"""
main.py — FastAPI backend for the MRR Dashboard.

Thin API layer that queries BigQuery views and returns JSON.
Run: uv run uvicorn api.main:app --port 8888 --reload
"""

import os
import sys
import logging
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Validate required environment variables
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
if not PROJECT_ID:
    logger.error("GCP_PROJECT_ID environment variable is not set")
    sys.exit(1)

DATASET = os.getenv("BQ_DATASET", "stripe_mrr")

# Allow configurable CORS origins
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app = FastAPI(title="MRR Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Lazy-initialized BigQuery client
_bq_client = None


def get_bq_client() -> bigquery.Client:
    """Lazy-initialize BigQuery client on first use."""
    global _bq_client
    if _bq_client is None:
        try:
            _bq_client = bigquery.Client(project=PROJECT_ID)
            logger.info(f"BigQuery client initialized for project {PROJECT_ID}")
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery client: {e}")
            raise
    return _bq_client


@app.on_event("startup")
async def startup_event():
    """Validate BigQuery connection on startup."""
    logger.info("Starting MRR Dashboard API...")
    logger.info(f"Project ID: {PROJECT_ID}")
    logger.info(f"Dataset: {DATASET}")
    logger.info(f"CORS Origins: {CORS_ORIGINS}")

    try:
        client = get_bq_client()
        # Test connection with simple query
        client.query("SELECT 1").result(timeout=10)
        logger.info("✓ BigQuery connection validated")
    except Exception as e:
        logger.warning(f"⚠ BigQuery connection test failed: {e}")
        logger.warning("API will start but queries may fail")


def query_bq(sql: str) -> list[dict]:
    """Run a BigQuery query and return results as list of dicts."""
    try:
        client = get_bq_client()
        results = client.query(sql).result(timeout=30)  # 30 second timeout
        return [dict(row) for row in results]
    except TimeoutError:
        logger.error("BigQuery query timed out after 30 seconds")
        raise HTTPException(status_code=504, detail="Query timed out")
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
            active_subscriptions,
            past_due_customers,
            at_risk_mrr
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


@app.get("/api/churn")
def get_churn():
    """Monthly customer churn rate."""
    data = query_bq(f"""
        SELECT
            month,
            total_customers,
            prev_customers,
            churn_rate
        FROM `{PROJECT_ID}.{DATASET}.churn_monthly`
        ORDER BY month ASC
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
