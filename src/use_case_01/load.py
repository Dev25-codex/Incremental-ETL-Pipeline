import logging

from pathlib import Path
from uuid import uuid4

import pandas as pd

from database import get_db_connection
from transform import transform_data
from extract import extract_data
from incremental import filter_new_records
from watermark import update_watermark
from upsert import upsert_transactions


# --------------------------------------------------
# PROJECT CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FILE_PATH = PROJECT_ROOT / "data" / "raw" / "Online Retail.xlsx"

BATCH_SIZE = 5000

PIPELINE_NAME = "online_retail_incremental_etl"

BACKUP_TABLES = {
    "retail_staging_backup_20261113": 536641,
    "retail_transactions_backup_20261113": 536641,
    "etl_watermark_backup_20261113": 2
}


# --------------------------------------------------
# LOGGING CONFIGURATION
# --------------------------------------------------

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "load.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# MYSQL INSERT QUERY
# --------------------------------------------------

INSERT_QUERY = """
INSERT INTO retail_staging (
    record_hash,
    InvoiceNo,
    StockCode,
    Description,
    Quantity,
    InvoiceDate,
    UnitPrice,
    CustomerID,
    Country,
    batch_id
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)

ON DUPLICATE KEY UPDATE
    record_hash = VALUES(record_hash);
"""


# --------------------------------------------------
# DATA TYPE CONVERSION
# --------------------------------------------------

def convert_to_python_type(value):

    if value is None or pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if hasattr(value, "item"):
        return value.item()

    return value


# --------------------------------------------------
# PREPARE RECORDS
# --------------------------------------------------

def prepare_records(df: pd.DataFrame, batch_id: str) -> list:

    try:

        required_columns = [
            "record_hash",
            "InvoiceNo",
            "StockCode",
            "Description",
            "Quantity",
            "InvoiceDate",
            "UnitPrice",
            "CustomerID",
            "Country"
        ]

        missing = [
            col for col in required_columns
            if col not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Missing columns: {missing}"
            )

        records = []

        for row in df[required_columns].itertuples(
            index=False,
            name=None
        ):

            values = tuple(
                convert_to_python_type(value)
                for value in row
            )

            records.append(values + (batch_id,))

        logger.info(
            "Prepared %s records for MySQL",
            len(records)
        )

        return records

    except Exception:

        logger.exception(
            "Record preparation failed"
        )

        raise


# --------------------------------------------------
# LOAD DATA INTO MYSQL STAGING
# --------------------------------------------------

def load_to_staging(df: pd.DataFrame) -> int:

    if df.empty:
        logger.warning(
            "No records available for loading"
        )
        return 0

    batch_id = str(uuid4())

    records = prepare_records(df, batch_id)

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        total_records = len(records)

        logger.info("Starting MySQL staging load")
        logger.info("Batch ID: %s", batch_id)
        logger.info("Total records: %s", total_records)

        for start in range(
            0,
            total_records,
            BATCH_SIZE
        ):

            batch = records[
                start:start + BATCH_SIZE
            ]

            cursor.executemany(
                INSERT_QUERY,
                batch
            )

            logger.info(
                "Processed batch: %s / %s",
                min(start + BATCH_SIZE, total_records),
                total_records
            )

        connection.commit()

        logger.info(
            "Staging load completed successfully"
        )

        return total_records

    except Exception:

        if connection and connection.is_connected():
            connection.rollback()

        logger.exception(
            "Staging load failed"
        )

        raise

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

            logger.info(
                "MySQL connection closed"
            )


# --------------------------------------------------
# VERIFY DATABASE BACKUPS
# --------------------------------------------------

def verify_backups():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        logger.info("Verifying database backups")

        for table_name, expected_count in BACKUP_TABLES.items():

            cursor.execute(
                f"SELECT COUNT(*) FROM `{table_name}`"
            )

            actual_count = cursor.fetchone()[0]

            logger.info(
                "%s: %s records",
                table_name,
                actual_count
            )

            if actual_count != expected_count:

                raise ValueError(
                    f"Backup verification failed for {table_name}. "
                    f"Expected {expected_count}, got {actual_count}"
                )

        logger.info(
            "All database backups verified successfully"
        )

        return True

    except Exception:

        logger.exception(
            "Backup verification failed"
        )

        raise

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# --------------------------------------------------
# RESET LIVE TABLES FOR HASH MIGRATION
# --------------------------------------------------

def reset_live_tables():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        logger.warning(
            "Resetting live staging and final tables"
        )

        cursor.execute(
            "TRUNCATE TABLE retail_staging"
        )

        cursor.execute(
            "TRUNCATE TABLE retail_transactions"
        )

        cursor.execute(
            """
            UPDATE etl_watermark
            SET last_processed_date = NULL,
                last_run_status = 'MIGRATION_IN_PROGRESS'
            WHERE pipeline_name = %s
            """,
            (PIPELINE_NAME,)
        )

        connection.commit()

        logger.info(
            "Live tables reset successfully"
        )

    except Exception:

        if connection and connection.is_connected():
            connection.rollback()

        logger.exception(
            "Live table reset failed"
        )

        raise

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# --------------------------------------------------
# FULL SHA-256 MIGRATION
# --------------------------------------------------

