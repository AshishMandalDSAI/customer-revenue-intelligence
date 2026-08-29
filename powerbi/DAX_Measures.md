# DAX Measures — NovaMart CRIP

Ready-to-paste DAX measures for a Power BI report built on the CSVs in `powerbi_data/` (see
`README.md` for import/relationship setup). These have been written against the actual column
names in the exported CSVs (verified against `data_dictionary.md`) but **have not been
paste-tested inside Power BI Desktop itself**, since Power BI Desktop is not available in this
build's sandbox — double-check table/column names match your import if you renamed anything.

## Core KPI measures

```dax
Total Customers = DISTINCTCOUNT(customer_360[customer_id])

Total Revenue = SUM(customer_360[monetary])

Total Orders = SUM(customer_360[frequency])

Average Order Value =
DIVIDE([Total Revenue], [Total Orders], 0)

Repeat Purchase Rate =
DIVIDE(
    CALCULATE(DISTINCTCOUNT(customer_360[customer_id]), customer_360[frequency] > 1),
    CALCULATE(DISTINCTCOUNT(customer_360[customer_id]), customer_360[frequency] > 0),
    0
)

Churn Rate =
DIVIDE(
    CALCULATE(DISTINCTCOUNT(customer_360[customer_id]), customer_360[churned] = 1),
    [Total Customers],
    0
)

Retention Rate = 1 - [Churn Rate]

Average CLV (12m) = AVERAGE(customer_360[expected_clv_12m])

Total Predicted CLV (12m) = SUM(customer_360[expected_clv_12m])

Total Revenue at Risk = SUM(revenue_at_risk[revenue_at_risk])

High-Risk Customers =
CALCULATE(
    DISTINCTCOUNT(customer_360[customer_id]),
    customer_360[risk_category] = "High"
)

High-Risk Customer % =
DIVIDE([High-Risk Customers], [Total Customers], 0)
```

## Profitability measures

```dax
Total Estimated Profit = SUM(profitability[estimated_profit])

Overall Profit Margin =
DIVIDE([Total Estimated Profit], SUM(profitability[gross_revenue]), 0)

Customers in Low Revenue / Low Profit =
CALCULATE(
    DISTINCTCOUNT(profitability[customer_id]),
    profitability[profitability_quadrant] = "Low Revenue / Low Profit"
)

-- Repeat the pattern above for the other 3 quadrants:
--   "High Revenue / High Profit", "High Revenue / Low Profit", "Low Revenue / High Profit"
```

## Segmentation measures

```dax
Revenue by Segment =
CALCULATE([Total Revenue], ALLEXCEPT(customer_360, customer_360[segment_name]))

Churn Rate by Segment =
CALCULATE([Churn Rate], ALLEXCEPT(customer_360, customer_360[segment_name]))

Segment Size % =
DIVIDE(
    DISTINCTCOUNT(customer_360[customer_id]),
    CALCULATE(DISTINCTCOUNT(customer_360[customer_id]), ALL(customer_360[segment_name])),
    0
)
```

## Time-intelligence measures (on `monthly_revenue`)

```dax
Monthly Revenue = SUM(monthly_revenue[total_revenue])

Revenue MoM % Change =
VAR CurrentMonth = [Monthly Revenue]
VAR PriorMonth =
    CALCULATE([Monthly Revenue], DATEADD(monthly_revenue[month], -1, MONTH))
RETURN
    DIVIDE(CurrentMonth - PriorMonth, PriorMonth, BLANK())

Rolling 3-Month Avg Revenue =
AVERAGEX(
    DATESINPERIOD(monthly_revenue[month], LASTDATE(monthly_revenue[month]), -3, MONTH),
    [Monthly Revenue]
)
```

**Note:** `DATEADD`/`DATESINPERIOD` require `monthly_revenue[month]` to be marked as a proper
**Date** column and to be part of a continuous date table (Power BI's auto date/time or a manual
calendar table) — see `README.md` step 2 for the import-time type fix.

## Next-best-action measures

```dax
Customers Recommended for Retention =
CALCULATE(
    DISTINCTCOUNT(recommendations[customer_id]),
    recommendations[recommended_action] = "RETENTION"
)

-- Repeat for: "UPSELL", "CROSS_SELL", "LOYALTY_REWARD", "REACTIVATION", "PREMIUM_SUPPORT", "NO_ACTION"

Revenue-Weighted Action Priority =
SUMX(
    recommendations,
    recommendations[expected_clv_12m] *
        SWITCH(
            recommendations[risk_category],
            "High", 3,
            "Medium", 2,
            "Low", 1,
            0
        )
)
```
This last measure is a simple example of combining CLV and risk into a single sortable priority
score for a table visual — adjust the weighting to match your own business judgment.
