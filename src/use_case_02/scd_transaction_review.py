
import pandas as pd

FILE_PATH = "data/raw/Online Retail.xlsx"
TARGET_CODES = ["21818"]
print("\nREADING SOURCE DATA...")

df = pd.read_excel(FILE_PATH)

df["StockCode"] = df["StockCode"].astype(str).str.strip()
df["Description"] = df["Description"].fillna("").str.strip()
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])

for code in TARGET_CODES:

    print("\n" + "=" * 80)
    print(f"TRANSACTION HISTORY: {code}")
    print("=" * 80)

    product = df[df["StockCode"] == code].copy()

    product = product.sort_values("InvoiceDate")

    print("\nTotal Records:", len(product))

    print("\nDESCRIPTION SUMMARY:")

    summary = (
        product.groupby("Description")
        .agg(
            record_count=("InvoiceDate", "count"),
            first_seen=("InvoiceDate", "min"),
            last_seen=("InvoiceDate", "max")
        )
        .reset_index()
        .sort_values("first_seen")
    )

    print(summary.to_string(index=False))

    print("\nDESCRIPTION TRANSITIONS:")

    product["previous_description"] = (
        product["Description"].shift(1)
    )

    transitions = product[
        product["Description"] != product["previous_description"]
    ][
        ["InvoiceDate", "Description", "previous_description"]
    ]

    print(transitions.to_string(index=False))

    print("\n")

print("\nTRANSACTION REVIEW COMPLETED")
