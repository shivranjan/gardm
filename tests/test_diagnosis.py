
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from diagnosis.agent import DiagnosisAgent, diagnose_all, DiagnosisError


ROOT = Path(__file__).resolve().parents[1]


def load_monitoring():
    return json.loads((ROOT / "data/interim/monitoring_states.json").read_text())


def test_single_diagnosis():
    states = load_monitoring()
    result = DiagnosisAgent().diagnose(states[0])
    assert result.incident_id == states[0]["incident_id"]
    assert result.diagnosis_version == "AG02-v1.0.0"
    assert result.predicted_fault_code
    assert 0 <= result.diagnosis_confidence <= 1
    assert result.diagnosis_success is None


def test_all_100_diagnoses():
    results = diagnose_all(load_monitoring())
    assert len(results) == 100
    assert len({x.incident_id for x in results}) == 100


def test_diagnosis_uses_ag01_only():
    states = load_monitoring()
    result = DiagnosisAgent().diagnose(states[0])
    for meta in result.feature_provenance.values():
        assert meta["source"] == "AG01.MonitoringState"


def test_downstream_payload_rejected():
    states = load_monitoring()
    bad = dict(states[0])
    bad["selected_action"] = "A1"
    try:
        DiagnosisAgent().diagnose(bad)
    except DiagnosisError:
        pass
    else:
        raise AssertionError("AG02 accepted a downstream field")


def test_deterministic():
    state = load_monitoring()[0]
    agent = DiagnosisAgent()
    assert agent.diagnose(state).to_dict() == agent.diagnose(state).to_dict()
