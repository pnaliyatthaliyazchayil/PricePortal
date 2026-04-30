"""
PRICEPORTAL — Hospital Price Transparency Explorer
====================================================
Streamlit + DuckDB portal for exploring hospital prices across
CA and IN, four price types, and Medicare benchmarks.

Usage:
    pip install streamlit duckdb pandas plotly
    streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="PRICEPORTAL",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}
code, .stCode {
    font-family: 'JetBrains Mono', monospace;
}
h1, h2, h3 {
    font-family: 'DM Sans', sans-serif;
    font-weight: 700;
}
/* Metric cards */
[data-testid="stMetric"] {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 12px;
    padding: 16px 20px;
}
[data-testid="stMetric"] label {
    font-size: 0.85rem;
    color: #495057;
}
/* Tables */
.stDataFrame {
    border-radius: 8px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

# ── Navigation ─────────────────────────────────────────────────────────
st.sidebar.markdown("# 🏥 PRICEPORTAL")
st.sidebar.markdown("*Hospital Price Transparency*")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    [
        "📊 Overview",
        "🏥 Hospital Search",
        "🔍 CPT / Code Search",
        "🗺️ ZIP Map",
        "📈 Wang Replication",
        "💰 Payer Analysis",
    ],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Data:** 528 hospitals · CA + IN  \n"
    "**Source:** CMS HPT MRFs (2024–2026)  \n"
    "**Medicare:** OPPS/MPFS CY2026"
)

# ── Route to pages ─────────────────────────────────────────────────────
if page == "📊 Overview":
    from views import overview
    overview.render()
elif page == "🏥 Hospital Search":
    from pages import hospital_search
    hospital_search.render()
elif page == "🔍 CPT / Code Search":
    from pages import code_search
    code_search.render()
elif page == "🗺️ ZIP Map":
    from pages import zip_map
    zip_map.render()
elif page == "📈 Wang Replication":
    from pages import wang_replication
    wang_replication.render()
elif page == "💰 Payer Analysis":
    from pages import payer_analysis
    payer_analysis.render()
