"""
test_snapshots.py — Validate subscription snapshot data integrity.

Ensures the source-of-truth data that drives the entire dashboard is
internally consistent: correct MRR math, no duplicate customers per
month, and price amounts that match their plan tier.

Also includes cross-validation against Stripe's live subscription data
(skipped when STRIPE_SECRET_KEY is not set).

Run: uv run python -m pytest tests/test_snapshots.py -v
"""

import json
import os
import unittest
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SNAPSHOTS_FILE = Path(__file__).resolve().parent.parent / "config" / "sub_snapshots.json"
PRICES_FILE = Path(__file__).resolve().parent.parent / "config" / "stripe_prices.json"

EXPECTED_PRICES = {
    "free": 0,
    "standard": 1000,
    "pro_plus": 1500,
    "engage": 3000,
    "enterprise": 4500,
}


def load_snapshots():
    if not SNAPSHOTS_FILE.exists():
        return None
    with open(SNAPSHOTS_FILE) as f:
        return json.load(f)


@unittest.skipIf(
    not SNAPSHOTS_FILE.exists(),
    "config/sub_snapshots.json not found — run generate_data.py first",
)
class SnapshotIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshots = load_snapshots()

    def test_snapshots_not_empty(self):
        self.assertGreater(len(self.snapshots), 0, "Snapshot file is empty")

    def test_mrr_cents_equals_price_times_screens(self):
        """Every row's mrr_cents must equal price_amount * screens."""
        errors = []
        for i, row in enumerate(self.snapshots):
            expected = row["price_amount"] * row["screens"]
            if row["mrr_cents"] != expected:
                errors.append(
                    f"Row {i} ({row['month']}, {row['customer_id']}): "
                    f"mrr_cents={row['mrr_cents']} != "
                    f"price_amount({row['price_amount']}) * screens({row['screens']}) = {expected}"
                )
        self.assertEqual(errors, [], f"MRR math errors:\n" + "\n".join(errors))

    def test_no_duplicate_customers_per_month(self):
        """Each customer should appear at most once per month."""
        seen = {}
        duplicates = []
        for row in self.snapshots:
            key = (row["month"], row["customer_id"])
            if key in seen:
                duplicates.append(f"{row['month']}: {row['customer_id']}")
            seen[key] = True
        self.assertEqual(
            duplicates, [], f"Duplicate customers found:\n" + "\n".join(duplicates)
        )

    def test_price_amount_matches_plan(self):
        """Each row's price_amount must match the known price for its plan."""
        errors = []
        for i, row in enumerate(self.snapshots):
            plan = row["plan"]
            expected_price = EXPECTED_PRICES.get(plan)
            if expected_price is None:
                errors.append(f"Row {i}: unknown plan '{plan}'")
            elif row["price_amount"] != expected_price:
                errors.append(
                    f"Row {i} ({row['month']}, {row['customer_id']}): "
                    f"plan={plan} has price_amount={row['price_amount']}, "
                    f"expected {expected_price}"
                )
        self.assertEqual(errors, [], f"Price mismatch errors:\n" + "\n".join(errors))

    def test_screens_positive(self):
        """Every row should have at least 1 screen."""
        bad = [
            f"Row {i} ({row['month']}, {row['customer_id']}): screens={row['screens']}"
            for i, row in enumerate(self.snapshots)
            if row["screens"] < 1
        ]
        self.assertEqual(bad, [], f"Rows with invalid screen count:\n" + "\n".join(bad))

    def test_all_months_present(self):
        """Should have 7 distinct months (month 0 + 6 advances)."""
        months = sorted(set(row["month"] for row in self.snapshots))
        self.assertEqual(
            len(months), 7,
            f"Expected 7 months, got {len(months)}: {months}",
        )

    def test_status_field_valid(self):
        """Every row must have a status field with value 'active' or 'past_due'."""
        valid_statuses = {"active", "past_due"}
        bad = [
            f"Row {i} ({row['month']}, {row['customer_id']}): status={row.get('status')}"
            for i, row in enumerate(self.snapshots)
            if row.get("status") not in valid_statuses
        ]
        self.assertEqual(bad, [], f"Rows with invalid status:\n" + "\n".join(bad))

    def test_has_past_due_customers(self):
        """At least one snapshot row should have status='past_due'."""
        past_due_rows = [row for row in self.snapshots if row.get("status") == "past_due"]
        self.assertGreater(
            len(past_due_rows), 0,
            "No past_due customers found in snapshots — expected at least 1",
        )


