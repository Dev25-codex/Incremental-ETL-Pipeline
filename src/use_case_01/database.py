import os
import logging
from pathlib import Path

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv


# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load database credentials from .env
load_dotenv(PROJECT_ROOT / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def get_db_connection():
    """Create and return a MySQL database connection."""

    try:
        logger.info("Connecting to MySQL database...")

        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE"),
            connection_timeout=10
        )

        if not connection.is_connected():
            connection.close()
            raise ConnectionError("MySQL connection could not be established")

        logger.info("MySQL connection established successfully")
        return connection

    except Error:
        logger.exception("MySQL connection failed")
        raise

    except (ValueError, TypeError):
        logger.exception("Invalid database configuration")
        raise


def test_connection():
    """Test MySQL connection and close resources safely."""

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT DATABASE(), VERSION()")
        result = cursor.fetchone()

        print("\n========== MYSQL CONNECTION TEST ==========")
        print("Database:", result[0])
        print("MySQL Version:", result[1])
        print("Status: SUCCESS")
        print("===========================================")

    except Exception:
        logger.exception("Database connection test failed")
        raise

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
            logger.info("MySQL connection closed")


if __name__ == "__main__":
    test_connection()