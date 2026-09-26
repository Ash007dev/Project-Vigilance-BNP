"""Run the integrated risk pipeline on genuine cleaned workbook rows."""

import io
import os
from pathlib import Path

import pandas as pd
import polars as pl
import pytest

from app.detection.engine import AMLDetectionEngine
from app.ingestion.cleaner import RecordCleaner
from app.ingestion.mapper import ColumnMapper
from app.ingestion.normalizer import DataNormalizer
from app.ingestion.validator import DataValidator
from app.risk.engine import RiskEngine


@pytest.mark.dataset
def test_risk_pipeline_runs_on_real_workbook_rows():
    password = os.getenv("VIGILANCE_DATASET_PASSWORD")
    if not password:
        pytest.skip("Set VIGILANCE_DATASET_PASSWORD to run the encrypted dataset test")

    msoffcrypto = pytest.importorskip("msoffcrypto")
    dataset = Path(__file__).parents[2] / "Project_Vigilance_Dataset_Password_Protected.xlsx"
    decrypted = io.BytesIO()
    with dataset.open("rb") as encrypted:
        workbook = msoffcrypto.OfficeFile(encrypted)
        workbook.load_key(password=password)
        workbook.decrypt(decrypted)

    decrypted.seek(0)
    raw_frame = pd.read_excel(decrypted, nrows=1_000)
    mapped, _ = ColumnMapper().map_schema(pl.from_pandas(raw_frame))
    normalized, _ = DataNormalizer().normalize(mapped)
    validated, _ = DataValidator().validate(normalized)
    clean_frame, _, _ = RecordCleaner().process(
        validated.drop("_validation_issues", strict=False)
    )
    frame = clean_frame.to_pandas()

    detection_engine = AMLDetectionEngine(frame)
    scores = RiskEngine(detection_engine.run_all(), frame=frame).calculate()

    known_accounts = set(frame["sender_account"].dropna().astype(str)) | set(
        frame["receiver_account"].dropna().astype(str)
    )
    assert scores
    assert {item["account"] for item in scores} <= known_accounts
    assert all(0 <= item["risk_score"] <= 100 for item in scores)
    assert all(item["graph_metrics"] for item in scores)
    assert any(item["ml_anomaly_score"] is not None for item in scores)
