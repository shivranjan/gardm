
"""GARDM decision engine: governed, configurable, deterministic action scoring."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional
import math
import yaml


FEATURES = ("P", "R", "S", "H", "F")


@dataclass(frozen=True)
class GARDMDecision:
    incident_id: str
    decision_version: str
    decision_timestamp: Optional[str]
    P_score: float
    R_score: float
    S_score: float
    H_score: float
    F_score: float
    weights: Dict[str, float]
    action_compatibility: Dict[str, Dict[str, float]]
    action_scores: Dict[str, float]
    risk_constraint_triggered: bool
    selected_action: Optional[str]
    decision_confidence: float
    status_note: str

    def to_dict(self):
        d = asdict(self)
        d["w_P"] = self.weights["P"]
        d["w_R"] = self.weights["R"]
        d["w_S"] = self.weights["S"]
        d["w_H"] = self.weights["H"]
        d["w_F"] = self.weights["F"]
        for aid, values in self.action_compatibility.items():
            for f in FEATURES:
                d[f"{aid}_{f}"] = values[f]
        for aid, score in self.action_scores.items():
            d[f"{aid}_score"] = score
        return d


class GARDMError(ValueError):
    pass


class GARDMEngine:
    """Core GARDM implementation.

    Decision-time inputs are MonitoringState, DiagnosisState and GovernanceState.
    Ground truth, evaluation, recovery and validation outcomes are never read.
    """

    VERSION = "GARDM-v1.0.0"

    def __init__(self, config_path: Path):
        cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
        gardm = cfg.get("gardm", {})
        self.weights = {f: float(gardm["feature_weights"][f]) for f in FEATURES}
        self.risk_threshold = float(gardm["risk_threshold"])
        total = sum(self.weights.values())
        if not math.isclose(total, 1.0, rel_tol=0, abs_tol=1e-9):
            raise GARDMError(f"GARDM weights must sum to 1; got {total}")

    @staticmethod
    def _clip(x: Any) -> float:
        try:
            x = float(x)
        except (TypeError, ValueError):
            return 0.0
        if not math.isfinite(x):
            return 0.0
        return max(0.0, min(1.0, x))

    def build_features(self, monitoring_state, diagnosis_state, governance_state):
        """Construct X=[P,R,S,H,F] from prior-stage outputs only.

        P: pipeline/service state pressure (inverse state health)
        R: operational risk
        S: business/SLA impact pressure
        H: historical similarity
        F: fault/diagnosis confidence
        """
        h = monitoring_state.get("health_indicators", {})
        obs = monitoring_state.get("observed", {})

        P = 1.0 - self._clip(h.get("pipeline_state_score"))
        R = self._clip(governance_state.get("risk_score"))
        S = max(
            self._clip(h.get("business_impact_score")),
            self._clip(h.get("sla_breach_risk")),
        )
        H = self._clip(h.get("historical_similarity_score"))
        F = self._clip(diagnosis_state.get("diagnosis_confidence"))

        return {"P": P, "R": R, "S": S, "H": H, "F": F}

    def score_actions(self, features, candidate_actions, governance_state):
        """Score only governance-permitted actions."""
        permitted = set(governance_state.get("permitted_action_ids", []))
        compatibility = {}
        scores = {}

        for action in candidate_actions:
            aid = str(action.get("action_id"))
            if aid not in permitted:
                continue

            # Transparent development compatibility coefficients.
            # These describe action suitability to each GARDM dimension and
            # are deterministic baseline values until expert elicitation.
            action_class = str(action.get("action_class", "")).lower()
            data_mod = bool(action.get("data_modification"))
            rollback = bool(action.get("rollback_capability"))

            C = {
                "P": 1.0 if action_class in {"restart", "rerun", "rollback"} else 0.75,
                "R": 0.70 if rollback else 0.45,
                "S": 0.80 if action.get("expected_recovery_time_sec", 0) <= 300 else 0.60,
                "H": 0.85 if rollback else 0.65,
                "F": 0.60 if data_mod else 0.80,
            }

            compatibility[aid] = C
            scores[aid] = round(
                sum(self.weights[f] * features[f] * C[f] for f in FEATURES), 6
            )

        return compatibility, scores

    def decide(
        self,
        monitoring_state: Mapping[str, Any],
        diagnosis_state: Mapping[str, Any],
        governance_state: Mapping[str, Any],
        candidate_actions: List[Mapping[str, Any]],
        decision_timestamp: Optional[str] = None,
    ) -> GARDMDecision:

        incident_id = str(monitoring_state.get("incident_id", ""))
        if not incident_id:
            raise GARDMError("incident_id is required")
        if incident_id != str(diagnosis_state.get("incident_id")):
            raise GARDMError("Monitoring/diagnosis incident mismatch")
        if incident_id != str(governance_state.get("incident_id")):
            raise GARDMError("Monitoring/governance incident mismatch")

        # Explicitly reject downstream/evaluation data if accidentally passed.
        forbidden = {
            "ground_truth_action", "optimal_recovery_action",
            "recovery_success", "verified_restoration", "validation_status",
            "action_correct", "evaluation_results",
        }
        for payload_name, payload in (
            ("monitoring_state", monitoring_state),
            ("diagnosis_state", diagnosis_state),
            ("governance_state", governance_state),
        ):
            bad = forbidden.intersection(payload.keys())
            if bad:
                raise GARDMError(f"Forbidden downstream fields in {payload_name}: {sorted(bad)}")

        features = self.build_features(monitoring_state, diagnosis_state, governance_state)
        compatibility, scores = self.score_actions(features, candidate_actions, governance_state)

        # Governance remains authoritative. If risk exceeds the configured
        # threshold, GARDM cannot silently bypass the governance/HITL gate.
        risk = self._clip(governance_state.get("risk_score"))
        triggered = risk >= self.risk_threshold or bool(governance_state.get("hitl_required"))

        selected = None
        if scores:
            # Deterministic tie-break by action ID.
            selected = sorted(scores.items(), key=lambda x: (-x[1], x[0]))[0][0]
            if triggered and not governance_state.get("hitl_required"):
                # Kept for explicit auditability; no bypass occurs.
                selected = selected
        else:
            status = "NO_GOVERNED_ACTION_AVAILABLE"
            return GARDMDecision(
                incident_id=incident_id,
                decision_version=self.VERSION,
                decision_timestamp=decision_timestamp,
                P_score=features["P"], R_score=features["R"], S_score=features["S"],
                H_score=features["H"], F_score=features["F"],
                weights=self.weights,
                action_compatibility=compatibility,
                action_scores=scores,
                risk_constraint_triggered=triggered,
                selected_action=None,
                decision_confidence=0.0,
                status_note=status,
            )

        ranked = sorted(scores.values(), reverse=True)
        margin = ranked[0] - ranked[1] if len(ranked) > 1 else ranked[0]
        confidence = self._clip(0.5 + margin)

        note = (
            "GARDM action selected from governance-permitted candidates. "
            "Risk/HITL constraint is recorded and cannot be bypassed."
        )
        if governance_state.get("hitl_required"):
            note += " Human approval remains required before execution."

        return GARDMDecision(
            incident_id=incident_id,
            decision_version=self.VERSION,
            decision_timestamp=decision_timestamp,
            P_score=features["P"], R_score=features["R"], S_score=features["S"],
            H_score=features["H"], F_score=features["F"],
            weights=self.weights,
            action_compatibility=compatibility,
            action_scores=scores,
            risk_constraint_triggered=triggered,
            selected_action=selected,
            decision_confidence=round(confidence, 6),
            status_note=note,
        )


def decide_all(
    monitoring_states,
    diagnosis_states,
    governance_states,
    candidate_actions,
    config_path,
):
    engine = GARDMEngine(Path(config_path))
    return [
        engine.decide(m, d, g, candidate_actions)
        for m, d, g in zip(monitoring_states, diagnosis_states, governance_states)
    ]
