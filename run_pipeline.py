from pathlib import Path
from src.common.config import load_config
from src.ingestion.pipeline import run_ingestion

def main():
    config = load_config(Path("config/gardm_config.yaml"))
    print(f"BDP-GARDM v{config['project']['version']}")
    _, report = run_ingestion(
        Path(config["dataset"]["raw_dir"]),
        Path("schemas"),
        Path(config["dataset"]["output_dir"]) / "ag00_ingestion_report.json",
    )
    print(f"AG00 ingestion passed: {report.passed}")
    print(f"Tables checked: {len(report.results)}")
    if report.global_errors:
        print("Global errors:")
        for e in report.global_errors:
            print(" -", e)
    failed = [r for r in report.results if not r.passed]
    if failed:
        print("Failed tables:")
        for r in failed:
            print(f" - {r.table}: {r.errors}")

if __name__ == "__main__":
    main()
