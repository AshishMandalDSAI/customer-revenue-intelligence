-- ============================================================
-- NovaMart Customer 360 & Revenue Intelligence Platform
-- PostgreSQL Schema
-- ============================================================

DROP TABLE IF EXISTS customer_predictions CASCADE;
DROP TABLE IF EXISTS customer_features CASCADE;
DROP TABLE IF EXISTS marketing_campaigns CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS returns CASCADE;
DROP TABLE IF EXISTS customer_interactions CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE customers (
    customer_id         VARCHAR(12) PRIMARY KEY,
    signup_date         DATE NOT NULL,
    age                 SMALLINT CHECK (age BETWEEN 16 AND 100),
    gender              VARCHAR(10),
    region              VARCHAR(20) NOT NULL,
    acquisition_channel VARCHAR(30) NOT NULL,
    acquisition_cost    NUMERIC(10,2) NOT NULL DEFAULT 0
);
CREATE INDEX idx_customers_region ON customers(region);
CREATE INDEX idx_customers_channel ON customers(acquisition_channel);
CREATE INDEX idx_customers_signup ON customers(signup_date);

CREATE TABLE products (
    product_id   VARCHAR(10) PRIMARY KEY,
    product_name VARCHAR(200) NOT NULL,
    category     VARCHAR(50) NOT NULL,
    unit_price   NUMERIC(10,2) NOT NULL CHECK (unit_price > 0),
    unit_cost    NUMERIC(10,2) NOT NULL CHECK (unit_cost > 0)
);
CREATE INDEX idx_products_category ON products(category);

CREATE TABLE orders (
    order_id       VARCHAR(12) PRIMARY KEY,
    customer_id    VARCHAR(12) NOT NULL REFERENCES customers(customer_id),
    order_date     TIMESTAMP NOT NULL,
    order_value    NUMERIC(12,2) NOT NULL CHECK (order_value > 0),
    n_items        SMALLINT NOT NULL CHECK (n_items > 0),
    payment_method VARCHAR(30) NOT NULL,
    region         VARCHAR(20)
);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_date ON orders(order_date);

CREATE TABLE order_items (
    order_item_id VARCHAR(12) PRIMARY KEY,
    order_id      VARCHAR(12) NOT NULL REFERENCES orders(order_id),
    product_id    VARCHAR(10) NOT NULL REFERENCES products(product_id),
    category      VARCHAR(50),
    quantity      SMALLINT NOT NULL CHECK (quantity > 0),
    unit_price    NUMERIC(10,2) NOT NULL,
    discount_pct  NUMERIC(4,3) CHECK (discount_pct BETWEEN 0 AND 1),
    line_total    NUMERIC(12,2) NOT NULL
);
CREATE INDEX idx_items_order ON order_items(order_id);
CREATE INDEX idx_items_product ON order_items(product_id);

CREATE TABLE customer_interactions (
    interaction_id      VARCHAR(10) PRIMARY KEY,
    customer_id         VARCHAR(12) NOT NULL REFERENCES customers(customer_id),
    interaction_date    TIMESTAMP NOT NULL,
    channel              VARCHAR(30),
    type                VARCHAR(30),
    satisfaction_score  SMALLINT CHECK (satisfaction_score BETWEEN 1 AND 5)
);
CREATE INDEX idx_interactions_customer ON customer_interactions(customer_id);

CREATE TABLE returns (
    return_id     VARCHAR(10) PRIMARY KEY,
    order_id      VARCHAR(12) NOT NULL REFERENCES orders(order_id),
    customer_id   VARCHAR(12) NOT NULL REFERENCES customers(customer_id),
    return_date   TIMESTAMP NOT NULL,
    refund_amount NUMERIC(12,2) NOT NULL CHECK (refund_amount > 0),
    reason        VARCHAR(60)
);
CREATE INDEX idx_returns_customer ON returns(customer_id);

CREATE TABLE payments (
    order_id       VARCHAR(12) PRIMARY KEY REFERENCES orders(order_id),
    customer_id    VARCHAR(12) NOT NULL REFERENCES customers(customer_id),
    payment_method VARCHAR(30),
    amount         NUMERIC(12,2),
    payment_date   TIMESTAMP,
    status         VARCHAR(20)
);

CREATE TABLE marketing_campaigns (
    campaign_id   VARCHAR(10) PRIMARY KEY,
    campaign_name VARCHAR(100),
    channel       VARCHAR(30),
    start_date    DATE,
    end_date      DATE,
    budget        NUMERIC(12,2),
    target_region VARCHAR(20)
);

-- Analytical feature store (populated by src/data/feature_engineering.py)
CREATE TABLE customer_features (
    customer_id       VARCHAR(12) PRIMARY KEY REFERENCES customers(customer_id),
    snapshot_date      DATE,
    tenure_days         INT,
    frequency           INT,
    monetary            NUMERIC(14,2),
    avg_order_value     NUMERIC(12,2),
    recency_days        INT,
    order_trend         NUMERIC(8,4),
    return_rate         NUMERIC(6,4),
    n_support_tickets   INT,
    avg_satisfaction    NUMERIC(4,2),
    engagement_score    NUMERIC(6,2),
    churned             SMALLINT
);

-- ML output store (populated after model training / scoring)
CREATE TABLE customer_predictions (
    customer_id           VARCHAR(12) PRIMARY KEY REFERENCES customers(customer_id),
    churn_probability      NUMERIC(6,4),
    risk_category           VARCHAR(10),
    expected_clv_12m        NUMERIC(14,2),
    clv_category             VARCHAR(12),
    revenue_at_risk          NUMERIC(14,2),
    recommended_action       VARCHAR(30),
    action_reason            TEXT,
    scored_at                TIMESTAMP DEFAULT now()
);
