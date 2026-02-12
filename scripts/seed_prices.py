"""
seed_prices.py — Create 5 Stripe Products and Prices for the digital signage SaaS.

Products: Free, Standard, Pro Plus, Engage, Enterprise
Each product gets one monthly recurring Price (per-screen pricing).

Saves price IDs to config/stripe_prices.json so other scripts can read them automatically.

Run once: uv run python scripts/seed_prices.py
"""

import json
import os
import stripe
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

TIERS = [
    {"name": "Free", "key": "free", "amount": 0, "description": "Get Started for Free"},
    {"name": "Standard", "key": "standard", "amount": 1000, "description": "Digital Signage Simplified"},
    {"name": "Pro Plus", "key": "pro_plus", "amount": 1500, "description": "Maximize Your Potential"},
    {"name": "Engage", "key": "engage", "amount": 3000, "description": "Interactive Digital Experiences"},
    {"name": "Enterprise", "key": "enterprise", "amount": 4500, "description": "Scalable Enterprise Solutions"},
]

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
CONFIG_FILE = CONFIG_DIR / "stripe_prices.json"


def find_existing_price(tier_key):
    """Check if a product with this tier key already exists in Stripe."""
    products = stripe.Product.search(query=f"metadata['tier']:'{tier_key}'", limit=1)
    if not products.data:
        return None, None

    product = products.data[0]
    prices = stripe.Price.list(product=product.id, active=True, limit=1)
    if not prices.data:
        return product, None

    return product, prices.data[0]


def main():
    print("Creating Stripe Products and Prices...\n")

    config = {
        "price_ids": {},
        "price_to_plan": {},
    }

    for tier in TIERS:
        product, price = find_existing_price(tier["key"])

        if product and price:
            print(f"  {tier['name']:12s}  EXISTS  product={product.id}  price={price.id}  ${tier['amount']/100:.2f}/screen/mo")
        else:
            if not product:
                product = stripe.Product.create(
                    name=tier["name"],
                    description=tier["description"],
                    metadata={"tier": tier["key"]},
                )

            price = stripe.Price.create(
                product=product.id,
                unit_amount=tier["amount"],
                currency="usd",
                recurring={"interval": "month"},
                metadata={"tier": tier["key"]},
            )
            print(f"  {tier['name']:12s}  CREATED product={product.id}  price={price.id}  ${tier['amount']/100:.2f}/screen/mo")

        config["price_ids"][tier["key"]] = price.id
        config["price_to_plan"][price.id] = tier["name"]

    # Save config for other scripts to read
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nSaved price config to {CONFIG_FILE}")
    print("Other scripts will read this file automatically — no manual copy-paste needed.")


if __name__ == "__main__":
    main()
