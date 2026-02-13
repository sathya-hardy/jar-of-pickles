"""
seed_prices.py — Create 5 Stripe Products and Prices for the digital signage SaaS.

Products: Free, Standard, Pro Plus, Engage, Enterprise
Each product gets one monthly recurring Price (per-screen pricing).

Saves price IDs to config/stripe_prices.json so other scripts can read them automatically.

Run once: uv run python scripts/seed_prices.py
"""

import json
import os
import sys
import stripe
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Validate Stripe API key
stripe_api_key = os.getenv("STRIPE_SECRET_KEY")
if not stripe_api_key:
    print("ERROR: STRIPE_SECRET_KEY environment variable is not set.")
    print("Set it in your .env file or export it:")
    print("  export STRIPE_SECRET_KEY=sk_test_...")
    sys.exit(1)

stripe.api_key = stripe_api_key

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
    try:
        products = stripe.Product.search(query=f"metadata['tier']:'{tier_key}'", limit=1)
        if not products.data:
            return None, None

        product = products.data[0]
        prices = stripe.Price.list(product=product.id, active=True, limit=1)
        if not prices.data:
            return product, None

        return product, prices.data[0]
    except stripe.error.AuthenticationError as e:
        print(f"ERROR: Stripe authentication failed: {e}")
        print("Check that your STRIPE_SECRET_KEY is valid.")
        sys.exit(1)
    except stripe.error.APIConnectionError as e:
        print(f"ERROR: Failed to connect to Stripe API: {e}")
        print("Check your internet connection.")
        sys.exit(1)
    except stripe.error.StripeError as e:
        print(f"ERROR: Stripe API error while checking for existing product '{tier_key}': {e}")
        return None, None
    except Exception as e:
        print(f"ERROR: Unexpected error checking for existing product '{tier_key}': {e}")
        return None, None


def main():
    print("Creating Stripe Products and Prices...\n")

    config = {
        "price_ids": {},
        "price_to_plan": {},
    }

    for tier in TIERS:
        try:
            product, price = find_existing_price(tier["key"])

            if product and price:
                print(f"  {tier['name']:12s}  EXISTS  product={product.id}  price={price.id}  ${tier['amount']/100:.2f}/screen/mo")
            else:
                if not product:
                    try:
                        product = stripe.Product.create(
                            name=tier["name"],
                            description=tier["description"],
                            metadata={"tier": tier["key"]},
                        )
                    except stripe.error.StripeError as e:
                        print(f"  ERROR: Failed to create product for {tier['name']}: {e}")
                        sys.exit(1)

                try:
                    price = stripe.Price.create(
                        product=product.id,
                        unit_amount=tier["amount"],
                        currency="usd",
                        recurring={"interval": "month"},
                        metadata={"tier": tier["key"]},
                    )
                    print(f"  {tier['name']:12s}  CREATED product={product.id}  price={price.id}  ${tier['amount']/100:.2f}/screen/mo")
                except stripe.error.StripeError as e:
                    print(f"  ERROR: Failed to create price for {tier['name']}: {e}")
                    sys.exit(1)

            config["price_ids"][tier["key"]] = price.id
            config["price_to_plan"][price.id] = tier["name"]
        except Exception as e:
            print(f"  ERROR: Unexpected error processing tier {tier['name']}: {e}")
            sys.exit(1)

    # Save config for other scripts to read
    try:
        CONFIG_DIR.mkdir(exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        print(f"\nSaved price config to {CONFIG_FILE}")
        print("Other scripts will read this file automatically — no manual copy-paste needed.")
    except Exception as e:
        print(f"\nERROR: Failed to save config to {CONFIG_FILE}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
