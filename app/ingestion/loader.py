from pathlib import Path
import polars as pl

SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}

def load_dataset(path: str | Path) -> pl.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pl.read_csv(path, try_parse_dates=True)

    if suffix == ".xlsx":
        return pl.read_excel(path)

    raise ValueError(f"Unsupported file type: {suffix}")
