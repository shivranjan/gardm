
"""Step 11: append-only audit trail and reusable historical memory."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional
import hashlib
import json


@dataclass(frozen=True)
class AuditRecord:
    audit_id: str
    incident_id: str
    event_id: str
    actor_type: str
    actor_id: str
    action: str
    policy_evaluated: str
    policy_result: str
    risk_assessment: str
    decision: str
    justification: str
    timestamp: str
    previous_hash: str
    current_hash: str
    audit_integrity_status: str

    def to_dict(self):
        return asdict(self)


class AuditError(ValueError):
    pass


class AuditLedger:
    """Deterministic hash-linked audit ledger."""

    VERSION = "AUDIT-v1.0.0"

    def __init__(self):
        self.records: List[AuditRecord] = []

    @staticmethod
    def _hash(payload: Mapping[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def append(
        self,
        incident_id: str,
        event_id: str,
        actor_type: str,
        actor_id: str,
        action: str,
        policy_evaluated: str,
        policy_result: str,
        risk_assessment: str,
        decision: str,
        justification: str,
        timestamp: str,
    ) -> AuditRecord:
        audit_id = f"AUD-{len(self.records)+1:06d}"
        previous_hash = self.records[-1].current_hash if self.records else "GENESIS"

        base = {
            "audit_id": audit_id,
            "incident_id": str(incident_id),
            "event_id": str(event_id),
            "actor_type": str(actor_type),
            "actor_id": str(actor_id),
            "action": str(action),
            "policy_evaluated": str(policy_evaluated),
            "policy_result": str(policy_result),
            "risk_assessment": str(risk_assessment),
            "decision": str(decision),
            "justification": str(justification),
            "timestamp": str(timestamp),
            "previous_hash": previous_hash,
        }
        current_hash = self._hash(base)

        record = AuditRecord(
            **base,
            current_hash=current_hash,
            audit_integrity_status="VALID",
        )
        self.records.append(record)
        return record

    def verify(self) -> bool:
        previous = "GENESIS"
        for record in self.records:
            base = {
                "audit_id": record.audit_id,
                "incident_id": record.incident_id,
                "event_id": record.event_id,
                "actor_type": record.actor_type,
                "actor_id": record.actor_id,
                "action": record.action,
                "policy_evaluated": record.policy_evaluated,
                "policy_result": record.policy_result,
                "risk_assessment": record.risk_assessment,
                "decision": record.decision,
                "justification": record.justification,
                "timestamp": record.timestamp,
                "previous_hash": previous,
            }
            if record.previous_hash != previous:
                return False
            if record.current_hash != self._hash(base):
                return False
            previous = record.current_hash
        return True

    def export(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self.records]


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    incident_id: str
    fault_code: Optional[str]
    fault_category: Optional[str]
    pipeline_criticality: Optional[str]
    severity: Optional[str]
    risk_tier: Optional[str]
    selected_action: Optional[str]
    recovery_success: Optional[bool]
    recovery_time_sec: Optional[float]
    governance_compliance: Optional[bool]
    verified_restoration: Optional[bool]
    incident_timestamp: Optional[str]
    source: str
    memory_version: str

    def to_dict(self):
        return asdict(self)


class MemoryStore:
    """Stores historical incident summaries for future context retrieval.

    Memory is explicitly historical and is only eligible for incidents whose
    timestamp precedes the current incident. It does not mutate prior decisions.
    """

    VERSION = "MEMORY-v1.0.0"

    def __init__(self):
        self.records: List[MemoryRecord] = []

    def add(self, record: Mapping[str, Any]) -> MemoryRecord:
        memory_id = f"MEM-{len(self.records)+1:06d}"
        out = MemoryRecord(
            memory_id=memory_id,
            incident_id=str(record.get("incident_id")),
            fault_code=record.get("fault_code"),
            fault_category=record.get("fault_category"),
            pipeline_criticality=record.get("pipeline_criticality"),
            severity=record.get("severity"),
            risk_tier=record.get("risk_tier"),
            selected_action=record.get("selected_action"),
            recovery_success=record.get("recovery_success"),
            recovery_time_sec=record.get("recovery_time_sec"),
            governance_compliance=record.get("governance_compliance"),
            verified_restoration=record.get("verified_restoration"),
            incident_timestamp=record.get("incident_timestamp"),
            source="validated_historical_incident",
            memory_version=self.VERSION,
        )
        self.records.append(out)
        return out

    def retrieve_prior(self, current_timestamp: str, limit: int = 20) -> List[MemoryRecord]:
        """Return only memories strictly earlier than the current incident."""
        current = str(current_timestamp)
        eligible = [
            r for r in self.records
            if r.incident_timestamp is not None
            and str(r.incident_timestamp) < current
        ]
        eligible.sort(key=lambda r: str(r.incident_timestamp), reverse=True)
        return eligible[:limit]

    def export(self):
        return [r.to_dict() for r in self.records]
