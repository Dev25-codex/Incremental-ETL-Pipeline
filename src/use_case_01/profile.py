import logging
from pathlib import Path

import pandas as pd

from extract import extract_data


# Project directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]

FILE_PATH = PROJECT_ROOT / "data" / "raw" / "Online Retail.xlsx"


# Logging configuration
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "profiling.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def profile_data(df: pd.DataFrame) -> dict:
    """
    Generate a basic data quality profile.
    """

    try:
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Input must be a pandas DataFrame")

        if df.empty:
            raise ValueError("DataFrame is empty")

        logger.info("Starting data profiling")

        profile = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "missing_values": df.isnull().sum().to_dict(),
            "duplicate_rows": int(df.duplicated().sum()),
            "data_types": df.dtypes.astype(str).to_dict(),
            "unique_invoices": int(df["InvoiceNo"].nunique()),
            "unique_stock_codes": int(df["StockCode"].nunique()),
            "date_range": {
                "start": str(df["InvoiceDate"].min()),
                "end": str(df["InvoiceDate"].max())
            }
        }

        logger.info("Data profiling completed successfully")

        return profile

    except (TypeError, ValueError):
        logger.exception("Data profiling validation failed")
        raise

    except Exception:
        logger.exception("Unexpected error during data profiling")
        raise


def display_profile(profile: dict) -> None:
    """Display profiling results."""

    try:
        print("\n========== DATA PROFILE ==========")

        for key, value in profile.items():
            print(f"\n{key}:")
            print(value)

        print("\n==================================")

    except Exception:
        logger.exception("Unable to display profiling results")
        raise


if __name__ == "__main__":

    try:
        df = extract_data(FILE_PATH)

        profile = profile_data(df)

        display_profile(profile)

    except Exception:
        logger.exception("Profiling pipeline failed")
        raise