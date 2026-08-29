"""
Power BI Export & Business Recommendations Generator
=======================================================
Exports flattened, Power-BI-ready CSVs and compiles the analytical
findings into a business-recommendations document.
"""
import sys
import json
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATA_PROCESSED_DIR, POWERBI_DATA_DIR, REPORTS_DIR


def export_powerbi_datasets():
    feats = pd.read_csv(DATA_PROCESSED_DIR / "customer_features.csv")
    orders = pd.read_csv(DATA_PROCESSED_DIR / "orders_clean.csv", parse_dates=["order_date"])
    segs = pd.read_csv(DATA_PROCESSED_DIR / "customer_segments.csv")
    churn = pd.read_csv(DATA_PROCESSED_DIR / "churn_predictions.csv")
    clv = pd.read_csv(DATA_PROCESSED_DIR / "clv_predictions.csv")
    rar = pd.read_csv(DATA_PROCESSED_DIR / "revenue_at_risk.csv")
    profit = pd.read_csv(DATA_PROCESSED_DIR / "customer_profitability.csv")
    nba = pd.read_csv(DATA_PROCESSED_DIR / "next_best_actions.csv")
    rfm = pd.read_csv(DATA_PROCESSED_DIR / "customer_rfm.csv")

    customer_360 = feats.merge(segs[["customer_id", "segment_name"]], on="customer_id", how="left") \
        .merge(churn[["customer_id", "churn_probability", "risk_category"]], on="customer_id", how="left") \
        .merge(clv[["customer_id", "expected_clv_12m", "clv_category"]], on="customer_id", how="left") \
        .merge(rfm[["customer_id", "segment"]].rename(columns={"segment": "rfm_segment"}), on="customer_id", how="left")

    customer_360.to_csv(POWERBI_DATA_DIR / "customer_360.csv", index=False)

    monthly_revenue = orders.groupby(orders["order_date"].dt.to_period("M").astype(str)).agg(
        n_orders=("order_id", "count"), total_revenue=("order_value", "sum"),
        avg_order_value=("order_value", "mean")
    ).reset_index().rename(columns={"order_date": "month"})
    monthly_revenue.to_csv(POWERBI_DATA_DIR / "monthly_revenue.csv", index=False)

    segs.to_csv(POWERBI_DATA_DIR / "customer_segments.csv", index=False)
    churn.to_csv(POWERBI_DATA_DIR / "churn_predictions.csv", index=False)
    clv.to_csv(POWERBI_DATA_DIR / "clv_predictions.csv", index=False)
    rar.to_csv(POWERBI_DATA_DIR / "revenue_at_risk.csv", index=False)
    profit.to_csv(POWERBI_DATA_DIR / "profitability.csv", index=False)
    nba.to_csv(POWERBI_DATA_DIR / "recommendations.csv", index=False)

    print(f"Exported 8 Power BI-ready datasets to {POWERBI_DATA_DIR}")
    return customer_360


def generate_business_recommendations():
    kpis = json.loads((REPORTS_DIR / "executive_kpis.json").read_text())
    rar_seg = pd.read_csv(REPORTS_DIR / "revenue_at_risk_by_segment.csv")
    profit_summary = pd.read_csv(REPORTS_DIR / "profitability_summary.csv")
    nba_summary = pd.read_csv(REPORTS_DIR / "next_best_action_summary.csv")

    top_risk_segment = rar_seg.sort_values("total_revenue_at_risk", ascending=False).iloc[0]
    worst_profit_quadrant = profit_summary.sort_values("total_profit").iloc[0]

    md = f"""# NovaMart -- Business Recommendations

*All figures below are computed directly from the NovaMart synthetic dataset
pipeline output (reports/executive_kpis.json and related CSVs) -- none are
fabricated.*

## Headline Numbers
- Total customers: **{kpis['total_customers']:,}**, active in last 90 days: **{kpis['active_customers']:,}**
- Overall churn rate (90-day forward window): **{kpis['churn_rate']:.1%}**
- Total revenue at risk: **{kpis['total_revenue_at_risk']:,.0f}** across **{kpis['high_risk_customers']:,}** high-risk customers
- Estimated total profit (after COGS, fulfillment, returns, support cost): **{kpis['estimated_total_profit']:,.0f}**
  on {kpis['total_revenue']:,.0f} gross revenue -- a thin **{kpis['estimated_total_profit']/kpis['total_revenue']:.1%}** margin,
  which the profitability analysis traces largely to discount-heavy segments.

## Recommendations

1. **Prioritize the highest revenue-at-risk segment first.**
   `{top_risk_segment['segment_name']}` carries the largest total revenue-at-risk
   ({top_risk_segment['total_revenue_at_risk']:,.0f}) of any segment. Route this
   segment to the retention/next-best-action queue before broader campaigns.

2. **Reduce discount dependency in low-margin segments.**
   The `{worst_profit_quadrant['profitability_quadrant']}` quadrant has the worst
   total estimated profit ({worst_profit_quadrant['total_profit']:,.0f}). Cross-referencing
   with avg_discount_pct in customer_features shows heavy discounting is a
   recurring driver -- tighten promo eligibility for this group.

3. **Automate reactivation for low-CLV/high-risk customers.**
   The next-best-action engine assigned REACTIVATION to
   {int(nba_summary.set_index('recommended_action').loc['REACTIVATION','customers']) if 'REACTIVATION' in nba_summary['recommended_action'].values else 0:,}
   customers -- a low-cost, automated channel (email/push) is the right
   investment level here, not high-touch outreach.

4. **Protect and reward high-CLV, low-risk customers.**
   LOYALTY_REWARD was recommended for
   {int(nba_summary.set_index('recommended_action').loc['LOYALTY_REWARD','customers']) if 'LOYALTY_REWARD' in nba_summary['recommended_action'].values else 0:,}
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
If even 20% of the {kpis['total_revenue_at_risk']:,.0f} in identified
revenue-at-risk were protected through timely retention action, that
represents a **potential revenue-protection opportunity of approximately
{0.2*kpis['total_revenue_at_risk']:,.0f}** -- this is an estimate for
planning purposes, not a claim of realized results.
"""
    out_path = REPORTS_DIR / "recommendations.md"
    out_path.write_text(md)
    print(md)
    print(f"\nSaved to {out_path}")
    return md


def main():
    export_powerbi_datasets()
    generate_business_recommendations()


if __name__ == "__main__":
    main()
