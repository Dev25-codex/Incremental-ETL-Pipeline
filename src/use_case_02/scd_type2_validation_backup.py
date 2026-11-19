from sqlalchemy import text
from database import engine


PRODUCT_CODE = "21818"

EXPECTED_OLD_NAME = "GLITTER CHRISTMAS HEART"
EXPECTED_NEW_NAME = "GLITTER HEART DECORATION"


def validate_scd_type2():

    print("=" * 50)
    print("SCD TYPE 2 VALIDATION")
    print("=" * 50)

    try:

        with engine.connect() as connection:

            query = text("""
                SELECT
                    product_key,
                    product_code,
                    product_name,
                    effective_from,
                    effective_to,
                    is_current
                FROM dim_product
                WHERE product_code = :product_code
                ORDER BY effective_from
            """)

            result = connection.execute(
                query,
                {"product_code": PRODUCT_CODE}
            )

            versions = result.mappings().all()

            print("\nExisting Product Versions:\n")

            for version in versions:
                print(dict(version))

            names = [
                version["product_name"].strip()
                for version in versions
            ]

            old_exists = EXPECTED_OLD_NAME in names
            new_exists = EXPECTED_NEW_NAME in names

            if old_exists and new_exists:

                print("\nSCD Type 2 change already processed!")
                print("No duplicate insertion required.")

            else:

                print("\nSCD Type 2 validation requires review.")

                if not old_exists:
                    print("Old product version not found.")

                if not new_exists:
                    print("New product version not found.")

        print("\nSCD TYPE 2 VALIDATION COMPLETED!")

    except Exception as e:

        print("\nVALIDATION FAILED!")
        print("Error:", e)

    finally:
        engine.dispose()


if __name__ == "__main__":
    validate_scd_type2()