"""
Executive KPIs & EDA summary
==============================
Computes the headline business KPIs used across the dashboard, API, and
Power BI layer, all derived from real pipeline outputs (no hardcoded numbers).
"""
import sys
import json
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATA_PROCESSED_DIR, REPORTS_DIR


def compute_kpis():
    customers = pd.read_csv(DATA_PROCESSED_DIR / "customers_clean.csv", parse_dates=["signup_date"])
    orders = pd.read_csv(DATA_PROCESSED_DIR / "orders_clean.csv", parse_dates=["order_date"])
    feats = pd.read_csv(DATA_PROCESSED_DIR / "customer_features.csv")
    returns = pd.read_csv(DATA_PROCESSED_DIR / "returns_clean.csv")
    clv = pd.read_csv(DATA_PROCESSED_DIR / "clv_predictions.csv")
    rar = pd.read_csv(DATA_PROCESSED_DIR / "revenue_at_risk.csv")
    profit = pd.read_csv(DATA_PROCESSED_DIR / "customer_profitability.csv")

    orders["order_month"] = orders["order_date"].dt.to_period("M").astype(str)
    monthly_rev = orders.groupby("order_month")["order_value"].sum()
    current_month = monthly_rev.index.max()

    total_customers = len(customers)
    active_customers = int((feats["orders_last_90d"] > 0).sum())
    total_revenue = float(orders["order_value"].sum())
    monthly_revenue = float(monthly_rev.get(current_month, 0))
    aov = float(orders["order_value"].mean())
    total_orders = len(orders)

    repeat_customers = int((feats["frequency"] > 1).sum())
    purchasing_customers = int((feats["frequency"] > 0).sum())
    repeat_purchase_rate = repeat_customers / purchasing_customers if purchasing_customers else 0

    churn_rate = float(feats["churned"].mean())
    retention_rate = 1 - churn_rate

    avg_clv = float(clv["expected_clv_12m"].mean())
    total_predicted_clv = float(clv["expected_clv_12m"].sum())

    total_revenue_at_risk = float(rar["revenue_at_risk"].sum())
    high_risk_customers = int((rar["risk_category"] == "High").sum())

    avg_cac = float(feats["acquisition_cost"].mean())
    total_profit = float(profit["estimated_profit"].sum())
    return_rate = len(returns) / total_orders if total_orders else 0

    kpis = {
        "total_customers": total_customers,
        "active_customers": active_customers,
        "total_revenue": round(total_revenue, 2),
        "monthly_revenue_latest": round(monthly_revenue, 2),
        "total_orders": total_orders,
        "average_order_value": round(aov, 2),
        "repeat_purchase_rate": round(repeat_purchase_rate, 4),
        "customer_retention_rate": round(retention_rate, 4),
        "churn_rate": round(churn_rate, 4),
        "average_clv_12m": round(avg_clv, 2),
        "total_predicted_clv_12m": round(total_predicted_clv, 2),
        "total_revenue_at_risk": round(total_revenue_at_risk, 2),
        "high_risk_customers": high_risk_customers,
        "average_customer_acquisition_cost": round(avg_cac, 2),
        "estimated_total_profit": round(total_profit, 2),
        "return_rate": round(return_rate, 4),
    }

    with open(REPORTS_DIR / "executive_kpis.json", "w") as f:
        json.dump(kpis, f, indent=2)

    monthly_rev.round(2).to_csv(REPORTS_DIR / "monthly_revenue.csv", header=["revenue"])

    print("=== Executive KPIs ===")
    for k, v in kpis.items():
        print(f"{k}: {v:,}" if isinstance(v, (int, float)) else f"{k}: {v}")

    return kpis


def main():
    compute_kpis()


if __name__ == "__main__":
    main()
