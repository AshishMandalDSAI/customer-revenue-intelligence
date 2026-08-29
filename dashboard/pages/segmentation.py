"""Customer Segmentation page: ML cluster profiles, PCA view, RFM segments."""
import json
import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[2]))
from dashboard.data_loader import load_customer_360, load_segment_profiles, _fmt_currency
from src.config import REPORTS_DIR


def render():
    st.title("🧩 Customer Segmentation")
    st.caption("K-Means clustering on RFM + behavioral features, with elbow/silhouette-selected k and PCA visualization.")

    df = load_customer_360()
    profiles = load_segment_profiles()

    with open(REPORTS_DIR / "segmentation_summary.json") as f:
        summary = json.load(f)

    c1, c2 = st.columns(2)
    c1.metric("Selected k (clusters)", summary["best_k"])
    c2.metric("Silhouette Score", f"{summary['silhouette_score']:.3f}")

    st.subheader("Cluster Profiles")
    display_cols = ["segment_name", "customer_count", "total_revenue", "churn_rate",
                     "monetary", "engagement_score", "recommended_action"]
    st.dataframe(
        profiles[display_cols].sort_values("total_revenue", ascending=False),
        use_container_width=True, hide_index=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Revenue by Segment")
        fig = px.bar(profiles.sort_values("total_revenue"), x="total_revenue", y="segment_name",
                     orientation="h", color="segment_name")
        fig.update_layout(showlegend=False, height=380)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Churn Rate by Segment")
        fig2 = px.bar(profiles.sort_values("churn_rate"), x="churn_rate", y="segment_name",
                      orientation="h", color="segment_name")
        fig2.update_layout(showlegend=False, height=380, xaxis_tickformat=".0%")
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("PCA Cluster Visualization")
    st.image(str(REPORTS_DIR / "figures" / "09_pca_clusters.png"), use_container_width=True)

    st.markdown("---")
    st.subheader("RFM Segments (rule-based)")
    st.caption(
        "RFM segments (Champions, Loyal Customers, At Risk, etc.) are a complementary, "
        "business-interpretable view alongside the ML clusters above."
    )
    rfm_counts = df["rfm_segment"].value_counts().reset_index()
    rfm_counts.columns = ["segment", "customers"]
    fig3 = px.bar(rfm_counts, x="segment", y="customers", color="segment")
    fig3.update_layout(showlegend=False, height=380)
    st.plotly_chart(fig3, use_container_width=True)
