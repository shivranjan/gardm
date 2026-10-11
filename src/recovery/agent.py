
"""Step 9: governed recovery execution and HITL control."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Optional


@dataclass(frozen=True)
class RecoveryResult:
    incident_id: str
    recovery_version: str
    decision_id: Optional[str]
    action_id: Optional[str]
    hitl_activated: bool
    approval_status: str
    approval_latency_sec: Optional[float]
    execution_status: str
    recovery_success: Optional[bool]
    fallback_action: Optional[str]
    execution_trace: List[Dict[str, Any]]
    governance_compliant: bool
    status_note: str

    def to_dict(self):
        return asdict(self)


class RecoveryError(ValueError):
    pass


class RecoveryAgent:
    """Execute a governed decision using a deterministic development executor.

    The executor never reads ground truth, validation events, or evaluation
    results. Recovery success is an execution outcome and is therefore not
    fed back into GARDM.
    """

    VERSION = "RECOVERY-v1.0.0"

    def __init__(self, hitl_policies=None):
        self.hitl_policies = hitl_policies or []

    @staticmethod
    def _find_action(action_id, candidate_actions):
        for action in candidate_actions:
            if str(action.get("action_id")) == str(action_id):
                return action
        return None

    def execute(
        self,
        gardm_decision: Mapping[str, Any],
        governance_state: Mapping[str, Any],
        candidate_actions: List[Mapping[str, Any]],
        approved: Optional[bool] = None,
        approval_latency_sec: Optional[float] = None,
    ) -> RecoveryResult:

        incident_id = str(gardm_decision.get("incident_id", ""))
        selected = gardm_decision.get("selected_action")
        required_hitl = bool(governance_state.get("hitl_required"))

        if incident_id != str(governance_state.get("incident_id")):
            raise RecoveryError("GARDM/governance incident mismatch")

        if not selected:
            return RecoveryResult(
                incident_id=incident_id,
                recovery_version=self.VERSION,
                decision_id=gardm_decision.get("decision_id"),
                action_id=None,
                hitl_activated=required_hitl,
                approval_status="NOT_APPLICABLE",
                approval_latency_sec=None,
                execution_status="NO_ACTION",
                recovery_success=False,
                fallback_action=None,
                execution_trace=[],
                governance_compliant=True,
                status_note="No governed action was selected.",
            )

        permitted = set(governance_state.get("permitted_action_ids", []))
        if str(selected) not in permitted:
            raise RecoveryError("Selected GARDM action is not governance-permitted")

        action = self._find_action(selected, candidate_actions)
        if action is None:
            raise RecoveryError(f"Selected action not found: {selected}")

        approval_status = "NOT_REQUIRED"
        hitl_activated = required_hitl

        if required_hitl:
            if approved is True:
                approval_status = "APPROVED"
            elif approved is False:
                approval_status = "REJECTED"
            else:
                approval_status = "PENDING"

        # Rejection/pending means execution is not attempted.
        if required_hitl and approval_status != "APPROVED":
            fallback = None
            if approval_status == "REJECTED":
                fallback = "SAFE_STOP"
            return RecoveryResult(
                incident_id=incident_id,
                recovery_version=self.VERSION,
                decision_id=gardm_decision.get("decision_id"),
                action_id=str(selected),
                hitl_activated=True,
                approval_status=approval_status,
                approval_latency_sec=approval_latency_sec,
                execution_status="NOT_EXECUTED",
                recovery_success=False,
                fallback_action=fallback,
                execution_trace=[],
                governance_compliant=True,
                status_note=(
                    "Recovery execution blocked until required human approval."
                ),
            )

        # Development executor: execution is represented as a trace only.
        # It deliberately does not claim verified restoration.
        trace = [{
            "event": "RECOVERY_STARTED",
            "action_id": str(selected),
            "action_class": action.get("action_class"),
        }, {
            "event": "RECOVERY_COMPLETED",
            "action_id": str(selected),
            "execution_mode": "DEVELOPMENT_SIMULATOR",
        }]

        return RecoveryResult(
            incident_id=incident_id,
            recovery_version=self.VERSION,
            decision_id=gardm_decision.get("decision_id"),
            action_id=str(selected),
            hitl_activated=hitl_activated,
            approval_status=approval_status,
            approval_latency_sec=approval_latency_sec,
            execution_status="COMPLETED",
            recovery_success=True,
            fallback_action=None,
            execution_trace=trace,
            governance_compliant=True,
            status_note=(
                "Development recovery execution completed. "
                "Restoration remains subject to AG05 validation."
            ),
        )


def execute_all(
    gardm_decisions,
    governance_states,
    candidate_actions,
    hitl_policies=None,
    approvals=None,
):
    agent = RecoveryAgent(hitl_policies)
    approvals = approvals or {}
    results = []
    for d, g in zip(gardm_decisions, governance_states):
        incident_id = str(d["incident_id"])
        approval = approvals.get(incident_id)
        results.append(
            agent.execute(d, g, candidate_actions, approved=approval)
        )
    return results
