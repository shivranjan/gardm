# AG03 Governance/Risk

AG03 is the governance boundary between diagnosis and GARDM recovery selection.

It:
- computes a deterministic development risk score;
- assigns a risk tier using external `risk_rules` when available;
- evaluates governance/regulatory context;
- determines whether HITL is required;
- constrains candidate recovery actions;
- records provenance for risk inputs and governance outputs.

Ground truth, GARDM outputs, recovery outcomes and validation outcomes are excluded.
The implementation is a development policy baseline; final policy calibration
and empirical evaluation occur later.
