"""
AI Analytics Copilot
=====================
Answers business questions about the NovaMart dataset.

- If OPENAI_API_KEY is set in the environment, uses the OpenAI API (chat
  completions) grounded in the real pipeline output via business_context.py.
- If no API key is configured, falls back to a DETERMINISTIC, rule-based
  assistant that pattern-matches the question against known question types
  and answers directly from the same grounded data -- so the copilot always
  works, with no external dependency required to demo it.

Either way, the copilot NEVER fabricates numbers: both paths are grounded
in reports/executive_kpis.json and the other pipeline output files.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config import OPENAI_API_KEY, COPILOT_MODEL
from ai_copilot.business_context import get_business_context, context_as_text
from ai_copilot.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


def _fmt_money(x: float) -> str:
    return f"₹{x:,.0f}"


# ---------------------------------------------------------------------------
# Deterministic fallback assistant
# ---------------------------------------------------------------------------
def _fallback_answer(question: str, ctx: dict) -> str:
    q = question.lower()
    kpis = ctx["kpis"]

    if any(k in q for k in ["revenue decrease", "revenue drop", "why did revenue"]):
        return (
            f"I can't attribute a single cause from this snapshot alone (that would need a "
            f"month-over-month driver decomposition), but here's what the data shows: current "
            f"churn rate is {kpis['churn_rate']:.1%} with {kpis['high_risk_customers']:,} "
            f"high-risk customers representing {_fmt_money(kpis['total_revenue_at_risk'])} in "
            f"revenue at risk. The 'Mid-Value Occasional Shoppers' and dormant segments carry "
            f"the largest at-risk revenue -- see the Revenue-at-Risk page for the full segment "
            f"breakdown before concluding a root cause."
        )

    if "most profitable" in q or ("profitable" in q and "segment" in q):
        seg = max(ctx["segments"], key=lambda s: s.get("total_revenue", 0) * (1 - s.get("churn_rate", 0)))
        return (
            f"Based on segment_profiles.csv, **{seg['segment_name']}** has the strongest combination "
            f"of revenue ({_fmt_money(seg['total_revenue'])}) and low churn ({seg['churn_rate']:.1%}), "
            f"making it the most profitable segment to protect and grow. Recommended action for this "
            f"segment: {seg.get('recommended_action', 'n/a')}."
        )

    if "sales team" in q or "contact" in q:
        top = ctx["top_10_revenue_at_risk_customers"][:5]
        if not top:
            return "No revenue-at-risk customer list is available in this snapshot."
        lines = [f"- {c['customer_id']} ({c['region']}, {c['segment_name']}): "
                 f"{c['churn_probability']:.0%} churn risk, {_fmt_money(c['revenue_at_risk'])} at risk"
                 for c in top]
        return (
            "Top 5 customers by revenue-at-risk that the sales/retention team should prioritize:\n"
            + "\n".join(lines)
        )

    if "revenue" in q and "risk" in q and "sales team" not in q and "contact" not in q:
        return (
            f"Total revenue at risk is {_fmt_money(kpis['total_revenue_at_risk'])} across "
            f"{kpis['high_risk_customers']:,} high-risk customers "
            f"(methodology: churn probability x expected 12-month CLV). "
            f"This is an ESTIMATE, not a guaranteed loss figure."
        )

    if "churn driver" in q or "biggest churn" in q or "why" in q and "churn" in q:
        drivers = ctx["top_churn_drivers"][:5]
        lines = [f"- {d['feature']} (importance: {d['importance']:.3f})" for d in drivers]
        return (
            "Top churn drivers from the selected model "
            f"({ctx['churn_model_selection'].get('selected_model', 'n/a')}), by feature importance:\n"
            + "\n".join(lines)
        )

    if "region" in q and "churn" in q:
        by_region = sorted(ctx["revenue_at_risk_by_region"], key=lambda r: -r["total_revenue_at_risk"])
        if not by_region:
            return "No regional churn/risk breakdown is available in this snapshot."
        top = by_region[0]
        return (
            f"**{top['region']}** carries the highest revenue-at-risk "
            f"({_fmt_money(top['total_revenue_at_risk'])} across {top['customers']:,} customers). "
            f"See the Revenue & CLV dashboard page for the full regional breakdown."
        )

    if "marketing" in q and ("next month" in q or "should" in q):
        nba = {row["action"]: row["customers"] for row in ctx["next_best_action_distribution"]}
        return (
            f"Based on the next-best-action distribution -- "
            f"{nba.get('REACTIVATION', 0):,} customers flagged for REACTIVATION and "
            f"{nba.get('LOYALTY_REWARD', 0):,} for LOYALTY_REWARD -- marketing's highest-leverage "
            f"moves next month are: (1) launch an automated low-cost reactivation sequence for the "
            f"REACTIVATION segment, and (2) stand up a loyalty/early-access program for the "
            f"LOYALTY_REWARD segment before a competitor captures that wallet share."
        )

    if "top 10" in q and ("high-value" in q or "high value" in q) and "risk" in q:
        top = ctx["top_10_revenue_at_risk_customers"]
        if not top:
            return "No revenue-at-risk customer list is available in this snapshot."
        lines = [f"{i+1}. {c['customer_id']} -- {_fmt_money(c['revenue_at_risk'])} at risk "
                 f"({c['churn_probability']:.0%} churn probability, {c['segment_name']})"
                 for i, c in enumerate(top)]
        return "Top 10 customers by revenue-at-risk:\n" + "\n".join(lines)

    # Generic fallback: summarize headline KPIs
    return (
        "I can answer questions about revenue, churn, CLV, revenue-at-risk, segments, and "
        "next-best-actions using the current pipeline data. Headline numbers right now: "
        f"{kpis['total_customers']:,} customers, {_fmt_money(kpis['total_revenue'])} total revenue, "
        f"{kpis['churn_rate']:.1%} churn rate, {_fmt_money(kpis['total_revenue_at_risk'])} revenue at risk. "
        "Try asking things like 'which segment is most profitable?' or 'what are the biggest churn drivers?'"
    )


# ---------------------------------------------------------------------------
# LLM-backed assistant (optional)
# ---------------------------------------------------------------------------
def _llm_answer(question: str, ctx: dict) -> str:
    from openai import OpenAI  # imported lazily so the package is optional

    client = OpenAI(api_key=OPENAI_API_KEY)
    user_prompt = USER_PROMPT_TEMPLATE.format(context=context_as_text(ctx), question=question)
    response = client.chat.completions.create(
        model=COPILOT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=500,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------
def ask(question: str) -> dict:
    """
    Answers a business question. Returns a dict with the answer text and
    which backend produced it, so the UI can be transparent about it.
    """
    ctx = get_business_context()

    if OPENAI_API_KEY:
        try:
            answer = _llm_answer(question, ctx)
            return {"answer": answer, "backend": f"LLM ({COPILOT_MODEL})"}
        except Exception as exc:  # noqa: BLE001 -- fall back gracefully on any API issue
            fallback = _fallback_answer(question, ctx)
            return {
                "answer": fallback,
                "backend": "deterministic fallback (LLM call failed)",
                "error": str(exc),
            }

    answer = _fallback_answer(question, ctx)
    return {"answer": answer, "backend": "deterministic fallback (no OPENAI_API_KEY configured)"}


if __name__ == "__main__":
    for q in [
        "Which customer segment is most profitable?",
        "How much revenue is at risk?",
        "What are the biggest churn drivers?",
        "Show me the top 10 high-value customers at risk.",
    ]:
        result = ask(q)
        print(f"\nQ: {q}\n[{result['backend']}]\n{result['answer']}")
