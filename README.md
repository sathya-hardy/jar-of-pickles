# Stripe MRR Dashboard Pipeline

A complete pipeline for generating, extracting, transforming, and visualizing Monthly Recurring Revenue (MRR) data for a digital signage SaaS company.

## Architecture

```
Stripe Test Mode → Batch ETL (Python) → BigQuery → FastAPI → React Dashboard
```

### Pipeline Steps

1. **Data Generation** (`scripts/`) — Creates 100 test customers with 5 pricing tiers using Stripe test clocks to simulate 6 months of billing history
2. **ETL Pipeline** (`etl/`) — Extracts invoices and subscriptions from Stripe API, loads into BigQuery raw tables
3. **SQL Views** (`sql/`) — BigQuery views that calculate MRR, MRR by plan, and ARPPU
4. **API Server** (`api/`) — FastAPI backend on port 8888 serving dashboard data from BigQuery
5. **Dashboard** (`dashboard/`) — Vite + React + TypeScript + Tailwind CSS + Recharts

### Pricing Tiers

| Plan | Price | Screen Range |
|------|-------|-------------|
| Free | $0/screen/mo | 1–3 screens |
| Standard | $10/screen/mo | 2–8 screens |
| Pro Plus | $15/screen/mo | 5–20 screens |
| Engage | $30/screen/mo | 8–30 screens |
| Enterprise | $45/screen/mo | 25–100 screens (min 25) |

## Prerequisites

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Stripe account (test mode)
- Google Cloud Platform account with BigQuery enabled

## Setup

### 1. Credentials

You need two files that are **not** in the repo (they contain secrets):

| File | What it is | How to get it |
|------|-----------|---------------|
| `.env` | Environment variables (Stripe key, GCP project ID) | Copy `.env.example` → `.env` and fill in values |
| `service-account.json` | GCP service account key | GCP Console → IAM & Admin → Service Accounts → Create Key → JSON → download and place in project root |

```bash
cp .env.example .env
# Edit .env with your Stripe secret key and GCP project ID
# Place your GCP service account JSON file as service-account.json in the project root
```

The GCP service account needs these roles: **BigQuery Data Editor** + **BigQuery User**.

### 2. Install dependencies

```bash
uv sync
```

### 3. Run the pipeline

```bash
# Step 1a: Create Stripe products and prices
uv run python scripts/seed_prices.py

# Step 1b: Generate 100 test customers with 6 months of billing history
uv run python scripts/generate_data.py

# Step 2+3: Extract from Stripe, load to BigQuery, and create views
uv run python etl/extract_load.py

# Step 4: Start the API server
uv run uvicorn api.main:app --port 8888 --reload

# Step 5: Start the dashboard (in another terminal)
cd dashboard && npm install && npm run dev
```

### 4. Open the dashboard

Open `http://localhost:5173` to view the dashboard.

## Dashboard Metrics

- **MRR Trend** — Monthly recurring revenue over time
- **MRR by Plan** — Revenue breakdown by pricing tier
- **ARPPU** — Average Revenue Per Paying User
- **Customer Count** — Total and paying customers over time