def run_sha256_migration():

    logger.info("=" * 60)
    logger.info("SHA-256 MIGRATION STARTED")
    logger.info("=" * 60)

    try:

        # STEP 1: VERIFY BACKUPS
        logger.info("STEP 1: Verifying backup tables")

        verify_backups()

        # STEP 2: EXTRACT COMPLETE DATASET
        logger.info("STEP 2: Extracting complete dataset")

        extracted_df = extract_data(FILE_PATH)

        if extracted_df.empty:
            raise ValueError("Extracted dataset is empty")

        logger.info(
            "Extracted records: %s",
            len(extracted_df)
        )

        # STEP 3: TRANSFORM COMPLETE DATASET
        logger.info("STEP 3: Transforming complete dataset")

        transformed_df = transform_data(extracted_df)

        if transformed_df.empty:
            raise ValueError("Transformed dataset is empty")

        if len(transformed_df) != len(extracted_df):
            raise ValueError(
                "Source and transformed row counts do not match"
            )

        # STEP 4: VALIDATE SHA-256 HASHES
        logger.info("STEP 4: Validating SHA-256 fingerprints")

        if "record_hash" not in transformed_df.columns:
            raise ValueError("record_hash column is missing")

        if transformed_df["record_hash"].isna().any():
            raise ValueError("Missing SHA-256 fingerprints found")

        invalid_hashes = transformed_df[
            transformed_df["record_hash"].astype(str).str.len() != 64
        ]

        if not invalid_hashes.empty:
            raise ValueError("Invalid SHA-256 fingerprint length found")

        logger.info(
            "Validated source records: %s",
            len(transformed_df)
        )

        logger.info(
            "Unique SHA-256 fingerprints: %s",
            transformed_df["record_hash"].nunique()
        )

        # STEP 5: ASK FOR CONFIRMATION
        print("\nWARNING: SHA-256 DATABASE MIGRATION")
        print("Backups have been verified.")
        print("Extraction and transformation are successful.")
        print("Live staging and final tables will now be reset.")
        print("Backup tables will remain untouched.")

        confirmation = input(
            "\nType MIGRATE SHA256 to continue: "
        )

        if confirmation != "MIGRATE SHA256":

            logger.warning("Migration cancelled by user")
            print("Migration cancelled. Live tables were not reset.")

            return

        # STEP 6: RESET LIVE TABLES
        logger.info("STEP 6: Resetting live tables")

        reset_live_tables()

        # STEP 7: LOAD INTO STAGING
        logger.info("STEP 7: Loading SHA-256 records into staging")

        loaded_records = load_to_staging(transformed_df)

        logger.info(
            "Source records submitted for loading: %s",
            loaded_records
        )

        logger.info(
            "Expected unique fingerprints: %s",
            transformed_df["record_hash"].nunique()
        )

        # IMPORTANT:
        # Watermark will be updated only after
        # final table upsert is successfully verified.

        logger.info("SHA-256 staging migration completed")

        logger.info("=" * 60)
        logger.info("STAGING MIGRATION SUCCESSFUL")
        logger.info("=" * 60)

        print("\nSHA-256 staging migration completed.")
        print("Next step: Verify staging and run upsert.py.")
        print("Watermark has NOT been updated yet.")

    except Exception:

        logger.exception(
            "SHA-256 migration failed. "
            "Verified backup tables are available for recovery."
        )

        raise


# --------------------------------------------------
# NORMAL INCREMENTAL PIPELINE
# --------------------------------------------------

def run_staging_pipeline():

    try:

        logger.info("=" * 60)
        logger.info("INCREMENTAL ETL PIPELINE STARTED")
        logger.info("=" * 60)

        # STEP 1: EXTRACT
        logger.info("STEP 1: Extracting source data")

        extracted_df = extract_data(FILE_PATH)

        logger.info(
            "Extracted records: %s",
            len(extracted_df)
        )

        if extracted_df.empty:
            logger.warning("Source dataset is empty")
            return

        # STEP 2: INCREMENTAL FILTERING
        logger.info("STEP 2: Filtering new records")

        new_records_df = filter_new_records(
            extracted_df,
            PIPELINE_NAME
        )

        logger.info(
            "New records: %s",
            len(new_records_df)
        )

        if new_records_df.empty:

            logger.info("No new records available")
            return

        # STEP 3: TRANSFORM
        logger.info("STEP 3: Transforming new records")

        transformed_df = transform_data(
            new_records_df
        )

        if transformed_df.empty:
            raise ValueError("Transformation returned empty data")

        # STEP 4: LOAD INTO STAGING
        logger.info("STEP 4: Loading records into staging")

        loaded_records = load_to_staging(
            transformed_df
        )

        logger.info(
            "Records submitted to staging: %s",
            loaded_records
        )

        # STEP 5: UPSERT INTO FINAL TABLE
        logger.info("STEP 5: Upserting into final table")

        upsert_result = upsert_transactions()

        logger.info(
            "Final table records: %s",
            upsert_result["final_count"]
        )

        # Watermark is updated inside upsert_transactions()
        # only after successful UPSERT and count validation.

        logger.info("=" * 60)
        logger.info("INCREMENTAL ETL PIPELINE COMPLETED")
        logger.info("=" * 60)

    except Exception:

        logger.exception(
            "INCREMENTAL ETL PIPELINE FAILED"
        )

        raise

# --------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------
if __name__ == "__main__":

    run_staging_pipeline()