"""
test_snapshots.py — Validate subscription snapshot data integrity.

Ensures the source-of-truth data that drives the entire dashboard is
internally consistent: correct MRR math, no duplicate customers per
month, and price amounts that match their plan tier.

Run: uv run python -m pytest tests/test_snapshots.py -v
"""

import json
import unittest
from pathlib import Path

SNAPSHOTS_FILE = Path(__file__).resolve().parent.parent / "config" / "sub_snapshots.json"

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


if __name__ == "__main__":
    unittest.main()
