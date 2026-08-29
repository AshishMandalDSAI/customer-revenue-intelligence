"""
Business context builder for the AI Analytics Copilot.

Pulls a compact, grounded summary of the CURRENT pipeline outputs (KPIs,
segment table, revenue-at-risk, top churn drivers, recommendations) so that
whichever "brain" answers the question -- an LLM or the deterministic
fallback -- is answering from real numbers, not invented ones.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config import REPORTS_DIR, DATA_PROCESSED_DIR


def get_business_context() -> dict:
    """Returns a dict of grounded facts the copilot is allowed to reference."""
    with open(REPORTS_DIR / "executive_kpis.json") as f:
        kpis = json.load(f)

    segments = pd.read_csv(REPORTS_DIR / "segment_profiles.csv")
    risk_by_segment = pd.read_csv(REPORTS_DIR / "revenue_at_risk_by_segment.csv")
    risk_by_region = pd.read_csv(REPORTS_DIR / "revenue_at_risk_by_region.csv")
    churn_drivers = pd.read_csv(REPORTS_DIR / "churn_feature_importance.csv").head(8)
    churn_drivers.columns = ["feature", "importance"]
    nba_summary = pd.read_csv(REPORTS_DIR / "next_best_action_summary.csv")
    nba_summary.columns = ["action", "customers"]
    profitability = pd.read_csv(REPORTS_DIR / "profitability_summary.csv")
    churn_selection_path = REPORTS_DIR / "churn_model_selection.json"
    churn_selection = json.loads(churn_selection_path.read_text()) if churn_selection_path.exists() else {}

    top_at_risk = None
    risk_path = DATA_PROCESSED_DIR / "revenue_at_risk.csv"
    if risk_path.exists():
        risk_df = pd.read_csv(risk_path)
        top_at_risk = risk_df.sort_values("revenue_at_risk", ascending=False).head(10)[
            ["customer_id", "region", "segment_name", "churn_probability", "revenue_at_risk"]
        ]

    return {
        "kpis": kpis,
        "segments": segments.to_dict(orient="records"),
        "revenue_at_risk_by_segment": risk_by_segment.to_dict(orient="records"),
        "revenue_at_risk_by_region": risk_by_region.to_dict(orient="records"),
        "top_churn_drivers": churn_drivers.to_dict(orient="records"),
        "next_best_action_distribution": nba_summary.to_dict(orient="records"),
        "profitability_summary": profitability.to_dict(orient="records"),
        "churn_model_selection": churn_selection,
        "top_10_revenue_at_risk_customers": (
            top_at_risk.to_dict(orient="records") if top_at_risk is not None else []
        ),
    }


def context_as_text(context: dict | None = None) -> str:
    """Renders the context dict as compact text for an LLM system/user prompt."""
    ctx = context or get_business_context()
    lines = ["=== NovaMart Business Data Snapshot (grounded, from pipeline output) ==="]
    lines.append(f"KPIs: {json.dumps(ctx['kpis'])}")
    lines.append(f"Segments: {json.dumps(ctx['segments'])}")
    lines.append(f"Revenue at risk by segment: {json.dumps(ctx['revenue_at_risk_by_segment'])}")
    lines.append(f"Revenue at risk by region: {json.dumps(ctx['revenue_at_risk_by_region'])}")
    lines.append(f"Top churn drivers: {json.dumps(ctx['top_churn_drivers'])}")
    lines.append(f"Next-best-action distribution: {json.dumps(ctx['next_best_action_distribution'])}")
    lines.append(f"Profitability summary: {json.dumps(ctx['profitability_summary'])}")
    lines.append(f"Churn model selection: {json.dumps(ctx['churn_model_selection'])}")
    lines.append(f"Top 10 revenue-at-risk customers: {json.dumps(ctx['top_10_revenue_at_risk_customers'])}")
    return "\n".join(lines)
