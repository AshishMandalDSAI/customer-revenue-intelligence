# Data Dictionary — `powerbi/powerbi_data/*.csv`

Column-level reference for every file exported by `src/business/recommendations.py`. Types are
as Power BI/pandas would infer them on import.

## `customer_360.csv` (7,636 rows, 39 columns) — one row per snapshot-population customer

| Column | Type | Description |
|---|---|---|
| `customer_id` | Text | Primary key, e.g. `C100000` |
| `signup_date` | Date | When the customer first registered |
| `age` | Whole number | Customer age |
| `gender` | Text | Male / Female / Other |
| `region` | Text | North / South / East / West / Central |
| `acquisition_channel` | Text | Organic Search / Paid Search / Social Media / Referral / Email / Direct / Marketplace |
| `acquisition_cost` | Decimal | Cost to acquire this customer (₹) |
| `tenure_days` | Whole number | Days between signup and snapshot date |
| `frequency` | Whole number | Total order count (feature window) |
| `monetary` | Decimal | Total revenue from this customer (feature window) |
| `avg_order_value` | Decimal | `monetary / frequency` |
| `last_order_date` / `first_order_date` | Date | Order history bounds |
| `std_order_value` | Decimal | Standard deviation of order values (spend volatility) |
| `recency_days` | Whole number | Days since last order as of snapshot |
| `orders_last_90d` / `orders_prior_90d` | Whole number | Order counts in the two most recent 90-day periods before snapshot |
| `order_trend` | Decimal | `(orders_last_90d - orders_prior_90d) / (orders_prior_90d + 1)` — negative = declining |
| `avg_discount_pct` | Decimal (0-1) | Average discount rate across line items |
| `total_qty` | Whole number | Total units purchased |
| `n_categories` | Whole number | Distinct product categories purchased from |
| `n_returns` / `total_refund` / `return_rate` | Number | Return behavior |
| `n_support_tickets` / `avg_satisfaction` / `n_complaints` | Number | Support interaction summary |
| `complaints_last_90d` / `complaints_prior_90d` / `complaint_trend` | Number | Complaint trend, same windowing as orders |
| `engagement_score` | Decimal (0-100) | Composite engagement score — see `docs/ml_methodology.md` §2 |
| `snapshot_date` | Date | The feature/label split date used for this run |
| `churned` | Whole number (0/1) | Actual label: no order in the 90-day window after snapshot |
| `segment_name` | Text | ML cluster segment name (K-Means) |
| `churn_probability` | Decimal (0-1) | **Predicted** churn probability |
| `risk_category` | Text | Low / Medium / High, derived from `churn_probability` |
| `expected_clv_12m` | Decimal | **Predicted** 12-month customer lifetime value (₹) |
| `clv_category` | Text | Low / Medium / High / Very High, quartile-based |
| `rfm_segment` | Text | Rule-based RFM segment name (Champions, At Risk, etc.) |

## `monthly_revenue.csv` (44 rows) — one row per calendar month

| Column | Type | Description |
|---|---|---|
| `month` | Date (YYYY-MM) | Calendar month |
| `n_orders` | Whole number | Orders placed that month |
| `total_revenue` | Decimal | Sum of order values that month |
| `avg_order_value` | Decimal | Mean order value that month |

## `customer_segments.csv` (7,636 rows) — one row per customer

| Column | Type | Description |
|---|---|---|
| `customer_id` | Text | Primary key |
| `cluster_id` | Whole number | Raw K-Means cluster index (0-3 in the current 4-cluster run) |
| `segment_name` | Text | Business-readable name for the cluster |
| `pca_1`, `pca_2` | Decimal | First two principal components, for 2D scatter visuals |

## `churn_predictions.csv` (7,636 rows) — one row per customer

| Column | Type | Description |
|---|---|---|
| `customer_id` | Text | Primary key |
| `churn_probability` | Decimal (0-1) | Predicted churn probability, from the selected model (XGBoost in the current run) |
| `risk_category` | Text | Low (≤0.3) / Medium (0.3-0.6) / High (>0.6) |

## `clv_predictions.csv` (7,636 rows) — one row per customer

| Column | Type | Description |
|---|---|---|
| `customer_id` | Text | Primary key |
| `current_revenue` | Decimal | Actual historical revenue (= `monetary`) |
| `predicted_future_90d_revenue` | Decimal | Model-predicted next-90-day revenue |
| `retention_probability` | Decimal (0-1) | `1 - churn_probability`, clipped to [0.05, 0.98] |
| `expected_clv_12m` | Decimal | Predicted 12-month CLV |
| `clv_category` | Text | Low / Medium / High / Very High |

## `revenue_at_risk.csv` (7,636 rows) — one row per customer

| Column | Type | Description |
|---|---|---|
| `customer_id`, `region`, `acquisition_channel` | Text | Customer attributes for slicing |
| `churn_probability`, `risk_category` | — | Same as `churn_predictions.csv` |
| `expected_clv_12m`, `clv_category` | — | Same as `clv_predictions.csv` |
| `segment_name` | Text | ML cluster segment |
| `revenue_at_risk` | Decimal | `churn_probability × expected_clv_12m` (₹) |

## `profitability.csv` (7,658 rows — full order-history population, see `README.md`)

| Column | Type | Description |
|---|---|---|
| `customer_id` | Text | Primary key |
| `gross_revenue` | Decimal | Total revenue, all-time |
| `total_cogs` | Decimal | Total cost of goods sold |
| `n_orders` | Whole number | Total order count, all-time |
| `gross_contribution` | Decimal | `gross_revenue - total_cogs` |
| `fulfillment_cost` | Decimal | 8% of gross revenue (documented assumption) |
| `return_cost` | Decimal | Refunds plus a 5% penalty |
| `support_cost` | Decimal | ₹150 × support ticket count |
| `acquisition_cost` | Decimal | One-time cost to acquire this customer (shown separately, not netted into `estimated_profit`) |
| `estimated_profit` | Decimal | `gross_contribution - fulfillment_cost - return_cost - support_cost` |
| `profit_margin_pct` | Decimal | `estimated_profit / gross_revenue` |
| `profitability_quadrant` | Text | One of 4 quadrants — see `docs/ml_methodology.md` §9 |
| `recommendation` | Text | Quadrant-specific business recommendation |

## `recommendations.csv` (7,636 rows) — one row per customer

| Column | Type | Description |
|---|---|---|
| `customer_id` | Text | Primary key |
| `recommended_action` | Text | RETENTION / UPSELL / CROSS_SELL / LOYALTY_REWARD / REACTIVATION / PREMIUM_SUPPORT / NO_ACTION |
| `action_reason` | Text | Natural-language justification (rule-based, auditable) |
| `clv_category`, `risk_category`, `expected_clv_12m` | — | Inputs to the rule decision, included for transparency |
