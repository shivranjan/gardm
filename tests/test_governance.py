
import json
from pathlib import Path
import sys
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from governance.agent import GovernanceAgent, GovernanceError, evaluate_all

ROOT = Path(__file__).resolve().parents[1]


def load_json(name):
    return json.loads((ROOT / "data/interim" / name).read_text())


def policies(name):
    return pd.read_csv(ROOT / "data/raw" / f"{name}.csv").to_dict("records")


def test_single_governance():
    m = load_json("monitoring_states.json")[0]
    d = load_json("diagnosis_states.json")[0]
    g = GovernanceAgent().evaluate(
        m, d,
        policies("governance_policies"),
        policies("regulatory_constraints"),
        policies("candidate_recovery_actions"),
        policies("risk_rules"),
        policies("hitl_policies"),
    )
    assert g.incident_id == m["incident_id"]
    assert 0 <= g.risk_score <= 1
    assert g.risk_tier in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert isinstance(g.hitl_required, bool)


def test_all_100_governance_states():
    ms = load_json("monitoring_states.json")
    ds = load_json("diagnosis_states.json")
    gs = evaluate_all(
        ms, ds,
        policies("governance_policies"),
        policies("regulatory_constraints"),
        policies("candidate_recovery_actions"),
        policies("risk_rules"),
        policies("hitl_policies"),
    )
    assert len(gs) == 100
    assert len({g.incident_id for g in gs}) == 100


def test_governance_provenance():
    m = load_json("monitoring_states.json")[0]
    d = load_json("diagnosis_states.json")[0]
    g = GovernanceAgent().evaluate(m, d)
    assert all(x["source"].startswith("AG01") or x["source"].startswith("AG03")
               for x in g.feature_provenance.values())


def test_downstream_fields_rejected():
    m = load_json("monitoring_states.json")[0]
    d = load_json("diagnosis_states.json")[0]
    d["selected_action"] = "A1"
    try:
        GovernanceAgent().evaluate(m, d)
    except GovernanceError:
        pass
    else:
        raise AssertionError("AG03 accepted a downstream action field")


def test_deterministic():
    m = load_json("monitoring_states.json")[0]
    d = load_json("diagnosis_states.json")[0]
    a = GovernanceAgent().evaluate(m, d).to_dict()
    b = GovernanceAgent().evaluate(m, d).to_dict()
    assert a == b
