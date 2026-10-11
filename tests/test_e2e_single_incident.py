
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

ROOT = Path(__file__).resolve().parents[1]

def test_single_incident_trace_exists_and_is_complete():
    p = ROOT / "data/output/single_incident_e2e_trace.json"
    trace = json.loads(p.read_text())
    assert trace["trace_version"] == "E2E-v1.0.0"
    assert trace["incident_id"]
    assert trace["decision_time_inputs"]["context"]
    assert trace["decision"]
    assert trace["recovery"]
    assert trace["validation"]
    assert len(trace["audit_events"]) == 6

def test_decision_time_trace_has_no_outcome_leakage():
    trace = json.loads((ROOT / "data/output/single_incident_e2e_trace.json").read_text())
    forbidden = {
        "ground_truth_action", "action_correct", "recovery_success",
        "verified_restoration", "diagnosis_success", "detection_success",
        "service_restored", "data_integrity_restored", "data_quality_restored",
        "pipeline_state_restored", "governance_verified",
        "audit_record_verified", "validation_status"
    }
    assert not (set(trace["decision_time_inputs"]["context"]) & forbidden)

def test_audit_stage_order():
    trace = json.loads((ROOT / "data/output/single_incident_e2e_trace.json").read_text())
    assert [x["event_id"].split("-")[-1] for x in trace["audit_events"]] == [
        "MON", "DIA", "GOV", "GDM", "REC", "VAL"
    ]
