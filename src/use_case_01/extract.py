import logging
from pathlib import Path

import pandas as pd


# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Dataset path
FILE_PATH = PROJECT_ROOT / "data" / "raw" / "Online Retail.xlsx"


# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def extract_data(file_path: Path) -> pd.DataFrame:
    """
    Extract retail transaction data from an Excel file.
    """

    try:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Dataset not found: {file_path}"
            )

        if file_path.suffix.lower() != ".xlsx":
            raise ValueError("Expected an Excel .xlsx file")

        logger.info("Starting data extraction")

        df = pd.read_excel(file_path, engine="openpyxl")

        if df.empty:
            raise ValueError("Dataset is empty")

        logger.info("Data extraction successful")
        logger.info("Total rows: %s", len(df))
        logger.info("Total columns: %s", len(df.columns))

        return df

    except (FileNotFoundError, ValueError):
        logger.exception("Data extraction failed")
        raise

    except Exception:
        logger.exception("Unexpected error during extraction")
        raise


if __name__ == "__main__":
    data = extract_data(FILE_PATH)

    print("\nDataset Preview:")
    print(data.head())

    print("\nDataset Shape:")
    print(data.shape)