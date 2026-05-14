"""
Download analysis-grade parquet files from Zenodo into data/.
Run by GitHub Actions on schedule or manually.
Only downloads files that have changed (checks file size).
"""

import os
import sys
import requests
from pathlib import Path

ZENODO_RECORD = "19941038"
ZENODO_BASE   = f"https://zenodo.org/records/{ZENODO_RECORD}/files"

# Map: local filename -> Zenodo filename
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

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def download_file(local_name: str, zenodo_name: str) -> bool:
    """Download file from Zenodo. Returns True if file was updated."""
    url = f"{ZENODO_BASE}/{zenodo_name}?download=1"
    local_path = DATA_DIR / local_name

    print(f"  Checking {zenodo_name}...")

    # Stream download to check size first
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    remote_size = int(response.headers.get("content-length", 0))
    local_size  = local_path.stat().st_size if local_path.exists() else 0

    if remote_size > 0 and local_size == remote_size:
        print(f"  ✓ {local_name} unchanged ({local_size:,} bytes), skipping")
        return False

    print(f"  ↓ Downloading {local_name} ({remote_size/1024/1024:.1f} MB)...")
    tmp_path = local_path.with_suffix(local_path.suffix + ".tmp")
    with open(tmp_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
    tmp_path.rename(local_path)
    print(f"  ✓ Saved {local_name} ({local_path.stat().st_size:,} bytes)")
    return True


def main():
    print(f"Syncing {len(ZENODO_FILES)} files from Zenodo record {ZENODO_RECORD}...")
    updated = 0
    errors  = 0

    for local_name, zenodo_name in ZENODO_FILES.items():
        try:
            if download_file(local_name, zenodo_name):
                updated += 1
        except Exception as e:
            print(f"  ✗ ERROR downloading {zenodo_name}: {e}")
            errors += 1

    print(f"\nDone: {updated} updated, {len(ZENODO_FILES) - updated - errors} unchanged, {errors} errors")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
