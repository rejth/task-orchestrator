# Characterization Tests: Old-vs-New Dispatch Equivalence

## Overview

Build an equivalence test gate that proves the new event-driven dispatch is behaviorally equivalent to the old Celery-canvas path before the old layer is removed. Tests run representative scopes through both dispatch paths and assert that the new path dispatches the same set of Tasks and honors the same happens-before (dependency) relationships as the old path.

Tests assert observable orchestration behavior only, not internal structure, so they remain valid after the coercion code is deleted.

## Context

- Part of #1 — Event-driven task dispatch (replace the Celery-canvas coercion layer)
- Blocked by #4 — Event-driven dispatch behind a feature flag
- Existing linear and parallel graph fixtures serve as the oracle
- Adopted from `docs/prd/event-driven-dispatch/issue-7-characterization-equivalence-tests.md`

## Development Approach

- Testing approach: characterization / equivalence testing
- Complete each task fully before moving to the next
- Update this plan when scope changes during implementation

## Testing Strategy

- Tests must assert observable behavior (dispatched task set + dependency ordering), not internal structure
- Tests must survive deletion of graph-coercion code
- Run project tests after each task before proceeding

## Progress Tracking

- Mark completed items with `[x]` immediately when done
- Update plan if implementation deviates from original scope

## Implementation Steps

### Task 1: Reuse existing fixtures and set up equivalence test harness

- [x] Locate existing linear and parallel graph fixtures in the test suite
- [x] Define a test harness that can run a graph through both the old Celery-canvas path and the new event-driven path
- [x] Capture dispatched Task sets and happens-before relationships from each path in a comparable form
- [x] Write tests for the harness itself (fixture loading, output capture)
- [x] run project tests - must pass before next task

### Task 2: Implement equivalence assertions for linear graph scopes

- [x] Run representative linear graph fixtures through both dispatch paths
- [x] Assert that the set of dispatched Tasks matches between old and new for linear graphs
- [x] Assert that all dependency (happens-before) relationships are preserved by the new path for linear graphs
- [x] Write tests covering edge cases (single-node graph, chain of length >1)
- [x] run project tests - must pass before next task

### Task 3: Implement equivalence assertions for parallel graph scopes

- [x] Run representative parallel graph fixtures through both dispatch paths
- [x] Assert that the set of dispatched Tasks matches between old and new for parallel graphs
- [x] Assert that all happens-before relationships are preserved for parallel graphs (fan-out, fan-in)
- [x] Write tests covering edge cases (diamond dependency, sibling parallelism)
- [x] run project tests - must pass before next task

### Task 4: Verify acceptance criteria

- [ ] Verify equivalence tests run representative scopes through both dispatch paths
- [ ] Verify the set of dispatched Tasks matches between old and new paths in all covered scopes
- [ ] Verify all dependency (happens-before) relationships are preserved by the new path
- [ ] Verify existing linear and parallel graph fixtures are reused as the oracle
- [ ] Verify tests assert behavior only and survive deletion of graph-coercion code (review for internal-structure coupling)
- [ ] run full project test suite
- [ ] run project linter - all issues must be fixed

## Post-Completion

- Coordinate with #4 (feature flag) before enabling the new dispatch path in production
- After old coercion layer is deleted, confirm tests still pass without modification
