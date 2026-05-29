# Canary, flip flag default, delete the coercion layer

## Parent

#1 — Event-driven task dispatch (replace the Celery-canvas coercion layer)

## What to build

The rollout cutover. Canary the new event-driven dispatch on a few scopes, review behavior against the equivalence gate, then flip the feature flag default to the new path and remove the old coercion layer (the graph-reconstruction and chain-building modules) along with the chain-level expiry wiring. This is HITL: the canary evaluation, the decision to flip the default in production, and the irreversible deletion of the old path are human calls.

## Acceptance criteria

- [ ] New dispatch canaried on a limited set of scopes and reviewed
- [ ] Feature flag default flipped to the event-driven path
- [ ] Old graph-coercion modules (make_task_graph, make_celery_chain) removed
- [ ] Chain-level expiry wiring removed
- [ ] Full test suite (including characterization tests) green after deletion
- [ ] No remaining references to the old canvas path

## Blocked by

- #5 — Reconciliation sweep for stalled dispatch
- #6 — Stop-run and per-Task expiry
- #7 — Characterization tests: old-vs-new dispatch equivalence
