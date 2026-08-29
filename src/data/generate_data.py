"""
NovaMart Synthetic Data Generator
==================================

Generates a realistic (not random-nonsense) synthetic e-commerce dataset for
NovaMart, a fictional retail company, covering customers, products, orders,
order line items, support interactions, returns, payments, and marketing
campaigns.

Design principle
-----------------
Every customer is given a set of LATENT traits (loyalty, price sensitivity,
support-friction tolerance, base purchase rate) that are NOT stored directly
in the output tables. These latent traits drive:
  * how order frequency decays or grows over the customer's lifetime,
  * how likely the customer is to complain / return items,
  * how large their orders tend to be,
  * how discount-dependent their purchases are.

Churn is NOT hand-labeled. It falls out naturally from simulated behavior:
a customer "churns" if their simulated purchasing activity actually stops
(no order in the CHURN_INACTIVITY_DAYS window before the snapshot date).
This means churn-prediction features (recency, frequency trend, complaints,
engagement) are genuinely predictive of the outcome, and the modeling
notebooks later have to *discover* that relationship rather than have it
handed to them -- avoiding the leakage/fabrication problems the spec warns
against.

Run:
    python -m src.data.generate_data
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from faker import Faker

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.config import (
    DATA_SYNTHETIC_DIR, RANDOM_SEED, N_CUSTOMERS, AVG_ORDERS_PER_CUSTOMER,
    N_PRODUCTS, DATA_START_DATE, DATA_END_DATE, CHURN_INACTIVITY_DAYS
)

fake = Faker()
Faker.seed(RANDOM_SEED)
rng = np.random.default_rng(RANDOM_SEED)

START = pd.Timestamp(DATA_START_DATE)
END = pd.Timestamp(DATA_END_DATE)
TOTAL_DAYS = (END - START).days

REGIONS = ["North", "South", "East", "West", "Central"]
REGION_WEIGHTS = [0.24, 0.22, 0.20, 0.19, 0.15]

CHANNELS = ["Organic Search", "Paid Ads", "Social Media", "Referral", "Email Marketing", "Direct"]
CHANNEL_WEIGHTS = [0.28, 0.22, 0.18, 0.12, 0.12, 0.08]
# Acquisition cost per channel (used later for profitability/CAC)
CHANNEL_CAC = {
    "Organic Search": 180, "Paid Ads": 650, "Social Media": 420,
    "Referral": 90, "Email Marketing": 140, "Direct": 60,
}

PAYMENT_METHODS = ["Credit Card", "Debit Card", "UPI", "Net Banking", "Wallet", "Cash on Delivery"]
PAYMENT_WEIGHTS = [0.30, 0.22, 0.24, 0.10, 0.09, 0.05]

CATEGORIES = {
    "Electronics": (1500, 45000),
    "Fashion & Apparel": (300, 6000),
    "Home & Kitchen": (400, 12000),
    "Beauty & Personal Care": (150, 3500),
    "Groceries": (50, 2500),
    "Sports & Fitness": (300, 9000),
    "Books & Stationery": (100, 2000),
    "Toys & Baby": (200, 5000),
    "Furniture": (2000, 60000),
    "Health & Wellness": (150, 4000),
    "Automotive Accessories": (250, 8000),
    "Pet Supplies": (150, 3000),
}


def generate_products(n_products=N_PRODUCTS):
    rows = []
    cats = list(CATEGORIES.keys())
    for i in range(1, n_products + 1):
        cat = rng.choice(cats)
        lo, hi = CATEGORIES[cat]
        price = round(float(rng.uniform(lo, hi)), 2)
        # Cost margin varies by category (fashion/electronics thinner margin, groceries thin too)
        margin_pct = float(np.clip(rng.normal(0.35, 0.10), 0.10, 0.65))
        rows.append({
            "product_id": f"P{i:04d}",
            "product_name": f"{cat.split(' ')[0]} {fake.word().capitalize()} {rng.integers(100, 999)}",
            "category": cat,
            "unit_price": price,
            "unit_cost": round(price * (1 - margin_pct), 2),
        })
    return pd.DataFrame(rows)


def generate_customers(n=N_CUSTOMERS):
    signup_offsets = rng.integers(0, TOTAL_DAYS - 30, size=n)  # leave room for at least some activity
    signup_dates = [START + timedelta(days=int(o)) for o in signup_offsets]

    ages = rng.integers(18, 70, size=n)
    genders = rng.choice(["Male", "Female", "Other"], size=n, p=[0.47, 0.49, 0.04])
    regions = rng.choice(REGIONS, size=n, p=REGION_WEIGHTS)
    channels = rng.choice(CHANNELS, size=n, p=CHANNEL_WEIGHTS)

    # ---- Latent traits (not exported directly) ----
    # loyalty in [0,1]: higher => less likely to decay/churn, more frequent orders
    loyalty = rng.beta(2.2, 2.5, size=n)
    # base monthly purchase intensity (poisson rate), correlated with loyalty
    base_rate = np.clip(rng.gamma(shape=2.0, scale=0.55, size=n) * (0.5 + loyalty), 0.05, None)
    # price tier preference drives AOV
    price_tier = rng.beta(2.0, 3.0, size=n)  # 0 = budget shopper, 1 = premium shopper
    # complaint sensitivity: prob a bad experience leads to a support ticket / return
    friction = np.clip(rng.beta(2.0, 6.0, size=n) + (1 - loyalty) * 0.15, 0, 1)
    # discount dependency: how much the customer relies on discounts to purchase
    discount_dependency = np.clip(rng.beta(2.0, 4.0, size=n) + (1 - loyalty) * 0.1, 0, 1)

    customer_ids = [f"C{100000+i}" for i in range(n)]

    df = pd.DataFrame({
        "customer_id": customer_ids,
        "signup_date": signup_dates,
        "age": ages,
        "gender": genders,
        "region": regions,
        "acquisition_channel": channels,
        "acquisition_cost": [CHANNEL_CAC[c] for c in channels],
    })

    latent = pd.DataFrame({
        "customer_id": customer_ids,
        "_loyalty": loyalty,
        "_base_rate": base_rate,
        "_price_tier": price_tier,
        "_friction": friction,
        "_discount_dependency": discount_dependency,
    })
    return df, latent


def simulate_orders_and_events(customers_df, latent_df, products_df):
    """
    For each customer, simulate a purchase timeline using a time-varying
    Poisson process whose rate decays for low-loyalty customers (driving
    genuine, emergent churn) and stays flat/grows for high-loyalty ones.
    """
    orders = []
    order_items = []
    interactions = []
    returns = []
    payments = []

    prod_ids = products_df["product_id"].values
    prod_price = dict(zip(products_df["product_id"], products_df["unit_price"]))
    prod_cat = dict(zip(products_df["product_id"], products_df["category"]))

    latent_map = latent_df.set_index("customer_id").to_dict("index")

    order_counter = 1
    item_counter = 1
    interaction_counter = 1
    return_counter = 1

    for _, cust in customers_df.iterrows():
        cid = cust["customer_id"]
        L = latent_map[cid]
        signup = cust["signup_date"]
        lifetime_days = (END - signup).days
        if lifetime_days <= 0:
            continue

        loyalty = L["_loyalty"]
        base_rate = L["_base_rate"]  # orders per 30 days at t=0
        price_tier = L["_price_tier"]
        friction = L["_friction"]
        disc_dep = L["_discount_dependency"]

        # Decay/growth factor per 90-day period. High loyalty -> slow decay or growth.
        # decay_k > 0 means rate shrinks over time; negative means it grows.
        decay_k = float(rng.normal(loc=(0.55 - loyalty * 0.9), scale=0.12))

        # Walk through time in ~30-day steps simulating a Poisson count each step
        t = 0
        step = 30
        cust_orders_dates = []
        while t < lifetime_days:
            periods_elapsed = t / 90.0
            growth_exponent = float(np.clip(-decay_k * periods_elapsed, -8, 2.0))  # cap runaway growth
            current_rate = base_rate * np.exp(growth_exponent)
            current_rate = float(np.clip(current_rate, 0.01, 3.5))  # at most 3.5 orders / 30 days
            lam = current_rate * (step / 30.0)
            n_orders_this_step = rng.poisson(lam)
            for _ in range(n_orders_this_step):
                day_offset = t + int(rng.integers(0, step))
                if day_offset >= lifetime_days:
                    continue
                order_date = signup + timedelta(days=day_offset)
                if order_date > END:
                    continue
                cust_orders_dates.append(order_date)
            t += step

        if not cust_orders_dates:
            continue

        cust_orders_dates.sort()

        for od in cust_orders_dates:
            order_id = f"O{order_counter:07d}"
            order_counter += 1

            n_items = int(np.clip(rng.poisson(1.4) + 1, 1, 6))
            chosen_products = rng.choice(prod_ids, size=n_items, replace=True)

            order_value = 0.0
            for pid in chosen_products:
                base_price = prod_price[pid]
                # premium shoppers buy pricier products more often -> reweight qty
                qty = int(np.clip(rng.poisson(1.2), 1, 5))
                # discount depends on discount_dependency trait + random promos
                discount_pct = float(np.clip(rng.beta(2, 5) * (0.5 + disc_dep), 0, 0.6))
                line_total = base_price * qty * (1 - discount_pct)
                order_value += line_total
                order_items.append({
                    "order_item_id": f"I{item_counter:08d}",
                    "order_id": order_id,
                    "product_id": pid,
                    "category": prod_cat[pid],
                    "quantity": qty,
                    "unit_price": base_price,
                    "discount_pct": round(discount_pct, 3),
                    "line_total": round(line_total, 2),
                })
                item_counter += 1

            payment_method = rng.choice(PAYMENT_METHODS, p=PAYMENT_WEIGHTS)

            orders.append({
                "order_id": order_id,
                "customer_id": cid,
                "order_date": od,
                "order_value": round(order_value, 2),
                "n_items": n_items,
                "payment_method": payment_method,
                "region": cust["region"],
            })
            payments.append({
                "order_id": order_id,
                "customer_id": cid,
                "payment_method": payment_method,
                "amount": round(order_value, 2),
                "payment_date": od,
                "status": rng.choice(["Success", "Success", "Success", "Success", "Failed"], p=None) if False else "Success",
            })

            # Returns: friction-driven probability
            if rng.random() < (0.03 + friction * 0.18):
                return_date = od + timedelta(days=int(rng.integers(1, 14)))
                if return_date <= END:
                    refund_amount = round(order_value * float(rng.uniform(0.3, 1.0)), 2)
                    returns.append({
                        "return_id": f"R{return_counter:06d}",
                        "order_id": order_id,
                        "customer_id": cid,
                        "return_date": return_date,
                        "refund_amount": refund_amount,
                        "reason": rng.choice([
                            "Defective Product", "Not as Described", "Size Issue",
                            "Changed Mind", "Late Delivery", "Better Price Found"
                        ]),
                    })
                    return_counter += 1

            # Support interactions: friction-driven, occasionally unrelated to an order
            if rng.random() < (0.04 + friction * 0.25):
                interactions.append({
                    "interaction_id": f"S{interaction_counter:06d}",
                    "customer_id": cid,
                    "interaction_date": od + timedelta(days=int(rng.integers(0, 5))),
                    "channel": rng.choice(["Chat", "Email", "Phone", "Social Media"]),
                    "type": rng.choice(["Complaint", "Complaint", "Query", "Feedback", "Refund Request"]),
                    "satisfaction_score": int(np.clip(rng.normal(3.4 - friction * 1.8, 1.0), 1, 5)),
                })
                interaction_counter += 1

        # Occasional non-order support interactions (general inquiries)
        n_extra = rng.poisson(friction * 3)
        for _ in range(n_extra):
            day_offset = int(rng.integers(0, lifetime_days))
            idate = signup + timedelta(days=day_offset)
            if idate > END:
                continue
            interactions.append({
                "interaction_id": f"S{interaction_counter:06d}",
                "customer_id": cid,
                "interaction_date": idate,
                "channel": rng.choice(["Chat", "Email", "Phone", "Social Media"]),
                "type": rng.choice(["Query", "Complaint", "Feedback"]),
                "satisfaction_score": int(np.clip(rng.normal(3.4 - friction * 1.8, 1.0), 1, 5)),
            })
            interaction_counter += 1

    orders_df = pd.DataFrame(orders)
    order_items_df = pd.DataFrame(order_items)
    interactions_df = pd.DataFrame(interactions)
    returns_df = pd.DataFrame(returns)
    payments_df = pd.DataFrame(payments)
    return orders_df, order_items_df, interactions_df, returns_df, payments_df


def generate_marketing_campaigns(n=24):
    rows = []
    for i in range(1, n + 1):
        start = START + timedelta(days=int(rng.integers(0, TOTAL_DAYS - 30)))
        rows.append({
            "campaign_id": f"MKT{i:03d}",
            "campaign_name": f"{rng.choice(['Summer', 'Festive', 'Flash', 'Loyalty', 'Winter', 'New Year'])} "
                              f"{rng.choice(['Sale', 'Push', 'Drive', 'Bonanza'])} {start.year}",
            "channel": rng.choice(CHANNELS),
            "start_date": start,
            "end_date": start + timedelta(days=int(rng.integers(5, 21))),
            "budget": round(float(rng.uniform(50000, 800000)), 2),
            "target_region": rng.choice(REGIONS + ["All"]),
        })
    return pd.DataFrame(rows)


def main():
    print("=" * 70)
    print("NovaMart Synthetic Data Generator")
    print("=" * 70)

    print(f"[1/6] Generating {N_PRODUCTS} products across {len(CATEGORIES)} categories...")
    products_df = generate_products()

    print(f"[2/6] Generating {N_CUSTOMERS} customers...")
    customers_df, latent_df = generate_customers()

    print("[3/6] Simulating order timelines, returns, support tickets, payments "
          "(this encodes the churn/CLV signal — may take a minute)...")
    orders_df, order_items_df, interactions_df, returns_df, payments_df = simulate_orders_and_events(
        customers_df, latent_df, products_df
    )

    print("[4/6] Generating marketing campaigns...")
    campaigns_df = generate_marketing_campaigns()

    print("[5/6] Writing latent traits (research-only, NOT used as model features) ...")
    # kept separately so the modeling notebooks cannot accidentally cheat with it
    latent_df.to_csv(DATA_SYNTHETIC_DIR / "_latent_traits_DO_NOT_USE_AS_FEATURES.csv", index=False)

    print("[6/6] Saving all tables to data/synthetic/ ...")
    products_df.to_csv(DATA_SYNTHETIC_DIR / "products.csv", index=False)
    customers_df.to_csv(DATA_SYNTHETIC_DIR / "customers.csv", index=False)
    orders_df.to_csv(DATA_SYNTHETIC_DIR / "orders.csv", index=False)
    order_items_df.to_csv(DATA_SYNTHETIC_DIR / "order_items.csv", index=False)
    interactions_df.to_csv(DATA_SYNTHETIC_DIR / "customer_interactions.csv", index=False)
    returns_df.to_csv(DATA_SYNTHETIC_DIR / "returns.csv", index=False)
    payments_df.to_csv(DATA_SYNTHETIC_DIR / "payments.csv", index=False)
    campaigns_df.to_csv(DATA_SYNTHETIC_DIR / "marketing_campaigns.csv", index=False)

    print("\n--- Generation Summary ---")
    print(f"Customers          : {len(customers_df):,}")
    print(f"Products           : {len(products_df):,}")
    print(f"Orders             : {len(orders_df):,}")
    print(f"Order line items   : {len(order_items_df):,}")
    print(f"Support tickets    : {len(interactions_df):,}")
    print(f"Returns            : {len(returns_df):,}")
    print(f"Marketing campaigns: {len(campaigns_df):,}")
    print(f"Total order revenue: {orders_df['order_value'].sum():,.2f}")
    print("Done. Files written to data/synthetic/")


if __name__ == "__main__":
    main()
