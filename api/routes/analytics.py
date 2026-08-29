"""Aggregate analytics endpoints: executive overview, segments, revenue risk."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter

sys.path.append(str(Path(__file__).resolve().parents[2]))
from api.data_access import load_executive_kpis, load_segment_profiles, load_revenue_risk_by_segment
from api.schemas import AnalyticsOverview, SegmentSummary

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def analytics_overview():
    kpis = load_executive_kpis()
    return AnalyticsOverview(**kpis)


@router.get("/segments", response_model=list[SegmentSummary])
def analytics_segments():
    df = load_segment_profiles()
    out = []
    for _, row in df.iterrows():
        out.append(SegmentSummary(
            segment_name=row["segment_name"],
            customer_count=int(row["customer_count"]),
            total_revenue=float(row["total_revenue"]),
            avg_churn_probability=float(row.get("churn_rate", 0) or 0),
            recommended_action=row.get("recommended_action"),
        ))
    return out


@router.get("/revenue-risk")
def analytics_revenue_risk():
    df = load_revenue_risk_by_segment()
    return df.to_dict(orient="records")