@unittest.skipIf(
    not SNAPSHOTS_FILE.exists(),
    "config/sub_snapshots.json not found — run generate_data.py first",
)
@unittest.skipIf(
    not os.getenv("STRIPE_SECRET_KEY"),
    "STRIPE_SECRET_KEY not set — skipping Stripe cross-validation",
)
class StripeCrossValidationTests(unittest.TestCase):
    """Compare the latest month's snapshots against Stripe's live subscription data."""

    @classmethod
    def setUpClass(cls):
        import stripe

        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        cls.stripe = stripe

        with open(SNAPSHOTS_FILE) as f:
            all_snapshots = json.load(f)

        months = sorted(set(row["month"] for row in all_snapshots))
        cls.latest_month = months[-1]
        cls.snapshots = [row for row in all_snapshots if row["month"] == cls.latest_month]

        with open(PRICES_FILE) as f:
            config = json.load(f)
        plan_to_price_id = config["price_ids"]
        cls.price_id_to_plan = {v: k for k, v in plan_to_price_id.items()}

    def test_plan_matches_stripe(self):
        """Each snapshot's plan should match the subscription's current price in Stripe."""
        mismatches = []
        for snap in self.snapshots:
            sub = self.stripe.Subscription.retrieve(snap["subscription_id"])
            if sub.status in ("canceled", "incomplete_expired"):
                mismatches.append(
                    f"{snap['customer_id']}: snapshot says active, Stripe says {sub.status}"
                )
                continue
            stripe_price_id = sub["items"]["data"][0].price.id
            stripe_plan = self.price_id_to_plan.get(stripe_price_id, "unknown")
            if stripe_plan != snap["plan"]:
                mismatches.append(
                    f"{snap['customer_id']}: snapshot plan={snap['plan']}, stripe plan={stripe_plan}"
                )
        self.assertEqual(mismatches, [], "Plan mismatches:\n" + "\n".join(mismatches))

    def test_quantity_matches_stripe(self):
        """Each snapshot's screen count should match the subscription quantity in Stripe."""
        mismatches = []
        for snap in self.snapshots:
            sub = self.stripe.Subscription.retrieve(snap["subscription_id"])
            if sub.status in ("canceled", "incomplete_expired"):
                continue
            stripe_qty = sub["items"]["data"][0].quantity
            if stripe_qty != snap["screens"]:
                mismatches.append(
                    f"{snap['customer_id']}: snapshot screens={snap['screens']}, stripe qty={stripe_qty}"
                )
        self.assertEqual(mismatches, [], "Quantity mismatches:\n" + "\n".join(mismatches))

    def test_mrr_matches_stripe(self):
        """Each snapshot's mrr_cents should match price * quantity from Stripe."""
        mismatches = []
        for snap in self.snapshots:
            sub = self.stripe.Subscription.retrieve(snap["subscription_id"])
            if sub.status in ("canceled", "incomplete_expired"):
                continue
            item = sub["items"]["data"][0]
            stripe_mrr = item.price.unit_amount * item.quantity
            if stripe_mrr != snap["mrr_cents"]:
                mismatches.append(
                    f"{snap['customer_id']}: snapshot mrr={snap['mrr_cents']}, "
                    f"stripe mrr={stripe_mrr} ({item.price.unit_amount} x {item.quantity})"
                )
        self.assertEqual(mismatches, [], "MRR mismatches:\n" + "\n".join(mismatches))

    def test_total_mrr_matches_stripe(self):
        """Aggregate MRR from snapshots should match sum of all Stripe subscriptions."""
        snapshot_total = sum(row["mrr_cents"] for row in self.snapshots)
        stripe_total = 0
        for snap in self.snapshots:
            sub = self.stripe.Subscription.retrieve(snap["subscription_id"])
            if sub.status in ("canceled", "incomplete_expired"):
                continue
            item = sub["items"]["data"][0]
            stripe_total += item.price.unit_amount * item.quantity
        self.assertEqual(
            snapshot_total, stripe_total,
            f"Total MRR mismatch: snapshot=${snapshot_total/100:.2f}, stripe=${stripe_total/100:.2f}"
        )

    def test_status_matches_stripe(self):
        """Each snapshot's status should match the subscription status in Stripe."""
        mismatches = []
        for snap in self.snapshots:
            sub = self.stripe.Subscription.retrieve(snap["subscription_id"])
            if sub.status in ("canceled", "incomplete_expired"):
                continue
            expected_status = "past_due" if sub.status == "past_due" else "active"
            snap_status = snap.get("status", "active")
            if expected_status != snap_status:
                mismatches.append(
                    f"{snap['customer_id']}: snapshot status={snap_status}, "
                    f"stripe status={sub.status} (expected={expected_status})"
                )
        self.assertEqual(mismatches, [], "Status mismatches:\n" + "\n".join(mismatches))


if __name__ == "__main__":
    unittest.main()
