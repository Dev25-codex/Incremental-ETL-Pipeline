import pandas as pd

from decimal import Decimal
from sqlalchemy import text

from database import engine
from extract import extract_data


BATCH_SIZE = 5000


def load_fact(df):

    print("=" * 60)
    print("USE CASE 2: FACT TABLE LOADING")
    print("=" * 60)

    try:

        # STEP 1: EXTRACT

        if df is None or df.empty:
         raise ValueError("Source DataFrame is empty.")

        print("Source Records:", len(df))
        with engine.begin() as connection:

            # STEP 2: CHECK FACT TABLE

            print("\nSTEP 2: Checking Fact Table...")

            existing_count = connection.execute(
                text("SELECT COUNT(*) FROM fact_sales")
            ).scalar()

            if existing_count > 0:
                raise ValueError(
                    f"Fact table already contains {existing_count} records. "
                    "Loading stopped to prevent duplicates."
                )

            # STEP 3: UNKNOWN CUSTOMER

            print("\nSTEP 3: Handling Missing Customers...")

            connection.execute(text("""
                INSERT INTO dim_customer
                (customer_id, effective_from, effective_to, is_current)
                SELECT -1, '2000-01-01', NULL, TRUE
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM dim_customer
                    WHERE customer_id = -1
                )
            """))

            # STEP 4: FETCH DIMENSIONS

            print("\nSTEP 4: Fetching Dimension Keys...")

            product_dim = pd.read_sql(
                text("""
                    SELECT
                        product_key,
                        product_code,
                        effective_from,
                        effective_to
                    FROM dim_product
                """),
                connection
            )

            customer_dim = pd.read_sql(
                text("""
                    SELECT customer_key, customer_id
                    FROM dim_customer
                """),
                connection
            )

            date_dim = pd.read_sql(
                text("""
                    SELECT date_key, full_date
                    FROM dim_date
                """),
                connection
            )

            region_dim = pd.read_sql(
                text("""
                    SELECT region_key, country
                    FROM dim_region
                """),
                connection
            )

            # STEP 5: PRODUCT SCD TYPE 2 MAPPING

            print("\nSTEP 5: Mapping Product Versions...")

            df["_source_row_id"] = range(len(df))

            df["_product_code"] = (
                df["StockCode"]
                .astype("string")
                .str.strip()
            )

            df["_invoice_date"] = pd.to_datetime(
                df["InvoiceDate"],
                errors="coerce"
            ).dt.normalize()

            product_dim["product_code"] = (
                product_dim["product_code"]
                .astype("string")
                .str.strip()
            )

            product_dim["effective_from"] = pd.to_datetime(
                product_dim["effective_from"],
                errors="coerce"
            ).dt.normalize()

            product_dim["effective_to"] = pd.to_datetime(
                product_dim["effective_to"],
                errors="coerce"
            ).dt.normalize()

            product_candidates = df[
                [
                    "_source_row_id",
                    "_product_code",
                    "_invoice_date"
                ]
            ].merge(
                product_dim,
                left_on="_product_code",
                right_on="product_code",
                how="left"
            )

            valid_product_versions = product_candidates[
                product_candidates["effective_from"].notna()
                & (
                    product_candidates["_invoice_date"]
                    >= product_candidates["effective_from"]
                )
                & (
                    product_candidates["effective_to"].isna()
                    | (
                        product_candidates["_invoice_date"]
                        < product_candidates["effective_to"]
                    )
                )
            ].copy()

            product_match_counts = (
                valid_product_versions
                .groupby("_source_row_id")
                .size()
            )

            invalid_product_rows = (
                len(df)
                - int(
                    product_match_counts[
                        product_match_counts == 1
                    ].count()
                )
            )

            if invalid_product_rows > 0:

                raise ValueError(
                    f"{invalid_product_rows} source records have "
                    "missing or ambiguous product version mappings."
                )

            product_key_map = (
                valid_product_versions
                .set_index("_source_row_id")["product_key"]
            )

            product_keys = (
                df["_source_row_id"]
                .map(product_key_map)
            )

            print("Product Version Mapping Successful.")

            # CUSTOMER MAPPING

            print("\nMapping Customers...")

            customer_map = dict(zip(
                customer_dim["customer_id"].astype(int),
                customer_dim["customer_key"].astype(int)
            ))

            unknown_customer_key = customer_map[-1]

            customer_ids = pd.to_numeric(
                df["CustomerID"],
                errors="coerce"
            ).astype("Int64")

            customer_keys = (
                customer_ids.map(customer_map)
                .fillna(unknown_customer_key)
            )

            # DATE MAPPING

            date_map = dict(zip(
                pd.to_datetime(
                    date_dim["full_date"]
                ).dt.strftime("%Y-%m-%d"),
                date_dim["date_key"].astype(int)
            ))

            date_keys = (
                df["_invoice_date"]
                .dt.strftime("%Y-%m-%d")
                .map(date_map)
            )

            # REGION MAPPING

            region_map = dict(zip(
                region_dim["country"].astype(str).str.strip(),
                region_dim["region_key"].astype(int)
            ))

            region_keys = (
                df["Country"]
                .astype("string")
                .str.strip()
                .map(region_map)
            )

            # STEP 6: VALIDATE MAPPINGS

            print("\nSTEP 6: Validating Dimension Mappings...")

            missing_mappings = {
                "Product": int(product_keys.isna().sum()),
                "Customer": int(customer_keys.isna().sum()),
                "Date": int(date_keys.isna().sum()),
                "Region": int(region_keys.isna().sum())
            }

            for name, count in missing_mappings.items():
                print(f"{name}: {count}")

            if any(missing_mappings.values()):
                raise ValueError(
                    "Missing dimension mappings detected. "
                    "Fact loading stopped."
                )

            # STEP 7: PREPARE FACT DATA

            print("\nSTEP 7: Preparing Fact Records...")

            quantity = pd.to_numeric(
                df["Quantity"],
                errors="coerce"
            )

            unit_price = pd.to_numeric(
                df["UnitPrice"],
                errors="coerce"
            )

            if quantity.isna().any() or unit_price.isna().any():
                raise ValueError(
                    "Invalid Quantity or UnitPrice found."
                )

            fact_df = pd.DataFrame({

                "invoice_no": df["InvoiceNo"],

                "product_key": product_keys,

                "customer_key": customer_keys,

                "date_key": date_keys,

                "region_key": region_keys,

                "quantity": quantity.astype(int),

                "unit_price": unit_price,

                "sales_amount": quantity * unit_price

            })

            print("Prepared Fact Records:", len(fact_df))

            # STEP 8: BATCH LOADING

            print("\nSTEP 8: Loading Fact Records...")

            insert_query = text("""
                INSERT INTO fact_sales
                (
                    invoice_no,
                    product_key,
                    customer_key,
                    date_key,
                    region_key,
                    quantity,
                    unit_price,
                    sales_amount
                )
                VALUES
                (
                    :invoice_no,
                    :product_key,
                    :customer_key,
                    :date_key,
                    :region_key,
                    :quantity,
                    :unit_price,
                    :sales_amount
                )
            """)

            total_records = len(fact_df)

            for start in range(0, total_records, BATCH_SIZE):

                end = min(
                    start + BATCH_SIZE,
                    total_records
                )

                batch_df = fact_df.iloc[start:end].copy()

                records = []

                for row in batch_df.to_dict(orient="records"):

                    records.append({

                        "invoice_no": (
                            None if pd.isna(row["invoice_no"])
                            else str(row["invoice_no"])
                        ),

                        "product_key": int(row["product_key"]),

                        "customer_key": int(row["customer_key"]),

                        "date_key": int(row["date_key"]),

                        "region_key": int(row["region_key"]),

                        "quantity": int(row["quantity"]),

                        "unit_price": Decimal(
                            str(row["unit_price"])
                        ).quantize(Decimal("0.01")),

                        "sales_amount": Decimal(
                            str(row["sales_amount"])
                        ).quantize(Decimal("0.01"))

                    })

                connection.execute(
                    insert_query,
                    records
                )

                print(
                    f"Loaded {end} / {total_records} records"
                )

            # STEP 9: FINAL VALIDATION

            final_count = connection.execute(
                text("SELECT COUNT(*) FROM fact_sales")
            ).scalar()

            print("\n" + "=" * 60)
            print("FACT TABLE LOADING COMPLETED")
            print("=" * 60)

            print("Source Records:", total_records)
            print("Fact Records:", final_count)

            if final_count != total_records:
                raise ValueError(
                    "Source and Fact record counts do not match."
                )

            print("\nALL FACT RECORDS LOADED SUCCESSFULLY!")

    except Exception as e:

        print("\nFACT TABLE LOADING FAILED!")
        print("Error:", e)

        raise
    
if __name__ == "__main__":
    df = extract_data()
    load_fact(df)
    