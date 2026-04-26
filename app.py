import streamlit as st
import duckdb
import os
import pandas as pd

st.set_page_config(
    page_title="PricePortal",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

IU_PARQUET = "/data0/hcai-chargemasters/ingest/cdm_all.parquet"
SAMPLE_CSV = os.path.join(os.path.dirname(__file__), "data", "sample.csv")

@st.cache_resource
def get_con():
    con = duckdb.connect(database=":memory:")
    if os.path.exists(IU_PARQUET):
        con.execute(f"CREATE VIEW cdm AS SELECT * FROM read_parquet('{IU_PARQUET}')")
        return con, "full"
    elif os.path.exists(SAMPLE_CSV):
        df = pd.read_csv(SAMPLE_CSV)
        con.execute("CREATE VIEW cdm AS SELECT * FROM df")
        return con, "sample"
    else:
        return None, "none"

con, data_mode = get_con()
st.session_state.con = con

st.title("🏥 PricePortal")
st.caption("Open hospital price transparency — California & Indiana")

if data_mode == "sample":
    st.warning("⚠️ **Demo mode** — showing a 10,000-row sample. Full corpus (56M rows) runs on the IU server.")
elif data_mode == "none":
    st.error("No data source found. Please check README.")
    st.stop()

with st.spinner("Loading corpus stats..."):
    stats = con.execute("""
        SELECT
            COUNT(DISTINCT oshpd_id) AS hospitals,
            COUNT(*)                 AS total_rows,
            MIN(year)                AS min_year,
            MAX(year)                AS max_year
        FROM cdm
    """).fetchone()

c1, c2, c3 = st.columns(3)
c1.metric("Hospitals",     f"{stats[0]:,}")
c2.metric("Years covered", f"{stats[2]}–{stats[3]}")
c3.metric("Price records", f"{stats[1]:,.0f}")

st.markdown("""
---
**Use the sidebar to navigate:**

| Page | What it does |
|---|---|
| 🔍 Hospital Search | Look up a hospital and browse all its prices |
| 💊 CPT Search | Find a procedure and compare prices across hospitals |
| 🗺️ ZIP Map | ZIP-level price maps *(coming Week 3)* |
| 📊 Price Comparison | Four-price-type side-by-side *(coming Week 3)* |

*Data: California HCAI chargemaster disclosures 2014–2025 · Federal HPT MRFs CA + IN · Medicare MPFS/OPPS/IPPS*
""")
