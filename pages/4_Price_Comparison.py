import streamlit as st
import pandas as pd

st.set_page_config(page_title="Price Comparison · PricePortal", page_icon="📊", layout="wide")
st.title("📊 Four-Price-Type Comparison")
st.caption("Compare chargemaster, cash, minimum negotiated, and Medicare allowable for a given procedure.")

con = st.session_state.get("con")
if con is None:
    st.error("Database not initialised — please return to the Home page first.")
    st.stop()

# ── note on data availability ────────────────────────────────────────────────
st.info(
    "**Currently showing**: Chargemaster (gross) prices from the CA HCAI corpus.  \n"
    "**Coming in Week 3**: Cash, minimum-negotiated, and Medicare allowable prices "
    "from the federal HPT MRF pipeline (CA + IN)."
)

# ── controls ─────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    cpt_query = st.text_input("CPT code or description", placeholder="e.g. 99213, appendectomy")
with col2:
    year = st.selectbox("Year", options=list(range(2025, 2013, -1)), index=0)
with col3:
    top_n = st.slider("Number of hospitals", min_value=5, max_value=50, value=20)

if not cpt_query:
    st.info("Enter a CPT code or description to start comparing.")
    st.stop()

# ── chargemaster prices ───────────────────────────────────────────────────────
df_cdm = con.execute(f"""
    SELECT
        hospital_folder     AS hospital,
        procedure_code      AS code,
        description,
        MEDIAN(charge)      AS chargemaster
    FROM cdm
    WHERE year = {year}
      AND (
          LOWER(description)       LIKE '%{cpt_query.lower()}%'
          OR LOWER(procedure_code) LIKE '%{cpt_query.lower()}%'
      )
    GROUP BY hospital_folder, procedure_code, description
    ORDER BY chargemaster DESC
    LIMIT {top_n}
""").df()

if df_cdm.empty:
    st.warning(f"No chargemaster records found for **{cpt_query}** in {year}.")
    st.stop()

st.markdown(f"### {cpt_query} — {year} · Top {len(df_cdm)} hospitals by chargemaster price")

# ── placeholder columns for future price types ────────────────────────────────
df_display = df_cdm.copy()
df_display["cash"]        = "— (MRF, Week 3)"
df_display["negotiated"]  = "— (MRF, Week 3)"
df_display["medicare"]    = "— (MPFS, Week 3)"
df_display.columns       = ["Hospital", "Code", "Description", "Chargemaster ($)", "Cash ($)", "Min Negotiated ($)", "Medicare ($)"]

st.dataframe(
    df_display.style.format({"Chargemaster ($)": "${:,.0f}"}),
    use_container_width=True,
    height=500,
)

# ── chargemaster bar chart ────────────────────────────────────────────────────
st.subheader("Chargemaster price by hospital")
st.bar_chart(df_cdm.set_index("hospital")["chargemaster"])

# ── ratios (placeholder) ──────────────────────────────────────────────────────
st.subheader("Price-type ratios (chargemaster ÷ Medicare etc.)")
st.info("🚧 Ratio analysis will be populated in Week 3 once the MRF and Medicare benchmark parquets are joined.")

st.download_button(
    "⬇️ Download CSV",
    data=df_display.to_csv(index=False),
    file_name=f"price_comparison_{cpt_query}_{year}.csv",
    mime="text/csv",
)
