"""Churn Intelligence page: model comparison, risk distribution, high-risk customer list."""
import json
import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[2]))
from dashboard.data_loader import load_customer_360, load_churn_model_comparison, _fmt_currency
from src.config import REPORTS_DIR


def render():
    st.title("⚠️ Churn Intelligence")
    st.caption("Model comparison, churn risk distribution, and per-customer risk factors.")

    df = load_customer_360()
    comparison = load_churn_model_comparison()

    with open(REPORTS_DIR / "churn_model_selection.json") as f:
        selection = json.load(f)

    st.subheader("Model Comparison (held-out test set)")
    st.dataframe(comparison, use_container_width=True, hide_index=True)
    st.info(
        f"**Selected model: {selection['selected_model']}** -- {selection['rationale']}"
    )

    cm = selection["confusion_matrix"]
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Confusion Matrix")
        cm_df = px.imshow(
            cm, text_auto=True, x=["Predicted: Stay", "Predicted: Churn"],
            y=["Actual: Stay", "Actual: Churn"], color_continuous_scale="Blues",
        )
        cm_df.update_layout(height=350)
        st.plotly_chart(cm_df, use_container_width=True)
    with c2:
        st.subheader("Churn Probability Distribution")
        fig = px.histogram(df, x="churn_probability", nbins=40, color="risk_category")
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Top Churn Drivers")
    import pandas as pd
    fi = pd.read_csv(REPORTS_DIR / "churn_feature_importance.csv").head(10)
    fi.columns = ["feature", "importance"]
    fig2 = px.bar(fi.sort_values("importance"), x="importance", y="feature", orientation="h")
    fig2.update_layout(height=400)
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.subheader("High-Risk Customers")
    risk_filter = st.slider("Minimum churn probability", 0.0, 1.0, 0.6, 0.05)
    high_risk = df[df["churn_probability"] >= risk_filter].sort_values(
        "expected_clv_12m", ascending=False
    )
    st.write(f"{len(high_risk):,} customers at or above {risk_filter:.0%} churn probability, "
             f"sorted by CLV (highest-value at-risk customers first).")
    st.dataframe(
        high_risk[["customer_id", "region", "ml_segment", "churn_probability",
                   "expected_clv_12m", "top_risk_factors", "recommended_action"]].head(100),
        use_container_width=True, hide_index=True,
    )
    csv = high_risk.to_csv(index=False).encode("utf-8")
    st.download_button("Download high-risk customer list (CSV)", csv, "high_risk_customers.csv", "text/csv")
