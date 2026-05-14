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
    page_icon="◆",
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
    background: var(--secondary-background-color);
    border: 1px solid var(--text-color-05, rgba(128,128,128,0.2));
    border-radius: 12px;
    padding: 16px 20px;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background: #0f172a;
    border-right: 1px solid #1e293b;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #f1f5f9;
}
section[data-testid="stSidebar"] hr {
    border-color: #334155;
}

/* Radio buttons → pill-style navigation */
section[data-testid="stSidebar"] .stRadio > div {
    display: flex;
    flex-direction: column;
    gap: 4px;
}
section[data-testid="stSidebar"] .stRadio > div > label {
    background: transparent !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    cursor: pointer;
    transition: all 0.15s ease;
    border: 1px solid transparent !important;
}
section[data-testid="stSidebar"] .stRadio > div > label span,
section[data-testid="stSidebar"] .stRadio > div > label p,
section[data-testid="stSidebar"] .stRadio > div > label div {
    color: #ffffff !important;
    font-size: 1.1rem !important;
    font-weight: 500 !important;
}
section[data-testid="stSidebar"] .stRadio > div > label:hover {
    background: #1e293b;
    color: #e2e8f0 !important;
}
section[data-testid="stSidebar"] .stRadio > div > label[data-checked="true"],
section[data-testid="stSidebar"] .stRadio > div > label:has(input:checked) {
    background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
    border: 1px solid #3b82f6 !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
}
section[data-testid="stSidebar"] .stRadio > div > label:has(input:checked) span,
section[data-testid="stSidebar"] .stRadio > div > label:has(input:checked) p,
section[data-testid="stSidebar"] .stRadio > div > label:has(input:checked) div {
    color: #ffffff !important;
    font-weight: 700 !important;
}

/* Hide radio circles */
section[data-testid="stSidebar"] .stRadio > div > label > div:first-child {
    display: none;
}

/* Sidebar footer text */
section[data-testid="stSidebar"] .stMarkdown small,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #94a3b8;
    font-size: 1rem;
}

/* Tables */
.stDataFrame {
    border-radius: 8px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

# ── Navigation ─────────────────────────────────────────────────────────
st.sidebar.markdown("""
<div style="display:flex; align-items:center; gap:12px; margin-bottom:4px;">
    <svg width="36" height="36" viewBox="0 0 36 36">
        <rect x="2" y="18" width="8" height="16" rx="2" fill="#0d9488"/>
        <rect x="14" y="10" width="8" height="24" rx="2" fill="#d97706"/>
        <rect x="26" y="4" width="8" height="30" rx="2" fill="#6366f1"/>
    </svg>
    <span style="font-size:1.5rem; font-weight:700; letter-spacing:2px; color:#f1f5f9;">PRICEPORTAL</span>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("*Hospital Price Transparency*")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    [
        "Overview",
        "Hospital Search",
        "CPT / Code Search",
        "ZIP Map",
        "Wang Replication",
        "Payer Analysis",
    ],
    label_visibility="collapsed",
)
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Data:** 528 hospitals · CA + IN  \n"
    "**Source:** CMS HPT MRFs (2024–2026)  \n"
    "**Medicare:** OPPS/MPFS CY2026"
)

# ── Version + data freshness ────────────────────────────────────
import os
from pathlib import Path
from datetime import timezone

APP_VERSION = "v1.0.0"
_sentinel   = Path(__file__).parent / "data" / "state_compliance.parquet"

if _sentinel.exists():
    _mtime = _sentinel.stat().st_mtime
    from datetime import datetime
    _updated = datetime.fromtimestamp(_mtime, tz=timezone.utc).strftime("%b %d, %Y")
else:
    _updated = "unknown"

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"<small style='color:#64748b;'>"
    f"App {APP_VERSION} · Data updated {_updated}"
    f"</small>",
    unsafe_allow_html=True,
)
# ── Route to pages ─────────────────────────────────────────────────────
if page == "Overview":
    from views import overview
    overview.render()
elif page == "Hospital Search":
    from views import hospital_search
    hospital_search.render()
elif page == "CPT / Code Search":
    from views import code_search
    code_search.render()
elif page == "ZIP Map":
    from views import zip_map
    zip_map.render()
elif page == "Wang Replication":
    from views import wang_replication
    wang_replication.render()
elif page == "Payer Analysis":
    from views import payer_analysis
    payer_analysis.render()
