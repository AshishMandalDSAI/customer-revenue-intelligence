"""
Customer Profitability
========================
Revenue is not profit. This module estimates true customer profitability
by netting out product cost, discounts, returns, and estimated fulfillment/
support/acquisition costs from gross revenue.

Cost model (documented assumptions):
    - COGS: pulled from products.unit_cost (varies 10-65% margin by product)
    - Fulfillment cost: 8% of net order value (packaging, shipping, handling)
    - Support cost: 150 currency units per support ticket (agent time proxy)
    - Return cost: full refund_amount + a 5% restocking/logistics penalty
    - Acquisition cost: one-time, amortized here as already-sunk (shown separately)
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATA_PROCESSED_DIR, REPORTS_DIR

FULFILLMENT_COST_RATE = 0.08
SUPPORT_COST_PER_TICKET = 150
RETURN_LOGISTICS_PENALTY = 0.05


def main():
    order_items = pd.read_csv(DATA_PROCESSED_DIR / "order_items_clean.csv")
    orders = pd.read_csv(DATA_PROCESSED_DIR / "orders_clean.csv")
    products = pd.read_csv(DATA_PROCESSED_DIR / "products_clean.csv")
    returns = pd.read_csv(DATA_PROCESSED_DIR / "returns_clean.csv")
    interactions = pd.read_csv(DATA_PROCESSED_DIR / "interactions_clean.csv")
    customers = pd.read_csv(DATA_PROCESSED_DIR / "customers_clean.csv")

    items = order_items.merge(products[["product_id", "unit_cost"]], on="product_id", how="left")
    items["cogs"] = items["quantity"] * items["unit_cost"]

    order_cost = items.groupby("order_id")["cogs"].sum().reset_index()
    order_rev = orders.merge(order_cost, on="order_id", how="left")
    order_rev["cogs"] = order_rev["cogs"].fillna(0)

    cust_rev = order_rev.groupby("customer_id").agg(
        gross_revenue=("order_value", "sum"),
        total_cogs=("cogs", "sum"),
        n_orders=("order_id", "count"),
    ).reset_index()
    cust_rev["gross_contribution"] = cust_rev["gross_revenue"] - cust_rev["total_cogs"]
    cust_rev["fulfillment_cost"] = cust_rev["gross_revenue"] * FULFILLMENT_COST_RATE

    ret_cost = returns.groupby("customer_id")["refund_amount"].sum().reset_index()
    ret_cost["return_cost"] = ret_cost["refund_amount"] * (1 + RETURN_LOGISTICS_PENALTY)
    cust_rev = cust_rev.merge(ret_cost[["customer_id", "return_cost"]], on="customer_id", how="left")
    cust_rev["return_cost"] = cust_rev["return_cost"].fillna(0)

    supp_cost = interactions.groupby("customer_id").size().reset_index(name="n_tickets")
    supp_cost["support_cost"] = supp_cost["n_tickets"] * SUPPORT_COST_PER_TICKET
    cust_rev = cust_rev.merge(supp_cost[["customer_id", "support_cost"]], on="customer_id", how="left")
    cust_rev["support_cost"] = cust_rev["support_cost"].fillna(0)

    cust_rev = cust_rev.merge(
        customers[["customer_id", "acquisition_cost"]], on="customer_id", how="left"
    )
    # NOTE: acquisition_cost is sourced from customers_clean.csv (ALL customers), not from
    # customer_features.csv. customer_features.csv is deliberately snapshot-filtered (it
    # excludes customers who signed up on/after SNAPSHOT_DATE, to prevent label leakage --
    # see src/data/feature_engineering.py). Profitability, however, is computed over each
    # customer's FULL order history (not snapshot-limited), so it legitimately includes
    # recently-acquired customers who already have orders. Joining acquisition_cost against
    # the snapshot-filtered table would silently null it out for exactly that population.

    cust_rev["estimated_profit"] = (
        cust_rev["gross_contribution"]
        - cust_rev["fulfillment_cost"]
        - cust_rev["return_cost"]
        - cust_rev["support_cost"]
    )
    cust_rev["profit_margin_pct"] = np.where(
        cust_rev["gross_revenue"] > 0,
        cust_rev["estimated_profit"] / cust_rev["gross_revenue"],
        0
    )

    rev_median = cust_rev["gross_revenue"].median()
    profit_median = cust_rev["estimated_profit"].median()

    def quadrant(row):
        high_rev = row["gross_revenue"] >= rev_median
        high_profit = row["estimated_profit"] >= profit_median
        if high_rev and high_profit:
            return "High Revenue / High Profit"
        if high_rev and not high_profit:
            return "High Revenue / Low Profit"
        if not high_rev and high_profit:
            return "Low Revenue / High Profit"
        return "Low Revenue / Low Profit"

    cust_rev["profitability_quadrant"] = cust_rev.apply(quadrant, axis=1)

    RECOMMENDATIONS = {
        "High Revenue / High Profit": "Protect and grow: prioritize retention, loyalty rewards, premium service.",
        "High Revenue / Low Profit": "Investigate: reduce discount dependency, high return/support costs eroding margin.",
        "Low Revenue / High Profit": "Grow share of wallet: efficient customer, invest in upsell / cross-sell.",
        "Low Revenue / Low Profit": "De-prioritize: automate engagement, avoid further acquisition-cost investment.",
    }
    cust_rev["recommendation"] = cust_rev["profitability_quadrant"].map(RECOMMENDATIONS)

    cust_rev.round(2).to_csv(DATA_PROCESSED_DIR / "customer_profitability.csv", index=False)

    summary = cust_rev.groupby("profitability_quadrant").agg(
        customers=("customer_id", "count"),
        total_revenue=("gross_revenue", "sum"),
        total_profit=("estimated_profit", "sum"),
        avg_margin=("profit_margin_pct", "mean"),
    ).round(2)
    summary.to_csv(REPORTS_DIR / "profitability_summary.csv")

    print("=== Customer Profitability Summary ===")
    print(f"Assumptions: fulfillment={FULFILLMENT_COST_RATE:.0%} of revenue, "
          f"support={SUPPORT_COST_PER_TICKET}/ticket, "
          f"return penalty={RETURN_LOGISTICS_PENALTY:.0%} on top of refund")
    print(f"\nTotal Gross Revenue : {cust_rev['gross_revenue'].sum():,.2f}")
    print(f"Total Estimated Profit: {cust_rev['estimated_profit'].sum():,.2f}")
    print(f"Overall Margin        : {cust_rev['estimated_profit'].sum() / cust_rev['gross_revenue'].sum():.1%}")
    print(f"\nQuadrant Summary:\n{summary}")

    return cust_rev


if __name__ == "__main__":
    main()
