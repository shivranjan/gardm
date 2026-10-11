# Step 15 — Experiment Runner + Baseline Contracts

This step establishes the reproducible experimental framework.

## Final dataset design
- 5,000 development incidents
- 2,000 validation incidents
- 3,000 locked test incidents
- scenario-based splits
- untouched test set
- unseen-topology evaluation

## Baselines
- deterministic Rule-Based
- Random Forest (interface only; must be trained/frozen later)
- GARDM

## Important boundary
The existing 100-incident pilot is not final empirical evidence. Step 15 creates
the experiment contracts and manifest generator; it does not train the final RF,
create the final 10,000-incident dataset, or report hypothesis-supporting results.

## Ablations
The framework reserves controlled ablations for:
- historical memory H
- governance filtering
- fault/action compatibility
- risk/HITL constraints
