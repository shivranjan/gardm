# Step 10 — AG05 Validation

AG05 independently verifies whether a recovery execution restored the required
operational state.

Verification requires all six checks:
1. service restored
2. data integrity restored
3. data quality restored
4. pipeline state restored
5. governance verified
6. audit record verified

`verified_restoration` and `self_healing_success` are derived only here.

These outcomes are evaluation/post-recovery information and must never flow
back into the same incident's decision-time feature construction or GARDM.
