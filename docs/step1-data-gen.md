# Step 1: Data Generation

## Overview

Two Python scripts create realistic billing data in Stripe's test mode:

1. **`scripts/seed_prices.py`** — Creates 5 Products and Prices (run once)
2. **`scripts/generate_data.py`** — Creates 100 customers with subscriptions using test clocks, simulates 6 months of lifecycle events, and saves monthly subscription snapshots

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

This creates 5 Stripe Products and Prices and saves their IDs to `config/stripe_prices.json`. Other scripts read this file automatically — no manual copy-paste needed.

### Step 1b: Generate Test Customers

```bash
uv run python scripts/generate_data.py
```

This creates 100 customers, simulates 6 months of billing, and saves:
- `config/current_run.json` — customer IDs and clock IDs (used by ETL to filter)
- `config/sub_snapshots.json` — monthly subscription snapshots (source of truth for MRR)

## Test Clock Strategy

- **34 test clocks** (3 customers per clock, last clock has 1)
- Each clock starts with `frozen_time` = 6 months ago
- **6 advances** of 1 month each
- After each advance, lifecycle events are applied and a snapshot is taken
- Cleanup step at start deletes all existing test clocks (safe to re-run)

## Customer Distribution

| Plan | Count | Screen Range |
|------|-------|-------------|
| Free | 25 | 1–3 |
| Standard | 18 | 2–8 |
| Pro Plus | 32 | 5–20 |
| Engage | 15 | 8–30 |
| Enterprise | 10 | 25–100 |

## Lifecycle Events (spread across 6 months)

- **Upgrades (15 total)**: Mix of plan upgrades (e.g., Standard → Pro Plus) and screen count increases
- **Downgrades (2 total)**: Plan downgrades (e.g., Pro Plus → Standard)
- **Cancellations (8 total)**: Weighted toward Free/Standard tiers

Events are distributed across all 6 monthly phases for gradual, realistic MRR growth.

## Subscription Snapshots

After each monthly advance and lifecycle event batch, the script captures the exact state of every active subscription (plan, screen count, MRR). These snapshots are saved to `config/sub_snapshots.json` and used by the ETL to calculate MRR — this avoids issues with Stripe's inconsistent invoice generation on test clocks.

## Config Files Generated

| File | Purpose |
|------|---------|
| `config/stripe_prices.json` | Price IDs and price-to-plan mapping (created by `seed_prices.py`) |
| `config/current_run.json` | Customer IDs and clock IDs for ETL filtering |
| `config/sub_snapshots.json` | Monthly subscription snapshots for MRR calculation |

## Verification

1. [Stripe Dashboard → Customers](https://dashboard.stripe.com/test/customers) — should see 100 customers
2. [Stripe Dashboard → Test Clocks](https://dashboard.stripe.com/test/test-clocks) — should see 34 clocks
3. [Stripe Dashboard → Invoices](https://dashboard.stripe.com/test/invoices) — should see invoices spanning 6 months

## Stripe Test Cards

The script uses two Stripe test payment methods:

| Card | Where | Purpose |
|------|-------|---------|
| `pm_card_visa` | Customer creation | Default payment method — always succeeds |
| `4000 0000 0000 0341` | Past-due simulation | Attaches to a customer successfully, but **declines on charge**. When set as the default payment method, the next billing cycle charge fails and Stripe moves the subscription to `past_due`. |

**Why not `pm_card_chargeDeclined`?** That token declines at _attach_ time (throws `CardError` during `PaymentMethod.attach`), so it can never be set as the customer's default. Card `4000000000000341` is Stripe's dedicated "attach succeeds, charge fails" test card.

## Performance (Parallel Execution)

The script uses `ThreadPoolExecutor` with 10 workers to parallelize independent Stripe API calls:

| Phase | Operation | Strategy |
|-------|-----------|----------|
| Cleanup | Delete existing test clocks | Parallel deletion via thread pool |
| Phase 1 | Create clocks + customers | All 34 batches run concurrently. Each batch (1 clock + 3 customers) runs sequentially within a single thread, but all 34 batches execute in parallel across threads. |
| Phases 2–7 | Advance clocks | All 34 `TestClock.advance` calls fire in parallel |
| Phases 2–7 | Wait for clocks | Batch polling — one loop checks all clocks each iteration rather than waiting for each clock individually |

Customer indices are pre-assigned per batch before thread dispatch so threads don't share mutable state. Results are sorted by batch number after completion for deterministic ordering.

## API Calls

Rate-limited at 4 requests/second (0.25s sleep between sequential calls within a thread). Clock advances include a 5-minute timeout to handle Stripe slowness gracefully. The thread pool caps concurrent requests at 10 to stay within Stripe's test-mode rate limits.