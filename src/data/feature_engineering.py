"""
Feature Engineering
====================
Builds the customer-level analytical base table ("customer_features") used
by RFM, segmentation, churn prediction, and CLV prediction.

SNAPSHOT DESIGN (avoids leakage):
    We pick a SNAPSHOT_DATE. All features are computed using only data up to
    SNAPSHOT_DATE. The churn LABEL is computed by looking forward from
    SNAPSHOT_DATE into a holdout window (see churn_model.py) -- features and
    label are built from non-overlapping time windows.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATA_PROCESSED_DIR, DATA_END_DATE, CHURN_INACTIVITY_DAYS

SNAPSHOT_DATE = pd.Timestamp(DATA_END_DATE) - pd.Timedelta(days=CHURN_INACTIVITY_DAYS)
# ^ Features are computed as of 90 days before the true "today" in the dataset.
#   This leaves a clean 90-day forward-looking window (SNAPSHOT_DATE -> DATA_END_DATE)
#   to observe whether the customer actually churned, with ZERO overlap between
#   the feature window and the label window.


def load_clean_tables():
    return {
        "customers": pd.read_csv(DATA_PROCESSED_DIR / "customers_clean.csv", parse_dates=["signup_date"]),
        "orders": pd.read_csv(DATA_PROCESSED_DIR / "orders_clean.csv", parse_dates=["order_date"]),
        "order_items": pd.read_csv(DATA_PROCESSED_DIR / "order_items_clean.csv"),
        "interactions": pd.read_csv(DATA_PROCESSED_DIR / "interactions_clean.csv", parse_dates=["interaction_date"]),
        "returns": pd.read_csv(DATA_PROCESSED_DIR / "returns_clean.csv", parse_dates=["return_date"]),
        "products": pd.read_csv(DATA_PROCESSED_DIR / "products_clean.csv"),
    }


def build_customer_features(snapshot_date=SNAPSHOT_DATE, label_window_end=None):
    """
    Build features as of `snapshot_date`, using only orders/events that
    happened on or before that date.
    """
    tables = load_clean_tables()
    customers = tables["customers"].copy()
    orders = tables["orders"].copy()
    order_items = tables["order_items"].copy()
    interactions = tables["interactions"].copy()
    returns = tables["returns"].copy()

    orders_hist = orders[orders["order_date"] <= snapshot_date].copy()
    interactions_hist = interactions[interactions["interaction_date"] <= snapshot_date].copy()
    returns_hist = returns[returns["return_date"] <= snapshot_date].copy()
    items_hist = order_items[order_items["order_id"].isin(orders_hist["order_id"])].copy()

    feats = customers[["customer_id", "signup_date", "age", "gender", "region",
                        "acquisition_channel", "acquisition_cost"]].copy()
    feats["tenure_days"] = (snapshot_date - feats["signup_date"]).dt.days
    feats = feats[feats["tenure_days"] > 0]  # customer must exist by snapshot

    # ---- RFM base ----
    order_agg = orders_hist.groupby("customer_id").agg(
        frequency=("order_id", "count"),
        monetary=("order_value", "sum"),
        avg_order_value=("order_value", "mean"),
        last_order_date=("order_date", "max"),
        first_order_date=("order_date", "min"),
        std_order_value=("order_value", "std"),
    ).reset_index()

    feats = feats.merge(order_agg, on="customer_id", how="left")

    feats["frequency"] = feats["frequency"].fillna(0).astype(int)
    feats["monetary"] = feats["monetary"].fillna(0.0)
    feats["avg_order_value"] = feats["avg_order_value"].fillna(0.0)
    feats["std_order_value"] = feats["std_order_value"].fillna(0.0)

    feats["recency_days"] = (snapshot_date - feats["last_order_date"]).dt.days
    # Customers with zero orders: recency = tenure (never purchased)
    feats["recency_days"] = feats["recency_days"].fillna(feats["tenure_days"])

    # ---- Purchase-trend features (compare last 90d vs prior 90d activity) ----
    recent_start = snapshot_date - pd.Timedelta(days=90)
    prior_start = snapshot_date - pd.Timedelta(days=180)

    recent_orders = orders_hist[orders_hist["order_date"] > recent_start]
    prior_orders = orders_hist[(orders_hist["order_date"] > prior_start) & (orders_hist["order_date"] <= recent_start)]

    recent_cnt = recent_orders.groupby("customer_id").size().rename("orders_last_90d")
    prior_cnt = prior_orders.groupby("customer_id").size().rename("orders_prior_90d")

    feats = feats.merge(recent_cnt, on="customer_id", how="left")
    feats = feats.merge(prior_cnt, on="customer_id", how="left")
    feats["orders_last_90d"] = feats["orders_last_90d"].fillna(0)
    feats["orders_prior_90d"] = feats["orders_prior_90d"].fillna(0)

    # frequency trend: negative = declining, positive = accelerating
    feats["order_trend"] = (feats["orders_last_90d"] - feats["orders_prior_90d"]) / \
                            (feats["orders_prior_90d"] + 1)

    # ---- Discount dependency & category diversity ----
    item_agg = items_hist.groupby(items_hist["order_id"].map(
        orders_hist.set_index("order_id")["customer_id"]
    )).agg(
        avg_discount_pct=("discount_pct", "mean"),
        total_qty=("quantity", "sum"),
        n_categories=("category", "nunique"),
    ).reset_index().rename(columns={"order_id": "customer_id"})

    feats = feats.merge(item_agg, on="customer_id", how="left")
    feats["avg_discount_pct"] = feats["avg_discount_pct"].fillna(0.0)
    feats["total_qty"] = feats["total_qty"].fillna(0)
    feats["n_categories"] = feats["n_categories"].fillna(0)

    # ---- Returns behavior ----
    ret_agg = returns_hist.groupby("customer_id").agg(
        n_returns=("return_id", "count"),
        total_refund=("refund_amount", "sum"),
    ).reset_index()
    feats = feats.merge(ret_agg, on="customer_id", how="left")
    feats["n_returns"] = feats["n_returns"].fillna(0)
    feats["total_refund"] = feats["total_refund"].fillna(0.0)
    feats["return_rate"] = np.where(feats["frequency"] > 0, feats["n_returns"] / feats["frequency"], 0.0)

    # ---- Support / engagement ----
    supp_agg = interactions_hist.groupby("customer_id").agg(
        n_support_tickets=("interaction_id", "count"),
        avg_satisfaction=("satisfaction_score", "mean"),
        n_complaints=("type", lambda x: (x == "Complaint").sum()),
    ).reset_index()
    feats = feats.merge(supp_agg, on="customer_id", how="left")
    feats["n_support_tickets"] = feats["n_support_tickets"].fillna(0)
    feats["avg_satisfaction"] = feats["avg_satisfaction"].fillna(3.0)  # neutral prior
    feats["n_complaints"] = feats["n_complaints"].fillna(0)

    # complaints trend (last 90 vs prior 90)
    recent_complaints = interactions_hist[
        (interactions_hist["interaction_date"] > recent_start) & (interactions_hist["type"] == "Complaint")
    ].groupby("customer_id").size().rename("complaints_last_90d")
    prior_complaints = interactions_hist[
        (interactions_hist["interaction_date"] > prior_start) & (interactions_hist["interaction_date"] <= recent_start)
        & (interactions_hist["type"] == "Complaint")
    ].groupby("customer_id").size().rename("complaints_prior_90d")
    feats = feats.merge(recent_complaints, on="customer_id", how="left")
    feats = feats.merge(prior_complaints, on="customer_id", how="left")
    feats["complaints_last_90d"] = feats["complaints_last_90d"].fillna(0)
    feats["complaints_prior_90d"] = feats["complaints_prior_90d"].fillna(0)
    feats["complaint_trend"] = feats["complaints_last_90d"] - feats["complaints_prior_90d"]

    # ---- Engagement score (composite, 0-100) ----
    # Higher = more engaged: frequent, recent, low complaints, high satisfaction
    recency_score = np.clip(1 - feats["recency_days"] / feats["tenure_days"].clip(lower=1), 0, 1)
    freq_score = np.clip(feats["frequency"] / feats["frequency"].quantile(0.95).clip(min=1), 0, 1)
    sat_score = np.clip((feats["avg_satisfaction"] - 1) / 4, 0, 1)
    complaint_penalty = np.clip(feats["n_complaints"] / (feats["frequency"] + 1), 0, 1)
    feats["engagement_score"] = np.clip(
        100 * (0.35 * recency_score + 0.35 * freq_score + 0.2 * sat_score - 0.10 * complaint_penalty),
        0, 100
    )

    feats["snapshot_date"] = snapshot_date
    return feats, tables


def compute_churn_labels(feats, snapshot_date=SNAPSHOT_DATE, end_date=None):
    """
    Forward-looking label: did the customer place NO order in the window
    (snapshot_date, snapshot_date + CHURN_INACTIVITY_DAYS]?
    Uses raw cleaned orders (not the historical-only slice) to look forward.
    """
    end_date = pd.Timestamp(end_date or DATA_END_DATE)
    orders = pd.read_csv(DATA_PROCESSED_DIR / "orders_clean.csv", parse_dates=["order_date"])
    window_end = snapshot_date + pd.Timedelta(days=CHURN_INACTIVITY_DAYS)
    window_end = min(window_end, end_date)

    future_orders = orders[(orders["order_date"] > snapshot_date) & (orders["order_date"] <= window_end)]
    active_customers = set(future_orders["customer_id"])

    labels = feats[["customer_id"]].copy()
    labels["churned"] = (~labels["customer_id"].isin(active_customers)).astype(int)
    return labels


def main():
    print("Building customer_features analytical base table...")
    print(f"Snapshot date: {SNAPSHOT_DATE.date()}  |  Label window end: {DATA_END_DATE}")
    feats, _ = build_customer_features()
    labels = compute_churn_labels(feats)

    full = feats.merge(labels, on="customer_id", how="left")
    out_path = DATA_PROCESSED_DIR / "customer_features.csv"
    full.to_csv(out_path, index=False)

    print(f"\nCustomer feature table: {full.shape[0]:,} customers x {full.shape[1]} columns")
    print(f"Churn rate in label window: {full['churned'].mean():.2%}")
    print(f"Saved to {out_path}")
    return full


if __name__ == "__main__":
    main()
