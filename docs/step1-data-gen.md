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

- **34 test clocks** (3 customers per clock, Stripe max)
- Each clock starts with `frozen_time` = 6 months ago
- **6 advances** of 1 month each, done sequentially (one clock at a time)
- After each advance round, lifecycle events are applied and a snapshot is taken
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
- **Past Due (5 total)**: Payment method detached before clock advance so the next invoice fails

Events are distributed across all 6 monthly phases for gradual, realistic MRR growth.

## Subscription Snapshots

After each monthly advance, the script captures the exact state of every active subscription (plan, screen count, MRR, status). Snapshots use local tracking flags — not Stripe API calls — so they are fast and reflect the intended business state. Past_due customers remain as `past_due` in snapshots even if Stripe auto-cancelled them during the advance. These snapshots are saved to `config/sub_snapshots.json` and used by the ETL to calculate MRR — this avoids issues with Stripe's inconsistent invoice generation on test clocks.

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

## Stripe Test Cards & Past-Due Simulation

The script uses `pm_card_visa` as the default payment method for all customers (always succeeds).

To simulate **past-due** subscriptions, the script **detaches** the customer's payment method entirely. Without a valid payment method, Stripe cannot collect payment on the next billing cycle and automatically sets the subscription status to `past_due`.

**Why not use a declining test card?** Stripe's test tokens like `pm_card_chargeDeclined` decline at _attach_ time (throws `CardError`), and passing raw card numbers (e.g., `4000000000000341`) requires PCI compliance enabled on the account. Detaching the payment method is simpler and works universally.

**Auto-cancellation caveat:** After a subscription becomes past_due, Stripe retries payment according to its retry schedule. If all retries fail, Stripe automatically cancels the subscription. With test clocks, time is compressed so this can happen within a single advance — the subscription goes from past_due to canceled almost immediately. Our snapshots use **local tracking flags** and intentionally keep these customers as `past_due`, which is the correct business metric (the customer was past_due at that point in time). The `validate_mrr.py` script may report ~5 mismatches for these customers — this is expected behavior, not a data error.

## Performance

The script uses a mix of parallel and sequential strategies to balance speed with Stripe's backend capacity:

| Phase | Operation | Strategy |
|-------|-----------|----------|
| Cleanup | Delete existing test clocks | Parallel deletion via thread pool |
| Phase 1 | Create clocks + customers | All 34 batches run concurrently. Each batch (1 clock + 3 customers) runs sequentially within a single thread, but all 34 batches execute in parallel across threads. |
| Phases 2–7 | Advance clocks | Sequential — one clock at a time, wait for ready before next. Avoids Stripe backend contention (parallel advances create resource competition and are slower). |
| Phases 2–7 | Lifecycle events | Upgrades, downgrades, cancellations run in parallel |
| Phases 2–7 | Take snapshots | Instant — uses local tracking flags (no API calls) |

Customer indices are pre-assigned per batch before thread dispatch so threads don't share mutable state. Results are sorted by batch number after completion for deterministic ordering.

Stripe limits test clocks to 3 customers each, requiring 34 clocks for 100 customers.

### Why sequential clock advances?

Stripe's test clock infrastructure has limited concurrency. Advancing 34 clocks in parallel causes backend contention — each clock competes for the same resources, making every clock take minutes. Sequential advances give each clock Stripe's full attention, finishing in seconds each. Total wall-clock time is comparable or faster.

## API Calls

Rate-limited at 10 requests/second (0.1s sleep between sequential calls within a thread). The thread pool (15 workers) is used for clock/customer creation, cleanup, and lifecycle events. Clock advances are sequential to avoid Stripe contention.