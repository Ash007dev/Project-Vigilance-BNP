import time
from io import BytesIO

import polars as pl
from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import insert

from app.db.database import engine
from app.db.models import Transaction

from sqlalchemy import insert, text

router = APIRouter()


REQUIRED_COLUMNS = {
    "transaction_id",
    "timestamp",
    "sender_account",
    "receiver_account",
    "amount",
}


@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    start_time = time.perf_counter()

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided",
        )

    filename = file.filename.lower()

    if not filename.endswith((".csv", ".xlsx")):
        raise HTTPException(
            status_code=400,
            detail="Only CSV and XLSX files are supported",
        )

    try:
        contents = await file.read()

        # -----------------------------
        # Load dataset
        # -----------------------------
        if filename.endswith(".csv"):
            df = pl.read_csv(
                BytesIO(contents),
                try_parse_dates=True,
            )
        else:
            df = pl.read_excel(
                BytesIO(contents),
            )

        # -----------------------------
        # Validate columns
        # -----------------------------
        columns = set(df.columns)

        missing_columns = REQUIRED_COLUMNS - columns

        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Required columns are missing",
                    "missing_columns": sorted(missing_columns),
                    "received_columns": df.columns,
                },
            )

        # -----------------------------
        # Normalize optional columns
        # -----------------------------
        optional_columns = [
            "sender_customer",
            "receiver_customer",
            "currency",
            "channel",
            "ip_address",
            "device_id",
            "country",
            "city",
            "crypto_flag",
            "crypto_wallet",
        ]

        for column in optional_columns:
            if column not in df.columns:
                df = df.with_columns(
                    pl.lit(None).alias(column)
                )

        # -----------------------------
        # Normalize data types
        # -----------------------------

        df = df.with_columns(
            pl.col("transaction_id").cast(pl.String),
            pl.col("sender_account").cast(pl.String),
            pl.col("receiver_account").cast(pl.String),
            pl.col("amount").cast(pl.Float64),
        )

        # Timestamp may already be parsed by Polars.
        # Only parse it when it is still a string.
        if df.schema["timestamp"] == pl.String:
            df = df.with_columns(
                pl.col("timestamp").str.to_datetime(
                    strict=False
                )
            )
        else:
            df = df.with_columns(
                pl.col("timestamp").cast(
                    pl.Datetime("us")
                )
            )

        # -----------------------------
        # Remove invalid required rows
        # -----------------------------
        df = df.filter(
            pl.col("transaction_id").is_not_null()
            & pl.col("timestamp").is_not_null()
            & pl.col("sender_account").is_not_null()
            & pl.col("receiver_account").is_not_null()
            & pl.col("amount").is_not_null()
        )

        if df.height == 0:
            raise HTTPException(
                status_code=400,
                detail="No valid transactions found",
            )

        duplicate_count = (
            df
            .select(
                pl.col("transaction_id").is_duplicated().sum()
            )
            .item()
        )
        # -----------------------------
        # Convert to database records
        # -----------------------------
        records = df.to_dicts()

        # Keep only our database columns
        db_columns = {
            "transaction_id",
            "timestamp",
            "sender_account",
            "receiver_account",
            "sender_customer",
            "receiver_customer",
            "amount",
            "currency",
            "channel",
            "ip_address",
            "device_id",
            "country",
            "city",
            "crypto_flag",
            "crypto_wallet",
        }

        records = [
            {
                key: value
                for key, value in record.items()
                if key in db_columns
            }
            for record in records
        ]

        # -----------------------------
        # Bulk insert
        # -----------------------------
        with engine.begin() as connection:
            # Replace the currently loaded dataset
            connection.execute(
                text("TRUNCATE TABLE transactions RESTART IDENTITY")
            )

            connection.execute(
                insert(Transaction),
                records,
            )

        elapsed = round(
            time.perf_counter() - start_time,
            3,
        )

        return {
            "status": "success",
            "filename": file.filename,
            "rows_processed": df.height,
            "rows_inserted": len(records),
            "columns": df.columns,
            "processing_time_seconds": elapsed,
            "duplicate_transaction_ids": duplicate_count,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Dataset ingestion failed: {str(exc)}",
        )