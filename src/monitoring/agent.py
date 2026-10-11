
"""AG01 Monitoring: deterministic decision-time observation extraction."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional
import math


# Explicitly exclude downstream / post-event information.
FORBIDDEN_FIELDS = {
    "diagnosis_confidence",
    "root_cause_confidence",
    "predicted_fault_code",
    "predicted_severity",
    "ground_truth_action",
    "correct_fault_code",
    "correct_severity",
    "correct_risk_tier",
    "optimal_recovery_action",
    "permissible_actions",
    "recovery_success",
    "recovery_status",
    "verified_restoration",
    "service_restored",
    "data_integrity_restored",
    "data_quality_restored",
    "pipeline_state_restored",
    "governance_verified",
    "audit_record_verified",
    "validation_status",
    "selected_action",
    "A1_score",
    "A2_score",
    "A3_score",
}

# These are context values that AG01 can legitimately observe at decision time.
OBSERVED_FIELDS = {
    "failure_severity",
    "operational_risk",
    "pipeline_state_score",
    "policy_compliance_score",
    "historical_similarity_score",
    "business_impact_score",
    "sla_breach_risk",
    "pipeline_criticality",
    "pii_involved",
    "regulatory_relevance",
    "affected_records",
    "affected_partitions",
    "dependency_count",
    "available_recovery_options",
}

NUMERIC_HEALTH_FIELDS = (
    "operational_risk",
    "pipeline_state_score",
    "policy_compliance_score",
    "historical_similarity_score",
    "business_impact_score",
    "sla_breach_risk",
)

@dataclass(frozen=True)
class MonitoringState:
    incident_id: str
    monitoring_version: str
    failure_timestamp: Optional[str]
    detection_timestamp: Optional[str]
    context_timestamp: Optional[str]
    detection_latency_sec: Optional[float]
    observed: Dict[str, Any]
    health_indicators: Dict[str, Optional[float]]
    environment_metadata: Dict[str, Any]
    monitoring_confidence: float
    confidence_basis: List[str]
    data_quality_flags: List[str]
    feature_provenance: Dict[str, Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MonitoringError(ValueError):
    pass


def _parse_ts(value: Any) -> Optional[datetime]:
    if value in (None, "", "NaT"):
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _norm_01(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(x):
        return None
    return max(0.0, min(1.0, x))


class MonitoringAgent:
    """Build a monitoring state only from the supplied decision-time context."""

    VERSION = "AG01-v1.0.0"

    def build(self, context: Mapping[str, Any]) -> MonitoringState:
        if not context.get("incident_id"):
            raise MonitoringError("incident_id is required")

        forbidden_present = sorted(set(context.keys()) & FORBIDDEN_FIELDS)
        if forbidden_present:
            raise MonitoringError(
                "Downstream/evaluation fields supplied to AG01: "
                + ", ".join(forbidden_present)
            )

        observed = {
            key: context.get(key)
            for key in OBSERVED_FIELDS
            if key in context
        }

        # Normalize only numeric state/risk indicators; raw observed values remain intact.
        health = {key: _norm_01(context.get(key)) for key in NUMERIC_HEALTH_FIELDS}

        failure_ts = context.get("failure_timestamp")
        detection_ts = context.get("detection_timestamp")
        context_ts = context.get("context_timestamp")
        detection_latency = None
        if failure_ts and detection_ts:
            try:
                detection_latency = round(
                    (_parse_ts(detection_ts) - _parse_ts(failure_ts)).total_seconds(), 6
                )
                if detection_latency < 0:
                    raise MonitoringError("detection_timestamp precedes failure_timestamp")
            except TypeError:
                raise MonitoringError("Invalid timestamp ordering")

        # Fault/injection details are retained as environment metadata only.
        # They are not converted into diagnosis or action-selection features.
        environment_metadata = {
            "fault_code": context.get("fault_code"),
            "fault_category": context.get("fault_category"),
            "pipeline_id": context.get("pipeline_id"),
            "execution_id": context.get("execution_id"),
        }

        flags: List[str] = []
        required = [
            "failure_timestamp", "detection_timestamp", "failure_severity",
            "operational_risk", "pipeline_state_score",
            "policy_compliance_score", "business_impact_score",
            "sla_breach_risk",
        ]
        missing = [x for x in required if context.get(x) in (None, "")]
        if missing:
            flags.append("missing_core_observation:" + ",".join(missing))

        if any(v is None for v in health.values()):
            flags.append("incomplete_health_indicators")

        # Development heuristic: confidence reflects observation completeness only.
        # It is not an expert-derived probability and is not used as diagnosis confidence.
        completeness = sum(
            context.get(k) not in (None, "") for k in required
        ) / len(required)
        health_completeness = sum(v is not None for v in health.values()) / len(health)
        monitoring_confidence = round(0.7 * completeness + 0.3 * health_completeness, 6)

        confidence_basis = [
            "core_observation_completeness",
            "health_indicator_completeness",
        ]

        provenance = {}
        for key in observed:
            provenance[key] = {
                "source": "incident_context",
                "field": key,
                "role": "observed_decision_time_input",
            }
        for key in health:
            provenance[f"health_indicators.{key}"] = {
                "source": "incident_context",
                "field": key,
                "role": "normalized_derived_feature",
            }
        provenance["detection_latency_sec"] = {
            "source": "incident_context",
            "field": "failure_timestamp,detection_timestamp",
            "role": "derived_temporal_feature",
        }

        return MonitoringState(
            incident_id=str(context["incident_id"]),
            monitoring_version=self.VERSION,
            failure_timestamp=None if failure_ts is None else str(failure_ts),
            detection_timestamp=None if detection_ts is None else str(detection_ts),
            context_timestamp=None if context_ts is None else str(context_ts),
            detection_latency_sec=detection_latency,
            observed=observed,
            health_indicators=health,
            environment_metadata=environment_metadata,
            monitoring_confidence=monitoring_confidence,
            confidence_basis=confidence_basis,
            data_quality_flags=flags,
            feature_provenance=provenance,
        )


def build_all(contexts: List[Mapping[str, Any]]) -> List[MonitoringState]:
    agent = MonitoringAgent()
    return [agent.build(c) for c in contexts]
