# PRICEPORTAL — Streamlit App

Open hospital price transparency portal for California & Indiana.
Live: https://pricingapp.streamlit.app/

This app sits over the analytic outputs of the
[mrf-pricing-research](https://github.com/sunbiz/mrf-pricing-research)
pipeline (528-hospital CA + IN universe, four price types: chargemaster /
cash / negotiated / Medicare-allowable). All parquet inputs are bundled
under `data/` so the app deploys to Streamlit Community Cloud with no
external data dependencies.

## Structure

```
priceportal/
├── app.py                       # Sidebar nav + shared page styling
├── views/
│   ├── db.py                    # Cached DuckDB connection + parquet paths
│   ├── overview.py              # Headline stats + state comparison
│   ├── hospital_search.py       # Hospital lookup + 4-price profile
│   ├── code_search.py           # CPT/HCPCS lookup across hospitals
│   ├── zip_map.py               # ZIP bubble map + socioeconomic gradients
│   ├── wang_replication.py      # Wang 2023 within-hospital correlations
│   └── payer_analysis.py        # Negotiated rate × payer × state
├── data/                        # Bundled parquets (split to fit GitHub 25 MB cap)
├── requirements.txt
├── packages.txt
└── .devcontainer/
```

## Bundled data

| File | Contents |
|---|---|
| `data/ratios_hospital_code_{CA1,CA2,IN}.parquet` | 1.55 M hospital × code rows with gross / cash / neg_min / neg_median ratios; split into 3 files to stay under the 25 MB GitHub blob limit |
| `data/ratios_state_summary.parquet` | Per-state × price-type quantiles |
| `data/ratios_payer_state.parquet` | Per-payer × state median / IQR |
| `data/state_compliance.parquet` | CMS §180 participation rates |
| `data/facilities_crosswalk.parquet` | 528-hospital identity crosswalk (CCN, OSHPD, EIN, NPI) |
| `data/wang_per_hospital.parquet` | Per-hospital Pearson r (gross↔cash, gross↔negmin, cash↔negmin) |
| `data/wang_state_summary.parquet` | Median correlations × state × discounter segment |
| `data/chang_psek_zip_panel.parquet` | 259 hospital ZIPs × ratios + ACS demographics |
| `data/zip_centroids.csv` | ZIP → lat/lon (Census 2024 ZCTA Gazetteer; 259 rows) |

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Community Cloud

Push to GitHub, then point a new Streamlit Cloud app at `app.py`.
`requirements.txt` covers Python deps and `packages.txt` covers any
apt packages (currently empty).

## Tunneling from a remote host

If running on the IU server:

```bash
# On server
streamlit run app.py --server.port 8501 --server.headless true
# On local laptop
ssh -L 8501:localhost:8501 yournetid@plhi.uits.iu.edu
```
Then open http://localhost:8501.
