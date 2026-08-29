"""
Revenue-at-Risk
================
Definition (documented and defensible):

    Revenue at Risk (customer level) = Churn Probability x Expected CLV (12-month)

This treats "revenue at risk" as the PROBABILITY-WEIGHTED loss of future
expected value, not the customer's full historical spend (which would
overstate risk for low-value customers) and not just next-quarter revenue
(which understates risk for high-CLV customers with a long horizon).

Segment/region/overall risk are aggregations of the customer-level figure.
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATA_PROCESSED_DIR, REPORTS_DIR


def main():
    feats = pd.read_csv(DATA_PROCESSED_DIR / "customer_features.csv")
    churn = pd.read_csv(DATA_PROCESSED_DIR / "churn_predictions.csv")
    clv = pd.read_csv(DATA_PROCESSED_DIR / "clv_predictions.csv")
    segs = pd.read_csv(DATA_PROCESSED_DIR / "customer_segments.csv")

    df = feats[["customer_id", "region", "acquisition_channel"]].merge(
        churn[["customer_id", "churn_probability", "risk_category"]], on="customer_id"
    ).merge(
        clv[["customer_id", "expected_clv_12m", "clv_category"]], on="customer_id"
    ).merge(
        segs[["customer_id", "segment_name"]], on="customer_id"
    )

    df["revenue_at_risk"] = df["churn_probability"] * df["expected_clv_12m"]

    df.to_csv(DATA_PROCESSED_DIR / "revenue_at_risk.csv", index=False)

    overall_risk = df["revenue_at_risk"].sum()
    high_risk_customers = (df["risk_category"] == "High").sum()

    by_segment = df.groupby("segment_name").agg(
        customers=("customer_id", "count"),
        avg_churn_prob=("churn_probability", "mean"),
        total_revenue_at_risk=("revenue_at_risk", "sum"),
    ).sort_values("total_revenue_at_risk", ascending=False)

    by_region = df.groupby("region").agg(
        customers=("customer_id", "count"),
        total_revenue_at_risk=("revenue_at_risk", "sum"),
    ).sort_values("total_revenue_at_risk", ascending=False)

    by_risk_cat = df.groupby("risk_category", observed=True).agg(
        customers=("customer_id", "count"),
        total_revenue_at_risk=("revenue_at_risk", "sum"),
    )

    by_segment.round(2).to_csv(REPORTS_DIR / "revenue_at_risk_by_segment.csv")
    by_region.round(2).to_csv(REPORTS_DIR / "revenue_at_risk_by_region.csv")

    print("=== Revenue-at-Risk Summary ===")
    print(f"Methodology: Revenue at Risk = Churn Probability x Expected 12-Month CLV")
    print(f"\nTotal Revenue at Risk (all customers): {overall_risk:,.2f}")
    print(f"High-risk customers (churn prob > 60%): {high_risk_customers:,}")
    print(f"\nBy Risk Category:\n{by_risk_cat.round(2)}")
    print(f"\nBy Segment:\n{by_segment.round(2)}")
    print(f"\nBy Region:\n{by_region.round(2)}")

    return df, overall_risk, high_risk_customers


if __name__ == "__main__":
    main()
