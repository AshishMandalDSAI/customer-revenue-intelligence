# KPI Definitions — NovaMart CRIP

Every KPI below is computed by `src/analytics/eda.py` and written to
`reports/executive_kpis.json` — the same numbers shown on the dashboard's Executive Overview
page and returned by `GET /analytics/overview`. Current values are shown for reference; they
will change slightly on every pipeline re-run (different snapshot date if `DATA_END_DATE`
changes, etc.) since they're computed from live data, not hardcoded.

| KPI | Definition | Source | Current value |
|---|---|---|---|
| **Total Customers** | Count of all customers in `customers` table | `customers_clean.csv` row count | 8,000 |
| **Active Customers** | Customers with at least one order in the last 90 days (as of snapshot) | `customer_features.orders_last_90d > 0` | 4,648 |
| **Total Revenue** | Sum of all order values, all-time | `SUM(orders.order_value)` | ₹2,954,202,320.22 |
| **Monthly Revenue** | Total revenue in the most recent complete calendar month | `monthly_revenue_view` / `monthly_revenue.csv`, latest row | ₹34,839,995.43 |
| **Total Orders** | Count of all orders, all-time | `COUNT(orders.order_id)` | 168,250 |
| **Average Order Value (AOV)** | Total revenue ÷ total orders | `AVG(orders.order_value)` | ₹17,558.41 |
| **Repeat Purchase Rate** | Share of ordering customers with more than 1 order | `COUNT(frequency>1) / COUNT(frequency>0)` | 93.23% |
| **Customer Retention Rate** | 1 − churn rate (share of customers active in the label window) | `1 - churned.mean()` | 60.32% |
| **Churn Rate** | Share of customers with zero orders in the 90-day label window (see `docs/ml_methodology.md` §1 for the exact window definition) | `customer_features.churned.mean()` | 39.68% |
| **Average CLV (12-month)** | Mean of `expected_clv_12m` across all scored customers | `clv_predictions.expected_clv_12m.mean()` | ₹163,194.88 |
| **Total Predicted CLV (12-month)** | Sum of `expected_clv_12m` across all scored customers | `clv_predictions.expected_clv_12m.sum()` | ₹1,246,156,085.75 |
| **Revenue at Risk** | Sum of `churn_probability × expected_clv_12m` across all customers | `revenue_at_risk.revenue_at_risk.sum()` | ₹75,359,937.00 |
| **High-Risk Customers** | Count of customers with `risk_category == "High"` (churn probability > 0.6) | `churn_predictions` filter | 3,019 |
| **Customer Acquisition Cost (CAC)** | Average `acquisition_cost` across all customers | `customers.acquisition_cost.mean()` | ₹299.53 |
| **Estimated Total Profit** | Sum of `estimated_profit` across all customers with order history (see `docs/ml_methodology.md` §9 for the cost model) | `profitability.estimated_profit.sum()` | ₹7,322,469.05 |
| **Return Rate** | Total returns ÷ total orders | `COUNT(returns) / COUNT(orders)` | 8.39% |

## Distinguishing Actual / Predicted / Estimated

| Category | KPIs |
|---|---|
| **Actual** (directly observed) | Total Customers, Active Customers, Total Revenue, Monthly Revenue, Total Orders, AOV, Repeat Purchase Rate, Return Rate, CAC |
| **Predicted** (ML model output, validated on held-out data) | Churn Rate/Retention Rate is a training-time label observed in-sample for the KPI, but the underlying `churn_probability` used elsewhere (risk category, revenue-at-risk) is a genuine model prediction — see `docs/ml_methodology.md` §5; Average/Total Predicted CLV |
| **Estimated** (formula-based, documented assumptions) | Revenue at Risk, Estimated Total Profit |

This distinction matters for how each number should be presented to a business audience — see
`docs/ml_methodology.md` §12 for the full explanation and `reports/recommendations.md` for how
it's applied in the project's actual business recommendations.
