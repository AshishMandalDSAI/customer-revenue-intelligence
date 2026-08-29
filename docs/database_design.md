# Database Design — NovaMart CRIP

**Engine:** PostgreSQL (16, as pinned in `docker-compose.yml`)
**Schema file:** `database/schema.sql`
**Views:** `database/views.sql`
**Bulk load:** `database/seed.sql`

> **Sandbox limitation, stated plainly:** No PostgreSQL server was available in the development
> sandbox this project was built in. `schema.sql`, `views.sql`, and `seed.sql` have been written
> to be directly runnable against a real Postgres instance and are internally consistent (every
> column referenced in a view exists in the table it selects from, every foreign key target
> exists, every `\copy` source file is a real output of the pipeline) — but they have **not**
> actually been executed against a live database as part of this build. See
> `docs/installation.md` for exact commands to verify this yourself, and
> `reports/dashboard_test_results.md` for what has and hasn't been verified in this environment.
> The API and dashboard currently run against the flat CSV files in `data/processed/` instead
> (see `docs/architecture.md` §2 for why, and how to switch).

## 1. Entity-relationship overview

```mermaid
erDiagram
    customers ||--o{ orders : places
    customers ||--o{ customer_interactions : contacts_support
    customers ||--o{ returns : returns_items
    customers ||--o{ payments : pays
    customers ||--|| customer_features : "has (0 or 1)"
    customers ||--|| customer_predictions : "has (0 or 1)"
    orders ||--o{ order_items : contains
    orders ||--|| payments : "paid by"
    orders ||--o{ returns : "may generate"
    products ||--o{ order_items : "ordered as"

    customers {
        varchar customer_id PK
        date signup_date
        smallint age
        varchar gender
        varchar region
        varchar acquisition_channel
        numeric acquisition_cost
    }
    products {
        varchar product_id PK
        varchar product_name
        varchar category
        numeric unit_price
        numeric unit_cost
    }
    orders {
        varchar order_id PK
        varchar customer_id FK
        timestamp order_date
        numeric order_value
        smallint n_items
        varchar payment_method
        varchar region
    }
    order_items {
        varchar order_item_id PK
        varchar order_id FK
        varchar product_id FK
        varchar category
        smallint quantity
        numeric unit_price
        numeric discount_pct
        numeric line_total
    }
    customer_interactions {
        varchar interaction_id PK
        varchar customer_id FK
        timestamp interaction_date
        varchar channel
        varchar type
        smallint satisfaction_score
    }
    returns {
        varchar return_id PK
        varchar order_id FK
        varchar customer_id FK
        timestamp return_date
        numeric refund_amount
        varchar reason
    }
    payments {
        varchar order_id PK_FK
        varchar customer_id FK
        varchar payment_method
        numeric amount
        timestamp payment_date
        varchar status
    }
    marketing_campaigns {
        varchar campaign_id PK
        varchar campaign_name
        varchar channel
        date start_date
        date end_date
        numeric budget
        varchar target_region
    }
    customer_features {
        varchar customer_id PK_FK
        date snapshot_date
        int tenure_days
        int frequency
        numeric monetary
        numeric avg_order_value
        int recency_days
        numeric order_trend
        numeric return_rate
        int n_support_tickets
        numeric avg_satisfaction
        numeric engagement_score
        smallint churned
    }
    customer_predictions {
        varchar customer_id PK_FK
        numeric churn_probability
        varchar risk_category
        numeric expected_clv_12m
        varchar clv_category
        numeric revenue_at_risk
        varchar recommended_action
        text action_reason
        timestamp scored_at
    }
```

## 2. Tables (10, as required)

