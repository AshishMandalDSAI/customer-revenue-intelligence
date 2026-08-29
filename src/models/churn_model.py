"""
Churn Prediction
================
Trains and compares Logistic Regression, Random Forest, and XGBoost
classifiers to predict customer churn (defined in feature_engineering.py
as no purchase in the CHURN_INACTIVITY_DAYS window following the snapshot
date -- a genuinely forward-looking, leakage-free label).
"""
import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix, classification_report
)
from xgboost import XGBClassifier

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATA_PROCESSED_DIR, MODELS_DIR, RANDOM_SEED, REPORTS_DIR

FEATURE_COLS = [
    "age", "tenure_days", "acquisition_cost",
    "frequency", "monetary", "avg_order_value", "std_order_value",
    "recency_days", "orders_last_90d", "orders_prior_90d", "order_trend",
    "avg_discount_pct", "total_qty", "n_categories",
    "n_returns", "total_refund", "return_rate",
    "n_support_tickets", "avg_satisfaction", "n_complaints",
    "complaints_last_90d", "complaints_prior_90d", "complaint_trend",
    "engagement_score",
]
CATEGORICAL_COLS = ["gender", "region", "acquisition_channel"]


def load_data():
    df = pd.read_csv(DATA_PROCESSED_DIR / "customer_features.csv")
    df = pd.get_dummies(df, columns=CATEGORICAL_COLS, drop_first=True)
    dummy_cols = [c for c in df.columns if any(c.startswith(cc + "_") for cc in CATEGORICAL_COLS)]
    feature_cols = FEATURE_COLS + dummy_cols
    X = df[feature_cols].fillna(0)
    y = df["churned"]
    return X, y, df, feature_cols


def evaluate(model, X_test, y_test, name):
    proba = model.predict_proba(X_test)[:, 1]
    preds = (proba >= 0.5).astype(int)
    metrics = {
        "model": name,
        "accuracy": accuracy_score(y_test, preds),
        "precision": precision_score(y_test, preds),
        "recall": recall_score(y_test, preds),
        "f1": f1_score(y_test, preds),
        "roc_auc": roc_auc_score(y_test, proba),
        "pr_auc": average_precision_score(y_test, proba),
    }
    cm = confusion_matrix(y_test, preds)
    return metrics, cm, proba


def main():
    X, y, df, feature_cols = load_data()

    X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
        X, y, df.index, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    results = []
    models = {}

    print("Training Logistic Regression...")
    lr = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=RANDOM_SEED)
    lr.fit(X_train_scaled, y_train)
    m, cm, proba = evaluate(lr, X_test_scaled, y_test, "Logistic Regression")
    results.append(m)
    models["logistic_regression"] = (lr, cm)

    print("Training Random Forest...")
    rf = RandomForestClassifier(
        n_estimators=300, max_depth=10, min_samples_leaf=5,
        class_weight="balanced", random_state=RANDOM_SEED, n_jobs=-1
    )
    rf.fit(X_train, y_train)
    m, cm, proba_rf = evaluate(rf, X_test, y_test, "Random Forest")
    results.append(m)
    models["random_forest"] = (rf, cm)

    print("Training XGBoost...")
    pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    xgb = XGBClassifier(
        n_estimators=300, max_depth=5, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=pos_weight, random_state=RANDOM_SEED,
        eval_metric="logloss", n_jobs=-1
    )
    xgb.fit(X_train, y_train)
    m, cm, proba_xgb = evaluate(xgb, X_test, y_test, "XGBoost")
    results.append(m)
    models["xgboost"] = (xgb, cm)

    results_df = pd.DataFrame(results).set_index("model")
    print("\n=== Model Comparison ===")
    print(results_df.round(4))

    # ---- Model selection rationale ----
    # For churn, a False Negative (predicting a customer will stay, but they
    # churn) is more costly than a False Positive (flagging a loyal customer
    # for a retention offer they didn't need) -- the former loses the
    # customer's future revenue entirely, the latter just costs a discount/
    # outreach. We therefore prioritize RECALL and PR-AUC (better suited to
    # the ~40% imbalance here than ROC-AUC alone), not raw accuracy.
    results_df["business_score"] = 0.5 * results_df["recall"] + 0.5 * results_df["pr_auc"]
    best_model_name = results_df["business_score"].idxmax()
    print(f"\nSelected model (optimizing recall + PR-AUC, per churn business cost asymmetry): {best_model_name}")

    key_map = {"Logistic Regression": "logistic_regression", "Random Forest": "random_forest", "XGBoost": "xgboost"}
    best_key = key_map[best_model_name]
    best_model, best_cm = models[best_key]

    # Feature importance (tree models) / coefficients (LR)
    if best_key == "logistic_regression":
        importance = pd.Series(best_model.coef_[0], index=feature_cols).sort_values(key=abs, ascending=False)
    else:
        importance = pd.Series(best_model.feature_importances_, index=feature_cols).sort_values(ascending=False)

    print("\nTop 10 churn drivers:")
    print(importance.head(10).round(4))

    # Save artifacts
    joblib.dump({
        "model": best_model,
        "model_name": best_model_name,
        "scaler": scaler if best_key == "logistic_regression" else None,
        "feature_cols": feature_cols,
    }, MODELS_DIR / "churn_model.pkl")

    results_df.round(4).to_csv(REPORTS_DIR / "churn_model_comparison.csv")
    importance.round(4).to_csv(REPORTS_DIR / "churn_feature_importance.csv", header=["importance"])

    with open(REPORTS_DIR / "churn_model_selection.json", "w") as f:
        json.dump({
            "selected_model": best_model_name,
            "confusion_matrix": best_cm.tolist(),
            "test_set_size": int(len(y_test)),
            "churn_rate_test_set": float(y_test.mean()),
            "rationale": (
                "Selected for highest weighted recall + PR-AUC, not accuracy. "
                "In churn prediction, missing a true churner (false negative) forfeits "
                "that customer's remaining lifetime value, while a false positive only "
                "costs an unnecessary retention offer. PR-AUC is used alongside recall "
                "because ROC-AUC can look optimistic under class imbalance."
            ),
        }, f, indent=2)

    # Scored predictions for the full customer base (for downstream revenue-at-risk)
    if best_key == "logistic_regression":
        full_scaled = scaler.transform(X)
        churn_proba_all = best_model.predict_proba(full_scaled)[:, 1]
    else:
        churn_proba_all = best_model.predict_proba(X)[:, 1]

    scored = df[["customer_id"]].copy()
    scored["churn_probability"] = churn_proba_all
    scored["risk_category"] = pd.cut(
        scored["churn_probability"], bins=[-0.01, 0.3, 0.6, 1.0],
        labels=["Low", "Medium", "High"]
    )
    scored.to_csv(DATA_PROCESSED_DIR / "churn_predictions.csv", index=False)

    print(f"\nSaved best model ({best_model_name}) to models/churn_model.pkl")
    print(f"Scored {len(scored):,} customers -> data/processed/churn_predictions.csv")
    print(f"Risk distribution:\n{scored['risk_category'].value_counts()}")

    return results_df, best_model_name


if __name__ == "__main__":
    main()
