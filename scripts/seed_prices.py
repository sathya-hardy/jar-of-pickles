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


def main():
    print("Creating Stripe Products and Prices...\n")

    config = {
        "price_ids": {},
        "price_to_plan": {},
    }

    for tier in TIERS:
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

        config["price_ids"][tier["key"]] = price.id
        config["price_to_plan"][price.id] = tier["name"]

        print(f"  {tier['name']:12s}  product={product.id}  price={price.id}  ${tier['amount']/100:.2f}/screen/mo")

    # Save config for other scripts to read
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nSaved price config to {CONFIG_FILE}")
    print("Other scripts will read this file automatically — no manual copy-paste needed.")


if __name__ == "__main__":
    main()
