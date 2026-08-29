"""
Customer Lifetime Value (CLV) Prediction
=========================================
Predicts EXPECTED FUTURE 90-day revenue per customer using a Random Forest
regressor trained on historical behavior, then combines it with retention
probability (1 - churn_probability) to produce an Expected CLV estimate.

Target definition (documented, not fabricated):
    future_90d_revenue = sum(order_value) in the (snapshot_date, snapshot_date+90d] window
    This uses the SAME snapshot/label-window split as churn_model.py, so
    features never see the target period.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATA_PROCESSED_DIR, MODELS_DIR, RANDOM_SEED, REPORTS_DIR
from src.data.feature_engineering import SNAPSHOT_DATE, CHURN_INACTIVITY_DAYS
from src.models.churn_model import FEATURE_COLS, CATEGORICAL_COLS


def build_future_revenue_target():
    orders = pd.read_csv(DATA_PROCESSED_DIR / "orders_clean.csv", parse_dates=["order_date"])
    window_end = SNAPSHOT_DATE + pd.Timedelta(days=CHURN_INACTIVITY_DAYS)
    future = orders[(orders["order_date"] > SNAPSHOT_DATE) & (orders["order_date"] <= window_end)]
    target = future.groupby("customer_id")["order_value"].sum().rename("future_90d_revenue")
    return target


def main():
    df = pd.read_csv(DATA_PROCESSED_DIR / "customer_features.csv")
    target = build_future_revenue_target()
    df = df.merge(target, on="customer_id", how="left")
    df["future_90d_revenue"] = df["future_90d_revenue"].fillna(0.0)

    df_enc = pd.get_dummies(df, columns=CATEGORICAL_COLS, drop_first=True)
    dummy_cols = [c for c in df_enc.columns if any(c.startswith(cc + "_") for cc in CATEGORICAL_COLS)]
    feature_cols = FEATURE_COLS + dummy_cols

    X = df_enc[feature_cols].fillna(0)
    y = df_enc["future_90d_revenue"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=RANDOM_SEED)

    print("Training CLV Random Forest Regressor...")
    model = RandomForestRegressor(
        n_estimators=300, max_depth=10, min_samples_leaf=5,
        random_state=RANDOM_SEED, n_jobs=-1
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    r2 = r2_score(y_test, preds)

    print(f"\n=== CLV Model Performance (held-out test set) ===")
    print(f"MAE : {mae:,.2f}")
    print(f"RMSE: {rmse:,.2f}")
    print(f"R^2 : {r2:.4f}")

    # Predict for full base, combine with churn to form "Expected CLV"
    predicted_future_rev = model.predict(X)
    churn_scores = pd.read_csv(DATA_PROCESSED_DIR / "churn_predictions.csv")
    df_enc = df_enc.merge(churn_scores[["customer_id", "churn_probability"]], on="customer_id", how="left")

    retention_prob = 1 - df_enc["churn_probability"].fillna(0.5)
    # Expected CLV = predicted near-term revenue x retention probability x a
    # multi-period horizon factor (approximating a geometric series of future
    # 90-day periods discounted by ongoing churn risk each period)
    horizon_periods = 4  # approx 1 year of 90-day periods
    retention_prob_clipped = retention_prob.clip(0.05, 0.98)
    geometric_factor = (1 - retention_prob_clipped ** horizon_periods) / (1 - retention_prob_clipped)
    expected_clv = predicted_future_rev * geometric_factor

    clv_out = df_enc[["customer_id"]].copy()
    clv_out["current_revenue"] = df["monetary"]
    clv_out["predicted_future_90d_revenue"] = predicted_future_rev.round(2)
    clv_out["retention_probability"] = retention_prob.round(4)
    clv_out["expected_clv_12m"] = expected_clv.round(2)

    clv_out["clv_category"] = pd.qcut(
        clv_out["expected_clv_12m"].rank(method="first"), 4,
        labels=["Low", "Medium", "High", "Very High"]
    )

    clv_out.to_csv(DATA_PROCESSED_DIR / "clv_predictions.csv", index=False)

    joblib.dump({"model": model, "feature_cols": feature_cols, "horizon_periods": horizon_periods},
                MODELS_DIR / "clv_model.pkl")

    importance = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
    importance.round(4).to_csv(REPORTS_DIR / "clv_feature_importance.csv", header=["importance"])

    metrics = {"mae": float(mae), "rmse": float(rmse), "r2": float(r2)}
    pd.Series(metrics).to_csv(REPORTS_DIR / "clv_model_metrics.csv", header=["value"])

    print("\nTop 10 CLV drivers:")
    print(importance.head(10).round(4))
    print("\nCLV category distribution:")
    print(clv_out["clv_category"].value_counts())
    print(f"\nSaved model to models/clv_model.pkl")
    print(f"Saved predictions to data/processed/clv_predictions.csv")

    return metrics


if __name__ == "__main__":
    main()
