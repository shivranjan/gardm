from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[1]
def test_pilot_100_summary():
    s=json.loads((ROOT/"data/output/pilot_100_run_summary.json").read_text())
    assert s["incidents"]==100
    assert all(v==100 for v in s["stage_counts"].values())
    assert s["audit_records"]==600 and s["memory_records"]==100
    assert all(s["checks"].values())
def test_pilot_boundary():
    s=json.loads((ROOT/"data/output/pilot_100_run_summary.json").read_text())
    assert s["methodological_status"]["pilot_not_for_final_empirical_claims"]
    assert s["methodological_status"]["synthetic_expert_responses_are_development_only"]
