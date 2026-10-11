
"""AG03 Governance/Risk: policy, regulatory and HITL gate before GARDM."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Optional
import math


FORBIDDEN_DECISION_FIELDS = {
    "ground_truth_action", "correct_fault_code", "correct_severity",
    "correct_risk_tier", "optimal_recovery_action", "permissible_actions",
    "recovery_success", "verified_restoration", "service_restored",
    "validation_status", "selected_action", "A1_score", "A2_score", "A3_score",
}

# Conservative development mapping from observed operational risk and impact
# into a normalized governance risk score. This is a policy heuristic, not a
# learned model and not final research evidence.
RISK_WEIGHTS = {
    "operational_risk": 0.35,
    "business_impact_score": 0.25,
    "sla_breach_risk": 0.20,
    "pipeline_state_score_inverse": 0.20,
}


@dataclass(frozen=True)
class GovernanceState:
    incident_id: str
    governance_version: str
    governance_timestamp: Optional[str]
    risk_score: float
    risk_tier: str
    policy_compliant: bool
    regulatory_clear: bool
    criticality_clear: bool
    hitl_required: bool
    hitl_reason: Optional[str]
    action_class_constraints: Dict[str, Dict[str, Any]]
    permitted_action_ids: List[str]
    blocked_action_ids: List[str]
    policy_evaluations: List[Dict[str, Any]]
    regulatory_evaluations: List[Dict[str, Any]]
    governance_explanation: str
    feature_provenance: Dict[str, Dict[str, Any]]

    def to_dict(self):
        return asdict(self)


class GovernanceError(ValueError):
    pass


class GovernanceAgent:
    """Apply governance/risk gates using only AG01 + AG02 decision-time state."""

    VERSION = "AG03-v1.0.0"

    def _n(self, value):
        try:
            x = float(value)
            return max(0.0, min(1.0, x)) if math.isfinite(x) else None
        except (TypeError, ValueError):
            return None

    def evaluate(
        self,
        monitoring_state: Mapping[str, Any],
        diagnosis_state: Mapping[str, Any],
        governance_policies: Optional[List[Mapping[str, Any]]] = None,
        regulatory_constraints: Optional[List[Mapping[str, Any]]] = None,
        candidate_actions: Optional[List[Mapping[str, Any]]] = None,
        risk_rules: Optional[List[Mapping[str, Any]]] = None,
        hitl_policies: Optional[List[Mapping[str, Any]]] = None,
        governance_timestamp: Optional[str] = None,
    ) -> GovernanceState:

        forbidden = set(monitoring_state.keys()) & FORBIDDEN_DECISION_FIELDS
        if forbidden:
            raise GovernanceError(
                "Forbidden downstream fields in monitoring state: " +
                ", ".join(sorted(forbidden))
            )
        forbidden = set(diagnosis_state.keys()) & FORBIDDEN_DECISION_FIELDS
        if forbidden:
            raise GovernanceError(
                "Forbidden downstream fields in diagnosis state: " +
                ", ".join(sorted(forbidden))
            )

        incident_id = str(monitoring_state.get("incident_id", ""))
        if not incident_id or incident_id != str(diagnosis_state.get("incident_id", "")):
            raise GovernanceError("Monitoring and diagnosis incident IDs must match")

        obs = monitoring_state.get("observed", {})
        health = monitoring_state.get("health_indicators", {})

        op = self._n(health.get("operational_risk"))
        impact = self._n(health.get("business_impact_score"))
        sla = self._n(health.get("sla_breach_risk"))
        state = self._n(health.get("pipeline_state_score"))

        vals = [op, impact, sla, None if state is None else 1.0 - state]
        available = [v for v in vals if v is not None]
        risk_score = round(sum(v * w for v, w in zip(
            available,
            [0.35, 0.25, 0.20, 0.20][:len(available)]
        )) / (sum([0.35, 0.25, 0.20, 0.20][:len(available)]) or 1), 6)

        # Default governance tiers; external risk_rules override when supplied.
        risk_tier = "LOW"
        if risk_score >= 0.75:
            risk_tier = "CRITICAL"
        elif risk_score >= 0.60:
            risk_tier = "HIGH"
        elif risk_score >= 0.35:
            risk_tier = "MEDIUM"

        if risk_rules:
            matched = []
            for rule in risk_rules:
                try:
                    lo, hi = float(rule["min_score"]), float(rule["max_score"])
                    if lo <= risk_score < hi:
                        matched.append(rule)
                except (KeyError, TypeError, ValueError):
                    continue
            if matched:
                risk_tier = str(matched[0].get("risk_tier", risk_tier)).upper()

        pii = bool(obs.get("pii_involved"))
        regulatory = bool(obs.get("regulatory_relevance"))
        criticality = str(obs.get("pipeline_criticality", "")).upper()

        # Governance is conservative: sensitive/regulatory pipelines cannot be
        # auto-approved solely because a technical action looks safe.
        hitl_required = risk_tier in {"HIGH", "CRITICAL"} or pii or regulatory
        hitl_reason = None
        if risk_tier in {"HIGH", "CRITICAL"}:
            hitl_reason = f"{risk_tier.lower()} risk tier"
        elif pii:
            hitl_reason = "PII involved"
        elif regulatory:
            hitl_reason = "regulatory relevance"

        policy_evaluations = []
        policy_compliant = True
        for policy in governance_policies or []:
            policy_evaluations.append({
                "policy_id": policy.get("policy_id"),
                "category": policy.get("policy_category"),
                "condition": policy.get("condition"),
                "result": "REVIEW_REQUIRED" if hitl_required else "PASS",
            })

        regulatory_evaluations = []
        regulatory_clear = True
        for constraint in regulatory_constraints or []:
            result = "REVIEW_REQUIRED" if regulatory else "PASS"
            regulatory_evaluations.append({
                "constraint_id": constraint.get("constraint_id"),
                "obligation": constraint.get("obligation"),
                "regulatory_reference": constraint.get("regulatory_reference"),
                "result": result,
            })
            if regulatory:
                regulatory_clear = False

        # Criticality is a governance signal, not a recovery decision.
        criticality_clear = criticality not in {"CRITICAL", "HIGH"} or hitl_required

        permitted = []
        blocked = []
        constraints = {}

        for action in candidate_actions or []:
            aid = str(action.get("action_id"))
            requires_approval = bool(action.get("requires_approval"))
            data_modification = bool(action.get("data_modification"))
            rollback = bool(action.get("rollback_capability"))

            blocked_reason = None
            if not aid:
                blocked_reason = "missing action_id"
            elif data_modification and not rollback:
                blocked_reason = "data modification without rollback capability"
            elif hitl_required and not requires_approval:
                blocked_reason = "governance requires HITL approval"
            elif regulatory and data_modification:
                blocked_reason = "regulatory context requires review for data modification"

            allowed = blocked_reason is None
            if allowed:
                permitted.append(aid)
            else:
                blocked.append(aid)

            constraints[aid] = {
                "requires_approval": requires_approval,
                "data_modification": data_modification,
                "rollback_capability": rollback,
                "allowed": allowed,
                "blocked_reason": blocked_reason,
            }

        provenance = {}
        for key in ("operational_risk", "business_impact_score",
                    "sla_breach_risk", "pipeline_state_score"):
            provenance[f"risk.{key}"] = {
                "source": "AG01.MonitoringState",
                "field": key,
                "role": "risk_input",
            }
        provenance["risk_tier"] = {
            "source": "AG03.GovernanceAgent",
            "field": "risk_score",
            "role": "derived_policy_output",
        }
        provenance["hitl_required"] = {
            "source": "AG03.GovernanceAgent",
            "field": "risk_tier,pii_involved,regulatory_relevance",
            "role": "governance_gate",
        }

        return GovernanceState(
            incident_id=incident_id,
            governance_version=self.VERSION,
            governance_timestamp=governance_timestamp,
            risk_score=risk_score,
            risk_tier=risk_tier,
            policy_compliant=policy_compliant,
            regulatory_clear=regulatory_clear,
            criticality_clear=criticality_clear,
            hitl_required=hitl_required,
            hitl_reason=hitl_reason,
            action_class_constraints=constraints,
            permitted_action_ids=permitted,
            blocked_action_ids=blocked,
            policy_evaluations=policy_evaluations,
            regulatory_evaluations=regulatory_evaluations,
            governance_explanation=(
                "Governance gate applied before recovery selection. "
                "Permitted actions are constrained by approval, rollback, "
                "risk and regulatory conditions."
            ),
            feature_provenance=provenance,
        )


def evaluate_all(
    monitoring_states,
    diagnosis_states,
    governance_policies=None,
    regulatory_constraints=None,
    candidate_actions=None,
    risk_rules=None,
    hitl_policies=None,
):
    agent = GovernanceAgent()
    return [
        agent.evaluate(
            m, d, governance_policies, regulatory_constraints,
            candidate_actions, risk_rules, hitl_policies
        )
        for m, d in zip(monitoring_states, diagnosis_states)
    ]
