from pathlib import Path
import pandas as pd

SUPPORTED_SUFFIXES = {".csv"}

def discover_csv_files(raw_dir: Path) -> dict[str, Path]:
    raw_dir = Path(raw_dir)
    return {p.stem: p for p in sorted(raw_dir.glob("*.csv"))}

def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)

def load_dataset(raw_dir: Path) -> dict[str, pd.DataFrame]:
    return {name: load_csv(path) for name, path in discover_csv_files(raw_dir).items()}
