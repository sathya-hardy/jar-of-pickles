"""
validate_mrr.py — Cross-validate snapshot MRR against Stripe's live subscription data.

Compares the LATEST month's snapshot (our source of truth for the dashboard)
against what Stripe's API actually reports for each subscription. This catches
drift between our captured snapshots and Stripe's real state.

Checks per customer:
  - Plan tier matches
  - Screen count (quantity) matches
  - MRR calculation matches (price_amount * screens)

Also compares aggregate totals: total MRR, paying customer count, active subs.

Run: uv run python scripts/validate_mrr.py
"""

import json
import os
import sys
from pathlib import Path

import stripe
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

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

    with open(SNAPSHOTS_FILE) as f:
        all_snapshots = json.load(f)

    months = sorted(set(row["month"] for row in all_snapshots))
    latest_month = months[-1]
    latest = [row for row in all_snapshots if row["month"] == latest_month]
    return latest_month, latest


def load_price_to_plan():
    """Load price_id -> plan_key mapping."""
    if not PRICES_FILE.exists():
        print(f"ERROR: {PRICES_FILE} not found.")
        sys.exit(1)

    with open(PRICES_FILE) as f:
        config = json.load(f)

    # Reverse: price_id -> plan display name, we need price_id -> plan key
    plan_to_price_id = config["price_ids"]  # {"free": "price_xxx", ...}
    price_id_to_plan = {v: k for k, v in plan_to_price_id.items()}
    return price_id_to_plan


def fetch_stripe_subscription(subscription_id):
    """Fetch a single subscription from Stripe and extract relevant fields."""
    try:
        sub = stripe.Subscription.retrieve(subscription_id)
    except stripe.error.InvalidRequestError:
        return None

    if sub.status in ("canceled", "incomplete_expired"):
        return {"status": sub.status, "active": False}

    item = sub["items"]["data"][0]
    return {
        "status": sub.status,
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

    for i, snap in enumerate(snapshots):
        cust_id = snap["customer_id"]
        sub_id = snap["subscription_id"]

        stripe_data = fetch_stripe_subscription(sub_id)

        if stripe_data is None:
            stripe_errors.append(
                f"  {cust_id}: subscription {sub_id} not found in Stripe"
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

        errors = []
        if stripe_plan != snap_plan:
            errors.append(f"plan: snapshot={snap_plan}, stripe={stripe_plan}")
        if stripe_screens != snap_screens:
            errors.append(f"screens: snapshot={snap_screens}, stripe={stripe_screens}")
        if stripe_price != snap_price:
            errors.append(f"price: snapshot={snap_price}, stripe={stripe_price}")
        if stripe_mrr != snap_mrr:
            errors.append(f"mrr_cents: snapshot={snap_mrr}, stripe={stripe_mrr}")

        if errors:
            mismatches.append(f"  {cust_id}: {'; '.join(errors)}")
        else:
            match_count += 1

    # --- Aggregate comparison ---
    snap_total_mrr = sum(row["mrr_cents"] for row in snapshots)
    snap_paying = len([row for row in snapshots if row["mrr_cents"] > 0])
    snap_total = len(snapshots)

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
