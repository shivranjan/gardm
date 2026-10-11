
"""AG02 Diagnosis: deterministic diagnosis from AG01 MonitoringState only."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Optional
import math


DOWNSTREAM_TERMS = {
    "ground_truth", "optimal_recovery_action", "permissible_actions",
    "recovery_success", "verified_restoration", "selected_action",
    "gardm", "decision_id", "validation_status", "predicted_action",
}

# Fault-mechanism evidence is supplied by the context as environment/reference
# metadata, but AG02 makes the prediction from monitoring observations.
# The pilot fault catalogue contains categories/codes; AG02 uses a deterministic
# symptom-to-fault heuristic so that the development pipeline is executable.
FAULT_RULES = {
    "F001": {
        "category": "Data Quality",
        "severity": "Medium",
        "signals": ("data_quality", "quality", "completeness", "validity"),
    },
    "F002": {
        "category": "Resource Exhaustion",
        "severity": "High",
        "signals": ("resource", "capacity", "memory", "cpu"),
    },
    "F003": {
        "category": "Dependency Failure",
        "severity": "High",
        "signals": ("dependency", "upstream", "downstream"),
    },
    "F004": {
        "category": "Pipeline Failure",
        "severity": "High",
        "signals": ("pipeline", "task", "execution"),
    },
}


@dataclass(frozen=True)
class DiagnosisState:
    incident_id: str
    diagnosis_version: str
    diagnosis_timestamp: Optional[str]
    predicted_fault_code: str
    predicted_fault_category: str
    predicted_severity: str
    root_cause: str
    diagnosis_confidence: float
    diagnosis_latency_sec: Optional[float]
    diagnosis_success: Optional[bool]
    diagnosis_explanation: str
    evidence_features: List[str]
    feature_provenance: Dict[str, Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DiagnosisError(ValueError):
    pass


def _num(x):
    try:
        x = float(x)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


class DiagnosisAgent:
    """Development diagnosis baseline operating only on AG01 output."""

    VERSION = "AG02-v1.0.0"

    def diagnose(
        self,
        monitoring_state: Mapping[str, Any],
        diagnosis_timestamp: Optional[str] = None,
    ) -> DiagnosisState:

        # Reject obvious downstream leakage if someone passes a malformed state.
        serialized_keys = set(monitoring_state.keys())
        forbidden = [k for k in serialized_keys if k.lower() in DOWNSTREAM_TERMS]
        if forbidden:
            raise DiagnosisError(
                "Downstream/GARDM fields supplied to AG02: " + ", ".join(forbidden)
            )

        incident_id = str(monitoring_state.get("incident_id", ""))
        if not incident_id:
            raise DiagnosisError("incident_id is required")

        observed = monitoring_state.get("observed", {})
        health = monitoring_state.get("health_indicators", {})
        env = monitoring_state.get("environment_metadata", {})

        # Use only observed monitoring signals for diagnosis.
        state_score = _num(health.get("pipeline_state_score"))
        operational_risk = _num(health.get("operational_risk"))
        business_impact = _num(health.get("business_impact_score"))
        dependency_count = _num(observed.get("dependency_count"))
        affected_records = _num(observed.get("affected_records"))

        candidates = []

        # Deterministic symptom scoring.
        # These are development rules, not learned/final empirical weights.
        if affected_records is not None and affected_records > 0:
            candidates.append(("F001", 0.70, "affected_records observed"))
        if state_score is not None and state_score < 0.50:
            candidates.append(("F004", 0.75, "degraded pipeline state"))
        if operational_risk is not None and operational_risk >= 0.70:
            candidates.append(("F002", 0.70, "high operational risk"))
        if dependency_count is not None and dependency_count > 0:
            candidates.append(("F003", 0.65, "pipeline dependency exposure"))

        if not candidates:
            # Conservative fallback: use the environment fault code only as a
            # development reference when no symptom rule fires. It is not a
            # learned prediction and is explicitly reported as fallback.
            fallback = str(env.get("fault_code") or "UNKNOWN")
            candidates.append((fallback, 0.40, "no diagnostic symptom rule fired"))

        # Stable deterministic tie-break: score descending, then fault code.
        candidates.sort(key=lambda x: (-x[1], x[0]))
        code, confidence, reason = candidates[0]
        rule = FAULT_RULES.get(
            code,
            {"category": str(env.get("fault_category") or "Unknown"),
             "severity": str(observed.get("failure_severity") or "Unknown")}
        )

        severity = str(rule["severity"])
        if observed.get("failure_severity") not in (None, ""):
            # Monitoring severity is observed context; diagnosis does not invent
            # a new severity when the observed severity is available.
            severity = str(observed["failure_severity"])

        root_cause = {
            "F001": "Data-quality degradation affecting pipeline inputs or outputs.",
            "F002": "Operational resource or capacity pressure affecting execution.",
            "F003": "Dependency-related disruption affecting pipeline execution.",
            "F004": "Pipeline execution/state degradation affecting processing.",
        }.get(code, "Unclassified operational fault requiring further investigation.")

        evidence = [reason]
        for key in ("operational_risk", "pipeline_state_score",
                    "business_impact_score", "dependency_count", "affected_records"):
            if key in observed or key in health:
                evidence.append(key)

        provenance = {}
        for key in evidence:
            source_field = key
            if key in health:
                source_field = key
            provenance[key] = {
                "source": "AG01.MonitoringState",
                "field": source_field,
                "role": "diagnostic_evidence",
            }

        return DiagnosisState(
            incident_id=incident_id,
            diagnosis_version=self.VERSION,
            diagnosis_timestamp=diagnosis_timestamp,
            predicted_fault_code=code,
            predicted_fault_category=str(rule["category"]),
            predicted_severity=severity,
            root_cause=root_cause,
            diagnosis_confidence=round(float(confidence), 6),
            diagnosis_latency_sec=None,
            diagnosis_success=None,
            diagnosis_explanation=(
                "Development deterministic diagnosis: " + reason +
                ". This output is not used as ground truth."
            ),
            evidence_features=evidence,
            feature_provenance=provenance,
        )


def diagnose_all(monitoring_states: List[Mapping[str, Any]]) -> List[DiagnosisState]:
    agent = DiagnosisAgent()
    return [agent.diagnose(state) for state in monitoring_states]
