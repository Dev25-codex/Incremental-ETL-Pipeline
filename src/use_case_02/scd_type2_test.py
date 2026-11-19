from sqlalchemy import text
from database import engine
from datetime import datetime


APPROVED_CHANGES = [
    {
        "product_code": "TEST_SCD_001",
        "old_name": "OLD TEST PRODUCT",
        "new_name": "NEW TEST PRODUCT",
        "effective_date": "2025-01-10"
    }
]


def process_scd_type2():

    print("=" * 60)
    print("SCD TYPE 2 TEST ENGINE")
    print("=" * 60)

    with engine.begin() as connection:

        for change in APPROVED_CHANGES:

            code = change["product_code"]
            old_name = change["old_name"]
            new_name = change["new_name"]

            effective_date = datetime.strptime(
                change["effective_date"], "%Y-%m-%d"
            ).date()

            date_key = int(effective_date.strftime("%Y%m%d"))

            print("\nProcessing:", code)

            current_records = connection.execute(
                text("""
                    SELECT product_key, product_name, effective_from
                    FROM dim_product_scd_test
                    WHERE product_code = :code
                      AND is_current = 1
                    FOR UPDATE
                """),
                {"code": code}
            ).mappings().all()

            # Validation 1: Exactly one current record
            if len(current_records) == 0:
                raise ValueError("Current product not found.")

            if len(current_records) > 1:
                raise ValueError("Multiple current records found.")

            current = current_records[0]

            # Validation 2: Idempotency
            if current["product_name"].strip() == new_name:
                print("Already processed. Skipping.")
                continue

            # Validation 3: Expected old product name
            if current["product_name"].strip() != old_name:
                raise ValueError("Unexpected old product name.")

            # Validation 4: NULL effective_from
            if current["effective_from"] is None:
                raise ValueError("effective_from cannot be NULL.")

            # Validation 5: Effective date
            if current["effective_from"] >= effective_date:
                raise ValueError("Invalid effective date.")

            old_key = current["product_key"]

            # Step 1: Close old version
            close_result = connection.execute(
                text("""
                    UPDATE dim_product_scd_test
                    SET effective_to = :date,
                        is_current = 0
                    WHERE product_key = :key
                      AND is_current = 1
                """),
                {
                    "date": effective_date,
                    "key": old_key
                }
            )

            if close_result.rowcount != 1:
                raise ValueError("Old version closure failed.")

            # Step 2: Insert new version
            insert_result = connection.execute(
                text("""
                    INSERT INTO dim_product_scd_test
                    (
                        product_code,
                        product_name,
                        effective_from,
                        effective_to,
                        is_current
                    )
                    VALUES
                    (:code, :name, :date, NULL, 1)
                """),
                {
                    "code": code,
                    "name": new_name,
                    "date": effective_date
                }
            )

            new_key = insert_result.lastrowid

            if not new_key:
                raise ValueError("New version insertion failed.")

            # Step 3: Update fact records
            fact_result = connection.execute(
                text("""
                    UPDATE fact_sales_scd_test
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

            print("Old version closed:", old_key)
            print("New version inserted:", new_key)
            print("Fact records updated:", fact_result.rowcount)

    print("\nSCD TYPE 2 PROCESS COMPLETED!")


def test_transaction_rollback():

    print("\n" + "=" * 60)
    print("TRANSACTION ROLLBACK TEST")
    print("=" * 60)

    try:

        with engine.begin() as connection:

            current = connection.execute(
                text("""
                    SELECT product_key
                    FROM dim_product_scd_test
                    WHERE product_code = 'TEST_SCD_001'
                      AND is_current = 1
                    FOR UPDATE
                """)
            ).mappings().one()

            # Temporary update inside transaction
            connection.execute(
                text("""
                    UPDATE dim_product_scd_test
                    SET is_current = 0
                    WHERE product_key = :key
                """),
                {"key": current["product_key"]}
            )

            # Deliberately generate an error
            raise RuntimeError("Intentional rollback test")

    except RuntimeError as e:

        if str(e) != "Intentional rollback test":
            raise

        print("Expected error generated:", e)

    # Verify rollback
    with engine.connect() as connection:

        result = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM dim_product_scd_test
                WHERE product_code = 'TEST_SCD_001'
                  AND is_current = 1
            """)
        ).scalar()

        if result == 1:
            print("ROLLBACK SUCCESSFUL!")
            print("Original database state restored.")
        else:
            raise RuntimeError("ROLLBACK VALIDATION FAILED!")


if __name__ == "__main__":

    try:
        process_scd_type2()
        test_transaction_rollback()

    except Exception as e:
        print("\nSCD TEST FAILED!")
        print("Error:", e)

    finally:
        engine.dispose()