| Table | Purpose | Row source |
|---|---|---|
| `customers` | Customer master data (demographics, acquisition) | `data/processed/customers_clean.csv` |
| `products` | Product catalog (120 SKUs across 12 categories in this build) | `data/processed/products_clean.csv` |
| `orders` | One row per order | `data/processed/orders_clean.csv` |
| `order_items` | One row per order line item (product/qty/discount) | `data/processed/order_items_clean.csv` |
| `customer_interactions` | Support contacts, with satisfaction score | `data/processed/interactions_clean.csv` |
| `returns` | Product returns and refunds | `data/processed/returns_clean.csv` |
| `payments` | Payment record per order | `data/processed/payments_clean.csv` |
| `marketing_campaigns` | Campaign metadata (channel, budget, dates) | `data/synthetic/marketing_campaigns.csv` |
| `customer_features` | Snapshot-based analytical feature store | `data/processed/customer_features.csv` (partial column set — see `seed.sql`) |
| `customer_predictions` | Churn/CLV/revenue-risk/NBA model output | Populated by loading `data/processed/churn_predictions.csv`, `clv_predictions.csv`, `revenue_at_risk.csv`, `next_best_actions.csv` — a small combining script would need to be added to auto-join and load these 4 CSVs into this one table; `seed.sql` currently loads `customer_features` but leaves `customer_predictions` loading as a documented next step (see `docs/installation.md`) |

Primary keys, foreign keys (with `REFERENCES`), `CHECK` constraints (e.g.
`age BETWEEN 16 AND 100`, `order_value > 0`, `discount_pct BETWEEN 0 AND 1`), and indexes on
every foreign key / frequently-filtered column (`region`, `acquisition_channel`, `order_date`,
`signup_date`, `category`) are all defined in `database/schema.sql`.

## 3. Views (6, as required)

| View | Purpose |
|---|---|
| `customer_360_view` | One row per customer joining core demographics + features + predictions |
| `monthly_revenue_view` | Monthly order count, revenue, AOV, active customers |
| `customer_rfm_view` | SQL-native RFM scoring via `NTILE(5)` window functions (mirrors `src/analytics/rfm.py`'s Python scoring for BI-tool consumption) |
| `customer_churn_view` | Churn probability + risk category joined with recency/trend/engagement |
| `customer_clv_view` | Current revenue vs. expected 12-month CLV |
| `revenue_at_risk_view` | Revenue-at-risk aggregated by region |

`database/views.sql` also includes commented example analytical queries for average order
value, repeat purchase rate, churn rate, top customers, and revenue by region/segment (spec
section 6 requirements), ready to uncomment and run.

## 4. Design decisions worth calling out

- **VARCHAR IDs, not UUIDs or serial integers.** Customer/order/product IDs are generated as
  human-readable strings (`C100000`, `O1000000`, `P0001`) by `generate_data.py`, matching how a
  business/analyst audience typically reads sample data in a demo (versus opaque UUIDs).
- **`customer_features` and `customer_predictions` are separate tables**, not columns bolted
  onto `customers`, because they have different refresh cadences: `customers` is near-static
  master data; `customer_features`/`customer_predictions` are regenerated on every pipeline
  run. Keeping them separate means re-scoring never risks corrupting master data.
- **RFM is computed twice, deliberately** — once in Python (`src/analytics/rfm.py`, using
  `pd.qcut` on ranks) for the ML/dashboard/API path, and once in SQL (`customer_rfm_view`, using
  `NTILE(5)`) for BI tools that connect directly to Postgres. The two are expected to produce
  very similar but not always bit-identical quantile boundaries (different tie-breaking between
  `pd.qcut` and `NTILE`) — this is a known, acceptable characteristic of maintaining a
  SQL-native view alongside the Python pipeline, not a bug.
- **No partitioning / sharding.** At 8,000 customers / ~168K orders / ~403K order items (this
  build's default scale — see `docs/architecture.md` and `src/config.py`), a single unpartitioned
  Postgres instance is more than sufficient. At the master spec's target scale (50K customers /
  250K+ orders) this would still comfortably fit on a single instance; partitioning would only
  become worth considering at 10-100x that scale.
