"""Customer 360 page: search a customer and see their full profile."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[2]))
from dashboard.data_loader import load_customer_360, _fmt_currency


def render():
    st.title("🔍 Customer 360")
    st.caption("Search any customer to see their full profile: RFM, churn, CLV, profitability, and recommended action.")

    df = load_customer_360()

    col_search, col_filter = st.columns([2, 1])
    with col_search:
        customer_id = st.text_input("Customer ID", placeholder="e.g. C100000")
    with col_filter:
        risk_filter = st.selectbox("...or browse by risk", ["", "High", "Medium", "Low"])

    if not customer_id and risk_filter:
        candidates = df[df["risk_category"] == risk_filter].head(20)
        st.write(f"Sample of {risk_filter}-risk customers:")
        st.dataframe(
            candidates[["customer_id", "region", "ml_segment", "churn_probability", "expected_clv_12m"]],
            use_container_width=True, hide_index=True,
        )
        return

    if not customer_id:
        st.info("Enter a Customer ID above (or pick a risk tier) to view a profile.")
        st.write("A few sample IDs to try:")
        st.code(", ".join(df["customer_id"].head(8).tolist()))
        return

    row = df[df["customer_id"] == customer_id.strip()]
    if row.empty:
        st.error(f"Customer '{customer_id}' not found.")
        return
    r = row.iloc[0]

    st.subheader(f"Customer {r['customer_id']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Age / Gender", f"{int(r['age'])} / {r['gender']}")
    c2.metric("Region", r["region"])
    c3.metric("Acquisition Channel", r["acquisition_channel"])
    c4.metric("Tenure (days)", f"{int(r['tenure_days']):,}")

    st.markdown("### Purchase Behavior")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Revenue", _fmt_currency(r["monetary"]))
    c2.metric("Orders (Frequency)", f"{int(r['frequency'])}")
    c3.metric("Avg Order Value", _fmt_currency(r["avg_order_value"]))
    c4.metric("Recency (days)", f"{int(r['recency_days'])}")

    st.markdown("### RFM & Segmentation")
    c1, c2 = st.columns(2)
    c1.metric("RFM Segment", r["rfm_segment"])
    c2.metric("ML Cluster Segment", r["ml_segment"])

    st.markdown("### Churn Risk")
    c1, c2 = st.columns(2)
    prob = r["churn_probability"]
    color = "🔴" if r["risk_category"] == "High" else ("🟠" if r["risk_category"] == "Medium" else "🟢")
    c1.metric("Churn Probability", f"{prob:.1%}")
    c2.metric("Risk Category", f"{color} {r['risk_category']}")
    if pd.notna(r.get("top_risk_factors")):
        st.markdown("**Top risk factors:**")
        for factor in str(r["top_risk_factors"]).split(" | "):
            st.markdown(f"- {factor}")

    st.markdown("### Customer Lifetime Value")
    c1, c2, c3 = st.columns(3)
    c1.metric("Predicted 90-day Revenue", _fmt_currency(r["predicted_future_90d_revenue"]))
    c2.metric("Expected 12-Month CLV", _fmt_currency(r["expected_clv_12m"]))
    c3.metric("CLV Category", r["clv_category"])

    st.markdown("### Revenue at Risk & Profitability")
    c1, c2, c3 = st.columns(3)
    c1.metric("Revenue at Risk", _fmt_currency(r["revenue_at_risk"]))
    c2.metric("Estimated Profit", _fmt_currency(r["estimated_profit"]))
    c3.metric("Profitability Quadrant", r["profitability_quadrant"])

    st.markdown("### Support & Returns")
    c1, c2 = st.columns(2)
    c1.metric("Returns", f"{int(r['n_returns'])}")
    c2.metric("Support Tickets", f"{int(r.get('n_support_tickets', 0))}")

    st.markdown("### Recommended Action")
    st.success(f"**{r['recommended_action']}**")
    st.write(r["action_reason"])
