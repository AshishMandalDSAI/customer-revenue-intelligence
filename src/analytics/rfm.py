"""
RFM Analysis
============
Scores customers on Recency, Frequency, Monetary value (1-5 each, 5=best)
and assigns business-meaningful segment labels based on the RFM score
combination (the classic RFM segment map, adapted for NovaMart).
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATA_PROCESSED_DIR


def score_quantile(series, ascending=True, bins=5):
    """Quantile-based scoring 1-5. If ascending=False, low raw value = high score."""
    ranks = series.rank(method="first")
    q = pd.qcut(ranks, bins, labels=False) + 1
    if not ascending:
        q = (bins + 1) - q
    return q.astype(int)


SEGMENT_DEFINITIONS = {
    "Champions": "Bought recently, buy often, spend the most. Reward them -- they can become brand advocates.",
    "Loyal Customers": "Buy regularly and spend well. Upsell higher-value products, ask for reviews/referrals.",
    "Potential Loyalists": "Recent customers with decent frequency/spend. Nurture with loyalty programs.",
    "New Customers": "Bought recently but not often yet. Onboard well, build early habit.",
    "At Risk": "Used to purchase frequently/high value but haven't returned recently. Win-back campaigns needed urgently.",
    "Can't Lose Them": "Made big purchases historically but haven't returned in a long time. High-touch retention outreach.",
    "Hibernating": "Low recency, frequency, and monetary. Low-cost reactivation or let go.",
    "Lost Customers": "Lowest RFM scores across the board. Minimal investment; occasional win-back only.",
    "Needs Attention": "Above-average scores but not standout on any dimension. Targeted engagement.",
    "Promising": "Recent shoppers with low frequency/spend so far. Encourage second purchase.",
}


def assign_segment(row):
    r, f, m = row["R_score"], row["F_score"], row["M_score"]
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    if r >= 3 and f >= 4 and m >= 3:
        return "Loyal Customers"
    if r >= 4 and f <= 2 and m <= 2:
        return "New Customers"
    if r >= 4 and f >= 2 and m >= 2:
        return "Potential Loyalists"
    if r >= 4 and f <= 2:
        return "Promising"
    if r == 3 and f == 3 and m == 3:
        return "Needs Attention"
    if r <= 2 and f >= 4 and m >= 4:
        return "Can't Lose Them"
    if r <= 2 and f >= 3 and m >= 3:
        return "At Risk"
    if r <= 2 and f <= 2 and m <= 2:
        return "Lost Customers"
    if r <= 3 and f <= 3 and m <= 3:
        return "Hibernating"
    return "Needs Attention"


def build_rfm(feats=None):
    if feats is None:
        feats = pd.read_csv(DATA_PROCESSED_DIR / "customer_features.csv")

    rfm = feats[["customer_id", "recency_days", "frequency", "monetary"]].copy()

    rfm["R_score"] = score_quantile(rfm["recency_days"], ascending=False)  # low recency_days = good = high score
    rfm["F_score"] = score_quantile(rfm["frequency"].rank(method="first"), ascending=True)
    rfm["M_score"] = score_quantile(rfm["monetary"].rank(method="first"), ascending=True)

    rfm["rfm_score_str"] = rfm["R_score"].astype(str) + rfm["F_score"].astype(str) + rfm["M_score"].astype(str)
    rfm["rfm_total"] = rfm["R_score"] + rfm["F_score"] + rfm["M_score"]
    rfm["segment"] = rfm.apply(assign_segment, axis=1)
    rfm["segment_description"] = rfm["segment"].map(SEGMENT_DEFINITIONS)

    return rfm


def main():
    rfm = build_rfm()
    out_path = DATA_PROCESSED_DIR / "customer_rfm.csv"
    rfm.to_csv(out_path, index=False)

    print("=== RFM Segment Distribution ===")
    summary = rfm.groupby("segment").agg(
        customers=("customer_id", "count"),
    ).sort_values("customers", ascending=False)
    summary["pct"] = (summary["customers"] / summary["customers"].sum() * 100).round(1)
    print(summary)
    print(f"\nSaved to {out_path}")
    return rfm


if __name__ == "__main__":
    main()
