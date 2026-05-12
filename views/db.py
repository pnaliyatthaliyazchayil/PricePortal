"""
Shared DuckDB connection + Zenodo data loader.

On first run, downloads ~47 MB of analysis-grade parquet files from
the Zenodo deposit (DOI 10.5281/zenodo.19941038) into a local cache.
Subsequent runs use the cached files.
"""

from pathlib import Path
import urllib.request
import socket
import duckdb
import streamlit as st

# ── Zenodo source ────────────────────────────────────────────────────────────
ZENODO_RECORD = "19941038"
ZENODO_BASE   = f"https://zenodo.org/records/{ZENODO_RECORD}/files"

# Map: local_filename -> Zenodo filename
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

# socket-level timeout so a hung download can't freeze the app forever
socket.setdefaulttimeout(120)


def _download_file(local_name: str, zenodo_name: str) -> Path:
    """Download a single file from Zenodo if not already cached."""
    local_path = CACHE_DIR / local_name
    if local_path.exists() and local_path.stat().st_size > 0:
        return local_path

    url = f"{ZENODO_BASE}/{zenodo_name}?download=1"
    tmp_path = local_path.with_suffix(local_path.suffix + ".tmp")
    urllib.request.urlretrieve(url, tmp_path)
    tmp_path.rename(local_path)
    return local_path

@st.cache_resource(show_spinner=False)
def ensure_data_cached() -> dict:
    """Download all needed parquet files from Zenodo in parallel."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    paths = {}
    progress = st.progress(0.0, text="Downloading analysis files from Zenodo (one-time)…")
    total = len(ZENODO_FILES)
    done = 0
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
                st.error(f"❌ Failed to download {local}: {e}")
                st.stop()
            done += 1
            progress.progress(done / total, text=f"Downloaded {done}/{total} files")
    progress.empty()
    return paths
    return paths


def _get_paths() -> dict:
    """Lazy accessor — resolves to local Path objects, cached."""
    if "_zenodo_paths" not in st.session_state:
        st.session_state._zenodo_paths = ensure_data_cached()
    return st.session_state._zenodo_paths


# ── Path accessors (lazy) ────────────────────────────────────────────────────
def _path(name: str) -> str:
    return str(_get_paths()[name])


# Module-level "constants" become callables that resolve on first access.
# Views import these names; they're strings now (resolved on import).
# To preserve that interface, we resolve once at module load if cache exists,
# else use a sentinel that the view code can call.
def _try_resolve():
    """Try to resolve all paths from cache without triggering download."""
    paths = {}
    for local_name in ZENODO_FILES:
        p = CACHE_DIR / local_name
        if p.exists() and p.stat().st_size > 0:
            paths[local_name] = str(p)
        else:
            return None
    return paths


_cached = _try_resolve()
if _cached:
    RATIOS_PQ      = _cached["ratios_hospital_code.parquet"]
    RATIOS_SUM_PQ  = _cached["ratios_state_summary.parquet"]
    PAYER_PQ       = _cached["ratios_payer_state.parquet"]
    CROSSWALK_PQ   = _cached["facilities_crosswalk.parquet"]
    WANG_HOSP_PQ   = _cached["wang_per_hospital.parquet"]
    WANG_SUM_PQ    = _cached["wang_state_summary.parquet"]
    CHANG_PQ       = _cached["chang_psek_zip_panel.parquet"]
    COMPLIANCE_PQ  = _cached["state_compliance.parquet"]
else:
    # Files not yet downloaded — placeholders that resolve on first DB call
    RATIOS_PQ      = str(CACHE_DIR / "ratios_hospital_code.parquet")
    RATIOS_SUM_PQ  = str(CACHE_DIR / "ratios_state_summary.parquet")
    PAYER_PQ       = str(CACHE_DIR / "ratios_payer_state.parquet")
    CROSSWALK_PQ   = str(CACHE_DIR / "facilities_crosswalk.parquet")
    WANG_HOSP_PQ   = str(CACHE_DIR / "wang_per_hospital.parquet")
    WANG_SUM_PQ    = str(CACHE_DIR / "wang_state_summary.parquet")
    CHANG_PQ       = str(CACHE_DIR / "chang_psek_zip_panel.parquet")
    COMPLIANCE_PQ  = str(CACHE_DIR / "state_compliance.parquet")

# zip_centroids.csv stays local in the repo (not on Zenodo)
CENTROIDS_CSV = Path(__file__).parent.parent / "data" / "zip_centroids.csv"

# Backward-compat: views expect a list of split ratio files
RATIOS_PQ_PARTS = [RATIOS_PQ]


# ── DuckDB connection ────────────────────────────────────────────────────────
@st.cache_resource
def get_con():
    """Return a shared DuckDB connection. Triggers Zenodo download if needed."""
    # Ensure files are cached before any query runs
    _get_paths()
    con = duckdb.connect(database=":memory:", read_only=False)
    con.execute(f"CREATE VIEW ratios AS SELECT * FROM '{RATIOS_PQ}'")
    return con


def query(sql: str, **params):
    """Execute a SQL query and return a pandas DataFrame."""
    con = get_con()
    return con.execute(sql).df()
