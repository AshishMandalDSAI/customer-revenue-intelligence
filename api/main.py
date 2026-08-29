"""
CRIP REST API
=============
FastAPI application exposing customer 360, churn, CLV, revenue-at-risk and
next-best-action data produced by the analytics/ML pipeline
(scripts/run_pipeline.py). Run the pipeline at least once before starting
the API, or the routes will return a clear 500 telling you to do so.

Run locally:
    uvicorn api.main:app --reload --port 8000

Docs:
    http://localhost:8000/docs   (Swagger UI)
    http://localhost:8000/redoc
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

sys.path.append(str(Path(__file__).resolve().parent.parent))

from api.routes import customers, analytics, predictions
from api.schemas import HealthResponse

APP_VERSION = "1.0.0"

app = FastAPI(
    title="NovaMart Customer 360 & Revenue Intelligence Platform API",
    description=(
        "REST API for customer churn, CLV, revenue-at-risk, profitability and "
        "next-best-action analytics over the NovaMart synthetic e-commerce dataset."
    ),
    version=APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(FileNotFoundError)
async def missing_pipeline_output_handler(request, exc: FileNotFoundError):
    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "Pipeline output not found. Run `python scripts/run_pipeline.py` "
                "(or `make pipeline`) first to generate processed data and models."
            ),
            "error": str(exc),
        },
    )


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    return HealthResponse(status="ok", service="crip-api", version=APP_VERSION)


app.include_router(customers.router)
app.include_router(analytics.router)
app.include_router(predictions.router)
