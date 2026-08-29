"""Customer 360 endpoints: list, profile, churn, clv, recommendation."""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

sys.path.append(str(Path(__file__).resolve().parents[2]))
from api.data_access import load_customer_360
from api.schemas import (
    CustomerSummary, CustomerProfile, ChurnResult, CLVResult, RecommendationResult,
)

router = APIRouter(prefix="/customers", tags=["Customers"])


def _clean(v):
    """Convert NaN/NaT to None so FastAPI/Pydantic can serialize to JSON null."""
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


@router.get("", response_model=list[CustomerSummary])
def list_customers(
    region: Optional[str] = None,
    risk_category: Optional[str] = Query(None, description="Low, Medium, High"),
    segment_name: Optional[str] = None,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    df = load_customer_360()
    if region:
        df = df[df["region"] == region]
    if risk_category:
        df = df[df["risk_category"] == risk_category]
    if segment_name:
        df = df[df["ml_segment"] == segment_name]

    page = df.iloc[offset: offset + limit]
    results = []
    for _, row in page.iterrows():
        results.append(CustomerSummary(
            customer_id=row["customer_id"],
            region=_clean(row.get("region")),
            acquisition_channel=_clean(row.get("acquisition_channel")),
            segment_name=_clean(row.get("ml_segment")),
            risk_category=_clean(row.get("risk_category")),
            clv_category=_clean(row.get("clv_category")),
            recommended_action=_clean(row.get("recommended_action")),
        ))
    return results


def _get_row(customer_id: str) -> pd.Series:
    df = load_customer_360()
    match = df[df["customer_id"] == customer_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Customer '{customer_id}' not found")
    return match.iloc[0]


@router.get("/{customer_id}", response_model=CustomerProfile)
@router.get("/{customer_id}/profile", response_model=CustomerProfile)
def get_customer_profile(customer_id: str):
    row = _get_row(customer_id)
    return CustomerProfile(
        customer_id=row["customer_id"],
        age=_clean(row.get("age")),
        gender=_clean(row.get("gender")),
        region=_clean(row.get("region")),
        acquisition_channel=_clean(row.get("acquisition_channel")),
        tenure_days=_clean(row.get("tenure_days")),
        frequency=_clean(row.get("frequency")),
        monetary=_clean(row.get("monetary")),
        avg_order_value=_clean(row.get("avg_order_value")),
        recency_days=_clean(row.get("recency_days")),
        rfm_segment=_clean(row.get("rfm_segment")),
        ml_segment=_clean(row.get("ml_segment")),
        churn_probability=_clean(row.get("churn_probability")),
        risk_category=_clean(row.get("risk_category")),
        expected_clv_12m=_clean(row.get("expected_clv_12m")),
        clv_category=_clean(row.get("clv_category")),
        revenue_at_risk=_clean(row.get("revenue_at_risk")),
        estimated_profit=_clean(row.get("estimated_profit")),
        profitability_quadrant=_clean(row.get("profitability_quadrant")),
        recommended_action=_clean(row.get("recommended_action")),
        action_reason=_clean(row.get("action_reason")),
        top_risk_factors=_clean(row.get("top_risk_factors")),
        n_returns=_clean(row.get("n_returns")),
    )


@router.get("/{customer_id}/churn", response_model=ChurnResult)
def get_customer_churn(customer_id: str):
    row = _get_row(customer_id)
    if pd.isna(row.get("churn_probability")):
        raise HTTPException(status_code=404, detail="No churn score available for this customer")
    return ChurnResult(
        customer_id=row["customer_id"],
        churn_probability=float(row["churn_probability"]),
        risk_category=str(row["risk_category"]),
        top_risk_factors=_clean(row.get("top_risk_factors")),
    )


@router.get("/{customer_id}/clv", response_model=CLVResult)
def get_customer_clv(customer_id: str):
    row = _get_row(customer_id)
    if pd.isna(row.get("expected_clv_12m")):
        raise HTTPException(status_code=404, detail="No CLV score available for this customer")
    return CLVResult(
        customer_id=row["customer_id"],
        current_revenue=float(row["monetary"]),
        predicted_future_90d_revenue=float(row["predicted_future_90d_revenue"]),
        retention_probability=float(row["retention_probability"]),
        expected_clv_12m=float(row["expected_clv_12m"]),
        clv_category=str(row["clv_category"]),
    )


@router.get("/{customer_id}/recommendation", response_model=RecommendationResult)
def get_customer_recommendation(customer_id: str):
    row = _get_row(customer_id)
    if pd.isna(row.get("recommended_action")):
        raise HTTPException(status_code=404, detail="No recommendation available for this customer")
    return RecommendationResult(
        customer_id=row["customer_id"],
        recommended_action=str(row["recommended_action"]),
        action_reason=str(row["action_reason"]),
        clv_category=str(row["clv_category"]),
        risk_category=str(row["risk_category"]),
        expected_clv_12m=float(row["expected_clv_12m"]),
    )
