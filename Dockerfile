# NovaMart Customer 360 & Revenue Intelligence Platform (CRIP)
# Single image used for both the API and the dashboard services
# (see docker-compose.yml for how each service overrides the CMD).
#
# NOTE (sandbox limitation, documented honestly): this Dockerfile has been
# written to match the project's actual dependencies and entrypoints, but it
# has NOT been built or run in this development sandbox -- no Docker daemon
# is available here. Build and run it yourself with the commands in
# docs/installation.md to verify on your machine.

FROM python:3.11-slim

WORKDIR /app

# System dependencies needed by psycopg2 (PostgreSQL client) and matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Directories the pipeline writes into
RUN mkdir -p data/raw data/processed data/synthetic models reports/figures powerbi/powerbi_data

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 8000 8501

# Default: run the API. docker-compose.yml overrides this for the dashboard
# and pipeline services.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
