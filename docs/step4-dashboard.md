# Step 4: Dashboard (API + Frontend)

## Overview

- **FastAPI backend** (`api/main.py`) — Thin API layer querying BigQuery views, runs on port 8888
- **React frontend** (`frontend/`) — Vite + TypeScript + Tailwind CSS + Recharts, runs on port 5173

## Prerequisites

- Steps 1–3 completed (data in Stripe, loaded into BigQuery, views created)
- `.env` configured with GCP credentials
- Node.js 18+ installed

## Running

### Start the API server

```bash
uv run uvicorn api.main:app --port 8888 --reload
```

### Start the frontend (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

## API Endpoints

All endpoints return JSON. Base URL: `http://localhost:8888`

| Endpoint | Method | Response |
|----------|--------|----------|
| `/api/mrr` | GET | `{data: [{month, mrr_amount, paying_customers, total_customers, active_subscriptions, past_due_customers, at_risk_mrr}]}` |
| `/api/mrr-by-plan` | GET | `{data: [{month, plan_name, mrr_amount}]}` |
| `/api/arpu` | GET | `{data: [{month, arppu}]}` |
| `/api/customers-by-plan` | GET | `{data: [{month, plan_name, customer_count}]}` |
| `/api/churn` | GET | `{data: [{month, total_customers, prev_customers, churn_rate}]}` |
| `/api/health` | GET | `{status: "ok", bigquery: "connected"}` or `{status: "degraded", bigquery: "unavailable"}` |

The BigQuery client is lazy-initialized on first request, so the app starts even if credentials are misconfigured. The `/api/health` endpoint tests BigQuery connectivity and reports status without crashing.

### Auto-generated API docs

FastAPI provides interactive docs at:
- Swagger UI: `http://localhost:8888/docs`
- ReDoc: `http://localhost:8888/redoc`

## Dashboard Layout

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ Current MRR │ MoM Growth  │   Paying    │   ARPPU     │
│   $39,510   │   +8.2%     │  Customers  │  $527.00    │
│             │             │     75      │             │
└─────────────┴─────────────┴─────────────┴─────────────┘
┌──────────────────────────┬──────────────────────────────┐
│     MRR Trend            │     Revenue by Plan          │
│     (Line Chart)         │     (Stacked Area)           │
└──────────────────────────┴──────────────────────────────┘
┌──────────────────────────┬──────────────────────────────┐
│     ARPPU Trend          │     Customer Count           │
│     (Line Chart)         │     (Dual Line Chart)        │
└──────────────────────────┴──────────────────────────────┘
┌────────────────────────────────────────────────────────┐
│              Customers by Plan                          │
│              (Stacked Bar Chart)                        │
└────────────────────────────────────────────────────────┘
```

## Components

| Component | File | Chart Library | API Source |
|-----------|------|--------------|------------|
| Summary Cards | `SummaryCards.tsx` | — | `/api/mrr` + `/api/arpu` |
| MRR Trend | `MrrChart.tsx` | Recharts LineChart | `/api/mrr` |
| Plan Breakdown | `PlanBreakdown.tsx` | Recharts AreaChart (stacked) | `/api/mrr-by-plan` |
| ARPPU Trend | `ArpuChart.tsx` | Recharts LineChart | `/api/arpu` |
| Customer Count | `CustomerChart.tsx` | Recharts LineChart (dual) | `/api/mrr` |
| Customers by Plan | `CustomersByPlan.tsx` | Recharts BarChart (stacked) | `/api/customers-by-plan` |

## Error Handling

- **API**: All BigQuery query errors return HTTP 500 with descriptive error messages
- **SummaryCards**: Checks `res.ok` on both fetch calls; renders an error banner on failure; guards against division by zero on MoM growth calculation
- **All chart components**: Show loading, error, and empty states

## Development

### Vite Proxy

During development, Vite proxies `/api/*` requests to `http://localhost:8888`, so the React app can call `/api/mrr` without CORS issues.

### Tailwind CSS

Using Tailwind CSS v4 with the `@tailwindcss/vite` plugin. Styles are imported via `@import "tailwindcss"` in `src/index.css`.

### Adding New Charts

1. Create a new component in `frontend/src/components/`
2. Add a new BigQuery view in `create_views()` in `etl/extract_load.py`
3. Add a new API endpoint in `api/main.py`
4. Import and add to `App.tsx` grid layout