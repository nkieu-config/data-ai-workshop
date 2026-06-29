import os
import sys
import hashlib
import datetime
import argparse
import logging
import pandas as pd
import duckdb

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
        
        stg_parquet_path = f"data/stg/stg_student_snapshot_{business_date}.parquet"
        stg_df.to_parquet(stg_parquet_path, index=False)
        logger.info(f"Staging layer saved to {stg_parquet_path}")
        
        # ==========================================
        # 3. TRUSTED LAYER: Load into DuckDB with Idempotency
        # ==========================================
        logger.info("Step 3: Loading into Trusted layer (DuckDB)...")
        
        # Ensure trusted table exists
        # DuckDB can register a pandas df as a temporary relation to create table
        con.execute("CREATE TABLE IF NOT EXISTS trusted_student_snapshot AS SELECT * FROM stg_df WHERE 1=0")
        
        # IDEMPOTENCY STRATEGY: Delete existing data for the incoming snapshot_date/business_date
        unique_snapshot_dates = stg_df['snapshot_date'].unique()
        for s_date in unique_snapshot_dates:
            logger.info(f"Cleaning existing records for snapshot_date: {s_date} to prevent duplication...")
            con.execute("DELETE FROM trusted_student_snapshot WHERE snapshot_date = ?", (s_date,))
            
        # Insert new Staging data
        con.execute("INSERT INTO trusted_student_snapshot SELECT * FROM stg_df")
        loaded_count = len(stg_df)
        logger.info(f"Successfully loaded {loaded_count} rows into trusted_student_snapshot table.")
        
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
