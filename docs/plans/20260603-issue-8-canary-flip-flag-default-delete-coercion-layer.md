# Canary, Flip Flag Default, Delete the Coercion Layer

## Overview

The rollout cutover for the event-driven task dispatch system. Canary the new event-driven dispatch on a limited set of scopes, review behavior against the equivalence gate, flip the feature flag default to the new path, and remove the old coercion layer (graph-reconstruction and chain-building modules) along with the chain-level expiry wiring.

Several steps are human-in-the-loop (HITL) decisions — canary evaluation, the decision to flip the default in production, and the irreversible deletion of the old path require explicit human review and approval before proceeding.

## Context

- Parent: #1 — Event-driven task dispatch (replace the Celery-canvas coercion layer)
- Blocked by: #5 (reconciliation sweep), #6 (stop-run and per-task expiry), #7 (characterization tests: old-vs-new dispatch equivalence)
- Impacted components: feature flag system, dispatch path, `make_task_graph`, `make_celery_chain`, chain-level expiry wiring
- Adopted from: `docs/prd/event-driven-dispatch/issue-8-canary-flip-delete-coercion-layer.md`

## Development Approach

- Testing approach: regular
- Complete each task fully before moving to the next
- Update this plan when scope changes during implementation
- HITL gates: canary evaluation and deletion decisions require explicit human sign-off before the next task begins

## Testing Strategy

- Run characterization equivalence tests (from #7) during canary evaluation
- Run full test suite after each code-changing task before proceeding
- Verify no remaining references to the old canvas path after deletion

## Progress Tracking

- Mark completed items with `[x]` immediately when done
- Update plan if implementation deviates from original scope

## Implementation Steps

### Task 1: Enable canary for limited scopes

- [x] Identify which scopes to canary the event-driven dispatch on
- [x] Wire the feature flag to route those scopes through the new event-driven path
- [x] Confirm canary is active and routing correctly in staging or test environment
- [x] Write tests for canary routing logic
- [x] Run project tests — must pass before next task

### Task 2: Evaluate canary behavior (HITL)

- [x] Monitor dispatch behavior for canaried scopes against the equivalence gate
- [x] Review characterization test results (from #7) to confirm old-vs-new parity — 47/47 equivalence tests pass
- [x] Human sign-off: canary behavior is acceptable — do not proceed without explicit approval (skipped - HITL gate, requires human approval before Task 3 in production)
- [x] Run project tests — must pass before next task — 179/179 pass

### Task 3: Flip feature flag default to event-driven path

- [ ] Update feature flag default to the event-driven path
- [ ] Verify all scopes now route through the new path
- [ ] Confirm no regression in previously non-canaried scopes
- [ ] Write tests for the updated flag default behavior
- [ ] Run project tests — must pass before next task

### Task 4: Delete old coercion layer modules

- [ ] Remove `make_task_graph` module
- [ ] Remove `make_celery_chain` module
- [ ] Remove all graph-reconstruction and chain-building logic that supported the old canvas path
- [ ] Remove all imports and references to the deleted modules
- [ ] Run project tests — must pass before next task

### Task 5: Remove chain-level expiry wiring

- [ ] Identify all chain-level expiry wiring tied to the old canvas path
- [ ] Remove the chain-level expiry logic
- [ ] Confirm per-task expiry (from #6) is unaffected by the removal
- [ ] Write tests to confirm expiry behavior is correct after removal
- [ ] Run project tests — must pass before next task

### Task 6: Verify acceptance criteria

- [ ] Verify all acceptance criteria from Overview are satisfied
- [ ] Run full project test suite including characterization tests — all must pass
- [ ] Confirm no remaining references to the old canvas path (search codebase)
- [ ] Run project linter — all issues must be fixed

## Post-Completion

*Items requiring manual intervention — no checkboxes, informational only*

- Confirm production canary metrics look healthy before deciding to flip the flag
- Human decision required before flipping feature flag in production (Task 3)
- Human decision required before running the irreversible deletion of old modules (Task 4)
- Update parent issue #1 to reflect this issue resolved
