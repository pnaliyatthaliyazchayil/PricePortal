import streamlit as st
import pandas as pd

st.set_page_config(page_title="Hospital Search · PricePortal", page_icon="🔍", layout="wide")
st.title("🔍 Hospital Search")
st.caption("Look up a hospital and browse all its chargemaster prices.")

con = st.session_state.get("con")
if con is None:
    st.error("Database not initialised — please return to the Home page first.")
    st.stop()

# ── hospital picker ──────────────────────────────────────────────────────────
@st.cache_data
def get_hospital_list():
    return con.execute("""
        SELECT DISTINCT oshpd_id, hospital_folder
        FROM cdm
        ORDER BY hospital_folder
    """).df()

hospitals = get_hospital_list()
hospital_names = hospitals["hospital_folder"].tolist()

selected_name = st.selectbox("Search for a hospital", options=[""] + hospital_names)

if not selected_name:
    st.info("Select a hospital above to explore its prices.")
    st.stop()

oshpd_id = hospitals.loc[hospitals["hospital_folder"] == selected_name, "oshpd_id"].iloc[0]

# ── filters ──────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    years = con.execute(f"""
        SELECT DISTINCT year FROM cdm
        WHERE oshpd_id = '{oshpd_id}' ORDER BY year DESC
    """).df()["year"].tolist()
    selected_year = st.selectbox("Year", options=years)

with col2:
    code_types = con.execute(f"""
        SELECT DISTINCT code_type FROM cdm
        WHERE oshpd_id = '{oshpd_id}' AND year = {selected_year}
        ORDER BY code_type
    """).df()["code_type"].tolist()
    selected_code_type = st.selectbox("Code type", options=["All"] + code_types)

with col3:
    query_text = st.text_input("Filter by description or code", placeholder="e.g. MRI, 99213")

# ── query ────────────────────────────────────────────────────────────────────
code_filter   = f"AND code_type = '{selected_code_type}'" if selected_code_type != "All" else ""
desc_filter   = f"AND (LOWER(description) LIKE '%{query_text.lower()}%' OR LOWER(procedure_code) LIKE '%{query_text.lower()}%')" if query_text else ""

df = con.execute(f"""
    SELECT
        procedure_code  AS "Code",
        code_type       AS "Type",
        description     AS "Description",
        setting         AS "Setting",
        charge          AS "Charge ($)"
    FROM cdm
    WHERE oshpd_id = '{oshpd_id}'
      AND year = {selected_year}
      {code_filter}
      {desc_filter}
    ORDER BY charge DESC
    LIMIT 2000
""").df()

st.markdown(f"### {selected_name} — {selected_year}")
st.caption(f"OSHPD ID: `{oshpd_id}` · Showing up to 2,000 rows")

if df.empty:
    st.warning("No records found for this selection.")
else:
    # summary stats
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Records shown", f"{len(df):,}")
    s2.metric("Median charge", f"${df['Charge ($)'].median():,.0f}")
    s3.metric("Min charge",    f"${df['Charge ($)'].min():,.0f}")
    s4.metric("Max charge",    f"${df['Charge ($)'].max():,.0f}")

    st.dataframe(
        df.style.format({"Charge ($)": "${:,.2f}"}),
        use_container_width=True,
        height=500,
    )

    st.download_button(
        "⬇️ Download CSV",
        data=df.to_csv(index=False),
        file_name=f"{selected_name}_{selected_year}_prices.csv",
        mime="text/csv",
    )
