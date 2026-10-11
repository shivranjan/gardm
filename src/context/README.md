# Step 4 — Incident/Context Assembly

The context builder creates the decision-time input for AG01.

## Design principles

- One `IncidentContext` per pilot incident.
- Only decision-time information is assembled.
- Ground truth and post-outcome tables are excluded.
- Historical evidence is restricted to records strictly earlier than the current incident.
- Candidate actions and governance/risk references are included without applying the decision itself.
- Context construction is deterministic and versioned.

The next stage, AG01, should consume `IncidentContext` objects rather than raw tables.
