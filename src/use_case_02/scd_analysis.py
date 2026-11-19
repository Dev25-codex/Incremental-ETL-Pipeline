import os
import pandas as pd

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

FILE_PATH = "data/raw/Online Retail.xlsx"
OUTPUT_DIR = "reports"

MIN_RECORDS = 5

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --------------------------------------------------
# STEP 1: EXTRACT DATA
# --------------------------------------------------

print("\nREADING SOURCE DATA...")

df = pd.read_excel(FILE_PATH)

df["StockCode"] = df["StockCode"].astype(str).str.strip()
df["Description"] = df["Description"].fillna("").str.strip()
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])

print("Total Source Records:", len(df))


# --------------------------------------------------
# STEP 2: HANDLE MISSING DESCRIPTIONS
# --------------------------------------------------

missing_report = (
    df.groupby("StockCode")
    .agg(
        total_records=("InvoiceNo", "count"),
        missing_descriptions=(
            "Description",
            lambda x: (x == "").sum()
        )
    )
    .reset_index()
)


# --------------------------------------------------
# STEP 3: IDENTIFY QUALIFYING DESCRIPTIONS
# --------------------------------------------------

valid_df = df[df["Description"] != ""].copy()

description_counts = (
    valid_df.groupby(["StockCode", "Description"])
    .size()
    .reset_index(name="total_records")
)

qualifying = description_counts[
    description_counts["total_records"] >= MIN_RECORDS
].copy()

# Products having multiple qualifying descriptions
product_counts = (
    qualifying.groupby("StockCode")["Description"]
    .nunique()
)

target_codes = product_counts[
    product_counts >= 2
].index.tolist()

qualifying = qualifying[
    qualifying["StockCode"].isin(target_codes)
]

print("\nPRODUCTS WITH MULTIPLE QUALIFYING DESCRIPTIONS:",
      len(target_codes))

print("TOTAL QUALIFYING DESCRIPTION VERSIONS:",
      len(qualifying))


# --------------------------------------------------
# STEP 4: DESCRIPTION VERSION REPORT
# --------------------------------------------------

version_report = valid_df[
    valid_df["StockCode"].isin(target_codes)
].groupby(["StockCode", "Description"]).agg(
    first_seen=("InvoiceDate", "min"),
    last_seen=("InvoiceDate", "max"),
    total_records=("InvoiceNo", "count")
).reset_index()

version_report = version_report.merge(
    qualifying[["StockCode", "Description"]],
    on=["StockCode", "Description"],
    how="inner"
)

version_report.to_csv(
    os.path.join(OUTPUT_DIR, "scd_description_versions.csv"),
    index=False
)


# --------------------------------------------------
# STEP 5: TRANSACTION-LEVEL TRANSITION ANALYSIS
# --------------------------------------------------

transition_reports = []
product_reports = []

for code in target_codes:

    product = valid_df[
        valid_df["StockCode"] == code
    ].copy()

    product = product.sort_values(
        ["InvoiceDate", "InvoiceNo"]
    )

    # Only descriptions with at least MIN_RECORDS
    product = product[
        product["Description"].isin(
            qualifying.loc[
                qualifying["StockCode"] == code,
                "Description"
            ]
        )
    ].copy()

    product["previous_description"] = (
        product["Description"].shift(1)
    )

    transitions = product[
        product["Description"] !=
        product["previous_description"]
    ].copy()

    transitions = transitions[
        transitions["previous_description"].notna()
    ]

    transitions["StockCode"] = code

    for _, row in transitions.iterrows():
        transition_reports.append({
            "StockCode": code,
            "InvoiceNo": row["InvoiceNo"],
            "InvoiceDate": row["InvoiceDate"],
            "previous_description": row["previous_description"],
            "new_description": row["Description"]
        })

    switch_count = len(transitions)

    descriptions = product["Description"].nunique()

    if switch_count == 1:
        pattern = "ONE_WAY_CHANGE"
    elif switch_count > 1:
        pattern = "REPEATED_SWITCHING"
    else:
        pattern = "NO_SWITCH"

    product_reports.append({
        "StockCode": code,
        "total_records": len(product),
        "description_versions": descriptions,
        "description_switches": switch_count,
        "switching_pattern": pattern
    })


# --------------------------------------------------
# STEP 6: PRODUCT SUMMARY REPORT
# --------------------------------------------------

product_report = pd.DataFrame(product_reports)

product_report = product_report.merge(
    missing_report,
    on="StockCode",
    how="left"
)

product_report.to_csv(
    os.path.join(OUTPUT_DIR, "scd_product_summary.csv"),
    index=False
)


# --------------------------------------------------
# STEP 7: TRANSITION REPORT
# --------------------------------------------------

transition_report = pd.DataFrame(transition_reports)

transition_report.to_csv(
    os.path.join(OUTPUT_DIR, "scd_transition_events.csv"),
    index=False
)


# --------------------------------------------------
# STEP 8: FINAL SUMMARY
# --------------------------------------------------

print("\n" + "=" * 60)
print("SCD TYPE 2 ANALYSIS COMPLETED")
print("=" * 60)

print("\nTotal Products Analysed:", len(product_report))

print(
    "\nSwitching Pattern Summary:"
)

print(
    product_report["switching_pattern"].value_counts()
)

print("\nTotal Description Switches:", 
      product_report["description_switches"].sum())

print("\nMissing Descriptions:",
      product_report["missing_descriptions"].sum())

print("\nREPORTS GENERATED:")

print("1. reports/scd_product_summary.csv")
print("2. reports/scd_description_versions.csv")
print("3. reports/scd_transition_events.csv")

print("\n" + "=" * 60)