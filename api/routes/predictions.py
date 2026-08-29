"""
Live model-scoring endpoints.

These call the SAME trained artifacts (models/churn_model.pkl,
models/clv_model.pkl) produced by src/models/churn_model.py and
src/models/clv_model.py -- no separate/duplicated model logic. Any
FEATURE_COLS not supplied in the request body are filled with dataset-wide
medians (numeric) so the endpoint is usable without requiring every raw
engineered feature (e.g. complaint counts) from the caller.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException

sys.path.append(str(Path(__file__).resolve().parents[2]))
from api.data_access import load_churn_model, load_clv_model
from api.schemas import (
    ChurnPredictRequest, ChurnPredictResponse,
    CLVPredictRequest, CLVPredictResponse,
    RecommendationRequest, RecommendationResponse,
)
from src.config import DATA_PROCESSED_DIR
from src.business.next_best_action import recommend_action as _nba_rule  # single source of truth for NBA rules

router = APIRouter(tags=["Predictions"])


def _median_defaults() -> dict:
    """Dataset medians for engineered features not exposed in the simplified request schema."""
    df = pd.read_csv(DATA_PROCESSED_DIR / "customer_features.csv")
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    return df[numeric_cols].median().to_dict()


_DEFAULTS_CACHE: dict = {}


def _get_defaults() -> dict:
    if not _DEFAULTS_CACHE:
        _DEFAULTS_CACHE.update(_median_defaults())
    return _DEFAULTS_CACHE


def _build_feature_row(payload: dict, feature_cols: list[str]) -> pd.DataFrame:
    defaults = _get_defaults()
    row = {}
    for col in feature_cols:
        if col in payload and payload[col] is not None:
            row[col] = payload[col]
        elif col in defaults:
            row[col] = defaults[col]
        else:
            # One-hot categorical dummy columns (e.g. region_South) default to 0
            # (i.e. the reference/base category), matching pd.get_dummies(drop_first=True).
            row[col] = 0
    return pd.DataFrame([row])[feature_cols]


@router.post("/predict/churn", response_model=ChurnPredictResponse)
def predict_churn(payload: ChurnPredictRequest):
    artifact = load_churn_model()
    model = artifact["model"]
    scaler = artifact["scaler"]
    feature_cols = artifact["feature_cols"]

    X = _build_feature_row(payload.model_dump(), feature_cols)
    if scaler is not None:
        X = scaler.transform(X)
    proba = float(model.predict_proba(X)[:, 1][0])
    risk = "High" if proba > 0.6 else ("Medium" if proba > 0.3 else "Low")
    return ChurnPredictResponse(churn_probability=round(proba, 4), risk_category=risk)


@router.post("/predict/clv", response_model=CLVPredictResponse)
def predict_clv(payload: CLVPredictRequest):
    churn_artifact = load_churn_model()
    clv_artifact = load_clv_model()

    payload_dict = payload.model_dump()

    # 1. Predicted future 90-day revenue from the CLV regressor
    clv_feature_cols = clv_artifact["feature_cols"]
    X_clv = _build_feature_row(payload_dict, clv_feature_cols)
    predicted_future_rev = float(clv_artifact["model"].predict(X_clv)[0])

    # 2. Retention probability from the churn classifier (1 - churn probability)
    churn_feature_cols = churn_artifact["feature_cols"]
    X_churn = _build_feature_row(payload_dict, churn_feature_cols)
    if churn_artifact["scaler"] is not None:
        X_churn = churn_artifact["scaler"].transform(X_churn)
    churn_proba = float(churn_artifact["model"].predict_proba(X_churn)[:, 1][0])
    retention_prob = np.clip(1 - churn_proba, 0.05, 0.98)

    horizon_periods = clv_artifact.get("horizon_periods", 4)
    geometric_factor = (1 - retention_prob ** horizon_periods) / (1 - retention_prob)
    expected_clv = max(predicted_future_rev, 0) * geometric_factor

    if expected_clv < 5000:
        category = "Low"
    elif expected_clv < 25000:
        category = "Medium"
    elif expected_clv < 100000:
        category = "High"
    else:
        category = "Very High"

    return CLVPredictResponse(
        predicted_future_90d_revenue=round(max(predicted_future_rev, 0), 2),
        expected_clv_12m=round(expected_clv, 2),
        clv_category=category,
    )


@router.post("/recommend/action", response_model=RecommendationResponse)
def recommend_action_endpoint(payload: RecommendationRequest):
    row = payload.model_dump()
    action, reason = _nba_rule(row)
    return RecommendationResponse(recommended_action=action, action_reason=reason)
