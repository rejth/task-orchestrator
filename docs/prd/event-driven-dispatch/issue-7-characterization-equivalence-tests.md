# Characterization tests: old-vs-new dispatch equivalence

## Parent

#1 — Event-driven task dispatch (replace the Celery-canvas coercion layer)

## What to build

An equivalence test gate that proves the new event-driven dispatch is behaviorally equivalent to the old Celery-canvas path before the old layer is removed. Reuse the existing linear and parallel graph fixtures as the oracle: for representative scopes, assert that the new path dispatches the same set of Tasks and honors the same happens-before (dependency) relationships as the old path. These tests assert observable orchestration behavior, not internal structure, so they remain valid after the coercion code is deleted.

## Acceptance criteria

- [ ] Equivalence tests run representative scopes through both dispatch paths
- [ ] The set of dispatched Tasks matches between old and new
- [ ] All dependency (happens-before) relationships are preserved by the new path
- [ ] Existing linear and parallel graph fixtures are reused as the oracle
- [ ] Tests assert behavior only and survive deletion of the graph-coercion code

## Blocked by

- #4 — Event-driven dispatch behind a feature flag
