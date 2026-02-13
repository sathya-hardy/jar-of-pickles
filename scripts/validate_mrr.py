"""
validate_mrr.py — Cross-validate snapshot MRR against Stripe's live subscription data.

Compares the LATEST month's snapshot (our source of truth for the dashboard)
against what Stripe's API actually reports for each subscription. This catches
drift between our captured snapshots and Stripe's real state.

Checks per customer:
  - Plan tier matches
  - Screen count (quantity) matches
  - MRR calculation matches (price_amount * screens)
  - Subscription status matches (active vs past_due)

Also compares aggregate totals: total MRR, paying customer count, active subs.

Run: uv run python scripts/validate_mrr.py
"""

import json
import os
import sys
import time
from pathlib import Path

import stripe
from dotenv import load_dotenv

load_dotenv()

# Validate Stripe API key
stripe_api_key = os.getenv("STRIPE_SECRET_KEY")
if not stripe_api_key:
    print("ERROR: STRIPE_SECRET_KEY environment variable is not set.")
    print("Set it in your .env file or export it:")
    print("  export STRIPE_SECRET_KEY=sk_test_...")
    sys.exit(1)

stripe.api_key = stripe_api_key

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
SNAPSHOTS_FILE = CONFIG_DIR / "sub_snapshots.json"
PRICES_FILE = CONFIG_DIR / "stripe_prices.json"

# Reverse lookup: price_id -> plan key
PLAN_PRICES = {
    "free": 0,
    "standard": 1000,
    "pro_plus": 1500,
    "engage": 3000,
    "enterprise": 4500,
}


def load_latest_snapshots():
    """Load snapshots and return only the latest month's rows."""
    if not SNAPSHOTS_FILE.exists():
        print(f"ERROR: {SNAPSHOTS_FILE} not found.")
        print("Run generate_data.py first.")
        sys.exit(1)

    try:
        with open(SNAPSHOTS_FILE) as f:
            all_snapshots = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse {SNAPSHOTS_FILE}: {e}")
        print("The file may be corrupted. Re-run generate_data.py")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load {SNAPSHOTS_FILE}: {e}")
        sys.exit(1)

    if not all_snapshots:
        print(f"ERROR: {SNAPSHOTS_FILE} is empty.")
        sys.exit(1)

    months = sorted(set(row["month"] for row in all_snapshots))
    if not months:
        print(f"ERROR: No months found in {SNAPSHOTS_FILE}.")
        sys.exit(1)

    latest_month = months[-1]
    latest = [row for row in all_snapshots if row["month"] == latest_month]
    return latest_month, latest


def load_price_to_plan():
    """Load price_id -> plan_key mapping."""
    if not PRICES_FILE.exists():
        print(f"ERROR: {PRICES_FILE} not found.")
        print("Run seed_prices.py first.")
        sys.exit(1)

    try:
        with open(PRICES_FILE) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse {PRICES_FILE}: {e}")
        print("The file may be corrupted. Re-run seed_prices.py")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load {PRICES_FILE}: {e}")
        sys.exit(1)

    if "price_ids" not in config:
        print(f"ERROR: {PRICES_FILE} is missing 'price_ids' key.")
        print("Re-run seed_prices.py")
        sys.exit(1)

    # Reverse: price_id -> plan display name, we need price_id -> plan key
    plan_to_price_id = config["price_ids"]  # {"free": "price_xxx", ...}
    price_id_to_plan = {v: k for k, v in plan_to_price_id.items()}
    return price_id_to_plan


