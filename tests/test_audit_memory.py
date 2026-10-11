
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from audit.ledger import AuditLedger, MemoryStore


def test_audit_chain_integrity():
    ledger = AuditLedger()
    ledger.append("INC001", "E1", "AG01", "monitor", "OBSERVE",
                   "monitoring", "PASS", "LOW", "OBSERVED",
                   "Monitoring completed", "2026-01-01T00:00:01")
    ledger.append("INC001", "E2", "GARDM", "gardm", "DECIDE",
                   "governance", "PASS", "MEDIUM", "SELECT",
                   "Governed action selected", "2026-01-01T00:00:02")
    assert ledger.verify() is True
    assert ledger.records[1].previous_hash == ledger.records[0].current_hash


def test_audit_tamper_detection():
    ledger = AuditLedger()
    ledger.append("INC001", "E1", "AG01", "monitor", "OBSERVE",
                   "monitoring", "PASS", "LOW", "OBSERVED",
                   "Monitoring completed", "2026-01-01T00:00:01")
    record = ledger.records[0]
    object.__setattr__(record, "decision", "TAMPERED")
    assert ledger.verify() is False


def test_memory_temporal_filter():
    store = MemoryStore()
    store.add({"incident_id": "H1", "incident_timestamp": "2026-01-01T00:00:00",
               "fault_code": "F001"})
    store.add({"incident_id": "H2", "incident_timestamp": "2026-02-01T00:00:00",
               "fault_code": "F002"})
    store.add({"incident_id": "FUTURE", "incident_timestamp": "2026-05-01T00:00:00",
               "fault_code": "F003"})
    prior = store.retrieve_prior("2026-03-01T00:00:00")
    assert [x.incident_id for x in prior] == ["H2", "H1"]


def test_memory_limit():
    store = MemoryStore()
    for i in range(5):
        store.add({"incident_id": f"H{i}", "incident_timestamp": f"2026-01-0{i+1}T00:00:00"})
    assert len(store.retrieve_prior("2026-02-01T00:00:00", limit=2)) == 2
