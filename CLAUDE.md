# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Portfolio data science project analyzing the [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (100k orders, 3k sellers) plus the [Marketing Funnel dataset](https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist) (MQLs, closed deals). The project has three analytical axes described in the README:

1. **Lead scoring** — XGBoost model classifying which MQLs are worth pursuing (planned: `notebooks/02_lead_scoring.ipynb` + `models/xgb_lead_scoring.pkl`).
2. **Seller segmentation** — PCA + K-Means over seller behavior features (planned: `notebooks/03_seller_segmentation.ipynb`).
3. **Geospatial logistics impact** — Haversine distance between seller/customer zip codes, correlated with freight cost and review score.

Current state: EDA is done (`notebooks/EDA_1.ipynb`); the reusable ETL (`src/data.py`) exists but the notebooks haven't been migrated to use it yet (see Architecture below). Models 1 and 2, the BigQuery migration, and the Streamlit dashboard are not started (see README Roadmap).

## Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Download raw CSVs from Kaggle into data/ (requires ~/.kaggle/kaggle.json)
python src/download_data.py

# Run the ETL standalone (writes data/processed/*.parquet)
python src/data.py

# Work in notebooks
jupyter lab
```

There is no test suite, linter, or formatter configured in this repo — don't invent lint/test commands.

## Architecture

**Data flow:** `src/download_data.py` pulls both Kaggle datasets into `data/*.csv` (git-ignored, 11 CSVs total). `src/data.py` is the reusable ETL: `load_raw_tables()` reads all 11 raw CSVs, `aggregate_geolocation()` collapses the ~1M-row geolocation table to one row per zip prefix, then `build_order_items()` joins orders/customers/sellers/products/payments/reviews into one row-per-order-item table (`order_items_full`) and computes `distance_km` (haversine, via `haversine_distance()`) between each order's customer and seller coordinates. `build_seller_features()` aggregates `order_items_full` into one row-per-seller table (`seller_features`), including `avg_distance_km`. `build_datasets()` runs the full pipeline and saves both outputs as parquet to `data/processed/`.

**Notebook path convention:** the kernel's working directory for a notebook is *not* consistent across tools — classic Jupyter Lab/Notebook sets it to the notebook's own folder (`notebooks/`), while VS Code's Jupyter extension defaults to the workspace root (the folder opened in the editor). `notebooks/EDA_1.ipynb` handles both by probing at runtime: `base_path = 'data' if os.path.isdir('data') else '../data'`. Follow this pattern (don't hardcode `'../data'`) in any new notebook that reads raw CSVs directly. `src/data.py` and `src/download_data.py` sidestep the issue entirely by resolving the data dir absolutely via `Path(__file__).resolve().parents[1] / "data"`.

**`notebooks/EDA_1.ipynb`** currently loads the 11 raw CSVs directly with its own `pd.read_csv` calls (duplicating what `src/data.py` does) rather than importing `build_datasets()` from `src.data`. It's a long, narrative, sequentially-numbered EDA notebook (sections 1–11: sellers/buyers by state, payment methods, freight vs. price, delivery time and logistics analysis, etc.) — when extending it, follow the existing numbered-section style (`### N.M Título`) rather than restructuring it.

**Data model:** raw tables join on `order_id` (orders/items/payments/reviews), `customer_id`/`seller_id` (→ zip code prefix → geolocation), and `product_id` (→ category, translated PT→EN via `product_category_name_translation.csv`). A single order can have multiple payments (installments/vouchers) and multiple reviews (repeat purchase) — both are pre-aggregated to one row per `order_id` before joining (see `_aggregate_payments`, `_aggregate_reviews` in `src/data.py`) to avoid fanning out `order_items_full`.

See `reports/figures/data_model.png` for the entity-relationship diagram referenced in the README.
