# SupportOps Copilot

A customer support AI system that turns messy tickets into structured analysis, policy-safe draft replies, dashboards, and evaluation metrics.

**Workflow:** messy ticket → classify → extract → validate (Pydantic) → PII-safe logging → draft reply → dashboard → metrics

## Features

| Module | Purpose |
|--------|---------|
| `classify.py` | Category, priority, sentiment, SLA risk (few-shot + JSON) |
| `extract.py` | Product, request summary, missing info, refund flag, PII types |
| `draft_reply.py` | Policy-grounded reply using `data/support_policy.md` |
| `pii.py` | Detect and redact email, phone, address, card, SSN before logging |
| `dashboard.py` | Ticket pattern summaries and charts |
| `evaluate.py` | Macro-F1, priority accuracy, key-field accuracy on labeled CSV |
| `app.py` | Streamlit UI (single ticket, batch upload, dashboard, escalation flags) |
| `cli.py` | Command-line analyze, batch, evaluate, metrics |

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Set your OpenAI key
set OPENAI_API_KEY=sk-...

# Analyze one ticket
python cli.py analyze -m "I was charged twice for Pro plan."

# Run evaluation on 35 labeled test tickets
python evaluate.py

# Launch web app
streamlit run app.py
```

## Data

- `data/tickets_train.csv` — 35 labeled tickets for reference / prompt design
- `data/tickets_test_labeled.csv` — 35 held-out labeled tickets for evaluation
- `data/support_policy.md` — refund, access, shipping, PII, and escalation rules

Required CSV columns: `ticket_id`, `customer_message`, `true_category`, `true_priority`, `true_product`, `true_refund_request`

## Output schema

Each processed ticket produces JSON matching `TicketAnalysis` in `schemas.py`:

- `category`, `priority`, `sentiment`, `sla_risk`
- `product`, `customer_request`, `missing_information`, `refund_request`
- `pii_detected`, `safe_reply`, `confidence`

Validation uses Pydantic; on failure the pipeline **retries once** with the validation error appended to the prompt.

## Evaluation targets

| Metric | Target |
|--------|--------|
| Category macro-F1 | ≥ 0.75 |
| Priority accuracy | ≥ 0.75 |
| Key-field accuracy (product + refund) | ≥ 0.80 |
| PII redaction tests | 100% pass (`pytest tests/test_pii.py`) |

Run `python evaluate.py` to write:

- `results/eval_summary.json`
- `results/confusion_matrix.png`
- `results/latency_cost_summary.json`
- `results/sample_outputs.jsonl`

### Cost and latency (report after evaluation)

Using **gpt-4o-mini** (default), expect roughly:

- **Median latency:** ~2–4 s per ticket (3 LLM calls: classify, extract, draft)
- **Cost per ticket:** ~$0.001–0.003 USD (depends on message length)

Exact numbers are written to `results/latency_cost_summary.json` after each evaluation run.

## Tests

```bash
pytest tests/ -v
```

## Project structure

```
├── data/
│   ├── tickets_train.csv
│   ├── tickets_test_labeled.csv
│   └── support_policy.md
├── app.py
├── cli.py
├── schemas.py
├── prompts.py
├── classify.py
├── extract.py
├── draft_reply.py
├── pii.py
├── dashboard.py
├── evaluate.py
├── llm_client.py
├── pipeline.py
├── results/
├── tests/
├── requirements.txt
└── README.md
```

## Stretch goals included

- Confusion matrix image (`results/confusion_matrix.png`)
- Batch CSV upload in Streamlit
- Escalation queue flag for urgent / SLA-risk tickets
- Session latency and cost tracking

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Required for LLM calls |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model for classify / extract / draft |

## License

MIT — portfolio / educational use.
