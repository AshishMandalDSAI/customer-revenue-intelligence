# NovaMart CRIP -- Makefile
#
# All targets call the actual project entrypoints (scripts/run_pipeline.py,
# pytest, uvicorn, streamlit) -- nothing here is a placeholder.

.PHONY: setup data pipeline train test api dashboard docker-build docker-up docker-down clean

PYTHON ?= python3

## Install Python dependencies
setup:
	$(PYTHON) -m pip install -r requirements.txt --break-system-packages

## Generate the synthetic NovaMart dataset only (src/data/generate_data.py)
data:
	$(PYTHON) -m src.data.generate_data

## Run the full pipeline: generation -> cleaning -> features -> RFM ->
## segmentation -> churn/CLV models -> explainability -> revenue-at-risk ->
## profitability -> next-best-action -> KPIs -> charts -> Power BI export
pipeline:
	$(PYTHON) scripts/run_pipeline.py

## Re-run the pipeline WITHOUT regenerating synthetic data (reuse data/synthetic/*)
pipeline-fast:
	$(PYTHON) scripts/run_pipeline.py --skip-generate

## Train only the churn + CLV models (assumes features/RFM/segmentation already exist)
train:
	$(PYTHON) -m src.models.churn_model
	$(PYTHON) -m src.models.clv_model
	$(PYTHON) -m src.models.model_explainability

## Run the automated test suite (run `make pipeline` first at least once)
test:
	$(PYTHON) -m pytest tests/ -v

## Start the FastAPI REST API on http://localhost:8000 (docs at /docs)
api:
	$(PYTHON) -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

## Start the Streamlit dashboard on http://localhost:8501
dashboard:
	$(PYTHON) -m streamlit run dashboard/app.py

## Build the Docker image (NOT executed/verified in the build sandbox -- see docs/installation.md)
docker-build:
	docker compose build

## Start all services with Docker Compose (NOT executed/verified in the build sandbox)
docker-up:
	docker compose run --rm pipeline
	docker compose up

docker-down:
	docker compose down

## Remove generated artifacts (data, models, reports) -- NOT source code
clean:
	rm -rf data/processed/* data/synthetic/* models/*.pkl reports/figures/* \
	       powerbi/powerbi_data/*.csv .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
