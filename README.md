# PricePortal — Streamlit App

Open hospital price transparency portal for California & Indiana.

## Structure

```
priceportal/
├── app.py                          # Home page + shared DuckDB connection
├── pages/
│   ├── 1_🔍_Hospital_Search.py     # Hospital lookup + price browser
│   ├── 2_💊_CPT_DRG_Search.py      # Procedure search across hospitals
│   ├── 3_🗺️_ZIP_Map.py             # ZIP-level map (Week 3)
│   └── 4_📊_Price_Comparison.py    # Four-price-type comparison (Week 3)
├── requirements.txt
└── README.md
```

## Data dependencies

| File | Status |
|---|---|
| `/data0/hcai-chargemasters/ingest/cdm_all.parquet` | ✅ Ready |
| `/data0/hcai-chargemasters/ingest/matched_rows_with_zip_all.csv` | ✅ Ready (ZIP map page auto-detects) |
| MRF parquets (cash, negotiated) | 🚧 Week 2 pipeline |
| Medicare allowable parquet | 🚧 Week 2 pipeline |

## Running on the IU server

### 1. Install dependencies (first time only)
```bash
pip install -r requirements.txt
```

### 2. Start the app on the server
```bash
cd ~/chargemaster
streamlit run app.py --server.port 8501 --server.headless true
```

### 3. On your LOCAL Windows laptop — open a new terminal and run:
```bash
ssh -L 8501:localhost:8501 yournetid@plhi.uits.iu.edu
```
Keep this terminal open.

### 4. Open your browser at:
```
http://localhost:8501
```

## Adding Week 3 features

- **ZIP map**: populate `pages/3_🗺️_ZIP_Map.py` — the data-loading scaffold is already there
- **MRF prices**: add `mrf_cash.parquet`, `mrf_negotiated.parquet`, `medicare_allowable.parquet` to `/data0/hcai-chargemasters/ingest/` and register them as views in `app.py`
- **Ratio analysis**: wire into `pages/4_📊_Price_Comparison.py` — stubs are already marked with 🚧
