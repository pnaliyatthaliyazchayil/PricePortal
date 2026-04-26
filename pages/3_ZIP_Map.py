import streamlit as st
import pandas as pd
import json
import urllib.request
 
st.set_page_config(page_title="ZIP Map · PricePortal", page_icon="🗺️", layout="wide")
st.title("🗺️ ZIP-Level Price Map")
st.caption("Median chargemaster price by ZIP code — California & Indiana")
 
con = st.session_state.get("con")
if con is None:
    st.error("Database not initialised — please return to the Home page first.")
    st.stop()
 
# ── load ZIP aggregated data ─────────────────────────────────────────────────
import os
 
IU_ZIP = "/data0/hcai-chargemasters/ingest/matched_rows_with_zip_2024.csv"
SAMPLE_ZIP = os.path.join(os.path.dirname(__file__), "data", "sample_zip.csv")
 
@st.cache_data
def load_zip_data():
    if os.path.exists(IU_ZIP):
        df = pd.read_csv(IU_ZIP)
        return df, "full"
    elif os.path.exists(SAMPLE_ZIP):
        df = pd.read_csv(SAMPLE_ZIP)
        return df, "sample"
    return None, "none"
 
df_zip, zip_mode = load_zip_data()
 
if zip_mode == "none":
    st.warning("ZIP data not available yet.")
    st.stop()
elif zip_mode == "sample":
    st.warning("⚠️ Demo mode — showing sample ZIP data.")
 
# ── controls ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    cpt_filter = st.text_input("Filter by procedure code or description", placeholder="e.g. 99213, MRI")
with col2:
    metric = st.selectbox("Price metric", ["Median", "Mean", "Max", "Min"])
 
# ── aggregate by ZIP ─────────────────────────────────────────────────────────
df_filtered = df_zip.copy()
if cpt_filter:
    mask = (
        df_filtered["procedure_code"].astype(str).str.contains(cpt_filter, case=False, na=False) |
        df_filtered["description"].astype(str).str.contains(cpt_filter, case=False, na=False)
    )
    df_filtered = df_filtered[mask]
 
if df_filtered.empty:
    st.warning("No records match that filter.")
    st.stop()
 
agg_func = {"Median": "median", "Mean": "mean", "Max": "max", "Min": "min"}[metric]
zip_agg = (
    df_filtered.groupby("zip")["charge_numeric"]
    .agg(agg_func)
    .reset_index()
    .rename(columns={"charge_numeric": "price"})
)
zip_agg["zip"] = zip_agg["zip"].astype(str).str.zfill(5)
 
st.markdown(f"### {metric} chargemaster price by ZIP — {len(zip_agg)} ZIP codes")
 
# ── summary stats ────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("ZIP codes",    f"{len(zip_agg):,}")
c2.metric("Median price", f"${zip_agg['price'].median():,.0f}")
c3.metric("Min price",    f"${zip_agg['price'].min():,.0f}")
c4.metric("Max price",    f"${zip_agg['price'].max():,.0f}")
 
# ── map via pydeck ───────────────────────────────────────────────────────────
try:
    import pydeck as pdk
 
    # merge zip_agg with lat/lon from the original data if available
    if "latitude" in df_zip.columns and "longitude" in df_zip.columns:
        coords = df_zip.groupby("zip")[["latitude","longitude"]].mean().reset_index()
        coords["zip"] = coords["zip"].astype(str).str.zfill(5)
        map_df = zip_agg.merge(coords, on="zip", how="inner")
    else:
        st.info("📍 Map rendering requires latitude/longitude columns in the ZIP data. Showing table instead.")
        map_df = pd.DataFrame()
 
    if not map_df.empty:
        max_price = map_df["price"].max()
        map_df["radius"] = (map_df["price"] / max_price * 20000).clip(lower=2000)
        map_df["color_r"] = ((map_df["price"] / max_price) * 255).astype(int)
        map_df["color_g"] = (50).astype(int)
        map_df["color_b"] = ((1 - map_df["price"] / max_price) * 200).astype(int)
 
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_df,
            get_position=["longitude", "latitude"],
            get_radius="radius",
            get_fill_color=["color_r", "color_g", "color_b", 160],
            pickable=True,
        )
 
        view = pdk.ViewState(latitude=36.5, longitude=-119.5, zoom=5)
        st.pydeck_chart(pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            tooltip={"text": "ZIP: {zip}\nPrice: ${price}"},
        ))
 
except ImportError:
    st.info("Install pydeck for map rendering: `pip install pydeck`")
 
# ── table view ───────────────────────────────────────────────────────────────
st.subheader("ZIP-level price table")
 
display_df = zip_agg.copy()
if "county" in df_filtered.columns:
    county_map = df_filtered.groupby("zip")["county"].first().reset_index()
    county_map["zip"] = county_map["zip"].astype(str).str.zfill(5)
    display_df = display_df.merge(county_map, on="zip", how="left")
 
display_df.columns = [c.title() for c in display_df.columns]
st.dataframe(
    display_df.sort_values("Price", ascending=False),
    use_container_width=True,
    height=400,
)
 
st.download_button(
    "⬇️ Download ZIP price table",
    data=display_df.to_csv(index=False),
    file_name="zip_prices_2024.csv",
    mime="text/csv",
)
 
# ── placeholder note ─────────────────────────────────────────────────────────
st.markdown("---")
st.info(
    "🚧 **Coming Week 3**: Choropleth shading by ZIP boundary polygons, "
    "ACS socioeconomic overlays (median income, % uninsured), "
    "all-cause mortality overlay, CA vs IN side-by-side view."
)
