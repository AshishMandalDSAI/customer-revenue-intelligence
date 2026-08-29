"""
NovaMart CRIP -- Streamlit Dashboard
=====================================
Run with:
    streamlit run dashboard/app.py

Requires the pipeline to have been run at least once:
    python scripts/run_pipeline.py
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))
sys.path.append(str(Path(__file__).resolve().parent))

st.set_page_config(
    page_title="NovaMart | Customer 360 & Revenue Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.config import DATA_PROCESSED_DIR  # noqa: E402

if not (DATA_PROCESSED_DIR / "customer_features.csv").exists():
    st.error(
        "No processed data found. Run the pipeline first:\n\n"
        "`python scripts/run_pipeline.py`\n\n"
        "then relaunch this dashboard."
    )
    st.stop()

# Business-facing page modules. Each exposes a render() function; the
# underlying filenames (executive.py, customers.py, etc.) are unchanged --
# only how they're presented in navigation changes below.
from pages import executive, customers, segmentation, churn, revenue, recommendations, copilot  # noqa: E402

st.sidebar.markdown("## NOVAMART")
st.sidebar.caption("Customer 360 & Revenue Intelligence")
st.sidebar.markdown("")

# Using st.navigation()/st.Page() (rather than relying on Streamlit's
# automatic pages/-folder discovery, and rather than a manual st.radio)
# gives full control over the visible label/icon for each page and
# suppresses Streamlit's default raw-filename navigation entries (which
# would otherwise list "app", "churn", "customers", etc.). url_path is set
# explicitly because every page module's entrypoint function is named
# render(), which would otherwise collide as the auto-derived URL path.
pages = [
    st.Page(executive.render, title="Executive Overview", icon="🏠",
            url_path="executive-overview", default=True),
    st.Page(customers.render, title="Customer 360", icon="👥",
            url_path="customer-360"),
    st.Page(segmentation.render, title="Customer Segmentation", icon="🎯",
            url_path="customer-segmentation"),
    st.Page(churn.render, title="Churn Intelligence", icon="⚠️",
            url_path="churn-intelligence"),
    st.Page(revenue.render, title="Revenue & CLV", icon="💰",
            url_path="revenue-clv"),
    st.Page(recommendations.render, title="Next-Best Actions", icon="🚀",
            url_path="next-best-actions"),
    st.Page(copilot.render, title="AI Analytics Copilot", icon="🤖",
            url_path="ai-copilot"),
]

nav = st.navigation(pages, position="sidebar")

st.sidebar.markdown("---")
st.sidebar.caption(
    "Fictional company & synthetic dataset, built for an MBA Data Science "
    "portfolio project. No real customer data is used."
)

nav.run()
