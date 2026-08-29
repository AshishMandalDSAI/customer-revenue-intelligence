"""
Model Explainability
=====================
Uses SHAP to explain the churn model's predictions, and produces a
per-customer "Top Risk Factors" narrative for high-risk customers, as
required for the Customer 360 view.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
import shap

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATA_PROCESSED_DIR, MODELS_DIR, REPORTS_DIR
from src.models.churn_model import CATEGORICAL_COLS

FRIENDLY_NAMES = {
    "recency_days": "days since last purchase",
    "orders_last_90d": "orders in the last 90 days",
    "orders_prior_90d": "orders in the prior 90-day period",
    "order_trend": "change in purchase frequency",
    "engagement_score": "overall engagement score",
    "n_complaints": "total support complaints",
    "complaints_last_90d": "recent support complaints",
    "complaint_trend": "change in complaint volume",
    "return_rate": "product return rate",
    "n_returns": "number of returns",
    "avg_satisfaction": "average support satisfaction score",
    "avg_discount_pct": "reliance on discounts",
    "frequency": "total historical order count",
    "monetary": "total historical spend",
    "tenure_days": "customer tenure",
    "n_categories": "product category diversity",
}


def describe_factor(feat_name, cust_value, shap_value):
    direction = "increasing" if shap_value > 0 else "decreasing"
    friendly = FRIENDLY_NAMES.get(feat_name, feat_name.replace("_", " "))
    if feat_name == "recency_days":
        return f"{int(cust_value)} days since last purchase ({direction} churn risk)"
    if feat_name in ("orders_last_90d", "orders_prior_90d", "frequency", "n_returns", "n_complaints", "n_categories"):
        return f"{friendly}: {cust_value:.0f} ({direction} churn risk)"
    if feat_name in ("order_trend", "complaint_trend"):
        pct = cust_value * 100
        return f"{friendly}: {pct:+.0f}% ({direction} churn risk)"
    if feat_name in ("return_rate", "avg_discount_pct"):
        return f"{friendly}: {cust_value:.1%} ({direction} churn risk)"
    return f"{friendly}: {cust_value:.2f} ({direction} churn risk)"


def main():
    bundle = joblib.load(MODELS_DIR / "churn_model.pkl")
    model = bundle["model"]
    model_name = bundle["model_name"]
    feature_cols = bundle["feature_cols"]

    df = pd.read_csv(DATA_PROCESSED_DIR / "customer_features.csv")
    df_enc = pd.get_dummies(df, columns=CATEGORICAL_COLS, drop_first=True)
    for c in feature_cols:
        if c not in df_enc.columns:
            df_enc[c] = 0
    X = df_enc[feature_cols].fillna(0)

    print(f"Computing SHAP values for {model_name} model...")
    if model_name in ("Random Forest", "XGBoost"):
        explainer = shap.TreeExplainer(model)
        # sample for speed on the full customer base
        sample_idx = X.sample(n=min(2000, len(X)), random_state=42).index
        shap_values = explainer.shap_values(X.loc[sample_idx])
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
    else:
        scaler = bundle["scaler"]
        X_scaled = scaler.transform(X)
        explainer = shap.LinearExplainer(model, X_scaled)
        sample_idx = X.sample(n=min(2000, len(X)), random_state=42).index
        shap_values = explainer.shap_values(scaler.transform(X.loc[sample_idx]))

    shap_df = pd.DataFrame(shap_values, columns=feature_cols, index=sample_idx)

    # Global feature importance from SHAP (mean abs)
    global_importance = shap_df.abs().mean().sort_values(ascending=False)
    global_importance.round(4).to_csv(REPORTS_DIR / "shap_global_importance.csv", header=["mean_abs_shap"])
    print("\nTop 10 features by mean |SHAP value|:")
    print(global_importance.head(10).round(4))

    # Per-customer top risk factors for HIGH risk customers
    churn_preds = pd.read_csv(DATA_PROCESSED_DIR / "churn_predictions.csv")
    high_risk = churn_preds[churn_preds["risk_category"] == "High"]["customer_id"]
    target_ids = [cid for cid in high_risk if df[df["customer_id"] == cid].index[0] in sample_idx][:200]

    explanations = []
    id_to_pos = {cid: i for i, cid in enumerate(df["customer_id"])}
    for cid in target_ids:
        row_idx = id_to_pos[cid]
        if row_idx not in shap_df.index:
            continue
        row_shap = shap_df.loc[row_idx]
        top_factors_idx = row_shap.abs().sort_values(ascending=False).head(5).index
        cust_row = df[df["customer_id"] == cid].iloc[0]
        factors = [describe_factor(f, cust_row[f] if f in cust_row else 0, row_shap[f]) for f in top_factors_idx]
        churn_prob = churn_preds.loc[churn_preds["customer_id"] == cid, "churn_probability"].values[0]
        explanations.append({
            "customer_id": cid,
            "churn_probability": round(float(churn_prob), 4),
            "risk_category": "High",
            "top_risk_factors": " | ".join(factors),
        })

    exp_df = pd.DataFrame(explanations)
    exp_df.to_csv(DATA_PROCESSED_DIR / "churn_explanations.csv", index=False)
    print(f"\nGenerated risk-factor explanations for {len(exp_df)} high-risk customers.")
    if len(exp_df):
        print("\nExample:")
        ex = exp_df.iloc[0]
        print(f"Customer {ex['customer_id']}")
        print(f"Churn Probability: {ex['churn_probability']:.0%}")
        print("Risk Factors:")
        for i, f in enumerate(ex["top_risk_factors"].split(" | "), 1):
            print(f"  {i}. {f}")

    return exp_df


if __name__ == "__main__":
    main()
