# GARDM Engine

Implements the research decision core:

`Score(A|X) = Σ w_j X_j C_ij`

with `X=[P,R,S,H,F]`.

Weights and risk threshold are loaded from `config/gardm_config.yaml`.
Compatibility coefficients are explicit development-baseline coefficients and
must be replaced/calibrated through expert elicitation before final experiments.

GARDM can only score actions that pass the AG03 governance gate.
Ground truth and post-recovery outcomes are never consumed.
