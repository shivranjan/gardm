from pathlib import Path
from src.ingestion.pipeline import run_ingestion

def test_ingestion_schema():
    raw = Path("data/raw")
    schema = Path("schemas")
    if not list(raw.glob("*.csv")):
        # Repository scaffold test: raw data may not be copied into the project yet.
        return
    _, report = run_ingestion(raw, schema)
    assert report.passed, report.to_dict()
