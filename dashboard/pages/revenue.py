"""Revenue & CLV page: revenue-at-risk by segment/region, CLV distribution, profitability quadrants."""
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[2]))
from dashboard.data_loader import (
    load_customer_360, load_revenue_risk_by_segment, load_revenue_risk_by_region,
    load_profitability_summary, load_kpis, _fmt_currency,
)


def render():
    st.title("💰 Revenue-at-Risk, CLV & Profitability")
    st.caption("Revenue at Risk = Churn Probability x Expected 12-Month CLV. See docs/ml_methodology.md for the full definition.")

    kpis = load_kpis()
    df = load_customer_360()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Revenue at Risk", _fmt_currency(kpis["total_revenue_at_risk"]))
    c2.metric("High-Risk Customers", f"{kpis['high_risk_customers']:,}")
    c3.metric("Estimated Total Profit", _fmt_currency(kpis["estimated_total_profit"]))

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Revenue at Risk by Segment")
        by_seg = load_revenue_risk_by_segment()
        fig = px.bar(by_seg.sort_values("total_revenue_at_risk"), x="total_revenue_at_risk",
                     y="segment_name", orientation="h", color="segment_name")
        fig.update_layout(showlegend=False, height=380)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Revenue at Risk by Region")
        by_region = load_revenue_risk_by_region()
        fig2 = px.bar(by_region.sort_values("total_revenue_at_risk"), x="total_revenue_at_risk",
                      y="region", orientation="h", color="region")
        fig2.update_layout(showlegend=False, height=380)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.subheader("CLV Category Distribution")
    clv_counts = df["clv_category"].value_counts().reset_index()
    clv_counts.columns = ["clv_category", "customers"]
    fig3 = px.pie(clv_counts, names="clv_category", values="customers", hole=0.4)
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    st.subheader("Customer Profitability Quadrants")
    st.caption("Revenue is not the same as profit. Quadrants combine revenue level with estimated profit "
               "(after COGS, discounts, returns, fulfillment, support and acquisition costs).")
    prof_summary = load_profitability_summary()
    st.dataframe(prof_summary, use_container_width=True, hide_index=True)

    fig4 = px.scatter(
        df.sample(min(2000, len(df)), random_state=1),
        x="monetary", y="estimated_profit", color="profitability_quadrant",
        hover_data=["customer_id"], opacity=0.6,
        labels={"monetary": "Total Revenue", "estimated_profit": "Estimated Profit"},
    )
    fig4.update_layout(height=450)
    st.plotly_chart(fig4, use_container_width=True)

    with st.expander("Quadrant definitions & recommendations"):
        for _, row in prof_summary.iterrows():
            st.markdown(f"**{row.get('profitability_quadrant', row.iloc[0])}** -- {row.get('recommendation', '')}")
