# Test Results — CRIP (Customer 360 & Revenue Intelligence Platform)

**Date of this run:** 2026-08-09
**Command:** `python3 -m pytest tests/ -v`
**Dataset state:** full pipeline (`python scripts/run_pipeline.py --skip-generate`) re-run after the profitability fix described below.

## Summary

| Metric | Count |
|---|---|
| Total tests | 45 |
| Passed | 45 |
| Failed | 0 |
| Skipped | 0 |

```
======================== 45 passed, 1 warning in 6.08s =========================
```

The one warning is a benign library deprecation notice (`starlette.testclient` recommending
the `httpx2` package name) — not a test failure or application issue.

## Breakdown by file

| File | Tests | Status |
|---|---|---|
| `tests/test_data.py` | 8 | All passed — synthetic data integrity, referential integrity, and the "declining engagement → higher churn" realism check |
| `tests/test_features.py` | 6 | All passed — feature engineering leakage guard, RFM score ranges/segments, segmentation coverage and silhouette score |
| `tests/test_models.py` | 7 | All passed — churn/CLV model artifacts load, predictions are valid probabilities/non-negative, real (non-fabricated) comparison metrics beat random chance |
| `tests/test_business_logic.py` | 9 | All passed — revenue-at-risk formula reconciliation, profitability quadrant set, **profit-formula reconciliation (fixed, see below)**, NBA action set/reasons, **new NaN-regression guard tests** |
| `tests/test_api.py` | 15 | All passed — health, customer 360 endpoints, analytics endpoints, live model-scoring POST endpoints, input validation (422 on bad input), 404 on unknown customer |

## Investigation: NaN values in `customer_profitability.csv`

### What was found
An early version of `tests/test_business_logic.py::test_profit_equals_contribution_minus_costs`
failed. Investigating the underlying data showed **269 of 7,658 rows** in
`data/processed/customer_profitability.csv` had a `NaN` value in the `acquisition_cost` column.

### Root cause (confirmed, not assumed)
Two independent pipeline steps use different, deliberately different, customer populations:

- **`src/data/feature_engineering.py`** builds `customer_features.csv` as of a fixed
  `SNAPSHOT_DATE` (90 days before the dataset's end date), and explicitly **excludes any
  customer whose `tenure_days <= 0`** at that snapshot — i.e., customers who signed up on or
  after the snapshot date. This is intentional and correct: it prevents label leakage between
  the churn feature window and the churn label window (documented in the module's own
  docstring in `src/data/feature_engineering.py`; a standalone `docs/ml_methodology.md`
  write-up of the full methodology has not been written yet in this build).
- **`src/analytics/profitability.py`** computes profit from each customer's **full, all-time**
  order history (not snapshot-limited), because profitability is a backward-looking financial
  measure, not a leakage-sensitive predictive feature. It therefore legitimately includes
  customers who signed up after `SNAPSHOT_DATE` but already have orders.

The bug: `profitability.py` was joining `acquisition_cost` (a static, per-customer attribute
from customer master data) from `customer_features.csv` — the *snapshot-filtered* table —
instead of from `customers_clean.csv`, which has every customer unconditionally. Every
customer present in the profitability table but absent from the snapshot-filtered feature
table therefore got `NaN` for `acquisition_cost`.

This was verified precisely, not just inferred:
- 266 of the 269 affected customers signed up strictly after `SNAPSHOT_DATE`.
- The remaining 3 signed up exactly **on** `SNAPSHOT_DATE`, which the feature-engineering
  filter (`tenure_days > 0`, strict) also excludes as a boundary case.
- 266 + 3 = 269 — fully accounts for every affected row.

### Was this a genuine bug or a test assumption error? Both, in different tests
- The **NaN issue** was a genuine, if minor, pipeline bug: an unnecessary coupling between two
  modules that are supposed to operate on different (and differently-scoped) customer
  populations by design.
- Separately, my **first draft of the reconciliation test** was wrong on its own terms: it
  assumed `estimated_profit` should subtract `acquisition_cost`. It should not —
  `estimated_profit` intentionally excludes acquisition cost (a one-time, already-sunk cost,
  reported as its own column per the module's documented cost model) so it isn't netted
  against ongoing per-order profit. That was a test-authoring error, corrected without
  weakening what the test actually checks.

### Fix applied
In `src/analytics/profitability.py`, `acquisition_cost` is now joined from
`customers_clean.csv` (all 8,000 customers, unconditionally) instead of from
`customer_features.csv` (snapshot-filtered, 7,636 customers). A code comment documents why,
so this doesn't regress silently in the future.

### Verification after the fix
- Re-ran `src/analytics/profitability.py` standalone: `customer_profitability.csv` now has
  **7,658 rows, 0 NaNs** (previously 269 NaN rows).
- Re-ran the full pipeline (`scripts/run_pipeline.py --skip-generate`) so every downstream
  artifact (executive KPIs, revenue-at-risk, next-best-action, Power BI exports,
  recommendations) is consistent with the corrected profitability table.
- Corrected the test's reconciliation formula to match the module's actual (and correct)
  documented behavior, rather than loosening or deleting the test.
- Added two new regression tests:
  - `test_profitability_table_has_no_missing_values` — fails loudly if this NaN class ever
    reappears in any column, not just `acquisition_cost`.
  - `test_profitability_may_legitimately_include_customers_absent_from_features` — documents
    and locks in the fact that profitability's customer population is a superset in this
    specific, well-understood way, so a future contributor doesn't "fix" it by filtering
    profitability down to the snapshot population (which would silently drop real revenue).

No test was weakened, skipped, or removed to make the suite pass. The failing test was fixed
to check the correct thing, and the underlying application bug it exposed was fixed at the
source.

## Known limitations of the test suite
- Tests are **integration-style**, run against the actual pipeline output on disk
  (`data/processed/*.csv`, `models/*.pkl`, `reports/*`). They will `pytest.skip()` cleanly if
  the pipeline hasn't been run yet, rather than fail — run
  `python scripts/run_pipeline.py` (or `make pipeline`) first.
- No dedicated unit tests exist yet for `src/data/generate_data.py`'s internal random-variable
  wiring (e.g., the exact functional form linking complaint frequency to churn probability) —
  coverage here is at the "does the resulting correlation hold in the generated data" level
  (`test_declining_engagement_correlates_with_higher_churn_signal`), not at the level of testing
  individual probability-generation functions in isolation.
- Database tests (schema/views against a live PostgreSQL instance) are not included, since no
  PostgreSQL server is available in this sandbox — see `reports/dashboard_test_results.md` for
  the corresponding limitation on the Docker/Postgres side.
