from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.api import upload
from app.ingestion.loader import DataLoader
from app.ingestion.pipeline import IngestionPipeline


def _write_csv(path: Path, contents: str) -> Path:
    path.write_text(contents, encoding="utf-8")
    return path


def test_pipeline_maps_normalizes_and_quarantines_rows(tmp_path: Path):
    dataset = _write_csv(
        tmp_path / "transactions.csv",
        "Txn ID,Date,From Account,To Account,Amount,Currency,Channel,Crypto Flag\n"
        "tx-1,2026-01-02 03:04:05,A-1,B-1,100, usd ,upi,false\n"
        "tx-2,2026-01-02 03:04:05,A-2,B-2,-5,INR,neft,false\n",
    )

    result = IngestionPipeline().run(dataset)

    assert result["status"] == "COMPLETED"
    assert result["clean_df"]["transaction_id"].to_list() == ["tx-1"]
    assert result["clean_df"]["currency"].to_list() == ["USD"]
    assert result["clean_df"]["channel"].to_list() == ["UPI"]
    assert result["quarantined_df"]["transaction_id"].to_list() == ["tx-2"]
    assert result["stats"]["integrity_check"] is True


def test_pipeline_rejects_missing_required_columns(tmp_path: Path):
    dataset = _write_csv(
        tmp_path / "missing.csv",
        "name,description\nexample,not-a-transaction\n",
    )

    result = IngestionPipeline().run(dataset)

    assert result["status"] == "FAILED"
    assert result["reason"] == "MISSING_REQUIRED_COLUMNS"
    assert result["stats"]["missing_required_fields"] == [
        "transaction_id",
        "timestamp",
        "sender_account",
        "receiver_account",
        "amount",
    ]


def test_pipeline_keeps_results_in_memory_by_default(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    dataset = _write_csv(
        tmp_path / "transactions.csv",
        "transaction_id,timestamp,sender_account,receiver_account,amount\n"
        "tx-1,2026-01-02 03:04:05,A-1,B-1,100\n",
    )

    result = IngestionPipeline().run(dataset)

    assert result["status"] == "COMPLETED"
    assert result["output_files"] == {}
    assert not (tmp_path / "output").exists()


def test_loader_does_not_decrypt_a_plain_workbook(tmp_path: Path):
    dataset = tmp_path / "plain.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["transaction_id", "amount"])
    sheet.append(["tx-1", 100])
    workbook.save(dataset)

    frame, metadata = DataLoader(dataset, password="configured-but-not-needed").load()

    assert frame["transaction_id"].to_list() == ["tx-1"]
    assert metadata["is_encrypted"] is False


def test_pipeline_holds_an_encrypted_workbook_without_a_password(monkeypatch):
    monkeypatch.delenv("VIGILANCE_DATASET_PASSWORD", raising=False)
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    dataset = Path(__file__).parents[2] / "Project_Vigilance_Dataset_Password_Protected.xlsx"

    result = IngestionPipeline().run(dataset)

    assert result["status"] == "HOLD"
    assert result["reason"] == "ENCRYPTED_FILE_MISSING_PASSWORD"


def test_upload_preparation_uses_the_shared_ingestion_pipeline():
    contents = (
        "Txn ID,Date,From Account,To Account,Amount,Country,City,Crypto Flag\n"
        "tx-1,2026-01-02 03:04:05,A-1,B-1,100, india ,bengaluru,false\n"
    ).encode()

    records, report = upload.prepare_upload_records(contents, "transactions.csv")

    assert records == [
        {
            "transaction_id": "tx-1",
            "timestamp": datetime(2026, 1, 2, 3, 4, 5),
            "sender_account": "A-1",
            "receiver_account": "B-1",
            "amount": 100.0,
            "country": "India",
            "city": "Bengaluru",
            "crypto_flag": False,
        }
    ]
    assert report["rows_received"] == 1
    assert report["rows_quarantined"] == 0


@pytest.mark.dataset
def test_pipeline_loads_the_complete_encrypted_workbook():
    password = os.getenv("VIGILANCE_DATASET_PASSWORD")
    if not password:
        pytest.skip("Set VIGILANCE_DATASET_PASSWORD to run the encrypted dataset test")

    dataset = Path(__file__).parents[2] / "Project_Vigilance_Dataset_Password_Protected.xlsx"

    result = IngestionPipeline(default_password=password).run(dataset)

    assert result["status"] == "COMPLETED", result["stats"]
    assert result["stats"]["total_input_rows"] == 249_994
    assert result["stats"]["integrity_check"] is True
    assert result["stats"]["load"]["is_encrypted"] is True
    assert {
        "transaction_id",
        "timestamp",
        "sender_account",
        "receiver_account",
        "amount",
    } <= set(result["clean_df"].columns)
