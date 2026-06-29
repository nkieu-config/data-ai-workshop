import os
import sys
import hashlib
import datetime
import argparse
import logging
import pandas as pd
import duckdb
from cryptography.fernet import Fernet
import google.generativeai as genai
from sentence_transformers import SentenceTransformer

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def calculate_checksum(file_path):
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def ensure_directories():
    """Ensure raw, staging, and db directories exist."""
    os.makedirs('data/raw', exist_ok=True)
    os.makedirs('data/stg', exist_ok=True)

def main():
    parser = argparse.ArgumentParser(description="Thammasat Data & AI Batch Pipeline")
    parser.add_argument("--business-date", required=True, help="Business date for the run (YYYY-MM-DD)")
    parser.add_argument("--run-id", required=True, help="Unique Run Identifier (UUID or string)")
    parser.add_argument("--input-file", default="thammasat_workshop_dataset.xlsx", help="Path to input Excel file")
    parser.add_argument("--sheet-name", default="workshop_data", help="Sheet name in Excel file")
    
    args = parser.parse_args()
    
    business_date = args.business_date
    run_id = args.run_id
    input_file = args.input_file
    sheet_name = args.sheet_name
    
    start_time = datetime.datetime.now()
    ensure_directories()
    
    db_path = "data/trusted_database.db"
    con = duckdb.connect(db_path)
    
    # Initialize Audit Table
    con.execute("""
        CREATE TABLE IF NOT EXISTS batch_audit (
            run_id VARCHAR,
            business_date DATE,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            status VARCHAR,
            input_file_name VARCHAR,
            sheet_name VARCHAR,
            input_file_checksum VARCHAR,
            source_count INTEGER,
            loaded_count INTEGER,
            rejected_count INTEGER,
            error_message VARCHAR
        )
    """)
    
    # Calculate Checksum
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)
    file_checksum = calculate_checksum(input_file)
    input_file_name = os.path.basename(input_file)
    
    # Log Run Init
    con.execute("""
        INSERT INTO batch_audit (run_id, business_date, start_time, status, input_file_name, sheet_name, input_file_checksum)
        VALUES (?, ?, ?, 'RUNNING', ?, ?, ?)
    """, (run_id, business_date, start_time, input_file_name, sheet_name, file_checksum))
    
    try:
        logger.info(f"Starting run {run_id} for business date {business_date}")
        
        # ==========================================
        # 1. RAW LAYER: Ingest and save as-is
        # ==========================================
        logger.info("Step 1: Reading Excel file for Raw layer...")
        raw_df = pd.read_excel(input_file, sheet_name=sheet_name)
        source_count = len(raw_df)
        logger.info(f"Loaded {source_count} rows from source file.")
        
        raw_parquet_path = f"data/raw/raw_workshop_data_{business_date}.parquet"
        raw_df.to_parquet(raw_parquet_path, index=False)
        logger.info(f"Raw layer saved to {raw_parquet_path}")
        
        # ==========================================
        # 2. STAGING LAYER: Clean and Deduplicate
        # ==========================================
        logger.info("Step 2: Processing Staging layer...")
        stg_df = raw_df.copy()
        
        # Standardize Types
        stg_df['gpa'] = pd.to_numeric(stg_df['gpa'], errors='coerce').astype(float)
        stg_df['credit_earned'] = pd.to_numeric(stg_df['credit_earned'], errors='coerce').fillna(0).astype(int)
        stg_df['expected_salary_thb'] = pd.to_numeric(stg_df['expected_salary_thb'], errors='coerce').fillna(0).astype(int)
        stg_df['snapshot_date'] = stg_df['snapshot_date'].astype(str)
        stg_df['entity_id'] = stg_df['entity_id'].astype(str)
        
        # PII Encryption Key Management (Production Best Practice 1)
        # By default, to comply with the PDF assessment spec ("No masked, hashed, or encrypted output columns"),
        # we ingest PII as plaintext. Setting PII_ENCRYPTION_KEY enables AES encryption.
        pii_key_env = os.environ.get("PII_ENCRYPTION_KEY")
        if pii_key_env:
            logger.info("PII_ENCRYPTION_KEY environment variable found. Enabling PII Encryption...")
            try:
                key_to_use = pii_key_env.encode('utf-8')
                f = Fernet(key_to_use)
                
                def encrypt_val(val):
                    if pd.isna(val):
                        return val
                    return f.encrypt(str(val).encode('utf-8')).decode('utf-8')
                    
                pii_cols = ['citizen_id', 'mobile', 'email', 'student_name']
                for col in pii_cols:
                    if col in stg_df.columns:
                        stg_df[col] = stg_df[col].apply(encrypt_val)
                        logger.info(f"Encrypted PII column: {col}")
            except Exception as e:
                logger.error(f"Failed to initialize PII encryption: {e}. Proceeding with plaintext.")
        else:
            logger.warning("PII_ENCRYPTION_KEY env var not set. Ingesting PII as plaintext (complying with default brief spec).")
        
        # Deduplication Rule: unique (entity_id, snapshot_date)
        initial_len = len(stg_df)
        stg_df = stg_df.drop_duplicates(subset=['entity_id', 'snapshot_date'], keep='last')
        dedup_count = len(stg_df)
        rejected_count = initial_len - dedup_count
        if rejected_count > 0:
            logger.warning(f"Deduplicated {rejected_count} rows in staging.")
            
        # Add Technical / Metadata columns
        stg_df['batch_date'] = business_date
        stg_df['load_timestamp'] = datetime.datetime.utcnow()
        
        # 2.1 OFFLINE EMBEDDINGS (Local Nomic Embed v1.5 - Best Practice)
        logger.info("Generating local vector embeddings using nomic-ai/nomic-embed-text-v1.5...")
        try:
            model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)
            texts = stg_df['rag_document_text'].tolist()
            # Prefix search documents as per Nomic model guidelines
            nomic_texts = [f"search_document: {t}" for t in texts]
            embeddings = model.encode(nomic_texts, show_progress_bar=False)
            
            # Save vectors to DataFrame as float lists (DOUBLE[] in DuckDB)
            stg_df['vector_embedding'] = [emb.tolist() for emb in embeddings]
            logger.info("Successfully generated local embeddings for all staging records.")
        except Exception as e:
            logger.error(f"Failed to generate local vector embeddings: {e}")
            raise e
            
        stg_parquet_path = f"data/stg/stg_student_snapshot_{business_date}.parquet"
        stg_df.to_parquet(stg_parquet_path, index=False)
        logger.info(f"Staging layer saved to {stg_parquet_path}")
        
        # ==========================================
        # 3. TRUSTED LAYER: Load into DuckDB with Idempotency
        # ==========================================
        logger.info("Step 3: Loading into Trusted layer (DuckDB)...")
        
        # Ensure trusted table exists with matching schema. (Production Best Practice 2: Schema Evolution)
        table_exists = con.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'trusted_student_snapshot'").fetchone()
        if table_exists:
            info_df = con.execute("PRAGMA table_info(trusted_student_snapshot)").df()
            existing_cols = info_df['name'].tolist()
            
            # Check if vector_embedding is stored as a non-array type (e.g. if previous failed run created it as INTEGER)
            if 'vector_embedding' in existing_cols:
                vec_type = info_df[info_df['name'] == 'vector_embedding']['type'].values[0]
                if '[]' not in str(vec_type) and 'LIST' not in str(vec_type) and 'ARRAY' not in str(vec_type):
                    logger.warning("Table column 'vector_embedding' has incompatible type (non-array). Recreating table...")
                    con.execute("DROP TABLE trusted_student_snapshot")
                    table_exists = False
            
            if table_exists:
                for col in stg_df.columns:
                    if col not in existing_cols:
                        col_type = "VARCHAR"
                        if col == 'vector_embedding':
                            col_type = "DOUBLE[]"
                        elif pd.api.types.is_integer_dtype(stg_df[col]):
                            col_type = "BIGINT"
                        elif pd.api.types.is_float_dtype(stg_df[col]):
                            col_type = "DOUBLE"
                        
                        logger.info(f"Schema Evolution: Adding column '{col}' ({col_type}) to trusted_student_snapshot...")
                        con.execute(f"ALTER TABLE trusted_student_snapshot ADD COLUMN {col} {col_type}")
        else:
            con.execute("CREATE TABLE trusted_student_snapshot AS SELECT * FROM stg_df WHERE 1=0")
        
        # IDEMPOTENCY STRATEGY: Delete existing data for the incoming snapshot_date/business_date
        unique_snapshot_dates = stg_df['snapshot_date'].unique()
        for s_date in unique_snapshot_dates:
            logger.info(f"Cleaning existing records for snapshot_date: {s_date} to prevent duplication...")
            con.execute("DELETE FROM trusted_student_snapshot WHERE snapshot_date = ?", (s_date,))
            
        # Insert new Staging data
        con.execute("INSERT INTO trusted_student_snapshot SELECT * FROM stg_df")
        loaded_count = len(stg_df)
        logger.info(f"Successfully loaded {loaded_count} rows into trusted_student_snapshot table.")
        
        # Create or Replace Analytics View as defined in Data Specification
        con.execute("""
            CREATE OR REPLACE VIEW analytics_student_summary AS 
            SELECT 
                campus,
                program_name,
                status,
                COUNT(*) AS total_students,
                ROUND(AVG(gpa), 2) AS average_gpa,
                ROUND(AVG(credit_earned), 1) AS average_credits,
                ROUND(AVG(expected_salary_thb), 0) AS average_expected_salary
            FROM trusted_student_snapshot
            GROUP BY campus, program_name, status
        """)
        logger.info("Successfully created/updated analytics_student_summary view.")
        
        # ==========================================
        # 4. QUALITY CONTROL SUMMARY CHECKS
        # ==========================================
        logger.info("Step 4: Running Quality Control Checks...")
        
        # Calculate source metrics from dataframe
        src_gpa_sum = float(stg_df['gpa'].sum())
        src_credits_sum = int(stg_df['credit_earned'].sum())
        src_salary_sum = int(stg_df['expected_salary_thb'].sum())
        
        # Query target database metrics
        db_metrics = con.execute("""
            SELECT 
                COUNT(*), 
                SUM(gpa), 
                SUM(credit_earned), 
                SUM(expected_salary_thb) 
            FROM trusted_student_snapshot 
            WHERE batch_date = ?
        """, (business_date,)).fetchone()
        
        db_count, db_gpa_sum, db_credits_sum, db_salary_sum = db_metrics
        
        # Log comparison
        logger.info(f"Verification Results for batch_date {business_date}:")
        logger.info(f" - Row Count: Source = {loaded_count} | Database = {db_count}")
        logger.info(f" - GPA Sum: Source = {src_gpa_sum:.2f} | Database = {db_gpa_sum:.2f}")
        logger.info(f" - Credits Sum: Source = {src_credits_sum} | Database = {db_credits_sum}")
        logger.info(f" - Expected Salary Sum: Source = {src_salary_sum} | Database = {db_salary_sum}")
        
        # Quality Assertions
        assert loaded_count == db_count, "QC Fail: Row counts do not match!"
        assert abs(src_gpa_sum - db_gpa_sum) < 0.01, "QC Fail: GPA sum does not match!"
        assert src_credits_sum == db_credits_sum, "QC Fail: Credits sum does not match!"
        assert src_salary_sum == db_salary_sum, "QC Fail: Expected salary sum does not match!"
        
        logger.info("QC checks PASSED successfully.")
        
        # Log successful completion in Audit
        end_time = datetime.datetime.now()
        con.execute("""
            UPDATE batch_audit
            SET end_time = ?, status = 'SUCCESS', source_count = ?, loaded_count = ?, rejected_count = ?
            WHERE run_id = ?
        """, (end_time, source_count, loaded_count, rejected_count, run_id))
        logger.info(f"Run {run_id} completed successfully.")
        
    except Exception as e:
        end_time = datetime.datetime.now()
        error_msg = str(e)
        logger.error(f"Run {run_id} failed: {error_msg}")
        
        # Update Audit table with error status
        con.execute("""
            UPDATE batch_audit
            SET end_time = ?, status = 'FAILED', error_message = ?
            WHERE run_id = ?
        """, (end_time, error_msg, run_id))
        
        con.close()
        sys.exit(1)
        
    finally:
        con.close()

if __name__ == "__main__":
    main()
