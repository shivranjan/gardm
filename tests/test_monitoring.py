
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from context.assembler import IncidentContextAssembler
from monitoring.agent import MonitoringAgent, FORBIDDEN_FIELDS, build_all


ROOT = Path(__file__).resolve().parents[1]


def load_contexts():
    return json.loads((ROOT / "data/interim/incident_contexts.json").read_text())


def test_single_incident_monitoring_state():
    contexts = load_contexts()
    state = MonitoringAgent().build(contexts[0])
    assert state.incident_id == contexts[0]["incident_id"]
    assert state.monitoring_version == "AG01-v1.0.0"
    assert 0 <= state.monitoring_confidence <= 1
    assert "detection_latency_sec" in state.feature_provenance


def test_all_100_monitoring_states():
    states = build_all(load_contexts())
    assert len(states) == 100
    assert len({s.incident_id for s in states}) == 100


def test_no_downstream_fields_in_observed_features():
    states = build_all(load_contexts())
    forbidden_lower = {x.lower() for x in FORBIDDEN_FIELDS}
    for state in states:
        payload = json.dumps(state.to_dict()).lower()
        for field in forbidden_lower:
            assert field not in state.observed
            # Check keys, not arbitrary text values.
        assert "predicted_fault_code" not in state.observed
        assert "ground_truth_action" not in state.observed
        assert "selected_action" not in state.observed


def test_provenance_matches_features():
    states = build_all(load_contexts())
    for state in states:
        for feature, meta in state.feature_provenance.items():
            assert meta["source"] == "incident_context"
            assert "field" in meta


def test_deterministic():
    contexts = load_contexts()
    agent = MonitoringAgent()
    a = agent.build(contexts[0]).to_dict()
    b = agent.build(contexts[0]).to_dict()
    assert a == b


def test_downstream_input_rejected():
    contexts = load_contexts()
    bad = dict(contexts[0])
    bad["selected_action"] = "RECOVERY_A1"
    try:
        MonitoringAgent().build(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("AG01 accepted a downstream action field")
