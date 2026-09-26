"""Run the complete data-ingestion flow.

What: Loads, maps, normalizes, validates, and cleans transaction files.
How: Each ingestion step receives the result of the previous step.
Result: Returns clean and quarantined rows in memory, plus a clear report.
Example: ``IngestionPipeline().run("transactions.csv")``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import polars as pl

from app.ingestion.cleaner import RecordCleaner
from app.ingestion.loader import DataLoader, EncryptedWorkbookPasswordRequired
from app.ingestion.mapper import ColumnMapper
from app.ingestion.normalizer import DataNormalizer
from app.ingestion.validator import DataValidator

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Connect every ingestion step and return one result dictionary."""

    def __init__(
        self,
        default_password: str | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        self.password = (
            default_password
            or os.getenv("VIGILANCE_DATASET_PASSWORD")
            or os.getenv("ENCRYPTION_KEY")
            or None
        )
        self.output_dir = Path(output_dir) if output_dir is not None else None
        self.mapper = ColumnMapper()
        self.normalizer = DataNormalizer()
        self.validator = DataValidator()
        self.cleaner = RecordCleaner()

    @staticmethod
    def _failure(reason: str, stats: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "status": "FAILED",
            "reason": reason,
            "clean_df": None,
            "quarantined_df": None,
            "stats": stats or {},
            "output_files": {},
        }

    def run(self, file_path: str | Path) -> dict[str, Any]:
        """Run ingestion and keep results in memory unless an output folder is set."""
        try:
            raw_df, load_report = DataLoader(file_path, password=self.password).load()
        except FileNotFoundError:
            return self._failure("FILE_NOT_FOUND")
        except EncryptedWorkbookPasswordRequired:
            result = self._failure("ENCRYPTED_FILE_MISSING_PASSWORD")
            result["status"] = "HOLD"
            return result
        except ValueError as exc:
            return self._failure("UNSUPPORTED_FILE", {"error": str(exc)})
        except ImportError as exc:
            return self._failure("MISSING_DEPENDENCY", {"error": str(exc)})
        except Exception as exc:
            logger.exception("Could not load the ingestion file")
            return self._failure("UNREADABLE_FILE", {"error": str(exc)})

        mapped_df, mapping_report = self.mapper.map_schema(raw_df)
        missing_required = mapping_report["missing_required_fields"]
        if missing_required:
            return self._failure(
                "MISSING_REQUIRED_COLUMNS",
                {
                    "load": load_report,
                    "mapping": mapping_report,
                    "missing_required_fields": missing_required,
                },
            )

        normalized_df, normalization_report = self.normalizer.normalize(mapped_df)
        validated_df, validation_report = self.validator.validate(normalized_df)
        validated_df = validated_df.drop("_validation_issues", strict=False)
        clean_df, quarantined_df, cleaning_report = self.cleaner.process(validated_df)

        stats = {
            **cleaning_report,
            "load": load_report,
            "mapping": mapping_report,
            "normalization": normalization_report,
            "validation": validation_report,
            "missing_required_fields": [],
        }
        output_files = self._save_outputs(clean_df, quarantined_df)

        return {
            "status": "COMPLETED",
            "reason": None,
            "clean_df": clean_df,
            "quarantined_df": quarantined_df,
            "stats": stats,
            "output_files": output_files,
        }

    def _save_outputs(
        self,
        clean_df: pl.DataFrame,
        quarantined_df: pl.DataFrame,
    ) -> dict[str, str]:
        if self.output_dir is None:
            return {}

        self.output_dir.mkdir(parents=True, exist_ok=True)
        clean_path = self.output_dir / "cleaned_dataset.csv"
        quarantine_path = self.output_dir / "quarantined_dataset.csv"
        clean_df.write_csv(clean_path)
        quarantined_df.write_csv(quarantine_path)
        return {
            "clean_csv": str(clean_path),
            "quarantine_csv": str(quarantine_path),
        }
