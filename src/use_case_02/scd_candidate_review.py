import os
import pandas as pd
from difflib import SequenceMatcher

# -----------------------------------------
# CONFIGURATION
# -----------------------------------------

FILE_PATH = "data/raw/Online Retail.xlsx"
OUTPUT_DIR = "reports"

MIN_RECORDS = 5

os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------------------
# STEP 1: EXTRACT DATA
# -----------------------------------------

print("\nEXTRACTING SOURCE DATA...")

df = pd.read_excel(FILE_PATH)

df["StockCode"] = df["StockCode"].astype(str).str.strip()
df["Description"] = df["Description"].fillna("").str.strip()
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])

print("Total Records:", len(df))


# -----------------------------------------
# STEP 2: IDENTIFY QUALIFYING DESCRIPTIONS
# -----------------------------------------

valid_df = df[df["Description"] != ""].copy()

description_counts = (
    valid_df.groupby(["StockCode", "Description"])
    .size()
    .reset_index(name="record_count")
)

qualifying = description_counts[
    description_counts["record_count"] >= MIN_RECORDS
].copy()

product_counts = (
    qualifying.groupby("StockCode")["Description"]
    .nunique()
)

one_way_codes = product_counts[
    product_counts == 2
].index

# -----------------------------------------
# STEP 3: PRODUCT DESCRIPTION COMPARISON
# -----------------------------------------

results = []

for code in one_way_codes:

    product = valid_df[
        valid_df["StockCode"] == code
    ].copy()

    product = product[
        product["Description"].isin(
            qualifying.loc[
                qualifying["StockCode"] == code,
                "Description"
            ]
        )
    ]

    descriptions = (
        product.groupby("Description")
        .agg(
            first_seen=("InvoiceDate", "min"),
            last_seen=("InvoiceDate", "max"),
            record_count=("InvoiceDate", "count")
        )
        .reset_index()
        .sort_values("first_seen")
    )

    if len(descriptions) != 2:
        continue

    old = descriptions.iloc[0]
    new = descriptions.iloc[1]

    old_desc = old["Description"]
    new_desc = new["Description"]

    # Normalize text for comparison
    old_normalized = " ".join(old_desc.upper().split())
    new_normalized = " ".join(new_desc.upper().split())

    similarity = SequenceMatcher(
        None,
        old_normalized,
        new_normalized
    ).ratio()

    if old_normalized == new_normalized:
        classification = "FORMAT_CHANGE"
    elif similarity >= 0.85:
        classification = "POSSIBLE_TEXT_CORRECTION"
    else:
        classification = "NEEDS_MANUAL_REVIEW"

    results.append({
        "StockCode": code,
        "old_description": old_desc,
        "new_description": new_desc,
        "old_first_seen": old["first_seen"],
        "old_last_seen": old["last_seen"],
        "new_first_seen": new["first_seen"],
        "new_last_seen": new["last_seen"],
        "old_records": old["record_count"],
        "new_records": new["record_count"],
        "similarity_score": round(similarity, 3),
        "classification": classification
    })


# -----------------------------------------
# STEP 4: GENERATE REPORT
# -----------------------------------------

report = pd.DataFrame(results)

report = report.sort_values(
    by=["classification", "StockCode"]
)

output_file = os.path.join(
    OUTPUT_DIR,
    "scd_candidate_review.csv"
)

report.to_csv(output_file, index=False)


# -----------------------------------------
# STEP 5: SUMMARY
# -----------------------------------------

print("\n" + "=" * 60)
print("SCD CANDIDATE REVIEW COMPLETED")
print("=" * 60)

print("\nProducts Reviewed:", len(report))

print("\nClassification Summary:")

print(
    report["classification"].value_counts()
)

print("\nReport Generated:")
print(output_file)

print("\n" + "=" * 60)