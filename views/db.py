"""
Shared DuckDB connection + Zenodo data loader.

On first run, downloads ~47 MB of analysis-grade parquet files from
the Zenodo deposit (DOI 10.5281/zenodo.19941038) into a local cache.
Subsequent runs use the cached files. The 6+ GB raw MRF parquets are
NOT downloaded — only the pre-aggregated analysis files the app needs.
"""

from pathlib import Path
import urllib.request
import duckdb
import streamlit as st

# ── Zenodo source ────────────────────────────────────────────────────────────
ZENODO_RECORD = "19941038"
ZENODO_BASE   = f"https://zenodo.org/records/{ZENODO_RECORD}/files"

# Map: local_filename -> Zenodo filename
# Local names match what the views already expect; Zenodo names have prefixes
ZENODO_FILES = {
    "ratios_hospital_code.parquet"   : "analysis__ratios_hospital_code.parquet",
    "ratios_state_summary.parquet"   : "analysis__ratios_state_summary.parquet",
    "ratios_payer_state.parquet"     : "analysis__ratios_payer_state.parquet",
    "facilities_crosswalk.parquet"   : "crosswalk__facilities_crosswalk.parquet",
    "wang_per_hospital.parquet"      : "analysis__wang_per_hospital.parquet",
    "wang_state_summary.parquet"     : "analysis__wang_state_summary.parquet",
    "chang_psek_zip_panel.parquet"   : "analysis__chang_psek_zip_panel.parquet",
    "state_compliance.parquet"       : "analysis__state_compliance.parquet",
}

# ── Local cache directory ────────────────────────────────────────────────────
CACHE_DIR = Path(__file__).parent.parent / "data"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _download_file(local_name: str, zenodo_name: str) -> Path:
    """Download a single file from Zenodo if not already cached."""
    local_path = CACHE_DIR / local_name
    if local_path.exists() and local_path.stat().st_size > 0:
        return local_path

    url = f"{ZENODO_BASE}/{zenodo_name}?download=1"
    try:
        urllib.request.urlretrieve(url, local_path)
    except Exception as e:
        st.error(f"Failed to download {zenodo_name} from Zenodo: {e}")
        raise
    return local_path


@st.cache_resource(show_spinner="Downloading analysis files from Zenodo (one-time, ~47 MB)…")
def ensure_data_cached() -> dict:
    """Download all needed parquet files from Zenodo. Returns local paths."""
    paths = {}
    for local_name, zenodo_name in ZENODO_FILES.items():
        paths[local_name] = _download_file(local_name, zenodo_name)
    return paths


# ── Public path constants — same names the views already use ─────────────────
_paths = ensure_data_cached()

RATIOS_PQ      = str(_paths["ratios_hospital_code.parquet"])
RATIOS_SUM_PQ  = str(_paths["ratios_state_summary.parquet"])
PAYER_PQ       = str(_paths["ratios_payer_state.parquet"])
CROSSWALK_PQ   = str(_paths["facilities_crosswalk.parquet"])
WANG_HOSP_PQ   = str(_paths["wang_per_hospital.parquet"])
WANG_SUM_PQ    = str(_paths["wang_state_summary.parquet"])
CHANG_PQ       = str(_paths["chang_psek_zip_panel.parquet"])
COMPLIANCE_PQ  = str(_paths["state_compliance.parquet"])

# zip_centroids.csv stays local in the repo (not on Zenodo)
CENTROIDS_CSV = Path(__file__).parent.parent / "data" / "zip_centroids.csv"

# Backward-compat: old code expected a list of split ratio files
RATIOS_PQ_PARTS = [RATIOS_PQ]


# ── DuckDB connection ────────────────────────────────────────────────────────
@st.cache_resource
def get_con():
    """Return a shared DuckDB connection (cached across reruns)."""
    con = duckdb.connect(database=":memory:", read_only=False)
    con.execute(f"CREATE VIEW ratios AS SELECT * FROM '{RATIOS_PQ}'")
    return con


def query(sql: str, **params):
    """Execute a SQL query and return a pandas DataFrame."""
    con = get_con()
    return con.execute(sql).df()
