# AI Analytics Copilot

A business analytics assistant that answers natural-language questions about
the NovaMart dataset -- revenue, churn, CLV, revenue-at-risk, segments, and
recommended actions.

## How it works

1. **`business_context.py`** pulls a grounded snapshot of the *current*
   pipeline output (`reports/executive_kpis.json`, `segment_profiles.csv`,
   `revenue_at_risk_by_*.csv`, `churn_feature_importance.csv`,
   `next_best_action_summary.csv`, `profitability_summary.csv`, and the top
   10 revenue-at-risk customers). No numbers are invented -- everything here
   is read straight off pipeline output files.
2. **`copilot.py`** answers a question in one of two ways:
   - **LLM-backed** (if `OPENAI_API_KEY` is set in `.env`): sends the
     grounded snapshot + question to an LLM via the OpenAI chat completions
     API, with a system prompt (`prompts.py`) that forbids inventing figures
     and requires the model to distinguish Actual / Predicted / Estimated.
   - **Deterministic fallback** (default, no API key required): pattern-
     matches the question against known question types (profitability,
     churn drivers, revenue-at-risk, regional risk, recommended next
     actions, etc.) and answers directly from the same grounded snapshot.
     This means the copilot **always works out of the box** -- it's not a
     stub, it's a fully functional rule-based analytics assistant.
3. If an LLM call is configured but fails (bad key, network, rate limit),
   `copilot.py` catches the exception and transparently falls back to the
   deterministic assistant rather than erroring out.

## Usage

```python
from ai_copilot.copilot import ask

result = ask("Which customer segment is most profitable?")
print(result["answer"])
print(result["backend"])  # tells you which backend actually answered
```

Or from the command line:

```bash
python ai_copilot/copilot.py
```

Or in the Streamlit dashboard: navigate to the **AI Analytics Copilot** page.

## Enabling the LLM backend

1. Get an OpenAI API key.
2. Copy `.env.example` to `.env` and set `OPENAI_API_KEY=sk-...`.
3. (Optional) set `COPILOT_MODEL` to a different model name (default
   `gpt-4o-mini`).

No key is ever hardcoded in source -- it's read from the environment via
`src/config.py`.

## Supported question types (deterministic fallback)

- Revenue decline / trend questions
- "Which segment is most profitable?"
- "Which customers should the sales team contact?"
- "How much revenue is at risk?"
- "What are the biggest churn drivers?"
- "Which region has the highest churn / revenue-at-risk?"
- "What should marketing do next month?"
- "Show me the top N high-value customers at risk."
- Anything else falls back to a headline-KPI summary with suggested
  question types.
