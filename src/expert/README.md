# Step 12 — Synthetic Expert Interface

This module provides the development interface/schema for expert elicitation.

## Important methodological boundary

The bundled responses are **synthetic development fixtures only**. They are
not real expert evidence and must not be reported as expert elicitation.

The interface supports:
- GARDM weight responses
- confidence and rationale capture
- deterministic aggregation
- fault/action compatibility responses
- compatibility aggregation

For the final study, real expert responses should replace the synthetic
fixtures. Final parameters should then be calibrated using development/
validation data only and frozen before the untouched test experiment.
