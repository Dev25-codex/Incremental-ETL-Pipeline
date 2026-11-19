import logging
from pathlib import Path

import pandas as pd

from extract import extract_data


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FILE_PATH = PROJECT_ROOT / "data" / "raw" / "Online Retail.xlsx"

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "duplicate_analysis.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def analyze_duplicates(df: pd.DataFrame) -> dict:
    """
    Investigate exact duplicates and business-key duplicates.
    """

    try:
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Input must be a pandas DataFrame")

        if df.empty:
            raise ValueError("Dataset is empty")

        candidate_key = [
            "InvoiceNo",
            "StockCode",
            "InvoiceDate",
            "Quantity",
            "UnitPrice"
        ]

        required_columns = candidate_key + [
            "Description",
            "CustomerID"
        ]

        missing_columns = [
            col for col in required_columns if col not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {missing_columns}"
            )

        logger.info("Starting duplicate investigation")

        # 1. Exact duplicate records
        exact_duplicate_rows = df[df.duplicated(keep=False)]

        # 2. Candidate-key duplicate records
        business_duplicates = df[
            df.duplicated(subset=candidate_key, keep=False)
        ]

        # 3. Identify repeated candidate-key groups
        duplicate_groups = (
            df.groupby(candidate_key, dropna=False)
            .size()
            .reset_index(name="record_count")
        )

        duplicate_groups = duplicate_groups[
            duplicate_groups["record_count"] > 1
        ]

        # 4. Check whether repeated keys have different descriptions
        # or CustomerIDs
        grouped = df.groupby(candidate_key, dropna=False)

        conflicting_groups = grouped.filter(
            lambda group: (
                group["Description"].nunique(dropna=False) > 1
                or group["CustomerID"].nunique(dropna=False) > 1
            )
        )

        results = {
            "total_rows": len(df),
            "exact_duplicate_rows": len(exact_duplicate_rows),
            "candidate_duplicate_rows": len(business_duplicates),
            "candidate_duplicate_groups": len(duplicate_groups),
            "conflicting_candidate_rows": len(conflicting_groups)
        }

        logger.info("Duplicate investigation completed")
        logger.info("Results: %s", results)

        return {
            "summary": results,
            "duplicate_groups": duplicate_groups,
            "conflicting_records": conflicting_groups
        }

    except (TypeError, ValueError):
        logger.exception("Duplicate analysis validation failed")
        raise

    except Exception:
        logger.exception("Unexpected duplicate analysis error")
        raise


def display_results(results: dict) -> None:
    """Display duplicate investigation report."""

    print("\n========== DUPLICATE ANALYSIS ==========")

    for key, value in results["summary"].items():
        print(f"{key}: {value}")

    print("\n--- Duplicate Groups (First 10) ---")

    print(
        results["duplicate_groups"]
        .head(10)
        .to_string(index=False)
    )

    print("\n--- Conflicting Records (First 20) ---")

    print(
        results["conflicting_records"]
        .head(20)
        .to_string(index=False)
    )

    print("\n========================================")


if __name__ == "__main__":

    try:
        df = extract_data(FILE_PATH)

        results = analyze_duplicates(df)

        display_results(results)

    except Exception:
        logger.exception("Duplicate investigation pipeline failed")
        raise