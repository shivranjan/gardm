from pathlib import Path
import json

from src.ingestion.pipeline import run_ingestion
from src.context.assembler import IncidentContextAssembler

def _load():
    tables, report = run_ingestion(Path("data/raw"), Path("schemas"))
    assert report.passed, report.to_dict()
    return tables

def test_single_incident_context_is_decision_time_safe():
    tables = _load()
    incident_id = tables["incident_context"]["incident_id"].dropna().iloc[0]
    context = IncidentContextAssembler(tables).assemble(incident_id)
    payload = context.to_dict()
    assert payload["incident_id"] == str(incident_id)
    assert "ground_truth_decisions" not in payload
    assert "evaluation_results" not in payload
    serialized = json.dumps(payload, default=str).lower()
    assert "ground_truth_action" not in serialized
    assert "recovery_success" not in serialized

def test_all_pilot_incidents_assemble():
    tables = _load()
    contexts = IncidentContextAssembler(tables).assemble_all()
    assert len(contexts) == tables["incident_context"]["incident_id"].nunique()

def test_historical_context_is_temporally_restricted():
    tables = _load()
    assembler = IncidentContextAssembler(tables)
    contexts = assembler.assemble_all()
    current = tables["incident_context"].set_index("incident_id")
    hist = tables["historical_incidents"]
    ts_col = next((c for c in hist.columns if "timestamp" in c.lower()), None)
    if ts_col and not hist.empty:
        hist_ts = __import__("pandas").to_datetime(hist[ts_col], errors="coerce")
        current_ts_col = next((c for c in current.columns if "timestamp" in c.lower()), None)
        if current_ts_col:
            for c in contexts:
                cur_ts = __import__("pandas").to_datetime(current.loc[c.incident_id][current_ts_col], errors="coerce")
                for h in c.historical:
                    hts = __import__("pandas").to_datetime(h.get(ts_col), errors="coerce")
                    if not __import__("pandas").isna(hts) and not __import__("pandas").isna(cur_ts):
                        assert hts < cur_ts

def test_evaluation_only_fields_are_stripped():
    tables = _load()
    contexts = IncidentContextAssembler(tables).assemble_all()
    import json
    serialized = json.dumps([c.to_dict() for c in contexts], default=str).lower()
    for term in [
        "ground_truth_action", "action_correct", "recovery_success",
        "verified_restoration", "diagnosis_success", "detection_success",
        "validation_status"
    ]:
        assert term not in serialized
