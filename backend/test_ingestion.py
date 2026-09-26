import polars as pl

from app.ingestion.loader import load_dataset

from app.ingestion.validator import (
    validate_dataset,
    print_validation_report,
)

from app.ingestion.cleaner import (
    normalize_dataset,
)


# ============================================================
# DATASET CONFIGURATION
# ============================================================

FILE_PATH = (
    "Dataset/"
    "Project_Vigilance_Dataset_Password_Protected.xlsx"
)

PASSWORD = r"5kZa7cY=6SC&gw1GP0Qn6A%(g]O}CA\-"


# ============================================================
# 1. LOAD DATASET
# ============================================================

print("\nLoading dataset...")

df = load_dataset(
    file_path=FILE_PATH,
    password=PASSWORD,
)

print("\nDataset loaded successfully.")

print(
    f"Rows: {df.height:,}"
)

print(
    f"Columns: {df.width}"
)


# ============================================================
# 2. SHOW COLUMNS
# ============================================================

print("\n--- COLUMNS ---")

for column in df.columns:
    print(f"- {column}")


# ============================================================
# 3. SHOW SCHEMA
# ============================================================

print("\n--- SCHEMA ---")

for column, dtype in df.schema.items():
    print(
        f"{column}: {dtype}"
    )


# ============================================================
# 4. VALIDATION
# ============================================================

print("\nRunning validation...")

report = validate_dataset(df)

print_validation_report(report)


# ============================================================
# 5. PROFILE ACTUAL DATA
# ============================================================

print("\n--- UNIQUE CURRENCY VALUES ---")

print(
    df["currency"].value_counts()
)


print("\n--- UNIQUE CHANNEL VALUES ---")

print(
    df["channel"].value_counts()
)


print("\n--- UNIQUE COUNTRY VALUES ---")

print(
    df["location_country"].value_counts()
)


print("\n--- UNIQUE CRYPTO VALUES ---")

print(
    df["is_crypto"].value_counts()
)


print("\n--- TIMESTAMP SAMPLE ---")

print(
    df["timestamp"].head(20)
)


print("\n--- AMOUNT SAMPLE ---")

print(
    df["amount"].head(20)
)


# ============================================================
# 6. DUPLICATE TRANSACTION ID PROFILE
# ============================================================

print(
    "\n--- DUPLICATE TRANSACTION IDs ---"
)

duplicate_ids = (
    df
    .group_by("transaction_id")
    .agg(
        pl.len().alias("count")
    )
    .filter(
        pl.col("count") > 1
    )
)

print(
    duplicate_ids.head(20)
)


# ============================================================
# 7. NORMALIZATION
# ============================================================

print(
    "\nRunning normalization..."
)

normalized_df = normalize_dataset(df)
normalized_df.write_csv("Dataset/normalized_dataset.csv")

# ============================================================
# 8. NORMALIZATION RESULTS
# ============================================================

print(
    "\n--- NORMALIZATION COMPLETE ---"
)

print(
    f"Rows before: "
    f"{df.height:,}"
)

print(
    f"Rows after:  "
    f"{normalized_df.height:,}"
)


print(
    "\n--- NORMALIZED SCHEMA ---"
)

for column, dtype in normalized_df.schema.items():

    print(
        f"{column}: {dtype}"
    )


print(
    "\n--- NORMALIZED CURRENCY ---"
)

print(
    normalized_df["currency"]
    .value_counts()
)


print(
    "\n--- NORMALIZED CHANNEL ---"
)

print(
    normalized_df["channel"]
    .value_counts()
)


print(
    "\n--- NORMALIZED COUNTRY ---"
)

print(
    normalized_df["location_country"]
    .value_counts()
)


print(
    "\n--- NORMALIZED TIMESTAMP ---"
)

print(
    normalized_df["timestamp"]
    .head(5)
)


print(
    "\n--- NORMALIZED DATA SAMPLE ---"
)

print(
    normalized_df.head(5)
)