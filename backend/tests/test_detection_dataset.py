from __future__ import annotations

import io
import os
from pathlib import Path

import pandas as pd
import pytest


@pytest.mark.dataset
def test_every_detector_runs_on_the_complete_excel_dataset():
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
    frame = pd.read_excel(decrypted)

    from backend.app.detection.registry import PATTERN_FUNCTIONS, run_all_detections

    assert len(frame) == 249_994
    results = run_all_detections(frame)
    known_ids = set(frame["transaction_id"].dropna().astype(str))

    assert results
    assert {pattern for _, pattern, _ in results} <= set(PATTERN_FUNCTIONS)
    assert {"structuring", "layering", "circular_flow", "mule_behavior"} <= {
        pattern for _, pattern, _ in results
    }
    assert all(set(evidence["transaction_ids"]) <= known_ids for _, _, evidence in results)
