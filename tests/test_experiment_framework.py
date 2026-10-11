
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from experiments.runner import ExperimentRunner, RuleBasedBaseline, RandomForestBaseline, GARDMBaseline
from experiments.metrics import recovery_accuracy, governance_compliance, self_healing_rate, mean_mttr


def test_experiment_ids_are_deterministic():
    a = ExperimentRunner.make_experiment_id("gardm", "S01", "dev", 1, 42)
    b = ExperimentRunner.make_experiment_id("gardm", "S01", "dev", 1, 42)
    assert a == b


def test_manifest_has_one_row_per_approach_scenario():
    r = ExperimentRunner(seed=42)
    rows = r.manifest(
        ["rule_based", "rf", "gardm"],
        [{"scenario_id": "S01", "fault_category": "network", "topology_id": "T01"},
         {"scenario_id": "S02", "fault_category": "data", "topology_id": "T02"}],
        "dev",
    )
    assert len(rows) == 6
    assert len({x.experiment_id for x in rows}) == 6


def test_baseline_contracts():
    context = {"incident_id": "INC001", "selected_action": "A01",
               "decision_confidence": .8, "model_version": "G-v1"}
    assert GARDMBaseline().predict(context).predicted_action == "A01"
    assert RuleBasedBaseline().predict({"incident_id": "INC001", "selected_action_reference": "A02"}).predicted_action == "A02"
    try:
        RandomForestBaseline().predict(context)
    except RuntimeError:
        return
    assert False


def test_metrics():
    rows = [
        {"action_correct": True, "governance_compliance": True, "self_healing_success": True, "mttr_sec": 10},
        {"action_correct": False, "governance_compliance": True, "self_healing_success": False, "mttr_sec": 20},
    ]
    assert recovery_accuracy(rows) == .5
    assert governance_compliance(rows) == 1.0
    assert self_healing_rate(rows) == .5
    assert mean_mttr(rows) == 15
