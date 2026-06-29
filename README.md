# TU Student Analytics & RAG Pipeline

A production-minded batch data platform for Thammasat student workshop records. The system ingests Excel snapshots through a layered ETL pipeline (Raw → Staging → Trusted), stores analytics in DuckDB, and exposes a Streamlit dashboard with hybrid RAG: **local Nomic Embed v1.5** for semantic retrieval and **Google Gemini** for grounded answer generation.

---

## Table of Contents

- [Deliverables Map](#deliverables-map)
- [Architecture at a Glance](#architecture-at-a-glance)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Running the Platform](#running-the-platform)
- [Repository Layout](#repository-layout)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)

---

## Deliverables Map

Mapping for the workshop evaluation committee:

| # | Deliverable | Location | Description |
| :---: | :--- | :--- | :--- |
| 1 | Architecture Diagram | [docs/architecture.md](docs/architecture.md) | End-to-end data flow and RAG pipeline (Mermaid) |
| 2 | README / Setup Guide | [README.md](README.md) | Installation, configuration, and runbook |
| 3 | Ingestion & RAG Code | `src/pipeline.py`, `src/dashboard.py` | Batch ETL and Streamlit application |
| 4 | Data Specification | [docs/data_specification.md](docs/data_specification.md) | Profiling, data dictionary, governance matrix |
| 5 | Idempotent Run Evidence | [evidence_idempotent_and_quality.txt](evidence_idempotent_and_quality.txt) | Log proving duplicate-safe re-runs |
| 6 | Data Quality Evidence | [evidence_idempotent_and_quality.txt](evidence_idempotent_and_quality.txt) | Row-count and sum reconciliation checks |
| 7 | RAG Interface | `src/dashboard.py` (RAG Q&A tab) | Local semantic search + Gemini answer generation |
| 8 | Data Governance Policy | [docs/data_specification.md](docs/data_specification.md) §3 | Column classification and access rules |

---

## Architecture at a Glance

```text
Excel (workshop_data)
        │
        ▼
┌───────────────────┐     ┌─────────────────────────────────────┐
│  orchestrate.py   │────▶│  pipeline.py                        │
│  (retry wrapper)  │     │  Raw → Stg → Trusted + embeddings   │
└───────────────────┘     └─────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
              data/raw/*.parquet  data/stg/*.parquet  data/trusted_database.db
                                                        │
                                                        ▼
                                              ┌──────────────────┐
                                              │  dashboard.py    │
                                              │  Analytics + RAG │
                                              └──────────────────┘
```

| Layer | Storage | Purpose |
| :--- | :--- | :--- |
| Raw | `data/raw/raw_workshop_data_{date}.parquet` | Immutable source archive |
| Staging | `data/stg/stg_student_snapshot_{date}.parquet` | Cleaned, deduplicated, embedded |
| Trusted | `data/trusted_database.db` | Queryable analytics + vector store |
| Serving | Streamlit (`localhost:8501`) | Dashboards, audit logs, RAG Q&A |

**RAG split:** embeddings run locally (no API key); Gemini is used only when generating the final natural-language answer.

See [docs/architecture.md](docs/architecture.md) for full diagrams and design rationale.

---

## Prerequisites

| Requirement | Notes |
| :--- | :--- |
| Python | 3.10+ recommended (tested on 3.14) |
| Disk | ~500 MB for Python packages; ~300 MB for Nomic model cache (first run) |
| Network | Required on first pipeline run to download the Hugging Face model |
| Input file | `thammasat_workshop_dataset.xlsx` in the project root |

---

## Quick Start

```bash
# 1. Clone / enter project directory
cd kkpData-Ai Workshop

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run ingestion
python3 src/orchestrate.py --business-date 2026-06-28 --run-id FIRST_BATCH_RUN

# 5. Launch dashboard
python3 -m streamlit run src/dashboard.py
```

Open `http://localhost:8501`. Semantic search works without an API key; enter a Gemini key in the sidebar to enable AI answers.

---

## Environment Variables

| Variable | Required? | Used by | Description |
| :--- | :---: | :--- | :--- |
| `GEMINI_API_KEY` | Optional for pipeline; required for AI answers | `dashboard.py` | Google Gemini API key for grounded answer generation |
| `PII_ENCRYPTION_KEY` | Optional | `pipeline.py` | Fernet key for AES encryption of PII columns at ingest |
| `HF_TOKEN` | Optional | `sentence-transformers` | Hugging Face token for faster model downloads |

```bash
# Optional — only needed for Gemini answer generation in the dashboard
export GEMINI_API_KEY="your-gemini-api-key"

# Optional — enables PII encryption (citizen_id, mobile, email, student_name)
export PII_ENCRYPTION_KEY="your-fernet-key"

# Optional — speeds up first-time model download
export HF_TOKEN="your-huggingface-token"
```

> **Embedding note:** Vector embeddings are generated locally via `nomic-ai/nomic-embed-text-v1.5` during every pipeline run. No API key is required for ingestion or semantic search.
>
> **PII note:** If `PII_ENCRYPTION_KEY` is not set, PII columns are ingested as plaintext (with a warning), which matches the default workshop brief.

---

## Running the Platform

### Ingestion (recommended entry point)

The orchestrator wraps `pipeline.py` with structured logging and exponential-backoff retries for transient failures:

```bash
python3 src/orchestrate.py \
  --business-date 2026-06-28 \
  --run-id FIRST_BATCH_RUN \
  --input-file thammasat_workshop_dataset.xlsx \
  --sheet-name workshop_data
```

| Argument | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `--business-date` | Yes | — | Batch partition date (`YYYY-MM-DD`) |
| `--run-id` | Yes | — | Unique audit identifier per run |
| `--input-file` | No | `thammasat_workshop_dataset.xlsx` | Path to source Excel |
| `--sheet-name` | No | `workshop_data` | Worksheet name |

### Idempotency & quality validation

Runs the pipeline twice and verifies row counts stay at 180:

```bash
python3 src/verify_idempotency.py
```

Capture output for evidence submission:

```bash
python3 src/verify_idempotency.py > evidence_idempotent_and_quality.txt 2>&1
```

### Dashboard

```bash
python3 -m streamlit run src/dashboard.py
```

| Tab | Capability |
| :--- | :--- |
| Analytics Dashboard | KPIs, career/campus charts, GPA distribution |
| Audit Logs | `batch_audit` run history |
| RAG Q&A | Local Nomic semantic search + optional Gemini answers |
| SQL Explorer | Ad-hoc read-only DuckDB queries |

---

## Repository Layout

```text
.
├── README.md                          # This file — setup and runbook
├── requirements.txt                   # Python dependencies
├── evidence_idempotent_and_quality.txt# Idempotency + QC execution log
├── thammasat_workshop_dataset.xlsx    # Source dataset (180 rows)
├── src/
│   ├── pipeline.py                    # Core ETL: Raw → Stg → Trusted + embeddings
│   ├── orchestrate.py                 # Orchestrator with retry logic
│   ├── dashboard.py                   # Streamlit analytics and RAG UI
│   └── verify_idempotency.py          # Automated idempotency test runner
├── docs/
│   ├── architecture.md                # System design and data-flow diagrams
│   └── data_specification.md          # Profiling, dictionary, governance
└── data/                              # Generated at runtime (gitignored)
    ├── raw/                           # Immutable Parquet archives
    ├── stg/                           # Cleaned Parquet with embeddings
    └── trusted_database.db            # DuckDB trusted layer
```

---

## Documentation

| Document | Contents |
| :--- | :--- |
| [docs/architecture.md](docs/architecture.md) | Medallion layers, idempotency, QC gates, RAG flow, trade-offs |
| [docs/data_specification.md](docs/data_specification.md) | Profiling stats, column dictionary, security matrix, QC thresholds |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
| :--- | :--- | :--- |
| `Database file not found` | Pipeline not run yet | Run `orchestrate.py` first |
| `sentence_transformers` import error | Dependencies not installed | `pip install -r requirements.txt` |
| Slow first pipeline run | Model downloading from Hugging Face | Wait for completion; set `HF_TOKEN` to speed up |
| Semantic search falls back to keywords | No `vector_embedding` column or all NULL | Re-run pipeline after code changes |
| `vector_embedding` type mismatch | Schema from older failed run | Delete `data/` and re-run pipeline |
| Gemini answer fails | Missing or invalid API key | Enter key in dashboard sidebar |
| Idempotency test doubles rows | Delete-before-insert broken | Check `snapshot_date` values in staging data |

---

## Security Reminders

- Never commit API keys or Fernet keys to version control.
- The `data/` directory is gitignored; it may contain PII depending on encryption settings.
- RAG retrieval uses `rag_document_text` (safe summaries), not raw PII columns.
