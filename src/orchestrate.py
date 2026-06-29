import os
import sys
import time
import argparse
import subprocess
import logging

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [Orchestrator] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Thammasat Data & AI Pipeline Orchestrator (Production-Minded)")
    parser.add_argument("--business-date", required=True, help="Business date for the run (YYYY-MM-DD)")
    parser.add_argument("--run-id", required=True, help="Unique Run Identifier")
    parser.add_argument("--input-file", default="thammasat_workshop_dataset.xlsx", help="Path to input Excel file")
    parser.add_argument("--sheet-name", default="workshop_data", help="Sheet name in Excel file")
    
    args = parser.parse_args()
    
    # Check key management
    gemini_key = os.environ.get("GEMINI_API_KEY")
    pii_key = os.environ.get("PII_ENCRYPTION_KEY")
    
    if not gemini_key:
        logger.info("GEMINI_API_KEY is not set. Vector embeddings use local Nomic Embed v1.5; Gemini is only needed for LLM answer generation in the dashboard.")
    if not pii_key:
        logger.warning("PII_ENCRYPTION_KEY environment variable is NOT set. The pipeline will fallback to a default encryption key (unsafe for production!).")
        
    cmd = [
        "python3", "src/pipeline.py",
        "--business-date", args.business_date,
        "--run-id", args.run_id,
        "--input-file", args.input_file,
        "--sheet-name", args.sheet_name
    ]
    
    max_retries = 3
    retry_delay = 15  # seconds (initial delay)
    
    for attempt in range(1, max_retries + 2):
        logger.info(f"Attempt {attempt}/{max_retries + 1}: Starting pipeline execution...")
        
        # Start subprocess
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        # Log subprocess output
        if process.stdout:
            print(process.stdout)
        if process.stderr:
            print(process.stderr, file=sys.stderr)
            
        if process.returncode == 0:
            logger.info("✅ Pipeline executed successfully.")
            sys.exit(0)
        else:
            error_msg = process.stderr or process.stdout or ""
            is_quota_error = "429" in error_msg or "quota" in error_msg.lower() or "limit" in error_msg.lower()
            
            if is_quota_error and attempt <= max_retries:
                backoff_time = retry_delay * attempt
                logger.warning(f"⚠️ API Rate Limit (429) hit during execution. Retrying in {backoff_time} seconds (Attempt {attempt} failed)...")
                time.sleep(backoff_time)
            else:
                logger.error(f"❌ Pipeline failed after attempt {attempt}. Exit code: {process.returncode}")
                if attempt > max_retries:
                    logger.error("❌ Max retries reached. Ingestion failed.")
                sys.exit(process.returncode)

if __name__ == "__main__":
    main()
