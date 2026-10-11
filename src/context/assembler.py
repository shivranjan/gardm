from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json
import pandas as pd


# Explicit decision-time allow-list. This is deliberately conservative.
# Ground-truth, evaluation, validation-after-recovery, and audit-only tables
# are excluded from the decision-time context.
DECISION_TIME_TABLES = {
    "incident_context",
    "pipeline_metadata",
    "pipeline_dependencies",
    "fault_catalog",
    "fault_injection_events",
    "historical_incidents",
    "detection_events",
    "candidate_recovery_actions",
    "governance_policies",
    "regulatory_constraints",
    "risk_rules",
    "hitl_policies",
    "customers",
    "accounts",
    "merchants",
    "transactions",
}

EXCLUDED_TABLES = {
    "ground_truth_decisions",
    "evaluation_results",
    "recovery_execution",
    "validation_events",
    "audit_logs",
    "audit_policies",
    "agent_events",
    "data_quality_metrics",
    "quality_audit",
    "experiment_runs",
    "pipeline_execution_logs",
    "diagnosis_events",
    "gardm_decisions",
}

@dataclass
class IncidentContext:
    incident_id: str
    context_version: str
    incident: dict[str, Any]
    pipeline: dict[str, Any]
    fault: dict[str, Any]
    injection: dict[str, Any]
    detection: dict[str, Any]
    historical: list[dict[str, Any]]
    candidate_actions: list[dict[str, Any]]
    governance: list[dict[str, Any]]
    risk_rules: list[dict[str, Any]]
    hitl_policy: list[dict[str, Any]]
    business_context: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ContextAssemblyError(Exception):
    pass


