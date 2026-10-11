# AG02 Diagnosis

AG02 consumes only `AG01 MonitoringState`.

The pilot implementation is a deterministic development baseline. It uses
transparent symptom rules rather than a trained ML model. This is intentional:
the final empirical experiment will freeze the diagnosis method separately.

Leakage controls:
- no ground-truth decisions
- no GARDM decisions
- no recovery outcomes
- no validation outcomes
- no post-recovery fields

`diagnosis_success` is deliberately `None` at decision time; evaluation code
will compare the prediction against independent ground truth later.
