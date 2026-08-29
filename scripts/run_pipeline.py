#!/usr/bin/env python3
"""
Runs the full CRIP pipeline end-to-end:
Data Generation -> Validation -> Cleaning -> Feature Engineering -> RFM ->
Segmentation -> Churn Model -> CLV Model -> Explainability -> Revenue-at-Risk ->
Profitability -> Next-Best-Action -> EDA/KPIs -> Charts -> Power BI Exports

Usage:
    python scripts/run_pipeline.py [--skip-generate]
"""
import sys
import time
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

STEPS = [
    ("Data Generation", "src.data.generate_data"),
    ("Data Validation", "src.data.validation"),
    ("Data Cleaning", "src.data.data_cleaning"),
    ("Feature Engineering", "src.data.feature_engineering"),
    ("RFM Analysis", "src.analytics.rfm"),
    ("Customer Segmentation", "src.analytics.segmentation"),
    ("Churn Model Training", "src.models.churn_model"),
    ("CLV Model Training", "src.models.clv_model"),
    ("Model Explainability (SHAP)", "src.models.model_explainability"),
    ("Revenue-at-Risk", "src.business.revenue_at_risk"),
    ("Customer Profitability", "src.analytics.profitability"),
    ("Next-Best-Action", "src.business.next_best_action"),
    ("Executive KPIs", "src.analytics.eda"),
    ("EDA Charts", "src.analytics.eda_charts"),
    ("Power BI Export & Recommendations", "src.business.recommendations"),
]


def run_step(name, module, skip=False):
    if skip:
        print(f"\n[SKIPPED] {name}")
        return
    print("\n" + "=" * 70)
    print(f"STEP: {name}  ({module})")
    print("=" * 70)
    import importlib
    t0 = time.time()
    mod = importlib.import_module(module)
    mod.main()
    print(f"-- Completed in {time.time() - t0:.1f}s --")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-generate", action="store_true",
                         help="Skip data generation (reuse existing data/synthetic files)")
    args = parser.parse_args()

    t_start = time.time()
    print("#" * 70)
    print("# NovaMart Customer 360 & Revenue Intelligence Platform -- FULL PIPELINE")
    print("#" * 70)

    for i, (name, module) in enumerate(STEPS, 1):
        skip = args.skip_generate and module == "src.data.generate_data"
        print(f"\n[{i}/{len(STEPS)}]", end=" ")
        run_step(name, module, skip=skip)

    print("\n" + "#" * 70)
    print(f"# PIPELINE COMPLETE in {time.time() - t_start:.1f}s")
    print("#" * 70)


if __name__ == "__main__":
    main()
