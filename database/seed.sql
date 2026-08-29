-- ============================================================
-- Load cleaned CSVs (produced by src/data/*.py) into PostgreSQL.
-- Run with: psql -d novamart -f database/schema.sql
--           psql -d novamart -f database/seed.sql
--           psql -d novamart -f database/views.sql
-- Adjust the paths below if running psql from a different working directory.
-- ============================================================

\copy customers FROM 'data/processed/customers_clean.csv' WITH (FORMAT csv, HEADER true)
\copy products FROM 'data/processed/products_clean.csv' WITH (FORMAT csv, HEADER true)
\copy orders(order_id,customer_id,order_date,order_value,n_items,payment_method,region) FROM 'data/processed/orders_clean.csv' WITH (FORMAT csv, HEADER true)
\copy order_items FROM 'data/processed/order_items_clean.csv' WITH (FORMAT csv, HEADER true)
\copy customer_interactions FROM 'data/processed/interactions_clean.csv' WITH (FORMAT csv, HEADER true)
\copy returns FROM 'data/processed/returns_clean.csv' WITH (FORMAT csv, HEADER true)
\copy payments FROM 'data/processed/payments_clean.csv' WITH (FORMAT csv, HEADER true)
\copy marketing_campaigns FROM 'data/synthetic/marketing_campaigns.csv' WITH (FORMAT csv, HEADER true)

-- customer_features and customer_predictions are wide analytical tables generated
-- by the pipeline (src/data/feature_engineering.py, src/models/*). Load only the
-- columns that match the schema; the full detail remains in the CSV/Power BI exports.
\copy customer_features(customer_id,snapshot_date,tenure_days,frequency,monetary,avg_order_value,recency_days,order_trend,return_rate,n_support_tickets,avg_satisfaction,engagement_score,churned) FROM 'data/processed/customer_features.csv' WITH (FORMAT csv, HEADER true)