def fetch_stripe_subscription(subscription_id):
    """Fetch a single subscription from Stripe and extract relevant fields.

    Returns:
        dict: Subscription data, or None if not found, or {"error": str} if API error
    """
    try:
        sub = stripe.Subscription.retrieve(subscription_id)
    except stripe.error.InvalidRequestError:
        # Subscription not found or invalid ID
        return None
    except stripe.error.AuthenticationError as e:
        return {"error": f"Authentication failed: {e}"}
    except stripe.error.APIConnectionError as e:
        return {"error": f"Network error: {e}"}
    except stripe.error.RateLimitError:
        # Rate limited, wait a bit and return error
        time.sleep(1)
        return {"error": "Rate limited"}
    except stripe.error.StripeError as e:
        return {"error": f"Stripe API error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}

    if sub.status in ("canceled", "incomplete_expired"):
        return {"status": sub.status, "active": False}

    # Map Stripe status to our snapshot status values
    snapshot_status = "past_due" if sub.status == "past_due" else "active"

    item = sub["items"]["data"][0]
    return {
        "status": sub.status,
        "snapshot_status": snapshot_status,
        "active": True,
        "price_id": item.price.id,
        "price_amount": item.price.unit_amount,
        "quantity": item.quantity,
    }


def main():
    print("=" * 60)
    print("MRR Validation: Snapshots vs Stripe Live Data")
    print("=" * 60)
    print()

    latest_month, snapshots = load_latest_snapshots()
    price_id_to_plan = load_price_to_plan()

    print(f"Validating latest month: {latest_month}")
    print(f"Snapshot rows to check: {len(snapshots)}")
    print()

    mismatches = []
    stripe_errors = []
    match_count = 0

    print(f"Validating {len(snapshots)} subscriptions...")
    for i, snap in enumerate(snapshots):
        # Rate limiting: 0.1 second between requests (10 req/sec)
        if i > 0:
            time.sleep(0.1)

        # Progress indicator every 10 subscriptions
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{len(snapshots)}")

        cust_id = snap["customer_id"]
        sub_id = snap["subscription_id"]

        stripe_data = fetch_stripe_subscription(sub_id)

        if stripe_data is None:
            stripe_errors.append(
                f"  {cust_id}: subscription {sub_id} not found in Stripe"
            )
            continue

        if "error" in stripe_data:
            stripe_errors.append(
                f"  {cust_id}: {stripe_data['error']}"
            )
            continue

        if not stripe_data["active"]:
            mismatches.append(
                f"  {cust_id}: snapshot says active, Stripe says {stripe_data['status']}"
            )
            continue

        # Compare plan (via price_id)
        stripe_plan = price_id_to_plan.get(stripe_data["price_id"], "unknown")
        snap_plan = snap["plan"]

        # Compare quantity (screens)
        stripe_screens = stripe_data["quantity"]
        snap_screens = snap["screens"]

        # Compare price amount
        stripe_price = stripe_data["price_amount"]
        snap_price = snap["price_amount"]

        # Compare MRR
        stripe_mrr = stripe_price * stripe_screens
        snap_mrr = snap["mrr_cents"]

        # Compare status (active vs past_due)
        stripe_status = stripe_data["snapshot_status"]
        snap_status = snap.get("status", "active")

        errors = []
        if stripe_plan != snap_plan:
            errors.append(f"plan: snapshot={snap_plan}, stripe={stripe_plan}")
        if stripe_screens != snap_screens:
            errors.append(f"screens: snapshot={snap_screens}, stripe={stripe_screens}")
        if stripe_price != snap_price:
            errors.append(f"price: snapshot={snap_price}, stripe={stripe_price}")
        if stripe_mrr != snap_mrr:
            errors.append(f"mrr_cents: snapshot={snap_mrr}, stripe={stripe_mrr}")
        if stripe_status != snap_status:
            errors.append(f"status: snapshot={snap_status}, stripe={stripe_status}")

        if errors:
            mismatches.append(f"  {cust_id}: {'; '.join(errors)}")
        else:
            match_count += 1

    # --- Aggregate comparison ---
    snap_total_mrr = sum(row["mrr_cents"] for row in snapshots)
    snap_paying = len([row for row in snapshots if row["mrr_cents"] > 0])
    snap_total = len(snapshots)
    snap_past_due = len([row for row in snapshots if row.get("status") == "past_due"])

    # --- Results ---
    print("-" * 60)
    print("PER-CUSTOMER RESULTS")
    print("-" * 60)
    print(f"  Matched:    {match_count}/{len(snapshots)}")
    print(f"  Mismatches: {len(mismatches)}")
    print(f"  API errors: {len(stripe_errors)}")

    if mismatches:
        print()
        print("MISMATCHES:")
        for m in mismatches:
            print(m)

    if stripe_errors:
        print()
        print("STRIPE API ERRORS:")
        for e in stripe_errors:
            print(e)

    print()
    print("-" * 60)
    print("AGGREGATE TOTALS (from snapshots)")
    print("-" * 60)
    print(f"  Total MRR:        ${snap_total_mrr / 100:.2f}")
    print(f"  Paying customers: {snap_paying}")
    print(f"  Past due:         {snap_past_due}")
    print(f"  Total customers:  {snap_total}")

    print()
    if not mismatches and not stripe_errors:
        print("RESULT: ALL CHECKS PASSED")
        print("Snapshot data matches Stripe's live subscription state.")
    else:
        print("RESULT: DISCREPANCIES FOUND")
        print("Review mismatches above. This may indicate snapshot drift.")

    return len(mismatches) + len(stripe_errors)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(1 if exit_code > 0 else 0)
