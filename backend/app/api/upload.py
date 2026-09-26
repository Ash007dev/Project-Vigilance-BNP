"""Accept a transaction file and store its clean rows.

What: Handles CSV and Excel uploads.
How: Runs the shared ingestion pipeline, then maps clean fields to the database.
Result: Invalid rows are quarantined and only clean transactions are inserted.
Example: Upload ``transactions.xlsx`` to ``POST /api/upload``.
"""

from __future__ import annotations

import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import insert, text
from starlette.concurrency import run_in_threadpool

from app.db.database import engine
from app.db.models import Transaction
from app.ingestion.pipeline import IngestionPipeline

router = APIRouter()

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
DATABASE_COLUMNS = (
    "transaction_id",
    "timestamp",
    "sender_account",
    "sender_name",
    "sender_customer_id",
    "receiver_account",
    "receiver_name",
    "receiver_customer_id",
    "amount",
    "currency",
    "channel",
    "ip_address",
    "device_id",
    "country",
    "city",
    "crypto_flag",
    "crypto_wallet",
)


class UploadPreparationError(ValueError):
    """Raised when an uploaded file cannot produce clean transactions."""


def prepare_upload_records(
    contents: bytes,
    filename: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Clean one upload and return database-ready records plus a report."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise UploadPreparationError("Only CSV, XLSX, and XLS files are supported")

    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
            temporary_file.write(contents)
            temporary_path = Path(temporary_file.name)

        result = IngestionPipeline().run(temporary_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    if result["status"] != "COMPLETED":
        raise UploadPreparationError(result["reason"])

    frame = result["clean_df"]
    if frame.height == 0:
        raise UploadPreparationError("No clean transactions found")

    rename_columns = {
        "location_country": "country",
        "location_city": "city",
        "is_crypto": "crypto_flag",
    }
    frame = frame.rename(
        {source: target for source, target in rename_columns.items() if source in frame.columns}
    )
    selected_columns = [column for column in DATABASE_COLUMNS if column in frame.columns]
    records = frame.select(selected_columns).to_dicts()

    stats = result["stats"]
    report = {
        "rows_received": stats["total_input_rows"],
        "rows_inserted": len(records),
        "rows_quarantined": stats["quarantined_records"],
        "duplicates_removed": stats["removed_duplicate_copies"],
        "flagged_rows": stats["keep_and_flag_rows"],
    }
    return records, report


@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """Ingest one uploaded dataset and replace the database transaction table."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    start_time = time.perf_counter()
    try:
        contents = await file.read()
        records, report = await run_in_threadpool(
            prepare_upload_records,
            contents,
            file.filename,
        )

        with engine.begin() as connection:
            connection.execute(text("TRUNCATE TABLE transactions RESTART IDENTITY"))
            connection.execute(insert(Transaction), records)
    except UploadPreparationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Dataset ingestion failed") from exc

    return {
        "status": "success",
        "filename": file.filename,
        **report,
        "processing_time_seconds": round(time.perf_counter() - start_time, 3),
    }
