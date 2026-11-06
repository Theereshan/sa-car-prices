# 🚗 SA Used-Car Price Predictor

Predicting fair market prices for used cars in South Africa, and analysing what drives them: depreciation by brand, the diesel premium, mileage and regional differences.

> **Status:** Phase 1 (data pipeline) ✅ · Phase 2 (EDA) 🚧

## The problem
Used-car prices in SA vary widely for similar vehicles. Buyers can't easily tell whether a listing is fair, and sellers price by guesswork. This project builds a model that estimates a car's market value from its specs and explains *why* it's priced that way.

## Architecture
```
 sources (scrapers / CSV datasets)
            │  src/collect/
            ▼
 raw_listings      ← untouched, text-typed, idempotent inserts
            │  src/data/clean.py
            ▼
 listings_clean    ← typed, normalised, filtered, de-duplicated
            │
            ▼
 notebooks (EDA → features → models) → model → API
```
Raw and clean layers are kept separate on purpose: cleaning rules change constantly, and the raw data can always be re-cleaned.

## Quick start
```bash
# 1. Environment
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# 2. Database (Postgres in Docker; schema is applied automatically)
docker compose up -d

# 3. Load data: synthetic sample for development
python scripts/make_sample_data.py --rows 5000
python -m src.collect.import_csv data/raw/sample_listings.csv --source synthetic

# 4. Clean
python -m src.data.clean

# 5. Explore
jupyter lab notebooks/01_eda.ipynb

# Tests
pytest
```

## Getting real data
- **Public datasets:** `python -m src.collect.import_csv <file> --source <name> --mapping <cols.json>`
- **Scraping:** copy `src/collect/sources/template_site.py` and fill in the selectors. The base class handles robots.txt, rate limiting, retries and de-duplication. **Check the site's Terms of Service first**; if scraping is not allowed, don't scrape that site.

## Roadmap
- [x] **1. Data pipeline:** schema, collectors, cleaning with tests
- [ ] **2. EDA:** distributions, depreciation curves, categorical effects
- [ ] **3. Features:** age, km/year, brand tier, target encoding of model
- [ ] **4. Models:** linear baseline → XGBoost, cross-validated (MAE, MAPE)
- [ ] **5. Explainability:** SHAP: "why is this car R180k?"
- [ ] **6. Serving:** FastAPI `/predict` plus a simple frontend: "fair price / good deal / overpriced"

## Results
_Coming in Phase 4._

## Project structure
```
sql/            schema + analysis queries
src/collect/    data collection (CSV import, polite scraper framework)
src/data/       cleaning pipeline
scripts/        utilities (synthetic data generator)
notebooks/      analysis, numbered in order
tests/          unit tests for cleaning rules
```
