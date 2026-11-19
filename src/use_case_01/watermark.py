import logging

from database import get_db_connection


logger = logging.getLogger(__name__)


def get_watermark(pipeline_name):

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
        SELECT last_processed_date
        FROM etl_watermark
        WHERE pipeline_name = %s
        """

        cursor.execute(query, (pipeline_name,))

        result = cursor.fetchone()

        if result:
            return result[0]

        return None

    except Exception:

        logger.exception("Failed to fetch watermark")
        raise

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


def update_watermark(pipeline_name, last_processed_date, status):
    
    connection = None
    cursor = None
    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
        INSERT INTO etl_watermark (
            pipeline_name,
            last_processed_date,
            last_run_status
        )
        VALUES (%s, %s, %s)

        ON DUPLICATE KEY UPDATE
            last_processed_date = VALUES(last_processed_date),
            last_run_status = VALUES(last_run_status)
        """

        cursor.execute(
            query,
            (pipeline_name, last_processed_date, status)
        )

        connection.commit()

        logger.info("Watermark updated successfully")

    except Exception:

        if connection and connection.is_connected():
            connection.rollback()

        logger.exception("Failed to update watermark")
        raise

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":

    pipeline_name = "watermark_test"

    test_date = "2011-12-09 12:50:00"

    # Save watermark
    update_watermark(
        pipeline_name,
        test_date,
        "SUCCESS"
    )

    # Retrieve watermark
    result = get_watermark(pipeline_name)

    print("Retrieved Watermark:", result)

