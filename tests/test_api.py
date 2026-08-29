"""Tests for the CRIP REST API (api/main.py)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config import DATA_PROCESSED_DIR


def _require_pipeline_output():
    if not (DATA_PROCESSED_DIR / "customer_features.csv").exists():
        pytest.skip("Pipeline output not found -- run `python scripts/run_pipeline.py` first.")


@pytest.fixture(scope="module")
def client():
    _require_pipeline_output()
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def sample_customer_id():
    df = pd.read_csv(DATA_PROCESSED_DIR / "customer_features.csv")
    return df["customer_id"].iloc[0]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_customers(client):
    r = client.get("/customers", params={"limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 5
    assert "customer_id" in body[0]


def test_list_customers_respects_limit_bounds(client):
    r = client.get("/customers", params={"limit": 0})
    assert r.status_code == 422  # limit must be >= 1
    r = client.get("/customers", params={"limit": 5000})
    assert r.status_code == 422  # limit must be <= 1000


def test_get_customer_profile(client, sample_customer_id):
    r = client.get(f"/customers/{sample_customer_id}/profile")
    assert r.status_code == 200
    body = r.json()
    assert body["customer_id"] == sample_customer_id
    assert "churn_probability" in body
    assert "expected_clv_12m" in body


def test_get_unknown_customer_returns_404(client):
    r = client.get("/customers/NOT_A_REAL_ID/profile")
    assert r.status_code == 404


def test_get_customer_churn(client, sample_customer_id):
    r = client.get(f"/customers/{sample_customer_id}/churn")
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["churn_probability"] <= 1
    assert body["risk_category"] in {"Low", "Medium", "High"}


def test_get_customer_clv(client, sample_customer_id):
    r = client.get(f"/customers/{sample_customer_id}/clv")
    assert r.status_code == 200
    body = r.json()
    assert body["expected_clv_12m"] >= 0


def test_get_customer_recommendation(client, sample_customer_id):
    r = client.get(f"/customers/{sample_customer_id}/recommendation")
    assert r.status_code == 200
    assert "recommended_action" in r.json()


def test_analytics_overview(client):
    r = client.get("/analytics/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["total_customers"] > 0
    assert 0 <= body["churn_rate"] <= 1


def test_analytics_segments(client):
    r = client.get("/analytics/segments")
    assert r.status_code == 200
    assert len(r.json()) > 0


def test_analytics_revenue_risk(client):
    r = client.get("/analytics/revenue-risk")
    assert r.status_code == 200
    assert len(r.json()) > 0


def test_predict_churn_endpoint(client):
    payload = {
        "recency_days": 5, "frequency": 12, "monetary": 50000, "avg_order_value": 4000,
        "tenure_days": 400, "orders_last_90d": 4, "orders_prior_90d": 3, "order_trend": 0.2,
        "avg_discount_pct": 0.15, "total_qty": 30, "n_categories": 5, "n_returns": 0,
        "total_refund": 0, "return_rate": 0, "n_support_tickets": 0, "avg_satisfaction": 4.5,
        "engagement_score": 60, "age": 35, "std_order_value": 500,
    }
    r = client.post("/predict/churn", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["churn_probability"] <= 1
    assert body["risk_category"] in {"Low", "Medium", "High"}


def test_predict_clv_endpoint(client):
    payload = {
        "recency_days": 5, "frequency": 12, "monetary": 50000, "avg_order_value": 4000,
        "tenure_days": 400, "orders_last_90d": 4, "orders_prior_90d": 3,
        "avg_discount_pct": 0.15, "age": 35, "std_order_value": 500, "engagement_score": 60,
    }
    r = client.post("/predict/clv", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["expected_clv_12m"] >= 0
    assert body["clv_category"] in {"Low", "Medium", "High", "Very High"}


def test_predict_churn_rejects_invalid_input(client):
    payload = {"recency_days": -5}  # negative + missing required fields
    r = client.post("/predict/churn", json=payload)
    assert r.status_code == 422


def test_recommend_action_endpoint(client):
    payload = {
        "churn_probability": 0.8, "expected_clv_12m": 150000,
        "clv_category": "High", "risk_category": "High",
        "engagement_score": 50, "n_complaints": 0, "avg_satisfaction": 3.5, "n_categories": 2,
    }
    r = client.post("/recommend/action", json=payload)
    assert r.status_code == 200
    assert r.json()["recommended_action"] == "RETENTION"
