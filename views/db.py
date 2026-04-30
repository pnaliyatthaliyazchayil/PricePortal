"""
Shared DuckDB connection + data path config.
"""

from pathlib import Path

import duckdb
import streamlit as st

# Data directory — parquet files live here
DATA_DIR = Path(__file__).parent.parent / "data"

# Table paths — ratios split into 3 files to stay under GitHub 25 MB limit
RATIOS_PQ_PARTS = [
    str(DATA_DIR / "ratios_hospital_code_CA1.parquet"),
    str(DATA_DIR / "ratios_hospital_code_CA2.parquet"),
    str(DATA_DIR / "ratios_hospital_code_IN.parquet"),
]
RATIOS_SUM_PQ = str(DATA_DIR / "ratios_state_summary.parquet")
PAYER_PQ      = str(DATA_DIR / "ratios_payer_state.parquet")
CROSSWALK_PQ  = str(DATA_DIR / "facilities_crosswalk.parquet")
WANG_HOSP_PQ  = str(DATA_DIR / "wang_per_hospital.parquet")
WANG_SUM_PQ   = str(DATA_DIR / "wang_state_summary.parquet")
CHANG_PQ      = str(DATA_DIR / "chang_psek_zip_panel.parquet")
COMPLIANCE_PQ = str(DATA_DIR / "state_compliance.parquet")

# Build a DuckDB-friendly glob/union expression for the split ratio files
RATIOS_PQ = "(" + " UNION ALL ".join(
    f"SELECT * FROM '{p}'" for p in RATIOS_PQ_PARTS
) + ")"


@st.cache_resource
def get_con():
    """Return a shared DuckDB connection (cached across reruns)."""
    con = duckdb.connect(database=":memory:", read_only=False)
    # Register the split ratio files as a single view for convenience
    con.execute(f"""
        CREATE VIEW ratios AS
        {' UNION ALL '.join(f"SELECT * FROM '{p}'" for p in RATIOS_PQ_PARTS)}
    """)
    return con


def query(sql: str, **params):
    """Execute a SQL query and return a pandas DataFrame."""
    con = get_con()
    return con.execute(sql).df()
