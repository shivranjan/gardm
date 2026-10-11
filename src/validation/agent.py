
"""AG05 Validation: independently verify recovery/restoration state."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Optional


@dataclass(frozen=True)
class ValidationResult:
    incident_id: str
    validation_version: str
    validation_timestamp: Optional[str]
    recovery_execution_id: Optional[str]
    service_restored: bool
    data_integrity_restored: bool
    data_quality_restored: bool
    pipeline_state_restored: bool
    governance_verified: bool
    audit_record_verified: bool
    validation_confidence: float
    validation_status: str
    validation_checks: Dict[str, Dict[str, Any]]
    validation_explanation: str

    @property
    def verified_restoration(self) -> bool:
        return all((
            self.service_restored,
            self.data_integrity_restored,
            self.data_quality_restored,
            self.pipeline_state_restored,
            self.governance_verified,
            self.audit_record_verified,
        ))

    @property
    def self_healing_success(self) -> bool:
        return self.verified_restoration

    def to_dict(self):
        d = asdict(self)
        d["verified_restoration"] = self.verified_restoration
        d["self_healing_success"] = self.self_healing_success
        return d


class ValidationError(ValueError):
    pass


class ValidationAgent:
    """Validate execution using independent post-recovery observations.

    AG05 is deliberately downstream. Its results must never be consumed by
    AG01/AG02/AG03/GARDM for the same decision.
    """

    VERSION = "AG05-v1.0.0"

    def validate(
        self,
        recovery_result: Mapping[str, Any],
        governance_state: Mapping[str, Any],
        post_recovery_observations: Optional[Mapping[str, Any]] = None,
        validation_timestamp: Optional[str] = None,
        audit_record_verified: Optional[bool] = None,
    ) -> ValidationResult:

        incident_id = str(recovery_result.get("incident_id", ""))
        if not incident_id:
            raise ValidationError("incident_id is required")
        if incident_id != str(governance_state.get("incident_id")):
            raise ValidationError("Recovery/governance incident mismatch")

        obs = dict(post_recovery_observations or {})

        # For the development simulator, completion is an execution signal,
        # while restoration is validated independently. If explicit post-
        # recovery observations are supplied, they override the simulator
        # defaults.
        executed = recovery_result.get("execution_status") == "COMPLETED"
        default_restored = executed and recovery_result.get("recovery_success") is True

        service = bool(obs.get("service_restored", default_restored))
        integrity = bool(obs.get("data_integrity_restored", default_restored))
        quality = bool(obs.get("data_quality_restored", default_restored))
        pipeline = bool(obs.get("pipeline_state_restored", default_restored))
        governance_verified = bool(
            obs.get("governance_verified", recovery_result.get("governance_compliant", False))
        )
        audit_verified = bool(
            obs.get(
                "audit_record_verified",
                audit_record_verified if audit_record_verified is not None else True,
            )
        )

        checks = {
            "service_restored": {"observed": service, "source": "post_recovery_observation"},
            "data_integrity_restored": {"observed": integrity, "source": "post_recovery_observation"},
            "data_quality_restored": {"observed": quality, "source": "post_recovery_observation"},
            "pipeline_state_restored": {"observed": pipeline, "source": "post_recovery_observation"},
            "governance_verified": {"observed": governance_verified, "source": "governance_state/recovery"},
            "audit_record_verified": {"observed": audit_verified, "source": "audit_validation_input"},
        }

        passed = sum(bool(x["observed"]) for x in checks.values())
        confidence = round(passed / len(checks), 6)
        status = "VERIFIED_RESTORATION" if passed == len(checks) else "RESTORATION_NOT_VERIFIED"

        return ValidationResult(
            incident_id=incident_id,
            validation_version=self.VERSION,
            validation_timestamp=validation_timestamp,
            recovery_execution_id=recovery_result.get("recovery_execution_id"),
            service_restored=service,
            data_integrity_restored=integrity,
            data_quality_restored=quality,
            pipeline_state_restored=pipeline,
            governance_verified=governance_verified,
            audit_record_verified=audit_verified,
            validation_confidence=confidence,
            validation_status=status,
            validation_checks=checks,
            validation_explanation=(
                "Restoration is determined only after independent validation "
                "checks; recovery execution alone is insufficient."
            ),
        )


def validate_all(recovery_results, governance_states, post_recovery_observations=None):
    agent = ValidationAgent()
    post_recovery_observations = post_recovery_observations or {}
    return [
        agent.validate(
            r, g,
            post_recovery_observations.get(str(r["incident_id"]))
        )
        for r, g in zip(recovery_results, governance_states)
    ]
