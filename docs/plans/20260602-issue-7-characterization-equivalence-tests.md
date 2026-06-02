# Characterization Tests: Old-vs-New Dispatch Equivalence

## Overview

Build an equivalence test gate that proves the new event-driven dispatch is behaviorally equivalent to the old Celery-canvas path before the old layer is removed. Tests run representative scopes through both dispatch paths and assert that the new path dispatches the same set of Tasks and honors the same happens-before (dependency) relationships as the old path.

Tests assert observable orchestration behavior only, not internal structure.

NOTE: `test_dispatch_equivalence.py` is intentionally a temporary characterization harness. The canvas-dependent classes (`TestCanvasOutputCapture`, `TestLinearEquivalence`, `TestParallelEquivalence`) and the canvas capture utilities (`collect_canvas_spec_ids`, `canvas_wave_map`) import `TaskGraph`/`LeafTask`/`ParallelTasks`/`SequentialTasks` at module load time. When the Celery-canvas coercion layer is deleted, this entire module must be deleted (or substantially rewritten) alongside it — the top-level import means the module fails to load once `make_task_graph` is removed. The event-driven harness functions (`simulate_event_driven_waves`, `direct_dependency_edges`) and `TestEventDrivenOutputCapture`/`TestFixtureLoading` are reusable but must be migrated to a permanent test file before canvas deletion.

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

- Tests assert observable behavior (dispatched task set + dependency ordering), not internal structure
- Canvas-dependent tests are explicitly temporary; they prove equivalence during the transition period and will be deleted with the canvas layer
- Event-driven-only tests should be migrated to a permanent location before canvas deletion
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

- [x] Verify equivalence tests run representative scopes through both dispatch paths
- [x] Verify the set of dispatched Tasks matches between old and new paths in all covered scopes
- [x] Verify all dependency (happens-before) relationships are preserved by the new path
- [x] Verify existing linear and parallel graph fixtures are reused as the oracle
- [x] Verify tests assert behavior only (review for internal-structure coupling); canvas-dependent tests are intentionally temporary and must be deleted with the canvas layer — see NOTE and Post-Completion section
- [x] run full project test suite
- [x] run project linter - all issues must be fixed

## Post-Completion

- Coordinate with #4 (feature flag) before enabling the new dispatch path in production
- Before deleting the canvas layer: migrate `simulate_event_driven_waves`, `direct_dependency_edges`, `TestFixtureLoading`, and `TestEventDrivenOutputCapture` to a permanent test file
- After migrating surviving tests: delete `test_dispatch_equivalence.py` alongside the canvas layer (the top-level import of `TaskGraph`/`LeafTask`/etc. makes the module unloadable once `make_task_graph` is removed)
