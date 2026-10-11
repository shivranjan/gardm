# BDP-GARDM Schema Contracts — v1.0.0

These contracts were generated directly from the supplied BDP-GARDM-v0.3 pilot archive.

## Scope
- 32 CSV tables
- 100 pilot incidents
- 80 historical incidents
- 27 fault types
- 13 candidate recovery actions
- 3 approaches represented in the pilot evaluation traces

## Leakage control
Ground-truth and post-outcome fields are explicitly marked as `evaluation_or_ground_truth_only`.
They must not be included in decision-time feature construction.

Historical incidents are marked `historical_only`; they may contribute to the H component only when their timestamps precede the current incident.

## Next implementation step
Build AG00 ingestion and validation against these contracts. The ingestion layer should report violations and never silently repair research-critical values.
