
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from validation.agent import ValidationAgent, ValidationError, validate_all

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / "data/interim" / name).read_text())


def test_single_validation():
    r = load("recovery_results.json")[0]
    g = load("governance_states.json")[0]
    v = ValidationAgent().validate(r, g)
    assert v.incident_id == r["incident_id"]
    assert 0 <= v.validation_confidence <= 1
    assert v.verified_restoration is True
    assert v.self_healing_success is True


def test_all_100_validations():
    rs, gs = load("recovery_results.json"), load("governance_states.json")
    vs = validate_all(rs, gs)
    assert len(vs) == 100
    assert len({v.incident_id for v in vs}) == 100


def test_failed_post_recovery_observation():
    r = load("recovery_results.json")[0]
    g = load("governance_states.json")[0]
    v = ValidationAgent().validate(
        r, g,
        {"service_restored": True, "data_integrity_restored": False,
         "data_quality_restored": True, "pipeline_state_restored": True,
         "governance_verified": True, "audit_record_verified": True},
    )
    assert v.verified_restoration is False
    assert v.validation_status == "RESTORATION_NOT_VERIFIED"


def test_all_checks_required():
    r = load("recovery_results.json")[0]
    g = load("governance_states.json")[0]
    v = ValidationAgent().validate(r, g)
    assert v.verified_restoration == all([
        v.service_restored,
        v.data_integrity_restored,
        v.data_quality_restored,
        v.pipeline_state_restored,
        v.governance_verified,
        v.audit_record_verified,
    ])


def test_mismatched_incident_rejected():
    r = load("recovery_results.json")[0]
    g = dict(load("governance_states.json")[1])
    try:
        ValidationAgent().validate(r, g)
    except ValidationError:
        return
    raise AssertionError("Validation accepted mismatched incidents")


def test_deterministic():
    r = load("recovery_results.json")[0]
    g = load("governance_states.json")[0]
    a = ValidationAgent().validate(r, g).to_dict()
    b = ValidationAgent().validate(r, g).to_dict()
    assert a == b
