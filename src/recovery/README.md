# Step 9 — Recovery / HITL

Recovery is downstream of GARDM and AG03 governance.

The implementation:
- verifies that the selected action is governance-permitted;
- activates HITL when required;
- blocks pending/rejected approvals;
- supports an explicit safe-stop fallback on rejection;
- executes approved actions through a deterministic development simulator;
- records execution traces;
- does not claim restoration success until AG05 validation.

Recovery outcomes are never fed backward into GARDM.
