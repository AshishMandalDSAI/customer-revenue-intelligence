# Dashboard, API & AI Copilot — Verification Results

**Date of this run:** 2026-08-09
**Context:** Full end-to-end verification performed after fixing the `customer_profitability.csv`
NaN issue documented in `reports/test_results.md`, to confirm the fix didn't regress anything
downstream.

## Streamlit Dashboard (`dashboard/app.py`)

### Method
Two independent checks were run, since a full browser can't be driven from this sandbox:

1. **Bare-mode render check** — imported every page module and called its `render()` function
   directly in a Python process (outside `streamlit run`). Streamlit prints
   "missing ScriptRunContext" warnings in this mode (expected/documented Streamlit behavior,
   not an error), but any real exception in the page code still raises and fails loudly. This
   catches data/column/logic errors with full tracebacks.
2. **Live HTTP smoke test** — actually launched `streamlit run dashboard/app.py` as a real
   server process and issued HTTP requests against it.

### Results

| Page | Bare-mode render | Notes |
|---|---|---|
| Executive Overview | ✅ OK | KPIs, revenue trend, region/RFM/channel charts |
| Customer 360 | ✅ OK | Search + risk-tier browse paths both exercised |
| Customer Segmentation | ✅ OK | Cluster profiles, PCA image, RFM segment chart |
| Churn Intelligence | ✅ OK | Model comparison table, confusion matrix, churn drivers, high-risk list + CSV download |
| Revenue & CLV | ✅ OK | Revenue-at-risk by segment/region, CLV distribution, profitability quadrant scatter |
| Recommendations & NBA | ✅ OK | Action distribution, per-action filter, recommendations.md render |
| AI Analytics Copilot | ✅ OK | Sample-question buttons, free-text question, backend-transparency label |

**Two real bugs were found and fixed during this process** (both **before** the profitability
NaN investigation, in the same session):
1. `dashboard/data_loader.py` and `api/data_access.py` were merging `customer_rfm.csv`
   (which has its own `recency_days` / `frequency` / `monetary` columns) into a table that
   already had columns of the same names, producing pandas' auto-suffixed `_x`/`_y` columns
   instead of the plain names the rest of the code expected. Fixed by only pulling the
   `segment` column from `customer_rfm.csv` in both places, since `customer_features.csv`
   already has the canonical R/F/M values.
2. A leftover `if False else None` conditional-import artifact in `dashboard/data_loader.py`
   was removed.

Live HTTP smoke test (after all fixes, including the profitability fix):
```
$ streamlit run dashboard/app.py --server.headless true --server.port 8501
...
Uvicorn server started on 0.0.0.0:8501

$ curl -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8501/
HTTP 200

$ curl http://127.0.0.1:8501/_stcore/health
ok  (HTTP 200)
```
No exceptions in the server log. Server was stopped afterward to free sandbox resources.

### Limitation
This confirms the app *serves* correctly and every page's Python code executes without error
against real pipeline data. It does not substitute for a human clicking through the rendered
UI in a browser (verifying visual layout, chart readability, etc.) — that hasn't been done here.

## FastAPI REST API (`api/main.py`)

### Method
`fastapi.testclient.TestClient` against the real `api.main.app` object, backed by the actual
`data/processed/*.csv` and `models/*.pkl` files (no mocking).

### Results — 15/15 endpoint tests passed (see `reports/test_results.md` for the full pytest log)

| Endpoint | Status |
|---|---|
| `GET /health` | ✅ |
| `GET /customers` (list, with `limit`/`offset` bounds validation) | ✅ |
| `GET /customers/{id}` and `/customers/{id}/profile` | ✅ |
| `GET /customers/{id}/churn` | ✅ |
| `GET /customers/{id}/clv` | ✅ |
| `GET /customers/{id}/recommendation` | ✅ |
| `GET /customers/NOT_A_REAL_ID/...` → 404 | ✅ |
| `GET /analytics/overview` | ✅ |
| `GET /analytics/segments` | ✅ |
| `GET /analytics/revenue-risk` | ✅ |
| `POST /predict/churn` (valid + invalid input → 422) | ✅ |
| `POST /predict/clv` | ✅ |
| `POST /recommend/action` | ✅ |

