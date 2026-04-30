"""
Shared DuckDB connection + data path config.
"""

from pathlib import Path

import duckdb
import streamlit as st

# Data directory — parquet files live here
DATA_DIR = Path(__file__).parent.parent / "data"

# Table paths
RATIOS_PQ     = str(DATA_DIR / "ratios_hospital_code.parquet")
RATIOS_SUM_PQ = str(DATA_DIR / "ratios_state_summary.parquet")
PAYER_PQ      = str(DATA_DIR / "ratios_payer_state.parquet")
CROSSWALK_PQ  = str(DATA_DIR / "facilities_crosswalk.parquet")
WANG_HOSP_PQ  = str(DATA_DIR / "wang_per_hospital.parquet")
WANG_SUM_PQ   = str(DATA_DIR / "wang_state_summary.parquet")
CHANG_PQ      = str(DATA_DIR / "chang_psek_zip_panel.parquet")
COMPLIANCE_PQ = str(DATA_DIR / "state_compliance.parquet")


@st.cache_resource
def get_con():
    """Return a shared DuckDB connection (cached across reruns)."""
    con = duckdb.connect(database=":memory:", read_only=False)
    return con


def query(sql: str, **params):
    """Execute a SQL query and return a pandas DataFrame."""
    con = get_con()
    return con.execute(sql).df()
