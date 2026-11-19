from sqlalchemy import text
from database import engine
from datetime import datetime


# Only manually approved product changes will be processed.
APPROVED_CHANGES = [
    {
        "product_code": "21818",
        "old_name": "GLITTER CHRISTMAS HEART",
        "new_name": "GLITTER HEART DECORATION",
        "effective_date": "2011-02-02"
    }
]


def process_scd_type2():

    print("=" * 60)
    print("GENERIC SCD TYPE 2 ENGINE")
    print("=" * 60)

    try:

        with engine.begin() as connection:

            for change in APPROVED_CHANGES:

                product_code = change["product_code"]
                old_name = change["old_name"].strip()
                new_name = change["new_name"].strip()

                effective_date = datetime.strptime(
                    change["effective_date"], "%Y-%m-%d"
                ).date()

                date_key = int(effective_date.strftime("%Y%m%d"))

                print(f"\nProcessing Product: {product_code}")

                # STEP 1: Fetch current product versions
                current_versions = connection.execute(
                    text("""
                        SELECT
                            product_key,
                            product_name,
                            effective_from
                        FROM dim_product
                        WHERE product_code = :code
                          AND is_current = 1
                        FOR UPDATE
                    """),
                    {"code": product_code}
                ).mappings().all()

                # STEP 2: Validate current record
                if len(current_versions) == 0:
                    raise ValueError(
                        f"No current product found: {product_code}"
                    )

                if len(current_versions) > 1:
                    raise ValueError(
                        f"Multiple current versions found: {product_code}"
                    )

                current = current_versions[0]

                current_name = (
                    current["product_name"].strip()
                    if current["product_name"] else ""
                )

                # STEP 3: Idempotency check
                if current_name == new_name:

                    print("SCD change already processed.")
                    print("Skipping duplicate insertion.")
                    continue

                # STEP 4: Validate old product version
                if current_name != old_name:
                    raise ValueError(
                        f"Unexpected current product name: {current_name}"
                    )

                # STEP 5: Validate effective_from
                if current["effective_from"] is None:
                    raise ValueError(
                        f"Product {product_code} has NULL effective_from. "
                        "Manual review required."
                    )

                if current["effective_from"] >= effective_date:
                    raise ValueError(
                        "Effective date must be after the old version start date."
                    )

                old_key = current["product_key"]

                # STEP 6: Close old product version
                update_result = connection.execute(
                    text("""
                        UPDATE dim_product
                        SET effective_to = :effective_date,
                            is_current = 0
                        WHERE product_key = :old_key
                          AND is_current = 1
                    """),
                    {
                        "effective_date": effective_date,
                        "old_key": old_key
                    }
                )

                if update_result.rowcount != 1:
                    raise ValueError(
                        "Old product version could not be closed."
                    )

                print("Old product version closed.")

                # STEP 7: Insert new product version
                insert_result = connection.execute(
                    text("""
                        INSERT INTO dim_product
                        (
                            product_code,
                            product_name,
                            effective_from,
                            effective_to,
                            is_current
                        )
                        VALUES
                        (
                            :code,
                            :name,
                            :effective_date,
                            NULL,
                            1
                        )
                    """),
                    {
                        "code": product_code,
                        "name": new_name,
                        "effective_date": effective_date
                    }
                )

                new_key = insert_result.lastrowid

                print("New product version inserted.")

                # STEP 8: Update corresponding fact records
                fact_result = connection.execute(
                    text("""
                        UPDATE fact_sales
                        SET product_key = :new_key
                        WHERE product_key = :old_key
                          AND date_key >= :date_key
                    """),
                    {
                        "new_key": new_key,
                        "old_key": old_key,
                        "date_key": date_key
                    }
                )

                print("Fact records updated:", fact_result.rowcount)
                print("Old Product Key:", old_key)
                print("New Product Key:", new_key)

        print("\nSCD TYPE 2 PROCESS COMPLETED SUCCESSFULLY!")

    except Exception as e:

        print("\nSCD TYPE 2 PROCESS FAILED!")
        print("Transaction rolled back if an error occurred.")
        print("Error:", e)

        raise

    finally:
        engine.dispose()


if __name__ == "__main__":
    process_scd_type2()
