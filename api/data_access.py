"""
Data access layer for the CRIP API.

Loads the CSV outputs of the analytics/ML pipeline (data/processed/*.csv)
and joins them into an in-memory Customer 360 table. This mirrors what the
customer_360_view SQL view does in Postgres (database/views.sql) -- the API
can run against either the flat files (default, zero external dependencies)
or a real Postgres instance once DATABASE_URL is configured and the
warehouse is loaded via database/schema.sql + seed.sql.

Data is loaded once at process startup and cached in memory; call
`reload()` to pick up a freshly re-run pipeline without restarting the API.
"""
from __future__ import annotations

import sys
from pathlib import Path
from functools import lru_cache

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config import DATA_PROCESSED_DIR, MODELS_DIR

_CACHE: dict = {}


def _read(name: str) -> pd.DataFrame:
    path = DATA_PROCESSED_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python scripts/run_pipeline.py` first to generate processed data."
        )
    return pd.read_csv(path)


def _build_customer_360() -> pd.DataFrame:
    features = _read("customer_features.csv")
    rfm = _read("customer_rfm.csv")[["customer_id", "segment"]].rename(
        columns={"segment": "rfm_segment"}
    )
    segments = _read("customer_segments.csv")[["customer_id", "segment_name"]].rename(
        columns={"segment_name": "ml_segment"}
    )
    churn = _read("churn_predictions.csv")
    clv = _read("clv_predictions.csv")
    nba = _read("next_best_actions.csv")[["customer_id", "recommended_action", "action_reason"]]
    risk = _read("revenue_at_risk.csv")[["customer_id", "revenue_at_risk"]]
    profit = _read("customer_profitability.csv")[
        ["customer_id", "estimated_profit", "profitability_quadrant"]
    ]

    explanations_path = DATA_PROCESSED_DIR / "churn_explanations.csv"
    explanations = (
        pd.read_csv(explanations_path)[["customer_id", "top_risk_factors"]]
        if explanations_path.exists()
        else pd.DataFrame(columns=["customer_id", "top_risk_factors"])
    )

    df = features.merge(rfm, on="customer_id", how="left", suffixes=("", "_rfm"))
    df = df.merge(segments, on="customer_id", how="left")
    df = df.merge(churn, on="customer_id", how="left")
    df = df.merge(clv, on="customer_id", how="left")
    df = df.merge(nba, on="customer_id", how="left")
    df = df.merge(risk, on="customer_id", how="left")
    df = df.merge(profit, on="customer_id", how="left")
    df = df.merge(explanations, on="customer_id", how="left")
    return df


def load_customer_360(force_reload: bool = False) -> pd.DataFrame:
    if force_reload or "customer_360" not in _CACHE:
        _CACHE["customer_360"] = _build_customer_360()
    return _CACHE["customer_360"]


def load_segment_profiles() -> pd.DataFrame:
    from src.config import REPORTS_DIR
    path = REPORTS_DIR / "segment_profiles.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run the pipeline first.")
    return pd.read_csv(path)


def load_executive_kpis() -> dict:
    import json
    from src.config import REPORTS_DIR
    path = REPORTS_DIR / "executive_kpis.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run the pipeline first.")
    with open(path) as f:
        return json.load(f)


def load_revenue_risk_by_segment() -> pd.DataFrame:
    from src.config import REPORTS_DIR
    return pd.read_csv(REPORTS_DIR / "revenue_at_risk_by_segment.csv")


@lru_cache(maxsize=1)
def load_churn_model():
    import joblib
    return joblib.load(MODELS_DIR / "churn_model.pkl")


@lru_cache(maxsize=1)
def load_clv_model():
    import joblib
    return joblib.load(MODELS_DIR / "clv_model.pkl")


def reload_all():
    _CACHE.clear()
    load_churn_model.cache_clear()
    load_clv_model.cache_clear()
