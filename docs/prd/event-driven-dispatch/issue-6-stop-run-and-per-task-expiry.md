# Stop-run and per-Task expiry

## Parent

#1 — Event-driven task dispatch (replace the Celery-canvas coercion layer)

## What to build

Replace the run-level cancellation the Celery chain used to provide. Add an explicit "stop run" operation that, under the per-Job lock, cascade-aborts all non-terminal Tasks (so neither the dispatch path nor the reconciliation sweep will enqueue them) and revokes any currently running Launches. Each dispatched Task carries its own expiry to cover the "waited in the queue too long" case. No whole-run auto-kill deadline is introduced; that chain-level behavior is dropped deliberately.

## Acceptance criteria

- [ ] An explicit stop-run operation aborts all non-terminal Tasks of a Job
- [ ] Running Launches are revoked (terminated) on stop-run
- [ ] After stop-run, no further Tasks are dispatched and the sweep does not resurrect them
- [ ] Each dispatched Task carries a per-Task expiry
- [ ] An expired Task is finalized correctly (revoked -> failed)
- [ ] Integration test: stopping a Job leaves no non-terminal Tasks and triggers no further dispatch

## Blocked by

- #4 — Event-driven dispatch behind a feature flag
