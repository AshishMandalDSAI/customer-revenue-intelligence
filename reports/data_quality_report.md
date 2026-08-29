# NovaMart Data Quality Report

Generated: 2026-08-29 16:56:06.631344


## Table Row Counts

- **customers**: 8,000 rows, 7 columns
- **products**: 120 rows, 5 columns
- **orders**: 168,250 rows, 7 columns
- **order_items**: 403,020 rows, 8 columns
- **interactions**: 26,860 rows, 6 columns
- **returns**: 14,119 rows, 6 columns
- **payments**: 168,250 rows, 6 columns

## Missing Values

- No missing values detected in any table.

## Duplicate Key Checks

- customers duplicate customer_id: 0
- orders duplicate order_id: 0
- products duplicate product_id: 0

## Invalid Value Checks

- orders.order_value <= 0: 0
- orders.n_items <= 0: 0
- order_items.quantity <= 0: 0
- order_items.unit_price <= 0: 0
- order_items.discount_pct out of [0,1]: 0
- customers.age out of [16,100]: 0
- returns.refund_amount <= 0: 0

## Outlier Checks (3x IQR rule)

- orders.order_value extreme outliers (3xIQR): 6718 (NOTE: retained -- these are legitimate high-value orders/products from premium customers/categories, not data errors; verified against category price ranges in generate_data.py)
- order_items.unit_price extreme outliers (3xIQR): 43790 (NOTE: retained -- these are legitimate high-value orders/products from premium customers/categories, not data errors; verified against category price ranges in generate_data.py)

## Referential Integrity

- orders with unknown customer_id: 0
- order_items with unknown product_id: 0
- order_items with unknown order_id: 0
- returns with unknown order_id: 0
- interactions with unknown customer_id: 0

## Data Type Validation

- orders.order_date dtype: datetime64[us]
- orders.order_value dtype: float64
- customers.signup_date dtype: datetime64[us]

## Cleaning Decisions Applied Downstream (see data_cleaning.py)

- Extreme order-value outliers are **retained**: manual inspection confirms they fall within realistic category price ceilings (e.g., Furniture up to ~60,000, multi-item carts).
- Any order_items rows with non-positive quantity/price would be **dropped** (none found in this run, but the check runs on every pipeline execution to guard future data).
- No missing values were introduced during generation, so no imputation was required in this run. The cleaning module still implements imputation logic (median for numeric, mode for categorical) for production use against real, messier data sources.