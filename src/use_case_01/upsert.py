import logging

from database import get_db_connection
from watermark import update_watermark


logger = logging.getLogger(__name__)

PIPELINE_NAME = "online_retail_incremental_etl"


def get_table_count(cursor, table_name):

    allowed_tables = {
        "retail_staging",
        "retail_transactions"
    }

    if table_name not in allowed_tables:
        raise ValueError("Invalid table name")

    cursor.execute(
        f"SELECT COUNT(*) FROM {table_name}"
    )

    return cursor.fetchone()[0]


def upsert_transactions():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        # ------------------------------------------
        # STEP 1: CHECK STAGING TABLE
        # ------------------------------------------

        logger.info("STEP 1: Checking staging table")

        staging_count = get_table_count(
            cursor,
            "retail_staging"
        )

        if staging_count == 0:
            raise ValueError("Staging table is empty")

        logger.info(
            "Staging records: %s",
            staging_count
        )

        # ------------------------------------------
        # STEP 2: GET LATEST INVOICE DATE
        # ------------------------------------------

        logger.info("STEP 2: Getting latest InvoiceDate")

        cursor.execute(
            "SELECT MAX(InvoiceDate) FROM retail_staging"
        )

        latest_date = cursor.fetchone()[0]

        if latest_date is None:
            raise ValueError("Latest InvoiceDate is missing")

        # ------------------------------------------
        # STEP 3: UPSERT INTO FINAL TABLE
        # ------------------------------------------

        logger.info("STEP 3: Upserting into final table")

        query = """
        INSERT INTO retail_transactions (
            record_hash,
            InvoiceNo,
            StockCode,
            Description,
            Quantity,
            InvoiceDate,
            UnitPrice,
            CustomerID,
            Country
        )
        SELECT
            record_hash,
            InvoiceNo,
            StockCode,
            Description,
            Quantity,
            InvoiceDate,
            UnitPrice,
            CustomerID,
            Country
        FROM retail_staging

        ON DUPLICATE KEY UPDATE
            Description = VALUES(Description),
            Quantity = VALUES(Quantity),
            UnitPrice = VALUES(UnitPrice),
            CustomerID = VALUES(CustomerID),
            Country = VALUES(Country);
        """

        cursor.execute(query)

        affected_rows = cursor.rowcount

        # ------------------------------------------
        # STEP 4: VERIFY FINAL TABLE
        # ------------------------------------------

        logger.info("STEP 4: Verifying final table")

        final_count = get_table_count(
            cursor,
            "retail_transactions"
        )

        if final_count != staging_count:

            raise ValueError(
                f"Record count mismatch. "
                f"Staging: {staging_count}, "
                f"Final: {final_count}"
            )

        # ------------------------------------------
        # STEP 5: COMMIT UPSERT
        # ------------------------------------------

        connection.commit()

        logger.info("UPSERT committed successfully")

        # ------------------------------------------
        # STEP 6: UPDATE WATERMARK
        # ------------------------------------------

        logger.info("STEP 6: Updating watermark")

        update_watermark(
            PIPELINE_NAME,
            latest_date,
            "SUCCESS"
        )

        logger.info("Watermark updated successfully")

        logger.info("=" * 50)
        logger.info("UPSERT PIPELINE COMPLETED")
        logger.info("Staging records: %s", staging_count)
        logger.info("Final records: %s", final_count)
        logger.info("Affected rows: %s", affected_rows)
        logger.info("=" * 50)

        return {
            "staging_count": staging_count,
            "final_count": final_count,
            "affected_rows": affected_rows,
            "latest_date": latest_date
        }

    except Exception:

        if connection and connection.is_connected():
            connection.rollback()

        logger.exception("UPSERT operation failed")

        raise

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# ------------------------------------------
# MAIN EXECUTION
# ------------------------------------------

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    result = upsert_transactions()

    print("\n========== UPSERT RESULT ==========")

    print(
        "Staging records:",
        result["staging_count"]
    )

    print(
        "Final records:",
        result["final_count"]
    )

    print(
        "Affected rows:",
        result["affected_rows"]
    )

    print(
        "Latest InvoiceDate:",
        result["latest_date"]
    )

    print("Watermark: SUCCESS")
    print("==================================")