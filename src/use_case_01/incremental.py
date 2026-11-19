import logging

import pandas as pd

from watermark import get_watermark


logger = logging.getLogger(__name__)


def filter_new_records(
    df: pd.DataFrame,
    pipeline_name: str
) -> pd.DataFrame:

    try:

        # 1. Validate input
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Input must be a pandas DataFrame")

        if df.empty:
            logger.warning("Input dataset is empty")
            return df.copy()

        if "InvoiceDate" not in df.columns:
            raise ValueError("InvoiceDate column is missing")

        logger.info("Starting incremental data filtering")

        # 2. Convert InvoiceDate into datetime
        df = df.copy()

        df["InvoiceDate"] = pd.to_datetime(
            df["InvoiceDate"],
            errors="coerce"
        )

        # 3. Remove records with invalid dates
        invalid_dates = df["InvoiceDate"].isna().sum()

        if invalid_dates > 0:
            logger.warning(
                "Records with invalid InvoiceDate: %s",
                invalid_dates
            )

        df = df.dropna(subset=["InvoiceDate"])

        # 4. Get previous watermark from MySQL
        last_watermark = get_watermark(pipeline_name)

        # 5. First run: no previous watermark
        if last_watermark is None:

            logger.info("No previous watermark found. First run.")

            return df.copy()

        # 6. Convert watermark into datetime
        last_watermark = pd.to_datetime(last_watermark)

        # 7. Filter records newer than watermark
        new_records = df[
            df["InvoiceDate"] > last_watermark
        ].copy()

        # 8. Log filtering results
        logger.info("Previous watermark: %s", last_watermark)

        logger.info("Total source records: %s", len(df))

        logger.info("New records found: %s", len(new_records))

        logger.info(
            "Skipped old records: %s",
            len(df) - len(new_records)
        )

        return new_records

    except Exception:

        logger.exception("Incremental filtering failed")
        raise


# --------------------------------------------------
# TESTING
# --------------------------------------------------

if __name__ == "__main__":

    test_data = pd.DataFrame({
        "InvoiceNo": ["1001", "1002", "1003"],
        "InvoiceDate": [
            "2011-12-08 10:00:00",
            "2011-12-09 12:50:00",
            "2011-12-09 13:00:00"
        ]
    })

    pipeline_name = "watermark_test"

    result = filter_new_records(
        test_data,
        pipeline_name
    )

    print("\n========== INCREMENTAL TEST ==========")

    print("Original records:", len(test_data))
    print("New records:", len(result))

    print("\nFiltered records:")
    print(result)

    print("======================================")