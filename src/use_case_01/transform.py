import logging
from pathlib import Path

import pandas as pd

from extract import extract_data
from fingerprint_analysis import generate_fingerprint


# --------------------------------------------------
# PROJECT CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

FILE_PATH = PROJECT_ROOT / "data" / "raw" / "Online Retail.xlsx"

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# LOGGING CONFIGURATION
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "transform.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# REQUIRED COLUMNS
# --------------------------------------------------

REQUIRED_COLUMNS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country"
]


# --------------------------------------------------
# VALIDATE COLUMNS
# --------------------------------------------------

def validate_columns(df: pd.DataFrame) -> None:
    """Validate required source columns."""

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )


# --------------------------------------------------
# TRANSFORM DATA
# --------------------------------------------------

def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean, standardize and fingerprint retail data."""

    try:

        # 1. Validate input
        if not isinstance(df, pd.DataFrame):
            raise TypeError(
                "Input must be a pandas DataFrame"
            )

        if df.empty:
            raise ValueError(
                "Input dataset is empty"
            )

        logger.info("Starting data transformation")

        transformed_df = df.copy()

        initial_rows = len(transformed_df)

        # 2. Standardize column names
        transformed_df.columns = (
            transformed_df.columns.str.strip()
        )

        validate_columns(transformed_df)

        # 3. Standardize text columns
        text_columns = [
            "InvoiceNo",
            "StockCode",
            "Description",
            "Country"
        ]

        for column in text_columns:

            transformed_df[column] = (
                transformed_df[column]
                .astype("string")
                .str.strip()
            )

        # 4. Standardize data types
        transformed_df["InvoiceDate"] = pd.to_datetime(
            transformed_df["InvoiceDate"],
            errors="coerce"
        )

        transformed_df["Quantity"] = pd.to_numeric(
            transformed_df["Quantity"],
            errors="coerce"
        ).astype("Int64")

        transformed_df["UnitPrice"] = pd.to_numeric(
            transformed_df["UnitPrice"],
            errors="coerce"
        )

        transformed_df["CustomerID"] = pd.to_numeric(
            transformed_df["CustomerID"],
            errors="coerce"
        )

        # 5. Identify invalid records
        invalid_date_rows = int(
            transformed_df["InvoiceDate"].isna().sum()
        )

        invalid_quantity_rows = int(
            transformed_df["Quantity"].isna().sum()
        )

        invalid_price_rows = int(
            transformed_df["UnitPrice"].isna().sum()
        )

        # 6. Normalize missing descriptions
        transformed_df["Description"] = (
            transformed_df["Description"].replace(
                "", pd.NA
            )
        )

        # 7. Prepare fingerprint input
        fingerprint_df = transformed_df[
            REQUIRED_COLUMNS
        ].copy()

        # 8. Generate SHA-256 fingerprints
        fingerprint_result = generate_fingerprint(
            fingerprint_df
        )

        # 9. Validate fingerprint result
        if not isinstance(fingerprint_result, pd.DataFrame):
            raise TypeError(
                "Fingerprint function must return a DataFrame"
            )

        if "record_hash" not in fingerprint_result.columns:
            raise ValueError(
                "record_hash column missing from fingerprint output"
            )

        if len(fingerprint_result) != len(transformed_df):
            raise ValueError(
                "Fingerprint count does not match row count"
            )

        # Extract only record_hash column
        transformed_df["record_hash"] = (
            fingerprint_result["record_hash"].to_numpy()
        )

        if transformed_df["record_hash"].isna().any():
            raise ValueError(
                "Some records have missing fingerprints"
            )

        # Validate SHA-256 length
        fingerprint_lengths = (
            transformed_df["record_hash"]
            .astype("string")
            .str.len()
        )

        if not fingerprint_lengths.eq(64).all():
            raise ValueError(
                "Invalid SHA-256 fingerprint length detected"
            )

        # 10. Transformation summary
        logger.info(
            "Transformation completed successfully"
        )

        logger.info(
            "Initial rows: %s",
            initial_rows
        )

        logger.info(
            "Final rows: %s",
            len(transformed_df)
        )

        logger.info(
            "Invalid dates: %s",
            invalid_date_rows
        )

        logger.info(
            "Invalid quantities: %s",
            invalid_quantity_rows
        )

        logger.info(
            "Invalid prices: %s",
            invalid_price_rows
        )

        logger.info(
            "Fingerprint algorithm: SHA-256"
        )

        logger.info(
            "Fingerprint length: %s",
            fingerprint_lengths.unique().tolist()
        )

        logger.info(
            "Unique fingerprints: %s",
            transformed_df["record_hash"].nunique()
        )

        logger.info(
            "Duplicate fingerprint rows: %s",
            transformed_df.duplicated(
                subset=["record_hash"]
            ).sum()
        )

        return transformed_df

    except (TypeError, ValueError):

        logger.exception(
            "Transformation validation failed"
        )

        raise

    except Exception:

        logger.exception(
            "Unexpected transformation error"
        )

        raise


# --------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------

if __name__ == "__main__":

    try:

        # Extract data
        df = extract_data(FILE_PATH)

        # Transform data
        transformed_df = transform_data(df)

        # Display transformation report
        print("\n========== TRANSFORMATION REPORT ==========")

        print("\nOriginal shape:")
        print(df.shape)

        print("\nTransformed shape:")
        print(transformed_df.shape)

        print("\nMissing values:")
        print(transformed_df.isnull().sum())

        print("\nData types:")
        print(transformed_df.dtypes)

        print("\nFingerprint samples:")
        print(
            transformed_df[
                ["InvoiceNo", "StockCode", "record_hash"]
            ].head()
        )

        print("\nFingerprint length:")
        print(
            transformed_df["record_hash"]
            .str.len()
            .unique()
        )

        print("\nUnique fingerprints:")
        print(
            transformed_df["record_hash"].nunique()
        )

        print("\nDuplicate fingerprint rows:")
        print(
            transformed_df.duplicated(
                subset=["record_hash"]
            ).sum()
        )

        print("\nTransformed data preview:")
        print(transformed_df.head())

        print("\n===========================================")

    except Exception:

        logger.exception(
            "Transformation pipeline failed"
        )

        raise