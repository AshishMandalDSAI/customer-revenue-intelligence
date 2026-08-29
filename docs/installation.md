# Installation & Setup — NovaMart CRIP

Two supported paths: **local Python** (verified working in this build's sandbox) and
**Docker Compose** (written correctly, but not built/run in this sandbox — no Docker daemon was
available here; verify on your own machine).

## Option A — Local Python (verified)

### Requirements
- Python 3.11+ (this build was developed and tested on Python 3.12)
- ~2 GB free disk (synthetic data + models + figures)
- No external services required for the default flat-file mode

### Steps

```bash
# 1. Clone / unzip the project, then from the project root:
cd customer-revenue-intelligence

# 2. Install dependencies
pip install -r requirements.txt --break-system-packages
# (drop --break-system-packages if you're using a virtualenv, which is recommended:
#  python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt)

# 3. Copy the environment template (optional -- everything has sane defaults)
cp .env.example .env
# Edit .env only if you want to set OPENAI_API_KEY for the AI Copilot's LLM path,
# or point DATABASE_URL at a real Postgres instance.

# 4. Run the full pipeline (data generation -> cleaning -> features -> RFM ->
#    segmentation -> churn/CLV models -> explainability -> revenue-at-risk ->
#    profitability -> next-best-action -> KPIs -> charts -> Power BI export)
python scripts/run_pipeline.py
# Takes roughly 45-60 seconds on a typical machine at this build's default
# scale (8,000 customers / ~168K orders -- see src/config.py to scale up).

# 5a. Start the REST API
uvicorn api.main:app --reload --port 8000
# Docs at http://localhost:8000/docs

# 5b. In a separate terminal, start the dashboard
streamlit run dashboard/app.py
# Opens at http://localhost:8501

# 6. Run the test suite
pytest tests/ -v
# 45 tests, all passing as of the last verified run (see reports/test_results.md)
```

Or, using the Makefile shortcuts (equivalent commands):

```bash
make setup
make pipeline
make api          # in one terminal
make dashboard    # in another terminal
make test
```

### Re-running without regenerating data

`python scripts/run_pipeline.py --skip-generate` (or `make pipeline-fast`) reuses the existing
`data/synthetic/*.csv` files and re-runs cleaning through Power BI export — useful when
iterating on a downstream step (e.g. a model or business-logic change) without waiting for data
generation again.

### Scaling up to the master spec's target size

The default build uses 8,000 customers / ~48,000 target orders (see `src/config.py`'s
`N_CUSTOMERS`, `AVG_ORDERS_PER_CUSTOMER`) so the full pipeline runs in under a minute in a
constrained sandbox. To reproduce the original spec's 50,000 customers / 250,000+ transactions:

```python
# src/config.py
N_CUSTOMERS = 50000
AVG_ORDERS_PER_CUSTOMER = 6   # -> ~300,000 target orders
```

then re-run `python scripts/run_pipeline.py`. Nothing else in the codebase is hardcoded to the
smaller scale — every downstream step (features, models, dashboard, API) reads whatever
`customer_features.csv` actually contains. Expect proportionally longer runtimes, mainly in
model training.

## Option B — Docker Compose (NOT run in this sandbox — verify yourself)

> **Stated plainly:** No Docker daemon was available in the sandbox this project was built in.
> `Dockerfile` and `docker-compose.yml` have been written to accurately match the project's real
> dependencies, ports, and entrypoints, but have not actually been built or run here. Please
> verify with the commands below on a machine with Docker installed before relying on this path.

```bash
cp .env.example .env

# 1. Run the pipeline once inside a container to populate data/, models/, reports/
docker compose run --rm pipeline

# 2. Start Postgres, the API, and the dashboard
docker compose up --build
# API:       http://localhost:8000
# Dashboard: http://localhost:8501
# Postgres:  localhost:5432 (schema.sql + views.sql auto-applied on first init)

# 3. (Optional) Load the pipeline's CSV output into Postgres
#    seed.sql uses `\copy ... FROM 'data/processed/...'`, which needs to run
#    from a process that can see the data/ directory -- e.g. from your host,
#    or from inside the `api` container which has data/ mounted:
docker compose exec api psql "$DATABASE_URL" -f database/seed.sql
```

### Services (see `docker-compose.yml` for full detail)

| Service | Purpose | Port |
|---|---|---|
| `postgres` | PostgreSQL 16, auto-initialized with `schema.sql` + `views.sql` | 5432 |
| `pipeline` | One-shot: runs `scripts/run_pipeline.py`, then exits | — |
| `api` | FastAPI (`uvicorn api.main:app`) | 8000 |
| `app` | Streamlit dashboard | 8501 |

## Option C — Individual module commands

Every pipeline step is independently runnable as a module, useful for debugging one stage:

```bash
python -m src.data.generate_data          # synthetic data only
python -m src.data.validation              # data quality report
python -m src.data.data_cleaning
python -m src.data.feature_engineering
python -m src.analytics.rfm
python -m src.analytics.segmentation
python -m src.models.churn_model
python -m src.models.clv_model
python -m src.models.model_explainability
python -m src.business.revenue_at_risk
python -m src.analytics.profitability
python -m src.business.next_best_action
python -m src.analytics.eda                # executive_kpis.json
python -m src.analytics.eda_charts         # reports/figures/*.png
python -m src.business.recommendations     # Power BI export + recommendations.md
```

## Verifying the AI Copilot

No API key is required — the deterministic fallback works out of the box:

```bash
python ai_copilot/copilot.py
```

To enable the LLM-backed path, set `OPENAI_API_KEY` in `.env`. **Note:** this path has not been
exercised in this build's sandbox (no key configured, and the sandbox's network egress allowlist
does not include the OpenAI API domain) — see `ai_copilot/README.md` and
`reports/dashboard_test_results.md` for the exact limitation.

## Troubleshooting

| Symptom | Fix |
|---|---|
| API/dashboard error mentioning a missing `data/processed/*.csv` or `models/*.pkl` | Run `python scripts/run_pipeline.py` first |
| `pip install` fails on `psycopg2-binary` | Install PostgreSQL client headers (`apt-get install libpq-dev` on Debian/Ubuntu) or drop `psycopg2-binary` from `requirements.txt` if you don't need the Postgres path |
| `pytest` shows many `SKIPPED` | The pipeline hasn't been run yet — tests skip cleanly rather than fail when their required input file is missing |
| Streamlit shows "No processed data found" | Same as above — run the pipeline |
