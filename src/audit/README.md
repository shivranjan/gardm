# Step 11 — Audit + Memory

## Audit
`AuditLedger` creates a hash-linked, append-only audit chain. Each record stores
the previous hash and a SHA-256 hash of its canonical contents.

## Memory
`MemoryStore` stores validated historical incident summaries. Retrieval is
strictly temporal: only memories with timestamps earlier than the current
incident are eligible.

Memory is contextual evidence, not ground truth, and never mutates a completed
decision.
