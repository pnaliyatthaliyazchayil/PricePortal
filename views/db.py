"""
Shared DuckDB connection + data loader.

Data loading priority:
  1. LOCAL: data/ folder in the repo (populated by GitHub Actions weekly sync)
  2. FALLBACK: download directly from Zenodo (first run or if Actions haven't run yet)

This means the app loads instantly when GitHub Actions has run,
and still works on a fresh deploy by falling back to Zenodo.
"""

from pathlib import Path
import urllib.request
import socket
import duckdb
import streamlit as st

# ── Zenodo source ────────────────────────────────────────────────────────────
ZENODO_RECORD = "19941038"
ZENODO_BASE   = f"https://zenodo.org/records/{ZENODO_RECORD}/files"

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

# ── Local data directory (committed by GitHub Actions) ───────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

socket.setdefaulttimeout(120)


def _all_local_present() -> bool:
    """Return True if every parquet file already exists locally."""
    return all(
        (DATA_DIR / local_name).exists() and (DATA_DIR / local_name).stat().st_size > 0
        for local_name in ZENODO_FILES
    )


def _download_file(local_name: str, zenodo_name: str) -> Path:
    """Download a single file from Zenodo if not already present."""
    local_path = DATA_DIR / local_name
    if local_path.exists() and local_path.stat().st_size > 0:
        return local_path
    url = f"{ZENODO_BASE}/{zenodo_name}?download=1"
    tmp_path = local_path.with_suffix(local_path.suffix + ".tmp")
    urllib.request.urlretrieve(url, tmp_path)
    tmp_path.rename(local_path)
    return local_path


@st.cache_resource(show_spinner=False)
def ensure_data_cached() -> dict:
    """
    Return local paths for all parquet files.
    If already present locally (GitHub Actions ran), returns instantly.
    Otherwise downloads from Zenodo with a progress bar.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Fast path — files already committed to repo by GitHub Actions
    if _all_local_present():
        return {name: DATA_DIR / name for name in ZENODO_FILES}

    # Slow path — first deploy or Actions haven't run yet; download from Zenodo
    paths = {}
    total = len(ZENODO_FILES)
    done  = 0
    progress = st.progress(0.0, text="First-time setup: downloading data from Zenodo (~47 MB)…")

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {
            ex.submit(_download_file, local, zen): local
            for local, zen in ZENODO_FILES.items()
        }
        for fut in as_completed(futures):
            local = futures[fut]
            try:
                paths[local] = fut.result()
            except Exception as e:
                progress.empty()
                st.error(f"❌ Failed to download {local} from Zenodo: {e}")
                st.stop()
            done += 1
            progress.progress(done / total, text=f"Downloading from Zenodo… {done}/{total} files")

    progress.empty()
    return {name: DATA_DIR / name for name in ZENODO_FILES}


# ── Resolve paths ─────────────────────────────────────────────────────────────
def _get_paths() -> dict:
    if "_zenodo_paths" not in st.session_state:
        st.session_state._zenodo_paths = ensure_data_cached()
    return st.session_state._zenodo_paths


def _p(name: str) -> str:
    return str(_get_paths()[name])


# ── Public path constants ────────────────────────────────────────────────────
RATIOS_PQ      = str(DATA_DIR / "ratios_hospital_code.parquet")
RATIOS_SUM_PQ  = str(DATA_DIR / "ratios_state_summary.parquet")
PAYER_PQ       = str(DATA_DIR / "ratios_payer_state.parquet")
CROSSWALK_PQ   = str(DATA_DIR / "facilities_crosswalk.parquet")
WANG_HOSP_PQ   = str(DATA_DIR / "wang_per_hospital.parquet")
WANG_SUM_PQ    = str(DATA_DIR / "wang_state_summary.parquet")
CHANG_PQ       = str(DATA_DIR / "chang_psek_zip_panel.parquet")
COMPLIANCE_PQ  = str(DATA_DIR / "state_compliance.parquet")
CENTROIDS_CSV  = DATA_DIR / "zip_centroids.csv"

RATIOS_PQ_PARTS = [RATIOS_PQ]


# ── DuckDB connection ────────────────────────────────────────────────────────
@st.cache_resource
def get_con():
    """Return a shared in-memory DuckDB connection."""
    ensure_data_cached()   # make sure files exist before querying
    con = duckdb.connect(database=":memory:", read_only=False)
    con.execute(f"CREATE VIEW ratios AS SELECT * FROM '{RATIOS_PQ}'")
    return con


def query(sql: str, **_) -> "pd.DataFrame":
    """Execute SQL and return a pandas DataFrame."""
    return get_con().execute(sql).df()
