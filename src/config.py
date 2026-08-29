"""
Central configuration for the Customer 360 & Revenue Intelligence Platform (CRIP).

All paths, random seeds, and dataset-scale parameters live here so every
module (data generation, notebooks, API, dashboard) stays consistent.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ----------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"
DATA_SYNTHETIC_DIR = ROOT_DIR / "data" / "synthetic"
MODELS_DIR = ROOT_DIR / "models"
POWERBI_DATA_DIR = ROOT_DIR / "powerbi" / "powerbi_data"
REPORTS_DIR = ROOT_DIR / "reports"

for d in [DATA_RAW_DIR, DATA_PROCESSED_DIR, DATA_SYNTHETIC_DIR, MODELS_DIR, POWERBI_DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# Reproducibility
# ----------------------------------------------------------------------
RANDOM_SEED = 42

# ----------------------------------------------------------------------
# Dataset scale
#
# NOTE ON SCALE: The original spec calls for 50,000 customers and
# 250,000+ transactions. For this build, the dataset is generated at a
# reduced-but-still-substantial scale (8,000 customers / ~48,000 orders)
# so that the ENTIRE pipeline -- generation, cleaning, EDA, RFM,
# clustering, churn/CLV model training, SHAP explainability, revenue-risk
# scoring, and Power BI exports -- can actually be executed end-to-end
# in this environment with real, non-fabricated results. The generator
# (src/data/generate_data.py) accepts N_CUSTOMERS as a parameter, so
# scaling up to 50,000+ on a full machine is a one-line change.
# ----------------------------------------------------------------------
N_CUSTOMERS = 8000
AVG_ORDERS_PER_CUSTOMER = 6
N_PRODUCTS = 120

APP_ENV = os.getenv("APP_ENV", "development")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://novamart:novamart@localhost:5432/novamart")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
COPILOT_MODEL = os.getenv("COPILOT_MODEL", "gpt-4o-mini")
MODEL_PATH = os.getenv("MODEL_PATH", str(MODELS_DIR))

# Business calendar window for the synthetic dataset
DATA_START_DATE = "2023-01-01"
DATA_END_DATE = "2026-08-09"   # "today" for this build

# Churn definition: no purchase in the last N days as of snapshot date
CHURN_INACTIVITY_DAYS = 90
