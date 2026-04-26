import streamlit as st
import pandas as pd

st.set_page_config(page_title="CPT / DRG Search · PricePortal", page_icon="💊", layout="wide")
st.title("💊 CPT / DRG Search")
st.caption("Find a procedure code and compare chargemaster prices across hospitals.")

con = st.session_state.get("con")
if con is None:
    st.error("Database not initialised — please return to the Home page first.")
    st.stop()

# ── search bar ───────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    query_text = st.text_input(
        "Search by CPT code or description",
        placeholder="e.g. 99213, appendectomy, MRI brain"
    )
with col2:
    selected_year = st.selectbox(
        "Year",
        options=list(range(2025, 2013, -1)),
        index=0,
    )

if not query_text:
    st.info("Enter a CPT code or procedure description to search across all hospitals.")
    st.stop()

# ── query: match codes / descriptions ────────────────────────────────────────
df = con.execute(f"""
    SELECT
        procedure_code          AS "Code",
        code_type               AS "Type",
        description             AS "Description",
        hospital_folder         AS "Hospital",
        oshpd_id                AS "OSHPD ID",
        setting                 AS "Setting",
        charge                  AS "Charge ($)",
        year                    AS "Year"
    FROM cdm
    WHERE year = {selected_year}
      AND (
          LOWER(description)    LIKE '%{query_text.lower()}%'
          OR LOWER(procedure_code) LIKE '%{query_text.lower()}%'
      )
    ORDER BY charge DESC
    LIMIT 3000
""").df()

if df.empty:
    st.warning(f"No results for **{query_text}** in {selected_year}. Try a different year or search term.")
    st.stop()

st.markdown(f"### Results for **{query_text}** — {selected_year}")
st.caption(f"{len(df):,} records across {df['Hospital'].nunique()} hospitals")

# ── summary across hospitals ─────────────────────────────────────────────────
st.subheader("Price distribution across hospitals")
summary = df.groupby("Hospital")["Charge ($)"].median().sort_values(ascending=False).reset_index()
summary.columns = ["Hospital", "Median Charge ($)"]

st.bar_chart(summary.set_index("Hospital").head(30))

# ── full table ───────────────────────────────────────────────────────────────
st.subheader("All matching records")

# filter to specific code if multiple came back
codes_found = df["Code"].unique().tolist()
if len(codes_found) > 1:
    selected_code = st.selectbox("Narrow to specific code", options=["All"] + sorted(codes_found))
    if selected_code != "All":
        df = df[df["Code"] == selected_code]

st.dataframe(
    df.style.format({"Charge ($)": "${:,.2f}"}),
    use_container_width=True,
    height=500,
)

st.download_button(
    "⬇️ Download CSV",
    data=df.to_csv(index=False),
    file_name=f"cpt_search_{query_text}_{selected_year}.csv",
    mime="text/csv",
)
