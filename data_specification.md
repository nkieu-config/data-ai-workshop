# Data Specification & Profiling Report

This document contains the data discovery, profiling metrics, data dictionary, and security usage classification for the `thammasat_workshop_dataset.xlsx` workbook.

---

## 📊 1. Data Profiling Report (Real Mock Dataset Stats)
This profiling represents the summary statistics of the **180 rows** in the worksheet.

### Row Counts by Attributes
*   **Record Type (`record_type`):**
    *   `student`: 180 rows (100%)
*   **Campus (`campus`):**
    *   `Rangsit`: 144 rows (80.0%)
    *   `Tha Phra Chan`: 36 rows (20.0%)
*   **Level of Study (`level`):**
    *   `Undergraduate`: 140 rows (77.8%)
    *   `Postgraduate`: 40 rows (22.2%)
*   **Academic Status (`status`):**
    *   `Active`: 161 rows
    *   `Leave`: 6 rows
    *   `Exchange`: 6 rows
    *   `Withdrawn`: 4 rows
    *   `Graduated`: 3 rows
*   **Top 5 Study Programs (`program_id`):**
    *   `TU-SCI-UG` (Computer Science / Data Science): 29 rows
    *   `TU-ENG-UG` (Engineering): 24 rows
    *   `TU-PH-PG` (Public Health - Postgrad): 23 rows
    *   `TU-COM-UG` (Communication Arts): 18 rows
    *   `TU-SIIT-UG` (Sirindhorn International Institute of Tech): 15 rows
*   **Top Career Interests (`career_interest`):**
    *   `Data Engineer / AI Engineer`: 68 rows (37.8%)
    *   `Health Data Analyst`: 37 rows (20.6%)
    *   `Data Analyst / BI Analyst`: 29 rows (16.1%)
    *   `Data Governance / Policy Analyst`: 25 rows (13.9%)
    *   `Digital Analytics / Product Analyst`: 15 rows (8.3%)

### Numeric Summary & Quality Check Validation
These values must match the final loaded database to verify **data ingestion integrity (Quality Check)**.

| Metric / Check | GPA (`gpa`) | Credits Earned (`credit_earned`) | Expected Salary THB (`expected_salary_thb`) |
| :--- | :---: | :---: | :---: |
| **Row Count** | 180 | 180 | 180 |
| **Min Value** | 1.94 | 10.0 | 27,500 |
| **Max Value** | 4.00 | 140.0 | 42,500 |
| **Average** | 3.00 | 64.44 | 36,008 |
| **Total Sum** | **540.17** | **11,599.0** | **6,481,500** |

*   **Snapshot Date Coverage:** `2026-06-28` (All 180 rows represent a single date snapshot).

---

## 📖 2. Data Dictionary

The table below groups all 49 columns into logical categories, defining their business keys and formats.

### Category: Row Traceability & Profile (Identities)
| Column Name | Data Type | Key Type | Description |
| :--- | :--- | :--- | :--- |
| `record_type` | VARCHAR | - | Defines the object type (e.g., `student`). |
| `entity_id` | VARCHAR | Primary Key (Business) | Unique identifier for the student entity (e.g., `SK0001`). |
| `student_no` | VARCHAR | Alternate Key | Student ID card identifier (e.g., `TU202300001`). |
| `student_name` | VARCHAR | - | Full name of the student. |
| `citizen_id` | VARCHAR | Alternate Key | National ID card identifier. |
| `email` | VARCHAR | Alternate Key | University student email. |
| `mobile` | VARCHAR | - | Student mobile number contact. |
| `source_row_no` | INTEGER | Audit Key | The row number in the original Excel file for lineage tracing. |

### Category: Academic Attributes & Performance
| Column Name | Data Type | Format / Allowed Values | Description |
| :--- | :--- | :--- | :--- |
| `level` | VARCHAR | `Undergraduate`, `Postgraduate` | Degree level. |
| `faculty_or_school`| VARCHAR | Faculty Name | Faculty hosting the program. |
| `program_id` | VARCHAR | ID (e.g., `TU-SCI-UG`) | Study program code. |
| `program_name` | VARCHAR | Program Name | English name of the program. |
| `campus` | VARCHAR | `Rangsit`, `Tha Phra Chan` | University campus location. |
| `year_of_study` | INTEGER | 1, 2, 3, 4 | Current year of study. |
| `status` | VARCHAR | `Active`, `Leave`, `Graduated`, etc. | Academic registration status. |
| `gpa` | DECIMAL(3,2) | 0.00 to 4.00 | Cumulative Grade Point Average. |
| `credit_earned` | INTEGER | 0 to 150 | Total completed academic credits. |

### Category: Career & Behavioral Mock-up
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `behavior_profile` | VARCHAR | Summary of student's study behavior and style. |
| `teamwork_style` | VARCHAR | Mock teamwork behavior and preferences. |
| `learning_preference`| VARCHAR | Style of learning (e.g., Visual, Hands-on). |
| `career_interest` | VARCHAR | The student's target career path. |
| `expected_salary_thb`| INTEGER | Expected monthly salary in THB. |
| `salary_expectation_note`| VARCHAR | Context/disclaimer about the mock salary expectation. |

### Category: Metadata & Audit Columns
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `snapshot_date` | DATE | Date the snapshot was exported from source (YYYY-MM-DD). |
| `source_system` | VARCHAR | System of origin (e.g., `synthetic_public_training_extract`). |
| `batch_date` | DATE | (Target DB) Ingestion execution date (set at run time). |
| `load_timestamp` | TIMESTAMP | (Target DB) Exact date-time of database insertion. |

*(Note: Columns like `fact_category`, `doc_title` contain missing/empty data in the current Excel version and are set to NULL in Raw/Staging layers).*

---

## 🔒 3. Column-Level Usage Specification & Security Matrix (Part 3)

Although this is synthetic workshop data (and no encryption/masking should be implemented to preserve values for analytics), we apply the following production security classification guidelines:

| Column Group | Columns included | Classification | Access Rule / Production Governance |
| :--- | :--- | :---: | :--- |
| **PII (Personal Identifiable Information)** | `citizen_id`, `student_name`, `email`, `mobile` | **High Privacy** | Restrict to student registry staff. Masked or hashed in dev environments. |
| **Academic Records** | `gpa`, `credit_earned`, `status` | **Medium Privacy** | Restrict to student counselors/advisors. Anonymized in public dashboards. |
| **Mock Behavior & Salary** | `career_interest`, `expected_salary_thb`, `behavior_profile` | **Low Privacy** | Open for careers office analytics. |
| **Operational Metadata** | `source_row_no`, `snapshot_date`, `batch_date` | **Internal** | Data Engineers / DBAs only. |

*   **RAG Safety Check:** If these records are used as a document corpus, `citizen_id` and `mobile` must be excluded from chunks to prevent data leaks. Use only RAG columns (`rag_document_text`) which contain safe mock summaries.
