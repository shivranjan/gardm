from pathlib import Path
from src.common.config import load_config

def test_config_loads():
    cfg = load_config(Path("config/gardm_config.yaml"))
    assert cfg["project"]["name"] == "BDP-GARDM"

def test_gardm_weights_sum_to_one():
    cfg = load_config(Path("config/gardm_config.yaml"))
    weights = cfg["gardm"]["feature_weights"]
    assert abs(sum(weights.values()) - 1.0) < 1e-9

def test_risk_threshold():
    cfg = load_config(Path("config/gardm_config.yaml"))
    assert 0 <= cfg["gardm"]["risk_threshold"] <= 1
