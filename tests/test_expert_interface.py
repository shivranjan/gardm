
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from expert.interface import synthetic_weight_responses, aggregate_weights, CompatibilityResponse, aggregate_compatibility

def test_synthetic_responses_are_development_only():
    rows = synthetic_weight_responses()
    assert len(rows) == 25
    assert all(r.provider == "synthetic" and r.development_only for r in rows)

def test_aggregated_weights_sum_to_one():
    weights = aggregate_weights(synthetic_weight_responses())
    assert set(weights) == {"w_P", "w_R", "w_S", "w_H", "w_F"}
    assert abs(sum(weights.values()) - 1.0) < 1e-6

def test_compatibility_aggregation():
    rows = [
        CompatibilityResponse("E1", "F001", "A01", .8, .9, "r"),
        CompatibilityResponse("E2", "F001", "A01", .6, .8, "r"),
    ]
    assert aggregate_compatibility(rows)["F001|A01"] == .7

def test_invalid_weight_rejected():
    rows = synthetic_weight_responses()
    from dataclasses import replace
    rows[0] = replace(rows[0], value=1.5)
    try:
        aggregate_weights(rows)
    except ValueError:
        return
    assert False
