# NovaMart Customer 360 & Revenue Intelligence Platform (CRIP)

A customer analytics and revenue decision-support platform: churn prediction, customer
lifetime value (CLV), revenue-at-risk, customer profitability, and next-best-action
recommendations for a synthetic e-commerce dataset. Ships with a FastAPI backend, a Streamlit
dashboard, an AI Copilot, PostgreSQL schema, Power BI exports, and a pytest suite.

This README covers **installation, configuration, and running the project only**. For design
details see [`docs/`](docs/) (linked at the bottom of this file).
### 🚀 Live Demo

👉 **[Open Customer 360 & Revenue Intelligence Platform](YOUR-STREAMLIT-URL-HERE)**

> Explore the live Streamlit dashboard for customer churn prediction, CLV, revenue-at-risk, profitability analysis, and next-best-action recommendations.
## 1. Requirements

- Python 3.11+ (developed/tested on 3.12)
- ~2 GB free disk
- No external services required for default (flat-file) mode
- Optional: Docker + Docker Compose, PostgreSQL, an OpenAI API key

## 2. Installation

```bash
git clone <this-repo>
cd customer-revenue-intelligence

python3 -m venv .venv && source .venv/bin/activate   # recommended
pip install -r requirements.txt
# or, without a venv: pip install -r requirements.txt --break-system-packages
```

## 3. Environment configuration

```bash
cp .env.example .env
```

Edit `.env` only if you need to change defaults:

| Variable | Default | Purpose |
|---|---|---|
| `APP_ENV` | `development` | App environment flag |
| `DATABASE_URL` | `postgresql://novamart:novamart@localhost:5432/novamart` | Optional Postgres connection (not required to run API/dashboard) |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `novamart` | Used by `docker-compose.yml`'s `postgres` service |
| `OPENAI_API_KEY` | (empty) | Optional — enables the AI Copilot's LLM path. Leave blank to use the built-in deterministic fallback (works with zero config) |
| `COPILOT_MODEL` | `gpt-4o-mini` | Model name used if `OPENAI_API_KEY` is set |
| `MODEL_PATH` | `models` | Where trained model artifacts are read/written |
| `RANDOM_SEED` | `42` | Reproducibility seed for data generation and model training |

No secrets are hardcoded anywhere in source; `.env` is git-ignored (see `.gitignore`).

## 4. Run the pipeline

```bash
python scripts/run_pipeline.py
```

Runs, in order: data generation → validation → cleaning → feature engineering → RFM →
segmentation → churn model training → CLV model training → SHAP explainability →
revenue-at-risk → profitability → next-best-action → executive KPIs → EDA charts → Power BI
export. Takes ~45-60 seconds at the default scale (8,000 customers). Writes to
`data/processed/`, `models/`, `reports/`, and `powerbi/powerbi_data/`.

```bash
# Re-run without regenerating synthetic data (reuse data/synthetic/*.csv)
python scripts/run_pipeline.py --skip-generate
```

Individual pipeline stages can be run standalone — see `Makefile` targets or run any module
directly, e.g. `python -m src.models.churn_model`.

To scale up the dataset (default is 8,000 customers / ~168K orders), edit `N_CUSTOMERS` and
`AVG_ORDERS_PER_CUSTOMER` in `src/config.py`, then re-run the pipeline. Nothing downstream is
hardcoded to the default size.

## 5. Run the FastAPI backend

```bash
uvicorn api.main:app --reload --port 8000
# or: make api
```

- Health check: `GET http://localhost:8000/health`
- Interactive docs: `http://localhost:8000/docs` (Swagger) or `/redoc`
- Full endpoint reference: [`docs/api_documentation.md`](docs/api_documentation.md)

Requires the pipeline to have been run at least once (endpoints return `503` with a clear
message otherwise, not a stack trace).

## 6. Run the Streamlit dashboard

```bash
streamlit run dashboard/app.py
# or: make dashboard
```

Opens at `http://localhost:8501`. Pages: Executive Overview, Customer 360 (search), Customer
Segmentation, Churn Intelligence, Revenue & CLV, Recommendations & Next-Best-Action, AI
Analytics Copilot.

## 7. Run tests

```bash
pytest tests/ -v
# or: make test
```

45 tests across `tests/test_data.py`, `test_features.py`, `test_models.py`,
`test_business_logic.py`, `test_api.py`. Tests read real pipeline output on disk and will
`pytest.skip()` (not fail) for any file that doesn't exist yet — run the pipeline first.

## 8. AI Copilot

Works out of the box with **no configuration** — a deterministic, rule-based assistant grounded
in the pipeline's own output (`ai_copilot/copilot.py`):

```bash
python ai_copilot/copilot.py
```

To enable the LLM-backed path instead, set `OPENAI_API_KEY` in `.env`. If the LLM call fails for
any reason, the copilot transparently falls back to the deterministic assistant rather than
erroring. Details: [`ai_copilot/README.md`](ai_copilot/README.md).

## 9. Power BI exports

Generated automatically by the pipeline into `powerbi/powerbi_data/`:

```
customer_360.csv   monthly_revenue.csv   customer_segments.csv   churn_predictions.csv
clv_predictions.csv   revenue_at_risk.csv   profitability.csv   recommendations.csv
```

Import guide, relationships, DAX measures, and column dictionary:
[`powerbi/README.md`](powerbi/README.md), [`powerbi/DAX_Measures.md`](powerbi/DAX_Measures.md),
[`powerbi/data_dictionary.md`](powerbi/data_dictionary.md).

## 10. Optional: PostgreSQL

`database/schema.sql` (10 tables) and `database/views.sql` (6 analytical views) are provided.
The API/dashboard run against flat CSV files by default and do **not** require Postgres.

```bash
psql -U <user> -d <db> -f database/schema.sql
psql -U <user> -d <db> -f database/views.sql
# Load pipeline output (run the pipeline first):
psql -U <user> -d <db> -f database/seed.sql
```

## 11. Optional: Docker Compose

```bash
cp .env.example .env
docker compose run --rm pipeline      # generate data + train models once
docker compose up --build             # start postgres, api (:8000), app (:8501)
```

Services are defined in `docker-compose.yml` (`postgres`, `pipeline`, `api`, `app`).

## 12. Makefile shortcuts

```bash
make setup          # pip install
make pipeline       # full pipeline
make pipeline-fast  # pipeline, skip data generation
make train          # retrain churn + CLV models only
make test            # pytest
make api             # start FastAPI
make dashboard        # start Streamlit
make docker-build / docker-up / docker-down
make clean           # remove generated data/models/reports (not source code)
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| API/dashboard error about a missing `data/processed/*.csv` or `models/*.pkl` | Run `python scripts/run_pipeline.py` first |
| `pip install` fails on `psycopg2-binary` | Install `libpq-dev` (Debian/Ubuntu) or drop it from `requirements.txt` if you don't need Postgres |
| `pytest` shows many `SKIPPED` | Pipeline hasn't been run yet |
| Streamlit shows "No processed data found" | Same as above |

## Further documentation

- [`docs/architecture.md`](docs/architecture.md) — system diagram, module responsibilities
- [`docs/database_design.md`](docs/database_design.md) — ER diagram, table/view reference
- [`docs/ml_methodology.md`](docs/ml_methodology.md) — model methodology and real metrics
- [`docs/api_documentation.md`](docs/api_documentation.md) — full REST API reference
- [`docs/installation.md`](docs/installation.md) — extended setup notes and troubleshooting
- [`reports/test_results.md`](reports/test_results.md) / [`reports/dashboard_test_results.md`](reports/dashboard_test_results.md) — verification results
