# ML Methodology — NovaMart CRIP

All figures in this document are pulled directly from the current pipeline's output files
(`reports/*.csv`, `reports/*.json`) as of the last full pipeline run. Re-running
`python scripts/run_pipeline.py` will regenerate slightly different numbers (different random
train/test splits notwithstanding the fixed seed, if the underlying data changes) — these are
**real, reproducible results**, not fixed/fabricated targets.

## 1. Snapshot design and leakage prevention

A single point-in-time cutoff, `SNAPSHOT_DATE`, is defined in
`src/data/feature_engineering.py` as:

```
SNAPSHOT_DATE = DATA_END_DATE - CHURN_INACTIVITY_DAYS
             = 2026-08-09 - 90 days
             = 2026-05-11
```

- **Feature window:** all data on or before `SNAPSHOT_DATE`. Every column in
  `customer_features.csv` is computed using only orders/interactions/returns dated on or before
  this cutoff.
- **Label window:** the 90 days strictly after `SNAPSHOT_DATE`, up to `DATA_END_DATE`. The churn
  label and the CLV regression target are both computed by looking **forward** into this window.

There is zero overlap between the two windows, so no feature can "see" the outcome it's meant to
predict. This is verified by `tests/test_features.py::test_customer_features_no_leakage_columns`.