class IncidentContextAssembler:
    """Builds decision-time context for one or many pilot incidents."""

    VERSION = "1.0.0"

    def __init__(self, tables: dict[str, pd.DataFrame]):
        self.tables = tables

    def _row_by_value(self, table: str, column: str, value: Any) -> dict[str, Any]:
        df = self.tables.get(table)
        if df is None or column not in df.columns:
            return {}
        matches = df[df[column] == value]
        if matches.empty:
            return {}
        return self._clean_record(matches.iloc[0].to_dict())

    EVALUATION_ONLY_FIELDS = {
        "ground_truth_action", "action_correct", "recovery_success",
        "verified_restoration", "diagnosis_success", "detection_success",
        "service_restored", "data_integrity_restored", "data_quality_restored",
        "pipeline_state_restored", "governance_verified", "audit_record_verified",
        "validation_status"
    }

    @classmethod
    def _clean_record(cls, record: dict[str, Any]) -> dict[str, Any]:
        out = {}
        for k, v in record.items():
            # These fields are post-outcome/evaluation labels and are never
            # allowed into the decision-time context.
            if k in cls.EVALUATION_ONLY_FIELDS:
                continue
            if pd.isna(v):
                out[k] = None
            elif hasattr(v, "item"):
                out[k] = v.item()
            else:
                out[k] = v
        return out

    def _records_by_value(self, table: str, column: str, value: Any) -> list[dict[str, Any]]:
        df = self.tables.get(table)
        if df is None or column not in df.columns:
            return []
        matches = df[df[column] == value]
        return [self._clean_record(r) for r in matches.to_dict(orient="records")]

    def _incident_ids(self) -> list[Any]:
        df = self.tables.get("incident_context")
        if df is None or "incident_id" not in df.columns:
            raise ContextAssemblyError("incident_context.incident_id is required.")
        return df["incident_id"].dropna().drop_duplicates().tolist()

    def assemble(self, incident_id: Any) -> IncidentContext:
        ic = self._row_by_value("incident_context", "incident_id", incident_id)
        if not ic:
            raise ContextAssemblyError(f"Incident not found: {incident_id}")

        pipeline_id = ic.get("pipeline_id")
        execution_id = ic.get("execution_id")
        fault_code = ic.get("fault_code")

        pipeline = self._row_by_value("pipeline_metadata", "pipeline_id", pipeline_id)
        fault = self._row_by_value("fault_catalog", "fault_code", fault_code)

        injection = self._row_by_value("fault_injection_events", "incident_id", incident_id)
        detection = self._row_by_value("detection_events", "incident_id", incident_id)

        # Historical evidence is restricted to incidents strictly earlier
        # than the current incident. No current/future incident outcomes enter H.
        historical_df = self.tables.get("historical_incidents", pd.DataFrame()).copy()
        historical = []
        current_ts = self._timestamp_from_record(ic)
        if not historical_df.empty:
            ts_col = self._timestamp_column(historical_df)
            if ts_col and current_ts is not None:
                ts = pd.to_datetime(historical_df[ts_col], errors="coerce")
                eligible = historical_df[ts < current_ts]
                historical = [
                    self._clean_record(r)
                    for r in eligible.to_dict(orient="records")
                ]
            else:
                historical = [
                    self._clean_record(r)
                    for r in historical_df.to_dict(orient="records")
                ]

        candidate_actions = [
            self._clean_record(r)
            for r in self.tables.get("candidate_recovery_actions", pd.DataFrame()).to_dict(orient="records")
        ]

        governance = []
        for t, key in [
            ("governance_policies", None),
            ("regulatory_constraints", None),
            ("risk_rules", None),
        ]:
            df = self.tables.get(t)
            if df is not None:
                governance.extend(
                    [{"source_table": t, **self._clean_record(r)}
                     for r in df.to_dict(orient="records")]
                )

        hitl = [
            self._clean_record(r)
            for r in self.tables.get("hitl_policies", pd.DataFrame()).to_dict(orient="records")
        ]

        business_context = self._build_business_context(ic)

        context = IncidentContext(
            incident_id=str(incident_id),
            context_version=self.VERSION,
            incident=ic,
            pipeline=pipeline,
            fault=fault,
            injection=injection,
            detection=detection,
            historical=historical,
            candidate_actions=candidate_actions,
            governance=governance,
            risk_rules=[
                self._clean_record(r)
                for r in self.tables.get("risk_rules", pd.DataFrame()).to_dict(orient="records")
            ],
            hitl_policy=hitl,
            business_context=business_context,
        )

        self.validate(context)
        return context

    def _build_business_context(self, incident: dict[str, Any]) -> dict[str, Any]:
        result = {}
        # Include linked business records only when a direct identifier exists.
        for table, key in [
            ("customers", "customer_id"),
            ("accounts", "account_id"),
            ("merchants", "merchant_id"),
            ("transactions", "transaction_id"),
        ]:
            value = incident.get(key)
            if value is not None:
                result[table] = self._row_by_value(table, key, value)
        return result

    @staticmethod
    def _timestamp_column(df: pd.DataFrame) -> str | None:
        candidates = [c for c in df.columns if "timestamp" in c.lower()]
        return candidates[0] if candidates else None

    def _timestamp_from_record(self, record: dict[str, Any]):
        for k, v in record.items():
            if "timestamp" in k.lower() and v is not None:
                ts = pd.to_datetime(v, errors="coerce")
                if not pd.isna(ts):
                    return ts
        return None

    def validate(self, context: IncidentContext) -> None:
        payload = context.to_dict()

        # Hard leakage guard: none of the explicitly excluded table names may
        # appear as top-level decision-time context sections.
        forbidden_keys = EXCLUDED_TABLES.intersection(payload.keys())
        if forbidden_keys:
            raise ContextAssemblyError(
                f"Decision-time context contains excluded sections: {sorted(forbidden_keys)}"
            )

        # GARDM outputs and ground truth cannot appear anywhere in serialized context.
        serialized = json.dumps(payload, default=str).lower()
        forbidden_terms = [
            "ground_truth_action",
            "action_correct",
            "recovery_success",
            "verified_restoration",
            "diagnosis_success",
            "detection_success",
        ]
        found = [term for term in forbidden_terms if term in serialized]
        if found:
            raise ContextAssemblyError(
                f"Potential evaluation leakage detected: {found}"
            )

    def assemble_all(self) -> list[IncidentContext]:
        return [self.assemble(i) for i in self._incident_ids()]


def save_contexts(contexts: list[IncidentContext], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([c.to_dict() for c in contexts], indent=2, default=str),
        encoding="utf-8",
    )
