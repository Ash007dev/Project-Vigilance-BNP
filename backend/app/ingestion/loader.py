"""Load transaction files.

What: Opens CSV, XLS, and XLSX files.
How: Decrypts encrypted Excel files in memory, then reads them with Polars.
Result: Returns a DataFrame and basic file details.
Example: ``DataLoader("transactions.xlsx", password="...").load()``.
"""

import io
from pathlib import Path
from typing import Any, Dict, Tuple
import polars as pl

try:
    import msoffcrypto
    HAS_MSOFFCRYPTO = True
except ImportError:
    HAS_MSOFFCRYPTO = False


class EncryptedWorkbookPasswordRequired(Exception):
    """Raised when an encrypted workbook has no password."""


class DataLoader:
    """Handles raw file ingestion for CSV and Excel formats."""

    SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

    def __init__(self, file_path: str | Path, password: str | None = None) -> None:
        self.file_path = Path(file_path)
        self.password = password
        self._validate_file_existence()

    def _validate_file_existence(self) -> None:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Source file not found: {self.file_path}")
        if self.file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file extension '{self.file_path.suffix}'. "
                f"Supported types: {self.SUPPORTED_EXTENSIONS}"
            )

    def load(self) -> Tuple[pl.DataFrame, Dict[str, Any]]:
        """Loads file into Polars DataFrame without performing data cleaning."""
        ext = self.file_path.suffix.lower()
        metadata: Dict[str, Any] = {
            "file_name": self.file_path.name,
            "file_size_bytes": self.file_path.stat().st_size,
            "extension": ext,
            "is_encrypted": False,
        }

        if ext == ".csv":
            df = pl.read_csv(self.file_path, infer_schema_length=10000, ignore_errors=False)
        else:
            df, is_encrypted = self._load_excel()
            metadata["is_encrypted"] = is_encrypted

        metadata["initial_row_count"] = df.height
        metadata["initial_column_count"] = df.width
        return df, metadata

    def _load_excel(self) -> Tuple[pl.DataFrame, bool]:
        is_encrypted = False
        file_source: Any = self.file_path

        if HAS_MSOFFCRYPTO:
            with open(self.file_path, "rb") as f:
                office_file = msoffcrypto.OfficeFile(f)
                is_encrypted = office_file.is_encrypted()
                if is_encrypted and not self.password:
                    raise EncryptedWorkbookPasswordRequired
                if is_encrypted:
                    decrypted_stream = io.BytesIO()
                    office_file.load_key(password=self.password)
                    office_file.decrypt(decrypted_stream)
                    decrypted_stream.seek(0)
                    file_source = decrypted_stream

        try:
            df = pl.read_excel(file_source, engine="calamine")
        except Exception:
            if isinstance(file_source, io.BytesIO):
                file_source.seek(0)
            df = pl.read_excel(file_source, engine="openpyxl")

        return df, is_encrypted


def load_dataset(file_path: str | Path, password: str | None = None) -> pl.DataFrame:
    """Helper function to load raw dataset."""
    loader = DataLoader(file_path, password=password)
    df, _ = loader.load()
    return df
