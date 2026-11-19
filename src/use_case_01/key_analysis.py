import logging
from pathlib import Path

import pandas as pd

from extract import extract_data


# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

FILE_PATH = PROJECT_ROOT / "data" / "raw" / "Online Retail.xlsx"


# Logging configuration
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "key_analysis.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def analyze_candidate_keys(df: pd.DataFrame) -> dict:
    """
    Investigate candidate keys for retail transactions.
    """

    try:
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Input must be a pandas DataFrame")

        if df.empty:
            raise ValueError("Dataset is empty")

        required_columns = [
            "InvoiceNo",
            "StockCode",
            "InvoiceDate",
            "Quantity",
            "UnitPrice"
        ]

        missing_columns = [
            col for col in required_columns if col not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {missing_columns}"
            )

        logger.info("Starting candidate key investigation")

        candidate_keys = {
            "InvoiceNo": ["InvoiceNo"],
            "InvoiceNo_StockCode": ["InvoiceNo", "StockCode"],
            "InvoiceNo_StockCode_InvoiceDate": [
                "InvoiceNo", "StockCode", "InvoiceDate"
            ],
            "InvoiceNo_StockCode_InvoiceDate_Quantity_UnitPrice": [
                "InvoiceNo", "StockCode", "InvoiceDate",
                "Quantity", "UnitPrice"
            ]
        }

        results = {}

        for key_name, columns in candidate_keys.items():

            duplicate_count = int(
                df.duplicated(subset=columns).sum()
            )

            null_count = int(
                df[columns].isnull().any(axis=1).sum()
            )

            results[key_name] = {
                "columns": columns,
                "duplicate_rows": duplicate_count,
                "rows_with_null_key": null_count,
                "is_unique": duplicate_count == 0 and null_count == 0
            }

            logger.info(
                "%s | Duplicates: %s | Null keys: %s | Unique: %s",
                key_name,
                duplicate_count,
                null_count,
                results[key_name]["is_unique"]
            )

        logger.info("Candidate key investigation completed")

        return results

    except (TypeError, ValueError):
        logger.exception("Key analysis validation failed")
        raise

    except Exception:
        logger.exception("Unexpected error during key analysis")
        raise


def display_key_results(results: dict) -> None:
    """Display candidate key investigation results."""

    print("\n========== CANDIDATE KEY ANALYSIS ==========")

    for key_name, details in results.items():

        print(f"\nCandidate: {key_name}")
        print(f"Columns: {details['columns']}")
        print(f"Duplicate rows: {details['duplicate_rows']}")
        print(f"Rows with null key: {details['rows_with_null_key']}")
        print(f"Unique: {details['is_unique']}")

    print("\n============================================")


if __name__ == "__main__":

    try:
        df = extract_data(FILE_PATH)

        results = analyze_candidate_keys(df)

        display_key_results(results)

    except Exception:
        logger.exception("Key analysis pipeline failed")
        raise