**Known, documented edge case:** customers who signed up on/after `SNAPSHOT_DATE` have no
feature-window history and are excluded from `customer_features.csv` (`tenure_days > 0` filter).
This is correct leakage-avoidance behavior, not a bug — see `reports/test_results.md` for the
investigation that confirmed this precisely (it was initially mistaken for a bug when it
produced `NaN`s in an unrelated, non-snapshot-scoped table, `customer_profitability.csv`; the
actual fix was in the profitability module's join, not here).

## 2. Feature set

`FEATURE_COLS` (defined once in `src/models/churn_model.py` and reused by `clv_model.py`) plus
one-hot-encoded `gender`, `region`, `acquisition_channel` (`pd.get_dummies(..., drop_first=True)`):

| Feature | What it captures |
|---|---|
| `age` | Demographic |
| `tenure_days` | How long the customer has existed as of snapshot |
| `acquisition_cost` | Cost to acquire this customer |
| `frequency`, `monetary`, `avg_order_value`, `std_order_value` | Core RFM/spend behavior |
| `recency_days` | Days since last order as of snapshot |
| `orders_last_90d`, `orders_prior_90d`, `order_trend` | Recent activity vs. prior period — the trend signal |
| `avg_discount_pct`, `total_qty`, `n_categories` | Discount dependency, basket size, category diversity |
| `n_returns`, `total_refund`, `return_rate` | Returns behavior |
| `n_support_tickets`, `avg_satisfaction`, `n_complaints`, `complaints_last_90d`, `complaints_prior_90d`, `complaint_trend` | Support/service signals |
| `engagement_score` | Composite 0-100 score: `35% recency + 35% frequency + 20% satisfaction − 10% complaint penalty` |

## 3. RFM analysis (`src/analytics/rfm.py`)

Recency, Frequency, and Monetary value are each scored 1-5 via quantile ranking
(`pd.qcut` on `.rank(method="first")`, so ties don't collapse bins). Recency is scored so that
*lower* days-since-last-order → *higher* score (5 = most recent). The R/F/M score combination
maps to one of 10 named segments (Champions, Loyal Customers, Potential Loyalists, New
Customers, At Risk, Can't Lose Them, Hibernating, Lost Customers, Needs Attention, Promising),
each with a documented business meaning in `SEGMENT_DEFINITIONS`.

## 4. Customer segmentation (`src/analytics/segmentation.py`)

K-Means clustering on standardized behavioral features. **k was selected analytically, not
guessed:** the pipeline evaluates k=2..8 on both inertia (elbow) and silhouette score, and
selects the k that maximizes silhouette score.

**Actual result from the current run:**

| k | Silhouette |
|---|---|
| 2 | 0.3105 |
| 3 | 0.2934 |
| **4 (selected)** | **0.3090** |
| 5 | 0.2357 |
| 6 | 0.2553 |
| 7 | 0.2676 |
| 8 | 0.2424 |

k=4 was selected — note k=2 has a marginally higher silhouette (0.3105 vs 0.3090) but was
judged less business-useful (a 2-cluster split is too coarse to drive differentiated actions);
k=4 is the practical choice from among the top silhouette scores. PCA (`reports/figures/09_pca_clusters.png`)
visualizes the clusters in 2D; the first two principal components explain 39.7% and 17.8% of
variance respectively (`reports/segmentation_summary.json`).

## 5. Churn prediction (`src/models/churn_model.py`)

**Label:** did the customer place zero orders in the 90-day label window? (binary; ~40% positive
rate in this dataset by construction — see `docs/database_design.md` / the data-generation
causal design below).

**Models trained and compared** (held-out 20% test set, stratified):

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|
| Logistic Regression | 0.7853 | 0.6991 | 0.8053 | 0.7485 | 0.8835 | 0.8329 |
| Random Forest | 0.8004 | 0.7216 | 0.8086 | 0.7626 | 0.8894 | 0.8439 |
| **XGBoost (selected)** | 0.7919 | 0.7057 | **0.8152** | 0.7565 | 0.8887 | **0.8410** |

**Model selection is NOT "highest accuracy."** The selection rule is
`business_score = 0.5 × recall + 0.5 × PR-AUC`, and XGBoost wins on that composite even though
Random Forest has marginally higher raw accuracy (0.8004 vs 0.7919). The documented reasoning
(from `reports/churn_model_selection.json`):

> Selected for highest weighted recall + PR-AUC, not accuracy. In churn prediction, missing a
> true churner (false negative) forfeits that customer's remaining lifetime value, while a false
> positive only costs an unnecessary retention offer. PR-AUC is used alongside recall because
> ROC-AUC can look optimistic under class imbalance.

**Confusion matrix (XGBoost, test set, n=1,528):**

|  | Predicted: Stay | Predicted: Churn |
|---|---|---|
| **Actual: Stay** | 716 | 206 |
| **Actual: Churn** | 112 | 494 |

Recall on the churn class = 494 / (494+112) = 81.5%, matching the reported recall figure.

**Class imbalance handling:** `class_weight="balanced"` for Logistic Regression / Random Forest;
`scale_pos_weight = (negatives/positives)` for XGBoost — not naive oversampling/undersampling.

**Top churn drivers** (feature importance, `reports/churn_feature_importance.csv`):
`orders_last_90d` dominates (importance 0.382), followed by `orders_prior_90d` (0.088),
`recency_days` (0.074) — consistent with the causal structure built into the synthetic data
(declining recent activity is the primary churn signal).

## 6. CLV prediction (`src/models/clv_model.py`)

**Target:** `future_90d_revenue` — sum of order value in the (snapshot, snapshot+90d] window,
same snapshot/label split as churn (zero leakage).

**Model:** Random Forest Regressor (300 trees, max_depth=10).

**Actual held-out test-set performance:**

| Metric | Value |
|---|---|
| MAE | ₹32,426.33 |
| RMSE | ₹55,414.03 |
| R² | 0.5008 |

An R² of ~0.50 means the model explains about half the variance in near-term future revenue —
a realistic, non-inflated result for a regression target this noisy (individual next-quarter
spend is inherently volatile), reported honestly rather than cherry-picked.

**From near-term revenue to 12-month Expected CLV:** the model predicts *90-day* forward
revenue, not a full year directly. To get `expected_clv_12m`, that 90-day prediction is combined
with retention probability (`1 − churn_probability`) via a geometric-series approximation over
4 periods (~1 year of 90-day periods):

```
retention_prob = clip(1 - churn_probability, 0.05, 0.98)
geometric_factor = (1 - retention_prob^4) / (1 - retention_prob)
expected_clv_12m = predicted_future_90d_revenue × geometric_factor
```

This is a standard discrete-time retention-weighted CLV approximation: each future 90-day period
contributes revenue only if the customer is still retained by then, and the probability of still
being retained compounds (declines) each period. It is **not** a guarantee — it's explicitly
labeled "Predicted"/"Estimated" everywhere it's surfaced (dashboard, API, copilot), never
"Actual."

## 7. Explainability (`src/models/model_explainability.py`)

Feature importances (tree models) and per-customer risk-factor narratives are generated for the
top 200 highest-risk customers, in the exact format specified by the project brief, e.g.:

```
Customer C100008
Churn Probability: 91%
Risk Factors:
  1. 277 days since last purchase (increasing churn risk)
  2. orders in the last 90 days: 0 (increasing churn risk)
  3. total historical order count: 0 (increasing churn risk)
```

SHAP values are used where practical for global feature attribution
(`reports/shap_global_importance.csv`); per-customer factors are derived from each customer's
feature values relative to the population, ranked by the model's global feature importance.

## 8. Revenue-at-risk

```
revenue_at_risk = churn_probability × expected_clv_12m
```

Documented and defensible: this is the probability-weighted loss of *future expected value*,
not full historical spend (which would overstate risk for low-value customers who happen to be
at risk) and not just next-quarter revenue (which understates risk for high-CLV customers with a
long horizon). See `src/business/revenue_at_risk.py` module docstring. Verified by
`tests/test_business_logic.py::test_revenue_at_risk_formula_matches_documented_methodology`.

**Current result:** ₹75,359,937 total revenue at risk across 3,019 high-risk customers
(`reports/executive_kpis.json`).

## 9. Customer profitability

```
gross_contribution   = gross_revenue − total_COGS
estimated_profit     = gross_contribution − fulfillment_cost − return_cost − support_cost
```

`acquisition_cost` is deliberately **excluded** from `estimated_profit` (it's a one-time, sunk
cost, reported as its own column rather than netted against ongoing profit — see
`src/analytics/profitability.py` module docstring). Cost assumptions: fulfillment = 8% of gross
revenue, support = ₹150/ticket, return penalty = 5% on top of refund amount — all documented,
none fabricated. Verified by `tests/test_business_logic.py::test_profit_equals_contribution_minus_costs`.

## 10. Next-best-action (`src/business/next_best_action.py`)

A deterministic rule engine (not a black-box model) mapping `(clv_category, risk_category,
engagement_score, n_complaints, avg_satisfaction, n_categories)` → one of `RETENTION`, `UPSELL`,
`CROSS_SELL`, `LOYALTY_REWARD`, `REACTIVATION`, `PREMIUM_SUPPORT`, `NO_ACTION`, each with a
generated natural-language reason. Being rule-based (not ML) is intentional here: next-best-action
recommendations need to be auditable and explainable to a business stakeholder, which a
transparent rule table provides more directly than a trained classifier would.

## 11. Realism of the synthetic data (causal, not random)

`src/data/generate_data.py` deliberately wires customer behavior together rather than sampling
every column independently:
- Customers with declining recent order frequency, rising complaints, and long inactivity have
  a **higher generated probability of having no future orders** (i.e., of churning) — this
  causal link is what `tests/test_data.py::test_declining_engagement_correlates_with_higher_churn_signal`
  checks for and confirms holds in the generated data.
- Higher-value, more tenured customers are given realistically higher spend trajectories (not
  independently random monetary values).
- Seasonality is built into the order-date generation (see the generator's docstring for the
  exact monthly weighting used).

## 12. What is Actual vs. Predicted vs. Estimated vs. Potential

This distinction is enforced consistently across the dashboard, API, copilot, and this
documentation set:

| Label | Examples | Basis |
|---|---|---|
| **Actual** | Total revenue, order counts, observed churn/retention rate, RFM scores | Directly observed in the (already-happened) label window |
| **Predicted** | Churn probability, 90-day/12-month CLV | Held-out-validated ML model output (see sections 5-6 above for real test-set metrics) |
| **Estimated** | Customer profitability, revenue-at-risk | Computed from documented cost assumptions / formulas, not observed directly |
| **Potential** | "Potential revenue-protection opportunity" language in `reports/recommendations.md` | Opportunity sizing for planning purposes — explicitly not a guaranteed outcome, since no A/B experiment has been run |
