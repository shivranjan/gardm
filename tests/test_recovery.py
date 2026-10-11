
import json
from pathlib import Path
import sys
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from recovery.agent import RecoveryAgent, RecoveryError, execute_all

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / "data/interim" / name).read_text())


def actions():
    return pd.read_csv(ROOT / "data/raw/candidate_recovery_actions.csv").to_dict("records")


def test_single_recovery():
    d = load("gardm_decisions.json")[0]
    g = load("governance_states.json")[0]
    result = RecoveryAgent().execute(d, g, actions(), approved=True)
    assert result.incident_id == d["incident_id"]
    assert result.governance_compliant is True
    assert result.execution_status in {"COMPLETED", "NOT_EXECUTED", "NO_ACTION"}


def test_all_100_recovery_records():
    ds, gs = load("gardm_decisions.json"), load("governance_states.json")
    results = execute_all(ds, gs, actions())
    assert len(results) == 100
    assert len({r.incident_id for r in results}) == 100


def _hitl_case():
    ds, gs = load("gardm_decisions.json"), load("governance_states.json")
    for d, g in zip(ds, gs):
        if g["hitl_required"] and d["selected_action"]:
            return d, g

    # Controlled unit-test fixture: does not modify pilot data.
    d = dict(ds[0])
    g = dict(gs[0])
    selected = d["selected_action"]
    assert selected in g["permitted_action_ids"]
    g["hitl_required"] = True
    g["risk_tier"] = "HIGH"
    g["hitl_reason"] = "unit-test HITL fixture"
    return d, g


def test_higher_risk_requires_approval():
    d, g = _hitl_case()
    r = RecoveryAgent().execute(d, g, actions(), approved=None)
    assert r.hitl_activated is True
    assert r.approval_status == "PENDING"
    assert r.execution_status == "NOT_EXECUTED"


def test_rejected_higher_risk_safe_stops():
    d, g = _hitl_case()
    r = RecoveryAgent().execute(d, g, actions(), approved=False)
    assert r.approval_status == "REJECTED"
    assert r.fallback_action == "SAFE_STOP"
    assert r.execution_status == "NOT_EXECUTED"


def test_non_permitted_action_rejected():
    ds, gs = load("gardm_decisions.json"), load("governance_states.json")
    d = dict(ds[0])
    g = dict(gs[0])
    permitted = set(g["permitted_action_ids"])
    all_actions = [str(x["action_id"]) for x in actions()]
    blocked = next((a for a in all_actions if a not in permitted), None)
    if blocked:
        d["selected_action"] = blocked
        try:
            RecoveryAgent().execute(d, g, actions(), approved=True)
        except RecoveryError:
            return
        raise AssertionError("Recovery accepted non-permitted action")


def test_outcome_is_not_verified_restoration():
    d = load("gardm_decisions.json")[0]
    g = load("governance_states.json")[0]
    r = RecoveryAgent().execute(d, g, actions(), approved=True)
    assert "verified_restoration" not in r.to_dict()
