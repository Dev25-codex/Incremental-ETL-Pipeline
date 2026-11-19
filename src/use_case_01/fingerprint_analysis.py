import logging
import hashlib
import json
from pathlib import Path

import pandas as pd

from extract import extract_data


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
        logging.FileHandler(
            LOG_DIR / "fingerprint_analysis.log"
        ),
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
# NORMALIZE RECORD VALUES
# --------------------------------------------------

def normalize_value(column, value):
    """Convert values into a consistent representation."""

    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if column in [
        "InvoiceNo",
        "StockCode",
        "Description",
        "Country"
    ]:
        return str(value).strip()

    if column == "Quantity":
        return int(value)

    if column == "UnitPrice":
        return format(float(value), ".2f")

    if column == "CustomerID":
        return format(float(value), ".2f")

    return str(value)


# --------------------------------------------------
# GENERATE SHA-256 FINGERPRINT
# --------------------------------------------------

def generate_fingerprint(df: pd.DataFrame) -> pd.DataFrame:
    """Generate SHA-256 fingerprints for complete records."""

    try:

        if not isinstance(df, pd.DataFrame):
            raise TypeError(
                "Input must be a pandas DataFrame"
            )

        if df.empty:
            raise ValueError(
                "Dataset is empty"
            )

        missing_columns = [
            column for column in REQUIRED_COLUMNS
            if column not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Missing columns: {missing_columns}"
            )

        logger.info(
            "Starting SHA-256 fingerprint generation"
        )

        result = df.copy()

        fingerprints = []

        for row in result[REQUIRED_COLUMNS].itertuples(
            index=False,
            name=None
        ):

            normalized_record = {
                column: normalize_value(column, value)
                for column, value in zip(
                    REQUIRED_COLUMNS,
                    row
                )
            }

            serialized_record = json.dumps(
                normalized_record,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False
            )

            fingerprint = hashlib.sha256(
                serialized_record.encode("utf-8")
            ).hexdigest()

            fingerprints.append(fingerprint)

        result["record_hash"] = fingerprints

        logger.info(
            "Fingerprint generation completed"
        )

        logger.info(
            "Total records fingerprinted: %s",
            len(result)
        )

        logger.info(
            "Unique fingerprints: %s",
            result["record_hash"].nunique()
        )

        logger.info(
            "Duplicate fingerprint rows: %s",
            result.duplicated(
                subset=["record_hash"]
            ).sum()
        )

        return result

    except Exception:

        logger.exception(
            "Fingerprint generation failed"
        )

        raise


# --------------------------------------------------
# ANALYZE FINGERPRINTS
# --------------------------------------------------

def analyze_fingerprints(df: pd.DataFrame) -> dict:
    """Analyze duplicate and unique fingerprints."""

    try:

        if not isinstance(df, pd.DataFrame):
            raise TypeError(
                "Input must be a pandas DataFrame"
            )

        if "record_hash" not in df.columns:
            raise ValueError(
                "record_hash column is missing"
            )

        total_records = len(df)

        unique_hashes = df["record_hash"].nunique()

        duplicate_hash_rows = int(
            df.duplicated(
                subset=["record_hash"]
            ).sum()
        )

        duplicate_groups = (
            df.groupby("record_hash")
            .size()
            .reset_index(name="record_count")
        )

        duplicate_groups = duplicate_groups[
            duplicate_groups["record_count"] > 1
        ]

        results = {
            "total_records": total_records,
            "unique_fingerprints": int(unique_hashes),
            "duplicate_fingerprint_rows": duplicate_hash_rows,
            "duplicate_fingerprint_groups": len(
                duplicate_groups
            )
        }

        logger.info(
            "Fingerprint analysis completed: %s",
            results
        )

        return results

    except Exception:

        logger.exception(
            "Fingerprint analysis failed"
        )

        raise


# --------------------------------------------------
# GET DUPLICATE RECORD GROUPS
# --------------------------------------------------

def get_duplicate_records(df: pd.DataFrame) -> pd.DataFrame:
    """Return all records having duplicate fingerprints."""

    try:

        if "record_hash" not in df.columns:
            raise ValueError(
                "record_hash column is missing"
            )

        duplicate_records = df[
            df.duplicated(
                subset=["record_hash"],
                keep=False
            )
        ].copy()

        duplicate_records = duplicate_records.sort_values(
            by="record_hash"
        )

        logger.info(
            "Duplicate records identified: %s",
            len(duplicate_records)
        )

        return duplicate_records

    except Exception:

        logger.exception(
            "Duplicate record analysis failed"
        )

        raise


# --------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------

if __name__ == "__main__":

    try:

        # Extract source data
        df = extract_data(FILE_PATH)

        # Generate fingerprints
        fingerprinted_df = generate_fingerprint(df)

        # Analyze fingerprints
        results = analyze_fingerprints(
            fingerprinted_df
        )

        # Get duplicate records
        duplicate_records = get_duplicate_records(
            fingerprinted_df
        )

        # Display report
        print(
            "\n========== SHA-256 FINGERPRINT REPORT =========="
        )

        for key, value in results.items():
            print(f"{key}: {value}")

        print("\nFingerprint samples:")

        print(
            fingerprinted_df[
                [
                    "InvoiceNo",
                    "StockCode",
                    "record_hash"
                ]
            ].head()
        )

        print("\nFingerprint length:")

        print(
            fingerprinted_df["record_hash"]
            .str.len()
            .unique()
        )

        print("\nDuplicate record preview:")

        print(
            duplicate_records.head(10)
        )

        print("\n===============================================")

    except Exception:

        logger.exception(
            "Fingerprint analysis pipeline failed"
        )

        raise