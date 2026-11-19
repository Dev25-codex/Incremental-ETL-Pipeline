import pandas as pd


def transform_data(df):

    print("=" * 60)
    print("STARTING DATA TRANSFORMATION")
    print("=" * 60)

    # ==================================================
    # 1. PRODUCT DIMENSION
    # ==================================================

    print("\n1. Creating Product Dimension...")

    product_df = df[
        ["StockCode", "Description", "InvoiceDate"]
    ].copy()

    product_df = product_df.dropna(
        subset=["StockCode"]
    )

    product_df["InvoiceDate"] = pd.to_datetime(
        product_df["InvoiceDate"],
        errors="coerce"
    )

    product_df = product_df.dropna(
        subset=["InvoiceDate"]
    )

    product_df["StockCode"] = (
        product_df["StockCode"].astype(str).str.strip()
    )

    product_df = product_df.sort_values("InvoiceDate")

    # Earliest transaction for each product
    first_transaction = (
        product_df.groupby("StockCode", as_index=False)
        .first()
        [["StockCode", "InvoiceDate"]]
    )

    # First available non-null description
    named_products = product_df.dropna(
        subset=["Description"]
    )

    first_description = (
        named_products.groupby("StockCode", as_index=False)
        .first()
        [["StockCode", "Description"]]
    )

    dim_product = first_transaction.merge(
        first_description,
        on="StockCode",
        how="left"
    )

    dim_product = dim_product.rename(
        columns={
            "StockCode": "product_code",
            "Description": "product_name",
            "InvoiceDate": "effective_from"
        }
    )

    dim_product["effective_from"] = (
        dim_product["effective_from"].dt.date
    )

    print("Product Records:", len(dim_product))
    print(
        "Missing Product Names:",
        dim_product["product_name"].isna().sum()
    )

    print(
        "Missing Effective Dates:",
        dim_product["effective_from"].isna().sum()
    )

    # ==================================================
    # 2. CUSTOMER DIMENSION
    # ==================================================

    print("\n2. Creating Customer Dimension...")

    dim_customer = df[
        ["CustomerID"]
    ].drop_duplicates().copy()

    dim_customer = dim_customer.dropna(
        subset=["CustomerID"]
    )

    dim_customer = dim_customer.rename(
        columns={"CustomerID": "customer_id"}
    )

    dim_customer["customer_id"] = (
        dim_customer["customer_id"].astype(int)
    )

    print("Customer Records:", len(dim_customer))

    # ==================================================
    # 3. DATE DIMENSION
    # ==================================================

    print("\n3. Creating Date Dimension...")

    dates = pd.to_datetime(
        df["InvoiceDate"],
        errors="coerce"
    ).dropna()

    unique_dates = dates.dt.normalize().drop_duplicates()

    dim_date = pd.DataFrame({
        "full_date": unique_dates
    })

    dim_date["date_key"] = (
        dim_date["full_date"]
        .dt.strftime("%Y%m%d")
        .astype(int)
    )

    dim_date["day"] = dim_date["full_date"].dt.day
    dim_date["month"] = dim_date["full_date"].dt.month
    dim_date["quarter"] = dim_date["full_date"].dt.quarter
    dim_date["year"] = dim_date["full_date"].dt.year

    dim_date["full_date"] = dim_date["full_date"].dt.date

    print("Date Records:", len(dim_date))

    # ==================================================
    # 4. REGION DIMENSION
    # ==================================================

    print("\n4. Creating Region Dimension...")

    dim_region = df[
        ["Country"]
    ].drop_duplicates().copy()

    dim_region = dim_region.dropna(
        subset=["Country"]
    )

    dim_region = dim_region.rename(
        columns={"Country": "country"}
    )

    dim_region["country"] = (
        dim_region["country"].astype(str).str.strip()
    )

    dim_region = dim_region[
        dim_region["country"] != ""
    ].drop_duplicates(
        subset=["country"]
    )

    print("Region Records:", len(dim_region))

    # ==================================================
    # 5. CASE-INSENSITIVE PRODUCT ANALYSIS
    # ==================================================

    print("\n5. PRODUCT CASE-DUPLICATE ANALYSIS")
    print("-" * 60)

    dim_product["normalized_code"] = (
        dim_product["product_code"].str.lower()
    )

    case_duplicates = dim_product[
        dim_product.duplicated(
            subset=["normalized_code"],
            keep=False
        )
    ].sort_values("normalized_code")

    print(
        "Unique Product Codes:",
        dim_product["product_code"].nunique()
    )

    print(
        "Unique Codes After Lowercase:",
        dim_product["normalized_code"].nunique()
    )

    print(
        "Total Affected Records:",
        len(case_duplicates)
    )

    print(
        "Duplicate Groups:",
        case_duplicates["normalized_code"].nunique()
    )

    if not case_duplicates.empty:

        print("\nCase-insensitive Duplicate Product Codes:")

        print(
            case_duplicates[
                [
                    "product_code",
                    "product_name",
                    "normalized_code"
                ]
            ].to_string(index=False)
        )

    else:
        print("\nNo case-insensitive duplicate codes found.")

    dim_product = dim_product.drop(
        columns=["normalized_code"]
    )

    # ==================================================
    # 6. TRANSFORMATION SUMMARY
    # ==================================================

    print("\n" + "=" * 60)
    print("TRANSFORMATION SUMMARY")
    print("=" * 60)

    print("Product Dimension:", dim_product.shape)
    print("Customer Dimension:", dim_customer.shape)
    print("Date Dimension:", dim_date.shape)
    print("Region Dimension:", dim_region.shape)

    print("\nDATA TRANSFORMATION COMPLETED SUCCESSFULLY!")

    return (
        dim_product,
        dim_customer,
        dim_date,
        dim_region
    )


if __name__ == "__main__":

    print("\nTRANSFORM.PY DIRECT EXECUTION STARTED!")

    from extract import extract_data

    df = extract_data()

    if df is not None:
        transform_data(df)
    else:
        print("Transformation stopped: Data extraction failed.")
