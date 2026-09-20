"""
database/load_data.py
=====================
Reads each CSV file with pandas, cleans null values and data types, creates
all tables in PostgreSQL via SQLAlchemy, and bulk-inserts the data in the
correct foreign-key-safe order.
"""

import os
import sys
import pandas as pd
from sqlalchemy import text

from config import DATA_DIR, CSV_FILES
from database.connection import get_engine
from database.models import Base


# ---------------------------------------------------------------------------
# Mapping: CSV filename -> (target SQL table name, columns to parse as dates)
# ---------------------------------------------------------------------------
CSV_TABLE_MAP: dict[str, dict] = {
    "olist_geolocation_dataset.csv": {
        "table": "geolocation",
        "date_cols": [],
    },
    "olist_customers_dataset.csv": {
        "table": "customers",
        "date_cols": [],
    },
    "olist_sellers_dataset.csv": {
        "table": "sellers",
        "date_cols": [],
    },
    "product_category_name_translation.csv": {
        "table": "product_category_translation",
        "date_cols": [],
    },
    "olist_products_dataset.csv": {
        "table": "products",
        "date_cols": [],
    },
    "olist_orders_dataset.csv": {
        "table": "orders",
        "date_cols": [
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    },
    "olist_order_items_dataset.csv": {
        "table": "order_items",
        "date_cols": ["shipping_limit_date"],
    },
    "olist_order_payments_dataset.csv": {
        "table": "order_payments",
        "date_cols": [],
    },
    "olist_order_reviews_dataset.csv": {
        "table": "order_reviews",
        "date_cols": ["review_creation_date", "review_answer_timestamp"],
        "dedup_cols": ["review_id"],
    },
}


def _clean_dataframe(df: pd.DataFrame, date_cols: list[str]) -> pd.DataFrame:
    """
    Apply defensive cleaning to a raw DataFrame before insertion:
      - Strip whitespace from string columns
      - Parse date columns with coercion (invalid -> NaT)
      - Replace pandas NA / NaN with None (SQL-compatible NULL)
    """
    # Strip whitespace from all string columns
    str_cols = df.select_dtypes(include=["object"]).columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip()
        # Convert literal 'nan' strings (from astype) back to None
        df[col] = df[col].replace("nan", None)

    # Parse date columns safely
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Replace all remaining NaN / NA with None for clean SQL NULLs
    df = df.where(df.notna(), None)

    return df


def load_all_data() -> None:
    """
    Master ingestion function:
      1. Creates all tables defined in models.py (if they don't exist).
      2. Iterates through CSV_FILES in FK-safe order.
      3. Reads, cleans, and bulk-inserts each CSV into its target table.
    """
    engine = get_engine()

    # ----- Step 1: Create tables -----
    print("[Phase 1] Creating database tables...")
    Base.metadata.create_all(engine)
    print("         [OK] All tables created (or already exist).\n")

    # ----- Step 2: Load each CSV -----
    for csv_file in CSV_FILES:
        meta = CSV_TABLE_MAP.get(csv_file)
        if meta is None:
            print(f"  [!] No mapping found for {csv_file}, skipping.")
            continue

        table_name = meta["table"]
        date_cols = meta["date_cols"]
        csv_path = os.path.join(DATA_DIR, csv_file)

        # Check if file exists
        if not os.path.isfile(csv_path):
            print(f"  [X] File not found: {csv_path}")
            continue

        # Skip if table already has data (idempotent re-runs)
        with engine.connect() as conn:
            row_count = conn.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")
            ).scalar()
            if row_count and row_count > 0:
                print(
                    f"  [>>] {table_name:40s} already loaded "
                    f"({row_count:,} rows). Skipping."
                )
                continue

        # Read CSV (handle BOM with utf-8-sig encoding)
        print(f"  [..] Loading {csv_file} -> {table_name}...", end=" ", flush=True)
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        df = _clean_dataframe(df, date_cols)

        # Deduplicate if this table has known duplicate primary keys
        dedup_cols = meta.get("dedup_cols")
        if dedup_cols:
            before = len(df)
            df = df.drop_duplicates(subset=dedup_cols, keep="first")
            dropped = before - len(df)
            if dropped > 0:
                print(f"(deduped {dropped} rows) ", end="", flush=True)

        # For geolocation: drop the surrogate 'id' column we defined in ORM
        # -- pandas will let the DB auto-increment it.
        # No extra handling needed; to_sql with method='multi' is fine.

        # Bulk insert using pandas -> SQLAlchemy integration
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists="append",       # Tables already created by ORM
            index=False,              # Don't write DataFrame index
            method="multi",           # Batch INSERT for speed
            chunksize=5000,           # Rows per INSERT statement
        )
        print(f"[OK] {len(df):,} rows inserted.")

    print("\n[Phase 1] [DONE] Data ingestion complete.")


# ---------------------------------------------------------------------------
# Allow running as a standalone script: python -m database.load_data
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    load_all_data()
