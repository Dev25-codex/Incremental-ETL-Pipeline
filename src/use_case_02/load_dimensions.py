import pandas as pd

from sqlalchemy import text
from database import engine


def load_dimensions(
    dim_product,
    dim_customer,
    dim_date,
    dim_region
):

    print("=" * 60)
    print("USE CASE 2: SAFE DIMENSION LOADING")
    print("=" * 60)

    try:

        # STEP 1: Validate Input DataFrames

        print("\nSTEP 1: Validating Dimension Data...")

        dimensions = {
            "Product": dim_product,
            "Customer": dim_customer,
            "Date": dim_date,
            "Region": dim_region
        }

        for name, dataframe in dimensions.items():

            if not isinstance(dataframe, pd.DataFrame):
                raise TypeError(
                    f"{name} dimension must be a pandas DataFrame."
                )

            if dataframe.empty:
                raise ValueError(
                    f"{name} dimension is empty."
                )

            print(f"{name} Dimension: {dataframe.shape}")

        # STEP 2: Clean NULL Values

        print("\nSTEP 2: Preparing Records...")

        dim_product = dim_product.astype(object).where(
            pd.notna(dim_product), None
        )

        dim_customer = dim_customer.astype(object).where(
            pd.notna(dim_customer), None
        )

        dim_date = dim_date.astype(object).where(
            pd.notna(dim_date), None
        )

        dim_region = dim_region.astype(object).where(
            pd.notna(dim_region), None
        )

        # STEP 3: Load Dimensions

        print("\nSTEP 3: Loading Dimensions...")

        with engine.begin() as connection:

            # ==========================================
            # 1. PRODUCT DIMENSION
            # ==========================================

            print("\nLoading Product Dimension...")

            product_records = dim_product.to_dict(
                orient="records"
            )

            product_inserted = 0

            for row in product_records:

                result = connection.execute(
                    text("""
                        INSERT INTO dim_product
                        (
                            product_code,
                            product_name,
                            effective_from,
                            effective_to,
                            is_current
                        )
                        SELECT
                            :code,
                            :name,
                            :effective_from,
                            NULL,
                            1
                        WHERE NOT EXISTS
                        (
                            SELECT 1
                            FROM dim_product
                            WHERE BINARY product_code = BINARY :code
                        )
                    """),
                    {
                        "code": row["product_code"],
                        "name": row["product_name"],
                        "effective_from": row["effective_from"]
                    }
                )

                product_inserted += result.rowcount

            print("New Products Inserted:", product_inserted)
            print("Existing Product History Preserved.")

            # ==========================================
            # 2. CUSTOMER DIMENSION
            # ==========================================

            print("\nLoading Customer Dimension...")

            customer_records = [
                {
                    "customer_id": int(row["customer_id"]),
                    "effective_from": "2000-01-01",
                    "effective_to": None,
                    "is_current": 1
                }
                for row in dim_customer.to_dict(orient="records")
                if row["customer_id"] is not None
            ]

            if customer_records:

                connection.execute(
                    text("""
                        INSERT IGNORE INTO dim_customer
                        (
                            customer_id,
                            effective_from,
                            effective_to,
                            is_current
                        )
                        VALUES
                        (
                            :customer_id,
                            :effective_from,
                            :effective_to,
                            :is_current
                        )
                    """),
                    customer_records
                )

            print("Customer Dimension Loading Completed.")

            # ==========================================
            # 3. DATE DIMENSION
            # ==========================================

            print("\nLoading Date Dimension...")

            date_records = dim_date.to_dict(
                orient="records"
            )

            connection.execute(
                text("""
                    INSERT IGNORE INTO dim_date
                    (
                        date_key,
                        full_date,
                        day,
                        month,
                        quarter,
                        year
                    )
                    VALUES
                    (
                        :date_key,
                        :full_date,
                        :day,
                        :month,
                        :quarter,
                        :year
                    )
                """),
                date_records
            )

            print("Date Dimension Loading Completed.")

            # ==========================================
            # 4. REGION DIMENSION
            # ==========================================

            print("\nLoading Region Dimension...")

            region_records = dim_region.to_dict(
                orient="records"
            )

            connection.execute(
                text("""
                    INSERT IGNORE INTO dim_region
                    (country)
                    VALUES (:country)
                """),
                region_records
            )

            print("Region Dimension Loading Completed.")

        print("\n" + "=" * 60)
        print("ALL DIMENSIONS LOADED SUCCESSFULLY!")
        print("=" * 60)

    except Exception as e:

     print("\nDIMENSION LOADING FAILED!")
     print("Error:", e)

     raise
    