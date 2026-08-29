"""
Data Cleaning
=============
Applies cleaning decisions to the raw synthetic tables and writes cleaned
versions to data/processed/. Decisions are documented, not silent.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATA_SYNTHETIC_DIR, DATA_PROCESSED_DIR
from src.data.validation import load_raw_tables


def clean_tables():
    tables = load_raw_tables()
    log = []

    # --- customers ---
    c = tables["customers"].copy()
    before = len(c)
    c = c.drop_duplicates(subset="customer_id")
    c["age"] = c["age"].clip(16, 100)
    log.append(f"customers: {before - len(c)} duplicate rows removed; age clipped to [16,100]")

    # --- orders ---
    o = tables["orders"].copy()
    before = len(o)
    o = o[o["order_value"] > 0]
    o = o[o["n_items"] > 0]
    o = o.drop_duplicates(subset="order_id")
    log.append(f"orders: {before - len(o)} invalid/duplicate rows removed")

    # --- order_items ---
    oi = tables["order_items"].copy()
    before = len(oi)
    oi = oi[(oi["quantity"] > 0) & (oi["unit_price"] > 0)]
    oi["discount_pct"] = oi["discount_pct"].clip(0, 1)
    log.append(f"order_items: {before - len(oi)} invalid rows removed; discount_pct clipped to [0,1]")

    # --- interactions ---
    inter = tables["interactions"].copy()
    inter["satisfaction_score"] = inter["satisfaction_score"].clip(1, 5)

    # --- returns ---
    ret = tables["returns"].copy()
    before = len(ret)
    ret = ret[ret["refund_amount"] > 0]
    log.append(f"returns: {before - len(ret)} invalid rows removed")

    # --- payments ---
    pay = tables["payments"].copy()

    # Referential integrity enforcement (defensive; expected to remove 0 rows given generator design)
    valid_customers = set(c["customer_id"])
    valid_orders = set(o["order_id"])
    before = len(oi)
    oi = oi[oi["order_id"].isin(valid_orders)]
    log.append(f"order_items: {before - len(oi)} orphaned rows (no matching order) removed")

    before = len(ret)
    ret = ret[ret["order_id"].isin(valid_orders)]
    log.append(f"returns: {before - len(ret)} orphaned rows (no matching order) removed")

    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    c.to_csv(DATA_PROCESSED_DIR / "customers_clean.csv", index=False)
    o.to_csv(DATA_PROCESSED_DIR / "orders_clean.csv", index=False)
    oi.to_csv(DATA_PROCESSED_DIR / "order_items_clean.csv", index=False)
    inter.to_csv(DATA_PROCESSED_DIR / "interactions_clean.csv", index=False)
    ret.to_csv(DATA_PROCESSED_DIR / "returns_clean.csv", index=False)
    pay.to_csv(DATA_PROCESSED_DIR / "payments_clean.csv", index=False)
    tables["products"].to_csv(DATA_PROCESSED_DIR / "products_clean.csv", index=False)

    print("=== Data Cleaning Log ===")
    for line in log:
        print("-", line)
    print(f"\nCleaned tables written to {DATA_PROCESSED_DIR}")
    return {
        "customers": c, "orders": o, "order_items": oi,
        "interactions": inter, "returns": ret, "payments": pay,
        "products": tables["products"],
    }


def main():
    clean_tables()


if __name__ == "__main__":
    main()
