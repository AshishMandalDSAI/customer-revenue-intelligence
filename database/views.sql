-- ============================================================
-- NovaMart Analytical Views
-- ============================================================

-- Customer 360: one row per customer, joining core + ML outputs
CREATE OR REPLACE VIEW customer_360_view AS
SELECT
    c.customer_id, c.signup_date, c.age, c.gender, c.region, c.acquisition_channel,
    f.tenure_days, f.frequency, f.monetary, f.avg_order_value, f.recency_days,
    f.return_rate, f.engagement_score, f.churned,
    p.churn_probability, p.risk_category, p.expected_clv_12m, p.clv_category,
    p.revenue_at_risk, p.recommended_action
FROM customers c
LEFT JOIN customer_features f ON c.customer_id = f.customer_id
LEFT JOIN customer_predictions p ON c.customer_id = p.customer_id;

-- Monthly revenue trend
CREATE OR REPLACE VIEW monthly_revenue_view AS
SELECT
    date_trunc('month', order_date)::date AS month,
    COUNT(*) AS n_orders,
    SUM(order_value) AS total_revenue,
    AVG(order_value) AS avg_order_value,
    COUNT(DISTINCT customer_id) AS active_customers
FROM orders
GROUP BY 1
ORDER BY 1;

-- RFM view (recomputed in SQL for BI-tool consumption; scores mirror src/analytics/rfm.py)
CREATE OR REPLACE VIEW customer_rfm_view AS
SELECT
    customer_id,
    recency_days,
    frequency,
    monetary,
    NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
    NTILE(5) OVER (ORDER BY frequency ASC) AS f_score,
    NTILE(5) OVER (ORDER BY monetary ASC) AS m_score
FROM customer_features;

-- Churn view
CREATE OR REPLACE VIEW customer_churn_view AS
SELECT
    c.customer_id, c.region, c.acquisition_channel,
    p.churn_probability, p.risk_category, f.recency_days, f.order_trend, f.engagement_score
FROM customers c
JOIN customer_predictions p ON c.customer_id = p.customer_id
JOIN customer_features f ON c.customer_id = f.customer_id;

-- CLV view
CREATE OR REPLACE VIEW customer_clv_view AS
SELECT
    c.customer_id, c.region, f.monetary AS current_revenue,
    p.expected_clv_12m, p.clv_category
FROM customers c
JOIN customer_predictions p ON c.customer_id = p.customer_id
JOIN customer_features f ON c.customer_id = f.customer_id;

-- Revenue-at-risk view
CREATE OR REPLACE VIEW revenue_at_risk_view AS
SELECT
    c.region,
    COUNT(*) AS customers,
    SUM(p.revenue_at_risk) AS total_revenue_at_risk,
    AVG(p.churn_probability) AS avg_churn_probability
FROM customers c
JOIN customer_predictions p ON c.customer_id = p.customer_id
GROUP BY c.region
ORDER BY total_revenue_at_risk DESC;

-- ============================================================
-- Example analytical queries (spec section 6)
-- ============================================================

-- Average order value
-- SELECT AVG(order_value) FROM orders;

-- Repeat purchase rate
-- SELECT
--   COUNT(*) FILTER (WHERE frequency > 1)::float / NULLIF(COUNT(*) FILTER (WHERE frequency > 0), 0)
-- FROM customer_features;

-- Churn rate
-- SELECT AVG(churned::int)::numeric(6,4) FROM customer_features;

-- Top 10 customers by revenue
-- SELECT customer_id, monetary FROM customer_features ORDER BY monetary DESC LIMIT 10;

-- Revenue by region
-- SELECT region, SUM(order_value) FROM orders GROUP BY region ORDER BY 2 DESC;

-- Revenue by segment (requires customer_segments table/import)
-- SELECT segment_name, SUM(monetary) FROM customer_360_view v
--   JOIN customer_segments s ON v.customer_id = s.customer_id GROUP BY segment_name;
