# AG01 Monitoring

**Version:** AG01-v1.0.0

AG01 transforms the decision-time `IncidentContext` into a deterministic
`MonitoringState`.

## Design constraints

- No direct access to raw CSV tables.
- No diagnosis outputs.
- No GARDM decisions or selected actions.
- No ground-truth decisions.
- No recovery/validation outcomes.
- Raw observed values are preserved separately from normalized health indicators.
- Every derived feature carries provenance.
- `monitoring_confidence` is a development-time observation-completeness heuristic,
  not an expert probability and not diagnosis confidence.
- Fault/injection identifiers are retained only as environment metadata and are
  not converted into diagnosis/action-selection features.

## Flow

`IncidentContext -> AG01 Monitoring -> MonitoringState -> AG02 Diagnosis`

The implementation is deterministic: identical input context produces identical
output.
