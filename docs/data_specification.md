# Data Specification & Governance

Data discovery, profiling, dictionary, quality rules, and security classification for `thammasat_workshop_dataset.xlsx` and the derived trusted-layer objects.

---

## Table of Contents

- [Source Overview](#source-overview)
- [Profiling Report](#profiling-report)
- [Quality Acceptance Criteria](#quality-acceptance-criteria)
- [Data Dictionary](#data-dictionary)
- [Pipeline-Derived Columns](#pipeline-derived-columns)
- [Trusted Layer Objects](#trusted-layer-objects)
- [Security & Governance Matrix](#security--governance-matrix)
- [RAG Corpus Safety](#rag-corpus-safety)

---

## Source Overview

| Attribute | Value |
| :--- | :--- |
| File | `thammasat_workshop_dataset.xlsx` |
| Sheet | `workshop_data` |
| Rows | 180 |
| Columns | 49 |
| Snapshot date | `2026-06-28` (all rows) |
| Record type | `student` (100%) |
| Grain | One row per student per snapshot |

**Business keys**

| Key | Column(s) | Usage |
| :--- | :--- | :--- |
| Primary business key | `entity_id` | Unique student entity (e.g. `SK0001`) |
| Alternate keys | `student_no`, `citizen_id`, `email` | Human-readable identifiers |
| Snapshot key | `snapshot_date` | Partition for idempotent reload |
| Composite uniqueness | `(entity_id, snapshot_date)` | Deduplication rule in staging |

---

## Profiling Report

Summary statistics from the source workbook (180 rows).

### Categorical distributions

**Campus (`campus`)**

| Value | Count | Share |
| :--- | ---: | ---: |
| Rangsit | 144 | 80.0% |
| Tha Phra Chan | 36 | 20.0% |

**Level (`level`)**

| Value | Count | Share |
| :--- | ---: | ---: |
| Undergraduate | 140 | 77.8% |
| Postgraduate | 40 | 22.2% |

**Status (`status`)**

| Value | Count |
| :--- | ---: |
| Active | 161 |
| Leave | 6 |
| Exchange | 6 |
| Withdrawn | 4 |
| Graduated | 3 |

**Top programs (`program_id`)**

| Program ID | Program | Count |
| :--- | :--- | ---: |
| TU-SCI-UG | Computer Science / Data Science | 29 |
| TU-ENG-UG | Engineering | 24 |
| TU-PH-PG | Public Health (Postgrad) | 23 |
| TU-COM-UG | Communication Arts | 18 |
| TU-SIIT-UG | Sirindhorn International Institute of Tech | 15 |

**Top career interests (`career_interest`)**

| Interest | Count | Share |
| :--- | ---: | ---: |
| Data Engineer / AI Engineer | 68 | 37.8% |
| Health Data Analyst | 37 | 20.6% |
| Data Analyst / BI Analyst | 29 | 16.1% |
| Data Governance / Policy Analyst | 25 | 13.9% |
| Digital Analytics / Product Analyst | 15 | 8.3% |

### Numeric summary

Baseline values used by pipeline QC assertions (must match trusted layer after load):

| Metric | `gpa` | `credit_earned` | `expected_salary_thb` |
| :--- | ---: | ---: | ---: |
| Row count | 180 | 180 | 180 |
| Min | 1.94 | 10 | 27,500 |
| Max | 4.00 | 140 | 42,500 |
| Average | 3.00 | 64.44 | 36,008 |
| **Sum (QC baseline)** | **540.17** | **11,599** | **6,481,500** |

---

## Quality Acceptance Criteria

The pipeline enforces these checks after each successful insert (for the current `batch_date`):

| Rule ID | Check | Expected | Tolerance |
| :--- | :--- | :--- | :--- |
| QC-01 | Row count | `loaded_count` == DB count | Exact |
| QC-02 | GPA sum | Staging sum == DB sum | ±0.01 |
| QC-03 | Credits sum | Staging sum == DB sum | Exact |
| QC-04 | Salary sum | Staging sum == DB sum | Exact |
| QC-05 | Deduplication | `rejected_count` logged in audit | Informational |
| QC-06 | Idempotency | Re-run does not increase row count | Exact (180) |

**Staging validation rules (implicit)**

| Column | Rule |
| :--- | :--- |
| `gpa` | Coerced to float; invalid → NaN |
| `credit_earned` | Coerced to int; null → 0 |
| `expected_salary_thb` | Coerced to int; null → 0 |
| `entity_id`, `snapshot_date` | Cast to string; used for dedup |
| `rag_document_text` | Required for embedding; must be non-null for vector generation |

---

## Data Dictionary

### Traceability & identity

| Column | Type | Key | Description |
| :--- | :--- | :--- | :--- |
| `record_type` | VARCHAR | — | Object type (`student`) |
| `entity_id` | VARCHAR | PK (business) | Student entity ID (e.g. `SK0001`) |
| `student_no` | VARCHAR | Alt key | Student card ID (e.g. `TU202300001`) |
| `student_name` | VARCHAR | PII | Full name |
| `citizen_id` | VARCHAR | Alt key, PII | National ID |
| `email` | VARCHAR | Alt key, PII | University email |
| `mobile` | VARCHAR | PII | Mobile number |
| `source_row_no` | INTEGER | Audit | Original Excel row for lineage |

### Academic attributes

| Column | Type | Allowed values / format | Description |
| :--- | :--- | :--- | :--- |
| `level` | VARCHAR | Undergraduate, Postgraduate | Degree level |
| `faculty_or_school` | VARCHAR | Faculty name | Hosting faculty |
| `program_id` | VARCHAR | e.g. `TU-SCI-UG` | Program code |
| `program_name` | VARCHAR | Program name | English program title |
| `discipline_cluster` | VARCHAR | Cluster name | Academic discipline grouping |
| `campus` | VARCHAR | Rangsit, Tha Phra Chan | Campus location |
| `year_of_study` | INTEGER | 1–4 | Current study year |
| `admission_channel` | VARCHAR | Channel name | Admission pathway |
| `status` | VARCHAR | Active, Leave, Graduated, etc. | Registration status |
| `gpa` | DECIMAL(3,2) | 0.00–4.00 | Cumulative GPA |
| `credit_earned` | INTEGER | 0–150 | Completed credits |
| `is_international` | BOOLEAN | true / false | International student flag |

### Career & behavioral (synthetic)

| Column | Type | Description |
| :--- | :--- | :--- |
| `behavior_profile` | VARCHAR | Study behavior summary |
| `teamwork_style` | VARCHAR | Teamwork preferences |
| `learning_preference` | VARCHAR | Learning style (e.g. Visual, Hands-on) |
| `career_interest` | VARCHAR | Target career path |
| `expected_salary_thb` | INTEGER | Expected monthly salary (THB) |
| `salary_expectation_note` | VARCHAR | Context for mock salary data |
| `internship_interest` | VARCHAR | Internship preference / interest |
| `mock_interview_note` | VARCHAR | Mock interview scenario notes |

### Workshop / governance fields (source)

| Column | Type | Description |
| :--- | :--- | :--- |
| `metric_or_item` | VARCHAR | Workshop metric label (sparse) |
| `value` | VARCHAR | Associated metric value (sparse) |
| `unit` | VARCHAR | Unit of measure (sparse) |
| `year_or_as_of` | VARCHAR | Temporal reference (sparse) |
| `protection_classification` | VARCHAR | Data protection tier from source spec |
| `required_action` | VARCHAR | Required handling action per source spec |
| `task_hint` | VARCHAR | Workshop task guidance |

### Source metadata

| Column | Type | Description |
| :--- | :--- | :--- |
| `snapshot_date` | DATE | Export date (`YYYY-MM-DD`) |
| `source_system` | VARCHAR | Origin system identifier |
| `source_url` | VARCHAR | Reference URL for lineage |

### Document fields (legacy / sparse)

These columns exist in the workbook but are largely empty in the current extract. They are preserved in Raw/Staging as NULL where absent:

| Column | Type | Description |
| :--- | :--- | :--- |
| `fact_category` | VARCHAR | Fact taxonomy (sparse) |
| `doc_title` | VARCHAR | Document title (sparse) |
| `doc_section` | VARCHAR | Document section (sparse) |
| `doc_text` | VARCHAR | Document body (sparse) |
| `doc_type` | VARCHAR | Document type (sparse) |

### RAG corpus fields

Primary fields used for retrieval-augmented generation. These contain **safe synthetic summaries** — no raw PII.

| Column | Type | Used by | Description |
| :--- | :--- | :--- | :--- |
| `rag_document_title` | VARCHAR | Dashboard display | Chunk title for UI |
| `rag_document_text` | VARCHAR | Pipeline embedding, RAG context | Searchable document body |
| `rag_keywords` | VARCHAR | Keyword fallback search | Comma-separated tags |
| `rag_sample_question` | VARCHAR | Reference only | Example question per row |
| `rag_expected_answer_hint` | VARCHAR | Reference only | Expected answer hint (evaluation) |

---

## Pipeline-Derived Columns

Added during staging/trusted load — not present in source Excel:

| Column | Type | Layer | Description |
| :--- | :--- | :--- | :--- |
| `batch_date` | DATE | Staging, Trusted | Overwritten by `--business-date` CLI argument (replaces source value) |
| `load_timestamp` | TIMESTAMP | Staging, Trusted | UTC insertion time (pipeline-generated) |
| `vector_embedding` | DOUBLE[768] | Staging, Trusted | Nomic Embed v1.5 of `search_document: {rag_document_text}` |

---

## Trusted Layer Objects

### Table: `trusted_student_snapshot`

Contains all 49 source columns plus pipeline-derived columns. Primary analytical and RAG table.

### View: `analytics_student_summary`

Aggregated KPIs refreshed on every successful pipeline run:

```sql
SELECT
    campus,
    program_name,
    status,
    COUNT(*)              AS total_students,
    ROUND(AVG(gpa), 2)    AS average_gpa,
    ROUND(AVG(credit_earned), 1) AS average_credits,
    ROUND(AVG(expected_salary_thb), 0) AS average_expected_salary
FROM trusted_student_snapshot
GROUP BY campus, program_name, status;
```

### Table: `batch_audit`

Operational metadata for every pipeline execution. See [architecture.md](architecture.md#observability--audit) for full schema.

| Status | Meaning |
| :--- | :--- |
| `RUNNING` | Pipeline in progress |
| `SUCCESS` | QC passed, run complete |
| `FAILED` | Error or QC assertion failure |

---

## Security & Governance Matrix

Although this is synthetic workshop data, we document production-grade classification for real-world deployment.

### Column classification

| Group | Columns | Classification | Production access rule |
| :--- | :--- | :---: | :--- |
| PII | `citizen_id`, `student_name`, `email`, `mobile` | High | Registry staff only; encrypt or mask in non-prod |
| Academic records | `gpa`, `credit_earned`, `status`, `program_id` | Medium | Advisors/counselors; anonymize in public dashboards |
| Behavioral / salary | `career_interest`, `expected_salary_thb`, `behavior_profile` | Low | Career services analytics |
| Operational | `source_row_no`, `snapshot_date`, `batch_date`, `load_timestamp` | Internal | Data engineering / DBA |
| RAG corpus | `rag_document_text`, `rag_keywords`, `rag_document_title` | Low (curated) | Safe for search/LLM context |

### Encryption implementation

| Setting | Behavior |
| :--- | :--- |
| `PII_ENCRYPTION_KEY` set | Fernet-encrypt `citizen_id`, `mobile`, `email`, `student_name` at ingest |
| Key not set | Plaintext ingest with warning (workshop default) |

**Key management best practices**

- Generate Fernet keys with `Fernet.generate_key()` — never hardcode in source.
- Rotate keys on a schedule; plan re-encryption jobs for stored ciphertext.
- Store keys in a secrets manager (AWS Secrets Manager, GCP Secret Manager, Vault).

### Dashboard access

| Surface | PII exposure | Control |
| :--- | :--- | :--- |
| Analytics tab | Aggregated only | No row-level PII in charts |
| RAG Q&A tab | `rag_document_text` only | Curated summaries, not raw PII columns |
| SQL Explorer | Full table access | Read-only connection; restrict in production |

---

## RAG Corpus Safety

### Allowed in retrieval context

- `rag_document_text` — pre-sanitized mock summaries
- `rag_document_title`, `rag_keywords` — display and fallback search
- `source_row_no`, `student_no` — citation metadata

### Excluded from embedding input

| Column | Reason |
| :--- | :--- |
| `citizen_id` | Direct government identifier |
| `mobile` | Contact PII |
| `email` | Contact PII |
| `student_name` | Personal identifier |

The pipeline embeds **only** `rag_document_text` (with Nomic `search_document:` prefix). Raw PII columns are never passed to the embedding model.

### LLM grounding rules

1. Answer only from retrieved chunks.
2. Cite `source_row_no` for every factual claim.
3. Respond with "not found in workbook" when context is insufficient.

This prevents the LLM from hallucinating student details beyond the retrieved evidence.
