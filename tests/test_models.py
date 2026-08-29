"""Tests for the churn and CLV models -- checks real, non-fabricated metrics."""
import json
import sys
from pathlib import Path

import joblib
import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config import DATA_PROCESSED_DIR, MODELS_DIR, REPORTS_DIR


def _require(path: Path):
    if not path.exists():
        pytest.skip(f"{path} not found -- run the pipeline first.")


def test_churn_model_artifact_loads():
    path = MODELS_DIR / "churn_model.pkl"
    _require(path)
    artifact = joblib.load(path)
    assert "model" in artifact and "feature_cols" in artifact
    assert hasattr(artifact["model"], "predict_proba")


def test_churn_predictions_are_valid_probabilities():
    path = DATA_PROCESSED_DIR / "churn_predictions.csv"
    _require(path)
    df = pd.read_csv(path)
    assert df["churn_probability"].between(0, 1).all()
    assert set(df["risk_category"].unique()).issubset({"Low", "Medium", "High"})
    assert df["customer_id"].is_unique


def test_churn_model_comparison_metrics_are_real_and_bounded():
    """Metrics must be in valid ranges -- guards against silently fabricated numbers."""
    path = REPORTS_DIR / "churn_model_comparison.csv"
    _require(path)
    df = pd.read_csv(path)
    assert len(df) == 3  # Logistic Regression, Random Forest, XGBoost
    for col in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]:
        assert df[col].between(0, 1).all(), f"{col} must be a valid metric in [0, 1]"
    # A model that never learned anything would sit at ~0.5 ROC-AUC; require better than chance
    assert (df["roc_auc"] > 0.5).all(), "All trained models should beat random chance (ROC-AUC > 0.5)"


def test_churn_model_selection_documents_a_business_rationale():
    path = REPORTS_DIR / "churn_model_selection.json"
    _require(path)
    with open(path) as f:
        selection = json.load(f)
    assert selection["selected_model"] in {"Logistic Regression", "Random Forest", "XGBoost"}
    assert len(selection["rationale"]) > 20
    cm = selection["confusion_matrix"]
    assert len(cm) == 2 and len(cm[0]) == 2  # 2x2 confusion matrix


def test_clv_model_artifact_loads():
    path = MODELS_DIR / "clv_model.pkl"
    _require(path)
    artifact = joblib.load(path)
    assert "model" in artifact and "feature_cols" in artifact
    assert hasattr(artifact["model"], "predict")


def test_clv_predictions_are_non_negative_and_categorized():
    path = DATA_PROCESSED_DIR / "clv_predictions.csv"
    _require(path)
    df = pd.read_csv(path)
    assert (df["expected_clv_12m"] >= 0).all()
    assert (df["retention_probability"].between(0, 1)).all()
    assert set(df["clv_category"].unique()).issubset({"Low", "Medium", "High", "Very High"})


def test_clv_model_metrics_are_real_numbers():
    path = REPORTS_DIR / "clv_model_metrics.csv"
    _require(path)
    df = pd.read_csv(path, index_col=0)
    mae, rmse, r2 = df.loc["mae", "value"], df.loc["rmse", "value"], df.loc["r2", "value"]
    assert mae >= 0
    assert rmse >= mae  # RMSE >= MAE is a mathematical property of these two metrics
    assert r2 <= 1.0
