"""Tests for synthetic data generation (src/data/generate_data.py)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config import DATA_SYNTHETIC_DIR, N_CUSTOMERS, N_PRODUCTS


def _require_synthetic():
    if not (DATA_SYNTHETIC_DIR / "customers.csv").exists():
        pytest.skip("Synthetic data not generated. Run `python scripts/run_pipeline.py` first.")


def test_customers_file_exists_and_has_rows():
    _require_synthetic()
    df = pd.read_csv(DATA_SYNTHETIC_DIR / "customers.csv")
    assert len(df) == N_CUSTOMERS
    assert len(df) > 0


def test_customer_ids_are_unique():
    _require_synthetic()
    df = pd.read_csv(DATA_SYNTHETIC_DIR / "customers.csv")
    assert df["customer_id"].is_unique


def test_products_count_matches_config():
    _require_synthetic()
    df = pd.read_csv(DATA_SYNTHETIC_DIR / "products.csv")
    assert len(df) == N_PRODUCTS
    assert df["product_id"].is_unique


def test_orders_reference_valid_customers():
    _require_synthetic()
    customers = pd.read_csv(DATA_SYNTHETIC_DIR / "customers.csv")
    orders = pd.read_csv(DATA_SYNTHETIC_DIR / "orders.csv")
    assert orders["customer_id"].isin(customers["customer_id"]).all()


def test_order_items_reference_valid_orders_and_products():
    _require_synthetic()
    orders = pd.read_csv(DATA_SYNTHETIC_DIR / "orders.csv")
    products = pd.read_csv(DATA_SYNTHETIC_DIR / "products.csv")
    items = pd.read_csv(DATA_SYNTHETIC_DIR / "order_items.csv")
    assert items["order_id"].isin(orders["order_id"]).all()
    assert items["product_id"].isin(products["product_id"]).all()


def test_order_values_are_positive():
    _require_synthetic()
    orders = pd.read_csv(DATA_SYNTHETIC_DIR / "orders.csv")
    assert (orders["order_value"] > 0).all()


def test_discounts_within_valid_range():
    _require_synthetic()
    items = pd.read_csv(DATA_SYNTHETIC_DIR / "order_items.csv")
    assert items["discount_pct"].between(0, 1).all()


def test_declining_engagement_correlates_with_higher_churn_signal():
    """
    Sanity check on the causal structure of the generator: customers whose
    activity has fallen off (few/no orders in the most recent period vs.
    the period before) should skew toward eventual inactivity, not be
    uniformly random. We check this indirectly via the customer_features
    table produced downstream, since that's where "recent vs prior" order
    counts are already computed.
    """
    from src.config import DATA_PROCESSED_DIR
    feat_path = DATA_PROCESSED_DIR / "customer_features.csv"
    if not feat_path.exists():
        pytest.skip("customer_features.csv not generated yet -- run the pipeline first.")
    df = pd.read_csv(feat_path)
    declining = df[df["order_trend"] < -0.3]
    growing = df[df["order_trend"] > 0.3]
    if len(declining) < 20 or len(growing) < 20:
        pytest.skip("Not enough declining/growing customers in this run to compare reliably.")
    assert declining["churned"].mean() > growing["churned"].mean(), (
        "Customers with a declining order trend should churn more than those with a "
        "growing order trend -- this is the core realism check on the synthetic data."
    )
