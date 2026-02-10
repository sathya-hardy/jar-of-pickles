# Step 1: Data Generation

## Overview

Two Python scripts create realistic billing data in Stripe's test mode:

1. **`scripts/seed_prices.py`** — Creates 5 Products and Prices (run once)
2. **`scripts/generate_data.py`** — Creates 100 customers with subscriptions using test clocks

## Prerequisites

- Stripe account with test mode API key (`sk_test_...`)
- `uv sync` completed (Python dependencies installed)
- `.env` file configured with `STRIPE_SECRET_KEY`

## Pricing Tiers

| Product | Price/screen/mo | Stripe unit_amount (cents) |
|---------|----------------|---------------------------|
| Free | $0 | 0 |
| Standard | $10 | 1000 |
| Pro Plus | $15 | 1500 |
| Engage | $30 | 3000 |
| Enterprise | $45 | 4500 |

## Running

### Step 1a: Create Products and Prices

```bash
uv run python scripts/seed_prices.py
```

This prints Product IDs and Price IDs. Copy the `PRICE_IDS` dict into `scripts/generate_data.py`.

### Step 1b: Generate Test Customers

After updating PRICE_IDS in the script:

```bash
uv run python scripts/generate_data.py
```

## Test Clock Strategy

- **34 test clocks** (3 customers per clock, max allowed by Stripe)
- Each clock starts with `frozen_time` = 6 months ago
- **3 advances** of 2 months each (max allowed per advance for monthly billing)
- Between advances, lifecycle events are applied:
  - Month 2→4: ~15 upgrades, ~2 downgrades
  - Month 4→6: ~8 cancellations

## Customer Distribution

| Plan | Count | Screen Range |
|------|-------|-------------|
| Free | 25 | 1–3 |
| Standard | 18 | 2–8 |
| Pro Plus | 32 | 5–20 |
| Engage | 15 | 8–30 |
| Enterprise | 10 | 25–100 |

## Growth Story Events

- **Upgrades (~15)**: Mix of plan upgrades (e.g., Standard → Pro Plus) and screen count increases
- **Downgrades (~2)**: Plan downgrades (e.g., Pro Plus → Standard)
- **Cancellations (~8)**: Weighted toward Free/Standard tiers

## Verification

1. Go to [Stripe Dashboard → Customers](https://dashboard.stripe.com/test/customers) — should see 100 customers
2. Go to [Stripe Dashboard → Test Clocks](https://dashboard.stripe.com/test/test-clocks) — should see 34 clocks
3. Go to [Stripe Dashboard → Invoices](https://dashboard.stripe.com/test/invoices) — should see ~600 invoices spanning 6 months

## API Calls

~670 total API calls. Rate-limited at 4 requests/second (0.25s sleep between calls).
