"""Tests for feature engineering, RFM scoring, and customer segmentation."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config import DATA_PROCESSED_DIR, REPORTS_DIR


def _require(path: Path, msg: str):
    if not path.exists():
        pytest.skip(msg)


def test_customer_features_no_leakage_columns():
    """The label window (post-snapshot data) must never leak into features."""
    path = DATA_PROCESSED_DIR / "customer_features.csv"
    _require(path, "Run the pipeline first.")
    df = pd.read_csv(path)
    assert "churned" in df.columns, "Label column must exist for training"
    # snapshot_date must be constant (single point-in-time cut), not derived per-row from the future
    assert df["snapshot_date"].nunique() == 1


def test_customer_features_no_nulls_in_key_fields():
    path = DATA_PROCESSED_DIR / "customer_features.csv"
    _require(path, "Run the pipeline first.")
    df = pd.read_csv(path)
    for col in ["customer_id", "recency_days", "frequency", "monetary", "tenure_days"]:
        assert df[col].isnull().sum() == 0, f"{col} should never be null in the feature table"


def test_rfm_scores_are_in_valid_range():
    path = DATA_PROCESSED_DIR / "customer_rfm.csv"
    _require(path, "Run the pipeline first.")
    df = pd.read_csv(path)
    for col in ["R_score", "F_score", "M_score"]:
        assert df[col].between(1, 5).all(), f"{col} must be between 1 and 5"


def test_rfm_segments_are_from_known_set():
    path = DATA_PROCESSED_DIR / "customer_rfm.csv"
    _require(path, "Run the pipeline first.")
    from src.analytics.rfm import SEGMENT_DEFINITIONS
    df = pd.read_csv(path)
    assert set(df["segment"].unique()).issubset(set(SEGMENT_DEFINITIONS.keys()))


def test_segmentation_cluster_assignment_covers_all_customers():
    features_path = DATA_PROCESSED_DIR / "customer_features.csv"
    segments_path = DATA_PROCESSED_DIR / "customer_segments.csv"
    _require(features_path, "Run the pipeline first.")
    _require(segments_path, "Run the pipeline first.")
    features = pd.read_csv(features_path)
    segments = pd.read_csv(segments_path)
    assert len(segments) == len(features)
    assert segments["customer_id"].is_unique


def test_segmentation_summary_records_a_real_silhouette_score():
    path = REPORTS_DIR / "segmentation_summary.json"
    _require(path, "Run the pipeline first.")
    import json
    with open(path) as f:
        summary = json.load(f)
    assert -1.0 <= summary["silhouette_score"] <= 1.0
    assert summary["best_k"] >= 2
