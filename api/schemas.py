"""Pydantic request/response schemas for the CRIP REST API."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class CustomerSummary(BaseModel):
    customer_id: str
    region: Optional[str] = None
    acquisition_channel: Optional[str] = None
    segment_name: Optional[str] = None
    risk_category: Optional[str] = None
    clv_category: Optional[str] = None
    recommended_action: Optional[str] = None


class CustomerProfile(BaseModel):
    customer_id: str
    age: Optional[float] = None
    gender: Optional[str] = None
    region: Optional[str] = None
    acquisition_channel: Optional[str] = None
    tenure_days: Optional[float] = None
    frequency: Optional[float] = None
    monetary: Optional[float] = None
    avg_order_value: Optional[float] = None
    recency_days: Optional[float] = None
    rfm_segment: Optional[str] = None
    ml_segment: Optional[str] = None
    churn_probability: Optional[float] = None
    risk_category: Optional[str] = None
    expected_clv_12m: Optional[float] = None
    clv_category: Optional[str] = None
    revenue_at_risk: Optional[float] = None
    estimated_profit: Optional[float] = None
    profitability_quadrant: Optional[str] = None
    recommended_action: Optional[str] = None
    action_reason: Optional[str] = None
    top_risk_factors: Optional[str] = None
    n_returns: Optional[float] = None


class ChurnResult(BaseModel):
    customer_id: str
    churn_probability: float
    risk_category: str
    top_risk_factors: Optional[str] = None


class CLVResult(BaseModel):
    customer_id: str
    current_revenue: float
    predicted_future_90d_revenue: float
    retention_probability: float
    expected_clv_12m: float
    clv_category: str


class RecommendationResult(BaseModel):
    customer_id: str
    recommended_action: str
    action_reason: str
    clv_category: str
    risk_category: str
    expected_clv_12m: float


class ChurnPredictRequest(BaseModel):
    """Ad-hoc scoring request: features must match the churn model's training schema."""
    recency_days: float = Field(..., ge=0)
    frequency: float = Field(..., ge=0)
    monetary: float = Field(..., ge=0)
    avg_order_value: float = Field(..., ge=0)
    tenure_days: float = Field(..., ge=0)
    orders_last_90d: float = Field(..., ge=0)
    orders_prior_90d: float = Field(..., ge=0)
    order_trend: float = 0.0
    avg_discount_pct: float = Field(0.0, ge=0, le=1)
    total_qty: float = Field(..., ge=0)
    n_categories: float = Field(..., ge=0)
    n_returns: float = Field(0.0, ge=0)
    total_refund: float = Field(0.0, ge=0)
    return_rate: float = Field(0.0, ge=0, le=1)
    n_support_tickets: float = Field(0.0, ge=0)
    avg_satisfaction: float = Field(3.0, ge=1, le=5)
    engagement_score: float = Field(0.0, ge=0)
    age: float = Field(35, ge=16, le=100)
    std_order_value: float = 0.0


class ChurnPredictResponse(BaseModel):
    churn_probability: float
    risk_category: str


class CLVPredictRequest(BaseModel):
    recency_days: float = Field(..., ge=0)
    frequency: float = Field(..., ge=0)
    monetary: float = Field(..., ge=0)
    avg_order_value: float = Field(..., ge=0)
    tenure_days: float = Field(..., ge=0)
    orders_last_90d: float = Field(..., ge=0)
    orders_prior_90d: float = Field(..., ge=0)
    avg_discount_pct: float = Field(0.0, ge=0, le=1)
    age: float = Field(35, ge=16, le=100)
    std_order_value: float = 0.0
    engagement_score: float = Field(0.0, ge=0)


class CLVPredictResponse(BaseModel):
    predicted_future_90d_revenue: float
    expected_clv_12m: float
    clv_category: str


class RecommendationRequest(BaseModel):
    churn_probability: float = Field(..., ge=0, le=1)
    expected_clv_12m: float = Field(..., ge=0)
    clv_category: str = Field(..., description="Low, Medium, High, or Very High")
    risk_category: str = Field(..., description="Low, Medium, or High")
    engagement_score: float = Field(0.0, ge=0, description="0-100 engagement score")
    n_complaints: float = Field(0.0, ge=0)
    avg_satisfaction: float = Field(3.5, ge=1, le=5)
    n_categories: float = Field(1.0, ge=0)


class RecommendationResponse(BaseModel):
    recommended_action: str
    action_reason: str


class SegmentSummary(BaseModel):
    segment_name: str
    customer_count: int
    total_revenue: float
    avg_churn_probability: Optional[float] = None
    recommended_action: Optional[str] = None


class AnalyticsOverview(BaseModel):
    total_customers: int
    active_customers: int
    total_revenue: float
    total_orders: int
    average_order_value: float
    repeat_purchase_rate: float
    customer_retention_rate: float
    churn_rate: float
    average_clv_12m: float
    total_predicted_clv_12m: float
    total_revenue_at_risk: float
    high_risk_customers: int
    estimated_total_profit: float
    return_rate: float
