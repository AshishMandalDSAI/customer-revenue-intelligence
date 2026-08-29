# NovaMart -- Business Recommendations

*All figures below are computed directly from the NovaMart synthetic dataset
pipeline output (reports/executive_kpis.json and related CSVs) -- none are
fabricated.*

## Headline Numbers
- Total customers: **8,000**, active in last 90 days: **4,648**
- Overall churn rate (90-day forward window): **39.7%**
- Total revenue at risk: **75,359,937** across **3,019** high-risk customers
- Estimated total profit (after COGS, fulfillment, returns, support cost): **7,322,469**
  on 2,954,202,320 gross revenue -- a thin **0.2%** margin,
  which the profitability analysis traces largely to discount-heavy segments.

## Recommendations

1. **Prioritize the highest revenue-at-risk segment first.**
   `Mid-Value Occasional Shoppers` carries the largest total revenue-at-risk
   (63,030,399) of any segment. Route this
   segment to the retention/next-best-action queue before broader campaigns.

2. **Reduce discount dependency in low-margin segments.**
   The `High Revenue / Low Profit` quadrant has the worst
   total estimated profit (-88,182,976). Cross-referencing
   with avg_discount_pct in customer_features shows heavy discounting is a
   recurring driver -- tighten promo eligibility for this group.

3. **Automate reactivation for low-CLV/high-risk customers.**
   The next-best-action engine assigned REACTIVATION to
   2,993
   customers -- a low-cost, automated channel (email/push) is the right
   investment level here, not high-touch outreach.

4. **Protect and reward high-CLV, low-risk customers.**
   LOYALTY_REWARD was recommended for
   3,366
   customers. These customers are not at meaningful churn risk today, but
   they represent the platform's core revenue base and are the highest-ROI
   audience for a formal loyalty program.

5. **Fix service experience before commercial offers for complaint-heavy customers.**
   PREMIUM_SUPPORT was flagged for customers with elevated complaint history
   or low satisfaction scores. SHAP explainability confirms support-complaint
   signals materially raise predicted churn probability for this group --
   a discount alone will not fix a service problem.

6. **Reallocate acquisition budget toward higher-retention channels.**
   Compare `acquisition_channel` against `churn_rate` in customer_360
   (Power BI) -- channels with above-average CAC and above-average churn are
   the weakest capital allocation and are flagged for budget review.

## What is Predicted vs. Estimated vs. Actual
- **Actual**: total revenue, order counts, churn/retention rate in the observed
  label window, RFM scores.
- **Predicted**: churn probability, expected 90-day and 12-month CLV (from
  held-out-validated ML models; see reports/churn_model_comparison.csv and
  reports/clv_model_metrics.csv for real accuracy figures).
- **Estimated**: customer profitability (relies on documented cost
  assumptions in src/analytics/profitability.py), revenue-at-risk
  (churn probability x expected CLV).
- **Potential**: business impact language below is opportunity sizing, not a
  guarantee -- no A/B experiment was run in this project.

## Potential Business Impact (opportunity sizing, not a guaranteed outcome)
If even 20% of the 75,359,937 in identified
revenue-at-risk were protected through timely retention action, that
represents a **potential revenue-protection opportunity of approximately
15,071,987** -- this is an estimate for
planning purposes, not a claim of realized results.
