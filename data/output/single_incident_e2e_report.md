# BDP-GARDM Step 13 — Single-Incident End-to-End Trace

**Incident:** INC001
**Trace version:** E2E-v1.0.0

## Lifecycle

AG00 → Context → AG01 → AG02 → AG03 → GARDM → Recovery/HITL → AG05 → Audit/Memory

## Integration checks

- Context assembled: PASS
- Monitoring state available: PASS
- Diagnosis state available: PASS
- Governance state available: PASS
- GARDM decision available: PASS
- Recovery trace available: PASS
- Validation trace available: PASS
- Six audit events present: PASS (6)
- Audit chronology: PASS
- Decision-time leakage fields absent: PASS
- Ground truth/evaluation excluded from decision path: PASS
- Final restoration status: VERIFIED_RESTORATION
- Self-healing success: True

## GARDM decision

- Selected action: `A1.01`
- Decision confidence: `0.5`
- Risk constraint triggered: `False`
- Model version: `None`

## Recovery

- Status: `COMPLETED`
- Recovery success: `True`

## Validation

- Verified restoration: `True`
- Self-healing success: `True`

## Methodological boundary

Ground truth, evaluation results, recovery outcomes, and validation outcomes are downstream evidence and are not used to construct the same incident's decision-time GARDM input.