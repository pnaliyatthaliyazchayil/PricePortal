import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="ZIP Map · PricePortal", page_icon="🗺️", layout="wide")
st.title("🗺️ ZIP-Level Price Map")
st.caption("Geographic price variation with community socioeconomic overlays.")

con = st.session_state.get("con")
if con is None:
    st.error("Database not initialised — please return to the Home page first.")
    st.stop()

# ── check whether the ZIP-joined data is available yet ──────────────────────
DATA_DIR   = "/data0/hcai-chargemasters/ingest"
ZIP_FILE   = os.path.join(DATA_DIR, "matched_rows_with_zip_all.csv")
ZIP_2024   = os.path.join(DATA_DIR, "matched_rows_with_zip_2024.csv")
CENSUS_ZIP = os.path.join(DATA_DIR, "cache_census_zip_2024.csv")

zip_ready = os.path.exists(ZIP_FILE) or os.path.exists(ZIP_2024)

if not zip_ready:
    st.info(
        "📍 ZIP-level mapping will be enabled once the hospital→ZIP crosswalk is complete "
        "(Week 2 deliverable). The corpus already contains `matched_rows_with_zip_2024.csv` "
        "— this page will load it automatically once it's populated."
    )
    st.markdown("""
    **Planned features for this page:**
    - Choropleth map: median chargemaster price by ZIP code
    - Overlay: ACS socioeconomic variables (median income, % uninsured, % poverty)
    - Overlay: all-cause mortality rate by ZIP (CA 2019–2024)
    - Filter by CPT code, year, price type
    - Side-by-side CA vs IN comparison
    """)
    st.stop()

# ── load ZIP data (Week 3 implementation) ────────────────────────────────────
@st.cache_data
def load_zip_data():
    path = ZIP_2024 if os.path.exists(ZIP_2024) else ZIP_FILE
    return pd.read_csv(path)

@st.cache_data
def load_census():
    if os.path.exists(CENSUS_ZIP):
        return pd.read_csv(CENSUS_ZIP)
    return None

df_zip    = load_zip_data()
df_census = load_census()

st.success(f"ZIP data loaded: {len(df_zip):,} rows · {df_zip['zip'].nunique() if 'zip' in df_zip.columns else '?'} ZIP codes")

# ── controls ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    cpt_filter = st.text_input("Filter by CPT / procedure code", placeholder="e.g. 99213")
with col2:
    metric = st.selectbox("Price metric", ["Median charge", "Mean charge", "Max charge"])

st.info("🚧 Map rendering (pydeck / folium choropleth) will be wired in during Week 3 once the full ZIP crosswalk is validated.")

# preview table
st.subheader("ZIP data preview")
st.dataframe(df_zip.head(200), use_container_width=True)

if df_census is not None:
    st.subheader("Census ZIP data preview")
    st.dataframe(df_census.head(50), use_container_width=True)
