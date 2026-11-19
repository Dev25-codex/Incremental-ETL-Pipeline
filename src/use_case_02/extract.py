import pandas as pd
from pathlib import Path

# Project root directory
BASE_DIR = Path(__file__).resolve().parents[2]

# Original dataset path
FILE_PATH = BASE_DIR / "data" / "raw" / "Online Retail.xlsx"


def extract_data():

    print("Starting Data Extraction...")

    try:
        df = pd.read_excel(FILE_PATH)

        print("\nData Extraction Successful!")

        print("Total Records:", len(df))
        print("Dataset Shape:", df.shape)

        print("\nColumn Names:")
        print(df.columns.tolist())

        print("\nFirst 5 Records:")
        print(df.head())

        return df

    except Exception as e:
        print("Extraction Failed:", e)
        return None


if __name__ == "__main__":
    extract_data()