"""Executive Overview page: top-line KPIs, revenue trend, regional/category breakdowns."""
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[2]))
from dashboard.data_loader import (
    load_kpis, load_customer_360, load_monthly_revenue, _fmt_currency,
)


def render():
    st.title("📊 Executive Overview")
    st.caption("NovaMart -- Customer 360 & Revenue Intelligence Platform")

    kpis = load_kpis()
    df = load_customer_360()

    r1 = st.columns(4)
    r1[0].metric("Total Customers", f"{kpis['total_customers']:,}")
    r1[1].metric("Active Customers (90d)", f"{kpis['active_customers']:,}",
                 f"{kpis['active_customers']/kpis['total_customers']:.1%} of base")
    r1[2].metric("Total Revenue", _fmt_currency(kpis["total_revenue"]))
    r1[3].metric("Total Orders", f"{kpis['total_orders']:,}")

    r2 = st.columns(4)
    r2[0].metric("Avg Order Value", _fmt_currency(kpis["average_order_value"]))
    r2[1].metric("Repeat Purchase Rate", f"{kpis['repeat_purchase_rate']:.1%}")
    r2[2].metric("Retention Rate", f"{kpis['customer_retention_rate']:.1%}")
    r2[3].metric("Churn Rate", f"{kpis['churn_rate']:.1%}", delta_color="inverse")

    r3 = st.columns(4)
    r3[0].metric("Avg Predicted CLV (12m)", _fmt_currency(kpis["average_clv_12m"]))
    r3[1].metric("Total Revenue at Risk", _fmt_currency(kpis["total_revenue_at_risk"]))
    r3[2].metric("High-Risk Customers", f"{kpis['high_risk_customers']:,}")
    r3[3].metric("Return Rate", f"{kpis['return_rate']:.1%}")

    st.markdown("---")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Monthly Revenue Trend")
        mr = load_monthly_revenue()
        fig = px.line(mr, x="month", y="revenue", markers=True)
        fig.update_layout(yaxis_title="Revenue", xaxis_title="Month", height=380)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Revenue by Region")
        region_rev = df.groupby("region")["monetary"].sum().sort_values(ascending=False).reset_index()
        fig2 = px.pie(region_rev, names="region", values="monetary", hole=0.45)
        fig2.update_layout(height=380)
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("RFM Segment Distribution")
        seg_counts = df["rfm_segment"].value_counts().reset_index()
        seg_counts.columns = ["segment", "customers"]
        fig3 = px.bar(seg_counts, x="segment", y="customers", color="segment")
        fig3.update_layout(showlegend=False, height=380)
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.subheader("Acquisition Channel Mix")
        chan = df["acquisition_channel"].value_counts().reset_index()
        chan.columns = ["channel", "customers"]
        fig4 = px.bar(chan, x="customers", y="channel", orientation="h")
        fig4.update_layout(height=380)
        st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")
    st.caption(
        "All figures above are computed directly from the pipeline outputs "
        "(reports/executive_kpis.json, data/processed/*.csv) -- nothing on this page is hardcoded."
    )
