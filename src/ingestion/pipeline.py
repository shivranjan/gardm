from pathlib import Path
import json

from .loader import load_dataset
from .validator import DatasetValidator

def run_ingestion(
    raw_dir: Path,
    schema_dir: Path,
    report_path: Path | None = None,
):
    tables = load_dataset(raw_dir)
    validator = DatasetValidator(
        schema_dir / "entities.yaml",
        schema_dir / "relationships.yaml",
        schema_dir / "validation_rules.yaml",
    )
    report = validator.validate(tables)

    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report.to_dict(), indent=2),
            encoding="utf-8",
        )
    return tables, report
