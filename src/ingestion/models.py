from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class TableValidationResult:
    table: str
    rows: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors

@dataclass
class IngestionReport:
    results: list[TableValidationResult]
    global_errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.global_errors and all(r.passed for r in self.results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "global_errors": self.global_errors,
            "tables": [
                {
                    "table": r.table,
                    "rows": r.rows,
                    "passed": r.passed,
                    "errors": r.errors,
                    "warnings": r.warnings,
                }
                for r in self.results
            ],
        }
