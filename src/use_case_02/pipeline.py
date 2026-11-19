from extract import extract_data
from transform import transform_data
from load_dimensions import load_dimensions
from scd_type2 import process_scd_type2
from load_fact import load_fact


def run_pipeline():

    print("=" * 60)
    print("USE CASE 02: COMPLETE STAR SCHEMA ETL PIPELINE")
    print("=" * 60)

    # STEP 1: EXTRACT
    print("\nSTEP 1: EXTRACTING SOURCE DATA")

    df = extract_data()

    if df is None or df.empty:
        raise ValueError("Source extraction failed.")

    print("Source Records:", len(df))

    # STEP 2: TRANSFORM
    print("\nSTEP 2: TRANSFORMING DATA")

    dim_product, dim_customer, dim_date, dim_region = (
        transform_data(df)
    )

    # STEP 3: LOAD DIMENSIONS
    print("\nSTEP 3: LOADING DIMENSIONS")

    load_dimensions(
        dim_product,
        dim_customer,
        dim_date,
        dim_region
    )

    # STEP 4: SCD TYPE 2
    print("\nSTEP 4: PROCESSING SCD TYPE 2")

    process_scd_type2()

    # STEP 5: LOAD FACT
    print("\nSTEP 5: LOADING FACT TABLE")

    load_fact(df)

    print("\n" + "=" * 60)
    print("COMPLETE ETL PIPELINE FINISHED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_pipeline()