### Edge case specifically re-checked after the profitability fix
The 269 customers who are present in `customer_profitability.csv` but absent from
`customer_features.csv` (see root-cause explanation in `reports/test_results.md`) are, by
design, **not** part of the API's Customer 360 population (`api/data_access.py` builds its
360 view starting from `customer_features.csv`). Spot-checked 3 such customer IDs directly:

```
C102019 -> 404
C107416 -> 404
C100969 -> 404
```

This is correct, intended behavior — a clean 404, not a crash or a row full of nulls — because
these customers are outside the snapshot population that churn/CLV scores are defined for.
Their profitability figures are still correctly captured in the profitability-specific
outputs (`customer_profitability.csv`, `profitability_summary.csv`), which don't depend on the
snapshot population.

## AI Analytics Copilot (`ai_copilot/copilot.py`)

No `OPENAI_API_KEY` is configured in this sandbox, so **only the deterministic fallback path
was exercised** — see the "Known limitations" note below regarding the LLM path.

### Method
Called `ai_copilot.copilot.ask()` directly with 9 questions spanning every documented pattern
category, after the pipeline re-run.

### Results — all 9 questions answered correctly, grounded in real pipeline numbers

| Question | Pattern matched | Grounded in |
|---|---|---|
| "Which customer segment is most profitable?" | profitability | `segment_profiles.csv` |
| "How much revenue is at risk?" | revenue-at-risk | `executive_kpis.json` |
| "What are the biggest churn drivers?" | churn drivers | `churn_feature_importance.csv` |
| "Show me the top 10 high-value customers at risk." | top-N at-risk list | `revenue_at_risk.csv` |
| "Which customers should the sales team contact?" | sales prioritization | `revenue_at_risk.csv` (top 5) |
| "Which region has the highest churn?" | regional risk | `revenue_at_risk_by_region.csv` |
| "What should marketing do next month?" | NBA-driven marketing suggestion | `next_best_action_summary.csv` |
| "Why did revenue decrease?" | revenue-decline (no fabricated cause) | `executive_kpis.json` + explicit "can't attribute a single cause" caveat |
| "What's the weather like today?" (off-topic) | generic fallback | headline KPIs + suggested question types |

One gap was found and fixed during this verification: the phrase **"How much revenue **is** at
risk?"** did not match the original `"revenue at risk" in q` substring check (extra word "is").
Fixed by loosening the match to `"revenue" in q and "risk" in q` while explicitly excluding the
"sales team contact" and "top N at risk" patterns from that branch so they still route
correctly. Re-verified all 9 questions after the fix.

### Known limitation — LLM-backed path not exercised
`ai_copilot/copilot.py`'s `_llm_answer()` path (used when `OPENAI_API_KEY` is set) calls the
real OpenAI API and **was not executed in this sandbox**, because:
- No API key is configured here, and none should be fabricated.
- This environment's network egress allowlist does not include OpenAI's API domain (see the
  project's `<network_configuration>`), so even with a key, a live call would not reach it from
  here.

The fallback-triggering exception path (`except Exception` in `ask()`, which catches any LLM
call failure and transparently degrades to the deterministic assistant) is exercised by
construction whenever `OPENAI_API_KEY` is unset, but the *success* path of an actual LLM call
has not been verified end-to-end. Anyone deploying this with a real key should do one manual
smoke test against a live key before relying on it.

## Docker / PostgreSQL — explicitly not run
No Docker daemon or PostgreSQL server is available in this sandbox, and none was started or
simulated. `docker-compose.yml`, `Dockerfile`, and `database/schema.sql` / `views.sql` /
`seed.sql` have not been executed against real containers or a real Postgres instance as part
of this verification pass. The API and dashboard both currently run against the flat-file
`data/processed/*.csv` outputs (see `api/data_access.py`'s docstring), which is the verified,
working path. Treat any Docker/Postgres claims elsewhere in the docs as **unverified in this
environment** until run somewhere Docker/Postgres are actually available.

## Overall status
Dashboard, API, and AI Copilot (deterministic path) are all genuinely working against real,
freshly-regenerated pipeline output, with 45/45 automated tests passing and 0 skipped. The
profitability NaN bug that motivated this verification pass is fixed at the root cause, not
patched around, and is covered by two new regression tests.
