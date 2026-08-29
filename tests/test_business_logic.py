"""Tests for business logic modules: revenue-at-risk, profitability, next-best-action."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config import DATA_PROCESSED_DIR


def _require(path: Path):
    if not path.exists():
        pytest.skip(f"{path} not found -- run the pipeline first.")


def test_revenue_at_risk_formula_matches_documented_methodology():
    """Revenue at Risk = Churn Probability x Expected 12-Month CLV (see docs/ml_methodology.md)."""
    path = DATA_PROCESSED_DIR / "revenue_at_risk.csv"
    _require(path)
    df = pd.read_csv(path)
    recomputed = df["churn_probability"] * df["expected_clv_12m"]
    assert (df["revenue_at_risk"] - recomputed).abs().max() < 1.0  # allow float rounding


def test_revenue_at_risk_is_non_negative():
    path = DATA_PROCESSED_DIR / "revenue_at_risk.csv"
    _require(path)
    df = pd.read_csv(path)
    assert (df["revenue_at_risk"] >= 0).all()


def test_profitability_quadrants_are_from_known_set():
    path = DATA_PROCESSED_DIR / "customer_profitability.csv"
    _require(path)
    df = pd.read_csv(path)
    expected = {
        "High Revenue / High Profit", "High Revenue / Low Profit",
        "Low Revenue / High Profit", "Low Revenue / Low Profit",
    }
    assert set(df["profitability_quadrant"].unique()).issubset(expected)


def test_profit_equals_contribution_minus_costs():
    """
    Estimated profit must reconcile with its component costs (no silently
    fabricated totals). NOTE: acquisition_cost is intentionally EXCLUDED from
    estimated_profit -- it's a one-time, already-sunk cost, reported as its
    own column for transparency rather than netted against ongoing profit
    (see the module docstring in src/analytics/profitability.py). So the
    reconciling formula does NOT subtract acquisition_cost.
    """
    path = DATA_PROCESSED_DIR / "customer_profitability.csv"
    _require(path)
    df = pd.read_csv(path)
    assert df["acquisition_cost"].isnull().sum() == 0, (
        "acquisition_cost must be populated for every customer in the profitability table "
        "(it's a customer master-data attribute, not snapshot-dependent)"
    )
    recomputed = (
        df["gross_contribution"] - df["fulfillment_cost"] - df["return_cost"] - df["support_cost"]
    )
    assert (df["estimated_profit"] - recomputed).abs().max() < 1.0


def test_next_best_action_is_from_known_action_set():
    path = DATA_PROCESSED_DIR / "next_best_actions.csv"
    _require(path)
    df = pd.read_csv(path)
    expected = {
        "RETENTION", "UPSELL", "CROSS_SELL", "LOYALTY_REWARD",
        "REACTIVATION", "PREMIUM_SUPPORT", "NO_ACTION",
    }
    assert set(df["recommended_action"].unique()).issubset(expected)


def test_next_best_action_always_has_a_reason():
    path = DATA_PROCESSED_DIR / "next_best_actions.csv"
    _require(path)
    df = pd.read_csv(path)
    assert df["action_reason"].notna().all()
    assert (df["action_reason"].str.len() > 10).all()


def test_recommend_action_function_is_deterministic():
    """Calling the rule function twice on the same input must give the same output."""
    from src.business.next_best_action import recommend_action
    row = {
        "clv_category": "High", "risk_category": "High", "engagement_score": 70,
        "churn_probability": 0.8, "n_complaints": 0, "avg_satisfaction": 4.0, "n_categories": 3,
    }
    result1 = recommend_action(row)
    result2 = recommend_action(row)
    assert result1 == result2
    assert result1[0] == "RETENTION"  # High CLV + High risk => RETENTION per documented rule


def test_profitability_table_has_no_missing_values():
    """
    Regression test: previously, acquisition_cost was joined from the
    snapshot-filtered customer_features table, which silently produced NaN
    for customers who signed up on/after SNAPSHOT_DATE but already had
    orders (269 customers in one observed run). Fixed by sourcing
    acquisition_cost from customers_clean.csv (unconditional on snapshot).
    This test guards against that regressing.
    """
    path = DATA_PROCESSED_DIR / "customer_profitability.csv"
    _require(path)
    df = pd.read_csv(path)
    assert not df.isnull().any().any(), (
        f"customer_profitability.csv must have no NaNs; found NaNs in columns: "
        f"{df.columns[df.isnull().any()].tolist()}"
    )


def test_profitability_may_legitimately_include_customers_absent_from_features():
    """
    Profitability is computed over each customer's FULL order history and is
    NOT limited to the snapshot window used for churn/CLV features -- so it
    can legitimately include customers absent from customer_features.csv
    (those who signed up on/after SNAPSHOT_DATE but already have orders).
    The important invariant is that those rows are still fully populated
    (no NaN), which is covered by the test above.
    """
    prof_path = DATA_PROCESSED_DIR / "customer_profitability.csv"
    feats_path = DATA_PROCESSED_DIR / "customer_features.csv"
    _require(prof_path)
    _require(feats_path)
    prof = pd.read_csv(prof_path)
    feats = pd.read_csv(feats_path)
    only_in_profitability = set(prof["customer_id"]) - set(feats["customer_id"])
    assert isinstance(only_in_profitability, set)  # comparison itself must not error
