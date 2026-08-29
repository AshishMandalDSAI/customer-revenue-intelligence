"""
Next-Best-Action Engine
========================
Rule + analytics-based recommendation combining CLV tier, churn risk, and
engagement to recommend one action per customer, with an explanation of WHY.
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATA_PROCESSED_DIR, REPORTS_DIR


def recommend_action(row):
    clv_tier = row["clv_category"]
    risk = row["risk_category"]
    engagement = row["engagement_score"]
    high_clv = clv_tier in ("High", "Very High")
    low_clv = clv_tier in ("Low", "Medium")

    if high_clv and risk == "High":
        return "RETENTION", (
            f"High CLV ({clv_tier}) customer with high churn risk "
            f"({row['churn_probability']:.0%} probability) -- protecting this customer's future "
            f"value justifies an urgent, personalized retention offer."
        )
    if high_clv and risk == "Low":
        return "LOYALTY_REWARD", (
            f"High CLV, low churn risk -- reward loyalty to reinforce the relationship "
            f"and unlock referral / advocacy potential."
        )
    if clv_tier in ("Medium", "High") and engagement >= 60 and risk != "High":
        return "UPSELL", (
            f"Solid engagement score ({engagement:.0f}/100) with healthy CLV tier and manageable "
            f"churn risk -- a good candidate for upsell to higher-value products."
        )
    if low_clv and risk == "High":
        return "REACTIVATION", (
            f"Low CLV and high churn risk -- a low-cost automated reactivation campaign is more "
            f"cost-effective than a high-touch retention effort for this segment."
        )
    if row["n_complaints"] >= 3 or row["avg_satisfaction"] <= 2.2:
        return "PREMIUM_SUPPORT", (
            f"Elevated complaint history / low satisfaction score ({row['avg_satisfaction']:.1f}/5) "
            f"-- prioritize a service-recovery touchpoint before any commercial offer."
        )
    if row["n_categories"] >= 2 and engagement >= 40 and risk == "Medium":
        return "CROSS_SELL", (
            f"Purchases across {int(row['n_categories'])} categories with moderate engagement -- "
            f"a cross-sell nudge into an adjacent category is likely to land."
        )
    return "NO_ACTION", "No urgent signal in either direction -- monitor at next review cycle."


def main():
    feats = pd.read_csv(DATA_PROCESSED_DIR / "customer_features.csv")
    churn = pd.read_csv(DATA_PROCESSED_DIR / "churn_predictions.csv")
    clv = pd.read_csv(DATA_PROCESSED_DIR / "clv_predictions.csv")

    df = feats[["customer_id", "n_complaints", "avg_satisfaction", "n_categories", "engagement_score"]].merge(
        churn[["customer_id", "churn_probability", "risk_category"]], on="customer_id"
    ).merge(
        clv[["customer_id", "clv_category", "expected_clv_12m"]], on="customer_id"
    )

    actions = df.apply(recommend_action, axis=1, result_type="expand")
    actions.columns = ["recommended_action", "action_reason"]
    df = pd.concat([df, actions], axis=1)

    df[["customer_id", "recommended_action", "action_reason", "clv_category",
        "risk_category", "expected_clv_12m"]].to_csv(
        DATA_PROCESSED_DIR / "next_best_actions.csv", index=False
    )

    summary = df["recommended_action"].value_counts()
    summary.to_csv(REPORTS_DIR / "next_best_action_summary.csv", header=["customers"])

    print("=== Next-Best-Action Distribution ===")
    print(summary)
    print("\nExample recommendations:")
    for _, r in df.sample(3, random_state=1).iterrows():
        print(f"\n{r['customer_id']}: {r['recommended_action']}")
        print(f"  Reason: {r['action_reason']}")

    return df


if __name__ == "__main__":
    main()
