"""Check the graph layer against real rows from the encrypted workbook."""

import io
import os
from pathlib import Path

import pandas as pd
import polars as pl
import pytest

from app.graph.builder import graph_manager
from app.ingestion.cleaner import RecordCleaner
from app.ingestion.mapper import ColumnMapper
from app.ingestion.normalizer import DataNormalizer
from app.ingestion.validator import DataValidator


@pytest.mark.dataset
def test_graph_builds_from_real_workbook_rows():
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
    graph_manager.clear_graph()
    graph = graph_manager.build_graph_from_dataframe(frame)

    transaction_edges = [
        data
        for _, _, data in graph.edges(data=True)
        if data.get("relation") == "SENDS_TO"
    ]
    assert len(transaction_edges) == frame["transaction_id"].nunique()
    assert all(edge["transaction_id"] for edge in transaction_edges)
    assert any(data.get("node_type") == "Account" for _, data in graph.nodes(data=True))
