"""Recommendations page: NBA distribution, per-customer action explorer, business recommendations."""
import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[2]))
from dashboard.data_loader import load_customer_360, load_next_best_action_summary, load_recommendations_md


def render():
    st.title("🎯 Next-Best-Action & Business Recommendations")

    df = load_customer_360()
    nba_summary = load_next_best_action_summary()

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Recommended Action Distribution")
        fig = px.bar(nba_summary.sort_values("customers"), x="customers", y="action",
                     orientation="h", color="action")
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Filter by Action")
        action = st.selectbox("Action", sorted(df["recommended_action"].dropna().unique()))
        subset = df[df["recommended_action"] == action]
        st.write(f"{len(subset):,} customers")
        st.dataframe(
            subset[["customer_id", "region", "ml_segment", "churn_probability",
                    "expected_clv_12m", "action_reason"]].head(50),
            use_container_width=True, hide_index=True,
        )

    st.markdown("---")
    st.subheader("Business Recommendations")
    st.markdown(load_recommendations_md())
