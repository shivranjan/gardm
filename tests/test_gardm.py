
import json
from pathlib import Path
import sys
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gardm.engine import GARDMEngine, GARDMError, decide_all

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / "data/interim" / name).read_text())


def actions():
    return pd.read_csv(ROOT / "data/raw/candidate_recovery_actions.csv").to_dict("records")


def test_single_gardm():
    m, d, g = load("monitoring_states.json")[0], load("diagnosis_states.json")[0], load("governance_states.json")[0]
    e = GARDMEngine(ROOT / "config/gardm_config.yaml")
    r = e.decide(m, d, g, actions())
    assert r.incident_id == m["incident_id"]
    assert abs(sum(r.weights.values()) - 1.0) < 1e-9
    assert 0 <= r.decision_confidence <= 1


def test_all_100_decisions():
    ms, ds, gs = load("monitoring_states.json"), load("diagnosis_states.json"), load("governance_states.json")
    rs = decide_all(ms, ds, gs, actions(), ROOT / "config/gardm_config.yaml")
    assert len(rs) == 100
    assert len({r.incident_id for r in rs}) == 100


def test_score_formula_exact():
    m, d, g = load("monitoring_states.json")[0], load("diagnosis_states.json")[0], load("governance_states.json")[0]
    e = GARDMEngine(ROOT / "config/gardm_config.yaml")
    features = e.build_features(m, d, g)
    comp, scores = e.score_actions(features, actions(), g)
    for aid, c in comp.items():
        expected = round(sum(e.weights[f] * features[f] * c[f] for f in ("P","R","S","H","F")), 6)
        assert scores[aid] == expected


def test_weights_are_externalized():
    cfg = yaml.safe_load((ROOT / "config/gardm_config.yaml").read_text())
    e = GARDMEngine(ROOT / "config/gardm_config.yaml")
    assert e.weights == cfg["gardm"]["feature_weights"]


def test_only_permitted_actions_are_scored():
    m, d, g = load("monitoring_states.json")[0], load("diagnosis_states.json")[0], load("governance_states.json")[0]
    e = GARDMEngine(ROOT / "config/gardm_config.yaml")
    r = e.decide(m, d, g, actions())
    assert set(r.action_scores).issubset(set(g["permitted_action_ids"]))


def test_downstream_field_rejected():
    m, d, g = load("monitoring_states.json")[0], load("diagnosis_states.json")[0], load("governance_states.json")[0]
    d["ground_truth_action"] = "A1"
    try:
        GARDMEngine(ROOT / "config/gardm_config.yaml").decide(m, d, g, actions())
    except GARDMError:
        pass
    else:
        raise AssertionError("GARDM accepted ground truth")


def test_deterministic():
    m, d, g = load("monitoring_states.json")[0], load("diagnosis_states.json")[0], load("governance_states.json")[0]
    e = GARDMEngine(ROOT / "config/gardm_config.yaml")
    assert e.decide(m, d, g, actions()).to_dict() == e.decide(m, d, g, actions()).to_dict()
