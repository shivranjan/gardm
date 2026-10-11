from pathlib import Path
import math
import pandas as pd
import yaml

from .models import IngestionReport, TableValidationResult

class DatasetValidator:
    def __init__(self, schema_path: Path, relationships_path: Path, validation_rules_path: Path):
        self.schema = yaml.safe_load(Path(schema_path).read_text(encoding="utf-8"))
        self.relationships = yaml.safe_load(Path(relationships_path).read_text(encoding="utf-8"))
        self.rules = yaml.safe_load(Path(validation_rules_path).read_text(encoding="utf-8"))

    def validate(self, tables: dict[str, pd.DataFrame]) -> IngestionReport:
        results = []
        expected = set(self.schema["tables"])
        actual = set(tables)

        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        global_errors = []
        if missing:
            global_errors.append(f"Missing tables: {missing}")
        if unexpected:
            global_errors.append(f"Unexpected tables: {unexpected}")

        for table_name, spec in self.schema["tables"].items():
            if table_name not in tables:
                continue
            results.append(self._validate_table(table_name, tables[table_name], spec))

        global_errors.extend(self._validate_relationships(tables))
        global_errors.extend(self._validate_temporal_rules(tables))
        global_errors.extend(self._validate_leakage(tables))

        return IngestionReport(results=results, global_errors=global_errors)

    def _validate_table(self, name, df, spec):
        result = TableValidationResult(name, len(df))
        expected_cols = set(spec["columns"])
        actual_cols = set(df.columns)

        missing = sorted(expected_cols - actual_cols)
        unexpected = sorted(actual_cols - expected_cols)
        if missing:
            result.errors.append(f"Missing columns: {missing}")
        if unexpected:
            result.warnings.append(f"Unexpected columns: {unexpected}")

        pk = spec["primary_key"]
        if pk in df.columns:
            if df[pk].isna().any():
                result.errors.append(f"Primary key '{pk}' contains null values.")
            if df[pk].duplicated().any():
                result.errors.append(f"Primary key '{pk}' contains duplicates.")

        for col, contract in spec["columns"].items():
            if col not in df.columns:
                continue
            s = df[col]

            if contract.get("required") and s.isna().any():
                result.errors.append(f"Required column '{col}' contains null values.")

            rules = contract.get("rules", {})
            if "range" in rules:
                numeric = pd.to_numeric(s, errors="coerce")
                invalid = numeric.notna() & ((numeric < rules["range"][0]) | (numeric > rules["range"][1]))
                if invalid.any():
                    result.errors.append(
                        f"Column '{col}' has {int(invalid.sum())} values outside "
                        f"[{rules['range'][0]}, {rules['range'][1]}]."
                    )

            if "allowed" in rules:
                values = set(pd.to_numeric(s.dropna(), errors="coerce").dropna().astype(int).tolist())
                invalid = values - set(rules["allowed"])
                if invalid:
                    result.errors.append(f"Column '{col}' contains disallowed binary values: {sorted(invalid)}.")

        return result

    def _validate_relationships(self, tables):
        errors = []
        for rel in self.relationships.get("relationships", []):
            child = rel["child_table"]
            parent = rel["parent_table"]
            cc = rel["child_column"]
            pc = rel["parent_column"]
            if child not in tables or parent not in tables or cc not in tables[child].columns or pc not in tables[parent].columns:
                continue

            child_values = tables[child][cc].dropna()
            parent_values = set(tables[parent][pc].dropna().tolist())
            missing = child_values[~child_values.isin(parent_values)]
            if not missing.empty:
                errors.append(
                    f"FK violation: {child}.{cc} has {len(missing)} value(s) "
                    f"not found in {parent}.{pc}."
                )
        return errors

    def _validate_temporal_rules(self, tables):
        errors = []
        if "historical_incidents" in tables and "incident_context" in tables:
            h = tables["historical_incidents"]
            c = tables["incident_context"]
            htime = next((x for x in h.columns if "timestamp" in x.lower()), None)
            ctime = next((x for x in c.columns if "timestamp" in x.lower()), None)
            if htime and ctime:
                hv = pd.to_datetime(h[htime], errors="coerce").dropna()
                cv = pd.to_datetime(c[ctime], errors="coerce").dropna()
                if not hv.empty and not cv.empty and hv.max() >= cv.min():
                    errors.append("Temporal leakage risk: historical incidents overlap or follow pilot incident timestamps.")

        lifecycle = [
            ("failure_timestamp", "detection_timestamp"),
            ("detection_timestamp", "diagnosis_timestamp"),
            ("diagnosis_timestamp", "decision_timestamp"),
        ]
        if "incident_context" in tables:
            df = tables["incident_context"]
            for left, right in lifecycle:
                if left in df.columns and right in df.columns:
                    a = pd.to_datetime(df[left], errors="coerce")
                    b = pd.to_datetime(df[right], errors="coerce")
                    bad = a.notna() & b.notna() & (a > b)
                    if bad.any():
                        errors.append(f"Temporal ordering violation in incident_context: {left} > {right} for {int(bad.sum())} row(s).")
        return errors

    def _validate_leakage(self, tables):
        errors = []
        # Ground-truth/evaluation tables must not become decision-time source tables.
        forbidden_source_tables = {"ground_truth_decisions", "evaluation_results"}
        if forbidden_source_tables & set(tables):
            # Presence is expected; this is a guardrail for the feature builder.
            pass

        if "gardm_decisions" in tables:
            df = tables["gardm_decisions"]
            forbidden = {"ground_truth_action", "action_correct", "recovery_success", "verified_restoration"}
            found = sorted(forbidden & set(df.columns))
            if found:
                errors.append(f"Leakage violation: gardm_decisions contains evaluation/ground-truth fields: {found}")
        return errors
