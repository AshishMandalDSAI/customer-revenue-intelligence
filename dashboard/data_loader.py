"""Shared data-loading helpers for the Streamlit dashboard, mirrors api/data_access.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config import DATA_PROCESSED_DIR, REPORTS_DIR, POWERBI_DATA_DIR

CURRENCY = "₹"


def _fmt_currency(x: float) -> str:
    if x is None or pd.isna(x):
        return "-"
    if abs(x) >= 1e7:
        return f"{CURRENCY}{x/1e7:,.2f} Cr"
    if abs(x) >= 1e5:
        return f"{CURRENCY}{x/1e5:,.2f} L"
    return f"{CURRENCY}{x:,.0f}"


@st.cache_data(ttl=300)
def load_kpis() -> dict:
    path = REPORTS_DIR / "executive_kpis.json"
    with open(path) as f:
        return json.load(f)


@st.cache_data(ttl=300)
def load_customer_360() -> pd.DataFrame:
    features = pd.read_csv(DATA_PROCESSED_DIR / "customer_features.csv")
    rfm = pd.read_csv(DATA_PROCESSED_DIR / "customer_rfm.csv")[
        ["customer_id", "segment"]
    ].rename(columns={"segment": "rfm_segment"})
    segments = pd.read_csv(DATA_PROCESSED_DIR / "customer_segments.csv")[
        ["customer_id", "segment_name"]
    ].rename(columns={"segment_name": "ml_segment"})
    churn = pd.read_csv(DATA_PROCESSED_DIR / "churn_predictions.csv")
    clv = pd.read_csv(DATA_PROCESSED_DIR / "clv_predictions.csv")
    nba = pd.read_csv(DATA_PROCESSED_DIR / "next_best_actions.csv")[
        ["customer_id", "recommended_action", "action_reason"]
    ]
    risk = pd.read_csv(DATA_PROCESSED_DIR / "revenue_at_risk.csv")[["customer_id", "revenue_at_risk"]]
    profit = pd.read_csv(DATA_PROCESSED_DIR / "customer_profitability.csv")[
        ["customer_id", "estimated_profit", "profit_margin_pct", "profitability_quadrant"]
    ]
    explanations_path = DATA_PROCESSED_DIR / "churn_explanations.csv"
    explanations = (
        pd.read_csv(explanations_path)[["customer_id", "top_risk_factors"]]
        if explanations_path.exists()
        else pd.DataFrame(columns=["customer_id", "top_risk_factors"])
    )

    df = features.merge(rfm, on="customer_id", how="left")
    df = df.merge(segments, on="customer_id", how="left")
    df = df.merge(churn, on="customer_id", how="left")
    df = df.merge(clv, on="customer_id", how="left")
    df = df.merge(nba, on="customer_id", how="left")
    df = df.merge(risk, on="customer_id", how="left")
    df = df.merge(profit, on="customer_id", how="left")
    df = df.merge(explanations, on="customer_id", how="left")
    return df


@st.cache_data(ttl=300)
def load_segment_profiles() -> pd.DataFrame:
    return pd.read_csv(REPORTS_DIR / "segment_profiles.csv")


@st.cache_data(ttl=300)
def load_monthly_revenue() -> pd.DataFrame:
    df = pd.read_csv(REPORTS_DIR / "monthly_revenue.csv")
    df.columns = ["month", "revenue"]
    return df


@st.cache_data(ttl=300)
def load_revenue_risk_by_segment() -> pd.DataFrame:
    return pd.read_csv(REPORTS_DIR / "revenue_at_risk_by_segment.csv")


@st.cache_data(ttl=300)
def load_revenue_risk_by_region() -> pd.DataFrame:
    return pd.read_csv(REPORTS_DIR / "revenue_at_risk_by_region.csv")


@st.cache_data(ttl=300)
def load_next_best_action_summary() -> pd.DataFrame:
    df = pd.read_csv(REPORTS_DIR / "next_best_action_summary.csv")
    df.columns = ["action", "customers"]
    return df


@st.cache_data(ttl=300)
def load_profitability_summary() -> pd.DataFrame:
    return pd.read_csv(REPORTS_DIR / "profitability_summary.csv")


@st.cache_data(ttl=300)
def load_churn_model_comparison() -> pd.DataFrame:
    return pd.read_csv(REPORTS_DIR / "churn_model_comparison.csv")


@st.cache_data(ttl=300)
def load_recommendations_md() -> str:
    path = REPORTS_DIR / "recommendations.md"
    return path.read_text() if path.exists() else "Run the pipeline to generate recommendations."
