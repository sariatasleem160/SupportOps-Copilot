# SupportOps Copilot — Architecture

## System overview

SupportOps Copilot is a **multi-stage LLM pipeline** for customer support tickets. Each ticket passes through classification, extraction, and reply drafting before results are validated, logged safely, and summarized on a dashboard.

---

## High-level flow

```mermaid
sequenceDiagram
    participant User
    participant UI as app.py / cli.py
    participant Pipe as pipeline.py
    participant Cls as classify.py
    participant Ext as extract.py
    participant Draft as draft_reply.py
    participant LLM as llm_client.py
    participant Anthropic as Anthropic API
    participant PII as pii.py
    participant Schema as schemas.py

    User->>UI: Paste ticket or upload CSV
    UI->>Pipe: process_ticket(message)
    Pipe->>Cls: classify_ticket()
    Cls->>LLM: call_llm_validated()
    LLM->>Anthropic: Messages API (JSON)
    Anthropic-->>LLM: classification JSON
    LLM->>Schema: Pydantic validate (retry x1)
    Schema-->>Cls: ClassificationResult

    Pipe->>Ext: extract_ticket_facts()
    Ext->>LLM: call_llm_validated()
    LLM->>Anthropic: Messages API (JSON)
    Anthropic-->>Ext: extraction JSON
    Ext->>PII: merge regex PII detection

    Pipe->>Draft: draft_reply()
    Draft->>LLM: call_llm_validated() + support_policy.md
    LLM->>Anthropic: Messages API (JSON)
    Anthropic-->>Draft: safe_reply
    Draft->>PII: sanitize_reply()

    Pipe->>PII: redact_for_logging()
    Pipe-->>UI: TicketAnalysis + log payload
    UI-->>User: Classification, extraction, draft, dashboard
```

---

## Module responsibilities

| Layer | Module | Role |
|-------|--------|------|
| **UI** | `app.py` | Streamlit: analyze, batch, dashboard, policy viewer |
| **UI** | `cli.py` | CLI: analyze, batch, evaluate, metrics |
| **Orchestration** | `pipeline.py` | Runs classify → extract → draft → assemble `TicketAnalysis` |
| **LLM** | `llm_client.py` | Anthropic client, JSON parse, retry, cost/latency tracking |
| **Prompts** | `prompts.py` | System prompts + few-shot classification examples |
| **Classification** | `classify.py` | category, priority, sentiment, sla_risk, confidence |
| **Extraction** | `extract.py` | product, request, missing_info, refund, pii_detected |
| **Reply** | `draft_reply.py` | Policy-grounded `safe_reply` from `data/support_policy.md` |
| **Safety** | `pii.py` | Regex detect/redact email, phone, address, card, SSN |
| **Validation** | `schemas.py` | Pydantic models + enum types |
| **Analytics** | `dashboard.py` | Summaries, bar charts, confusion matrix plot |
| **Evaluation** | `evaluate.py` | macro-F1, priority accuracy, key-field accuracy |
| **Data** | `data/*.csv` | 35 train + 35 labeled test tickets |
| **Policy** | `data/support_policy.md` | Refund, access, shipping, PII, escalation rules |

---

## Data flow diagram

```mermaid
flowchart LR
    subgraph In
        T[Raw ticket text]
    end

    subgraph Process
        C[Classify]
        E[Extract]
        D[Draft reply]
        V[Pydantic validate]
        R[Retry on error]
    end

    subgraph Out
        J[Structured JSON]
        S[Safe reply]
        L[Redacted log]
    end

    T --> C --> E --> D --> V
    V -->|fail| R --> V
    V -->|pass| J
    D --> S
    T --> L
```

---

## LLM call pattern

Each ticket triggers **3 Anthropic API calls**:

1. **Classify** — few-shot examples from `prompts.py`, temperature ~0.1  
2. **Extract** — structured fact extraction, temperature ~0.1  
3. **Draft** — reads `support_policy.md`, temperature ~0.4  

All calls request **JSON-only** responses, parsed and validated by Pydantic. On validation failure, the error is appended to the prompt and the call **retries once**.

---

## Security & compliance

- **PII detection** runs via LLM + regex (`pii.py`)
- **Logs** use redacted message text before storage
- **Draft replies** are sanitized to avoid leaking PII
- **Policy** prevents unauthorized refund promises and internal disclosures
- **Escalation** flags urgent / SLA-risk tickets in the UI

---

## Evaluation pipeline

```mermaid
flowchart TB
    CSV[data/tickets_test_labeled.csv]
    EV[evaluate.py]
    CL[classify.py]
    EX[extract.py]
    MET[sklearn metrics]
    RES[results/eval_summary.json]
    CM[results/confusion_matrix.png]

    CSV --> EV
    EV --> CL
    EV --> EX
    CL --> MET
    EX --> MET
    MET --> RES
    MET --> CM
```

Metrics: **category macro-F1**, **priority accuracy**, **key-field accuracy** (product + refund).

---

## Deployment (local)

| File | Purpose |
|------|---------|
| `START.bat` | One-click Windows launcher |
| `run_web.ps1` | PowerShell launcher |
| `config.env` | API key (local only, gitignored) |
| `.env.example` | Template for new setups |

Default URL: **http://127.0.0.1:8501**
