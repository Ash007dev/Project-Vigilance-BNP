"""
Ingestion Pipeline Orchestrator (app/ingestion/pipeline.py)
Handles file detection, dynamic Excel/Zip decryption,
Polars data loading, record classification, and saving outputs to disk.
"""

import os
import io
import logging
import zipfile
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

import polars as pl

try:
    import msoffcrypto
except ImportError:
    msoffcrypto = None

from app.ingestion.cleaner import RecordCleaner

logging.basicConfig(level=logging.INFO, format="[+] %(message)s")
logger = logging.getLogger("IngestionPipeline")


class IngestionPipeline:
    def __init__(self, default_password: Optional[str] = None, output_dir: str = "output"):
        self.cleaner = RecordCleaner()
        self.password = default_password or os.getenv("ENCRYPTION_KEY", "")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def inspect_and_decrypt(self, file_path: str) -> Tuple[Optional[bytes], str]:
        ext = Path(file_path).suffix.lower()

        if ext in [".xlsx", ".xls"]:
            if msoffcrypto is None:
                with open(file_path, "rb") as f:
                    return f.read(), "UNENCRYPTED_FILE"

            try:
                with open(file_path, "rb") as f:
                    office_file = msoffcrypto.OfficeFile(f)
                    
                    if office_file.is_encrypted():
                        logger.warning(f"Encrypted Excel file detected: {file_path}")
                        if not self.password:
                            return None, "ENCRYPTED_FILE_MISSING_KEY"

                        decrypted_stream = io.BytesIO()
                        office_file.load_key(password=self.password)
                        office_file.decrypt(decrypted_stream)
                        decrypted_stream.seek(0)
                        return decrypted_stream.getvalue(), "DECRYPT_SUCCESS"
            except Exception as e:
                logger.error(f"Error checking or decrypting Excel file: {e}")
                return None, "DECRYPTION_FAILED_INVALID_KEY"

        elif ext == ".zip":
            try:
                with zipfile.ZipFile(file_path, "r") as zf:
                    is_encrypted = any(zinfo.flag_bits & 0x1 for zinfo in zf.infolist())

                    if is_encrypted:
                        logger.warning(f"Encrypted ZIP archive detected: {file_path}")
                        if not self.password:
                            return None, "ENCRYPTED_FILE_MISSING_KEY"

                    for filename in zf.namelist():
                        if filename.lower().endswith((".csv", ".xlsx", ".xls")):
                            pwd_bytes = self.password.encode("utf-8") if is_encrypted else None
                            content = zf.read(filename, pwd=pwd_bytes)
                            status = "DECRYPT_SUCCESS" if is_encrypted else "UNENCRYPTED_FILE"
                            return content, status
                            
            except RuntimeError:
                return None, "DECRYPTION_FAILED_INVALID_KEY"
            except Exception as e:
                logger.error(f"Error inspecting ZIP archive: {e}")
                return None, "CORRUPTED_ARCHIVE"

        with open(file_path, "rb") as f:
            return f.read(), "UNENCRYPTED_FILE"

    def run(self, file_path: str) -> Dict[str, Any]:
        logger.info(f"Starting Ingestion Pipeline for: {file_path}")

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return {
                "status": "FAILED",
                "reason": "FILE_NOT_FOUND",
                "clean_df": None,
                "quarantined_df": None,
                "stats": {},
            }

        file_bytes, decrypt_status = self.inspect_and_decrypt(file_path)

        if decrypt_status in ["ENCRYPTED_FILE_MISSING_KEY", "DECRYPTION_FAILED_INVALID_KEY"]:
            hold_or_quarantine = "HOLD" if decrypt_status == "ENCRYPTED_FILE_MISSING_KEY" else "QUARANTINE"
            logger.error(f"Pipeline Action: [{hold_or_quarantine}] | Reason: {decrypt_status}")
            return {
                "status": hold_or_quarantine,
                "reason": decrypt_status,
                "clean_df": None,
                "quarantined_df": None,
                "stats": {"decryption_status": decrypt_status},
            }

        try:
            ext = Path(file_path).suffix.lower()

            if ext == ".csv" or (decrypt_status in ["DECRYPT_SUCCESS", "UNENCRYPTED_FILE"] and ext == ".zip"):
                raw_df = pl.read_csv(io.BytesIO(file_bytes), infer_schema_length=10000)
            elif ext in [".xlsx", ".xls"]:
                raw_df = pl.read_excel(io.BytesIO(file_bytes))
            else:
                raise ValueError(f"Unsupported file format for ingestion: {ext}")

            logger.info(" Data successfully loaded into memory DataFrame.")
        except Exception as e:
            logger.error(f"Failed to read file into DataFrame: {e}")
            return {
                "status": "QUARANTINE",
                "reason": f"UNPARSEABLE_FILE_FORMAT: {str(e)}",
                "clean_df": None,
                "quarantined_df": None,
                "stats": {},
            }

        # Step 3: Run Cleaning and Classification Rules
        clean_df, quarantined_df, stats = self.cleaner.process(raw_df)
        stats["decryption_status"] = decrypt_status

        # -------------------------------------------------------------------
        # Step 4: SAVE OUTPUT DATASETS TO DISK (.csv)
        # -------------------------------------------------------------------
        clean_path = self.output_dir / "cleaned_dataset.csv"
        quarantine_path = self.output_dir / "quarantined_dataset.csv"

        if clean_df is not None and clean_df.height > 0:
            clean_df.write_csv(clean_path)
            logger.info(f" Saved cleaned dataset to: {clean_path}")

        if quarantined_df is not None and quarantined_df.height > 0:
            quarantined_df.write_csv(quarantine_path)
            logger.info(f" Saved quarantined dataset to: {quarantine_path}")

        logger.info(" Data normalization and record classification completed.")
        return {
            "status": "COMPLETED",
            "reason": None,
            "clean_df": clean_df,
            "quarantined_df": quarantined_df,
            "stats": stats,
            "output_files": {
                "clean_csv": str(clean_path),
                "quarantine_csv": str(quarantine_path)
            }
        }


if __name__ == "__main__":
    import sys

    target_file = "Dataset/Project_Vigilance_Dataset_Password_Protected.xlsx"
    if len(sys.argv) > 1:
        target_file = sys.argv[1]

    # Set password here
    FILE_PASSWORD = r"5kZa7cY=6SC&gw1GP0Qn6A%(g]O}CA\-"

    pipeline = IngestionPipeline(default_password=FILE_PASSWORD)
    result = pipeline.run(target_file)

    print("\n=================== Pipeline Result ===================")
    print(f"Status           : {result['status']}")
    print(f"Reason/Flag      : {result['reason']}")
    if result.get("output_files"):
        print(f"Saved Clean CSV  : {result['output_files']['clean_csv']}")
        print(f"Saved Quar. CSV  : {result['output_files']['quarantine_csv']}")
    if result["stats"]:
        print(f"Decryption Status: {result['stats'].get('decryption_status')}")
        print(f"Clean Records    : {result['stats'].get('clean_usable_records')}")
        print(f"Quarantined      : {result['stats'].get('quarantined_records')}")
        print(f"Duplicates Cleaned: {result['stats'].get('removed_duplicate_copies')}")
    print("=======================================================")