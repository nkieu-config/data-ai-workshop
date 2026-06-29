import subprocess
import duckdb
import pandas as pd
import os
import shutil

def run_cmd(cmd):
    print(f"Executing: {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(f"Error: {res.stderr}")
        return False
    return True

def cleanup():
    # Cleanup previous runs to start fresh
    if os.path.exists("data"):
        shutil.rmtree("data")
        print("Cleaned up old data directory.")

def main():
    cleanup()
    
    print("\n--- RUN 1: Ingesting dataset for the first time (Date: 2026-06-28) ---")
    run_1_status = run_cmd("python3 src/orchestrate.py --business-date 2026-06-28 --run-id RUN_ID_001")
    
    db_path = "data/trusted_database.db"
    if not os.path.exists(db_path):
        print("Database not created!")
        return
        
    con = duckdb.connect(db_path)
    
    # Check row count after Run 1
    count_1 = con.execute("SELECT COUNT(*) FROM trusted_student_snapshot").fetchone()[0]
    print(f"Row count in trusted_student_snapshot table after RUN 1: {count_1} (Expected: 180)")
    con.close() # Close connection to release database file lock
    
    print("\n--- RUN 2: Re-running the pipeline for the same date (Idempotency Check) ---")
    run_2_status = run_cmd("python3 src/orchestrate.py --business-date 2026-06-28 --run-id RUN_ID_002")
    
    con = duckdb.connect(db_path) # Reopen connection
    
    # Check row count after Run 2
    count_2 = con.execute("SELECT COUNT(*) FROM trusted_student_snapshot").fetchone()[0]
    print(f"Row count in trusted_student_snapshot table after RUN 2: {count_2} (Expected: 180 - if higher, idempotency failed!)")
    
    if count_1 == count_2 == 180:
        print("\n✅ SUCCESS: Idempotent behavior confirmed! Rerunning didn't double the rows.")
    else:
        print("\n❌ FAILURE: Row count mismatch or duplication detected.")
        
    # Print Audit logs
    print("\n--- 📋 Audit Log Table ('batch_audit') ---")
    audit_df = con.execute("SELECT run_id, business_date, start_time, end_time, status, source_count, loaded_count, rejected_count FROM batch_audit").df()
    print(audit_df.to_string())
    
    con.close()

if __name__ == "__main__":
    main()
