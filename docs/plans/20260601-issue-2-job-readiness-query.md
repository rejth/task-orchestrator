# Job Readiness Query: dispatchable_tasks()

## Overview

Add a pure query to the Job that answers "which Tasks are runnable right now": the PENDING (scheduled) Tasks whose every predecessor is SUCCESS or SKIPPED. This becomes the single source of truth that initial dispatch, successor dispatch, and the reconciliation sweep all build on.

The query takes no collaborators (no Celery, no DB) and does not mutate state. The decision-encoding interface is:

```python
def dispatchable_tasks(self) -> list[ScheduledScopedTask]:
    """PENDING tasks whose every predecessor is SUCCESS or SKIPPED — runnable now."""
```

## Context

- Part of parent #1 — Event-driven task dispatch (replace the Celery-canvas coercion layer).
- Impacted component: the Job aggregate and its task-graph readiness logic.
- Constraint: query is pure — no Celery, no DB, no state mutation.
- Constraint: tests assert observable behavior through the public method only, so they survive deletion of the graph-coercion code.
- Not blocked — can start immediately.
- Adopted from docs/prd/event-driven-dispatch/issue-2-job-readiness-query.md.

## Development Approach

- Testing approach: TDD — build test-first as vertical red-green slices, one behavior per cycle.
- Complete each task fully before moving to the next.
- Update this plan when scope changes during implementation.

## Testing Strategy

- Unit tests required for every behavior, written before the implementation (red-green).
- Assert observable behavior via the public `dispatchable_tasks()` method only — no internal-structure assertions.
- Run project tests after each Task before proceeding.

## Progress Tracking

- Mark completed items with `[x]` immediately when done
- Update plan if implementation deviates from original scope

## Technical Details

A Task is dispatchable when both hold:

- The Task is PENDING (scheduled), not New (un-scheduled).
- Every predecessor of the Task is SUCCESS or SKIPPED.

Behavior matrix to encode:

- Linear root: a freshly scheduled linear Job exposes only the root as dispatchable, not its pending successors (tracer bullet).
- Fan-in: a successor with multiple predecessors is not dispatchable until the last predecessor is satisfied.
- SKIPPED: a SKIPPED predecessor unblocks a successor exactly like SUCCESS.
- FAILED: a FAILED predecessor keeps the dependent permanently non-dispatchable.
- Un-scheduled: a New Task is never dispatchable even with all predecessors satisfied.
- Parallelism: multiple independent ready children are all returned.

## Implementation Steps

### Task 1: Tracer bullet — root of a linear Job

- [x] Red: write a failing test asserting a freshly scheduled linear Job returns only the root as dispatchable, not its pending successors
- [x] Green: implement `dispatchable_tasks()` minimally to pass
- [x] write tests for new functionality
- [x] run project tests - must pass before next task

### Task 2: Predecessor satisfaction rules

- [x] Red/green: a fan-in successor is not dispatchable until the last predecessor is satisfied
- [x] Red/green: a SKIPPED predecessor unblocks a successor exactly like SUCCESS
- [x] Red/green: a FAILED predecessor keeps the dependent permanently non-dispatchable
- [x] write tests for new/changed functionality
- [x] run project tests - must pass before next task

### Task 3: Scheduling gate and parallelism

- [ ] Red/green: a New (un-scheduled) Task is never dispatchable even with all predecessors satisfied
- [ ] Red/green: multiple independent ready children are all returned (parallelism preserved)
- [ ] write tests for new/changed functionality
- [ ] run project tests - must pass before next task

### Task 4: Verify acceptance criteria

- [ ] verify all acceptance criteria from Overview/Technical Details are implemented
- [ ] verify tests assert observable behavior via the public method only, with no internal-structure assertions
- [ ] run full project test suite
- [ ] run project linter - all issues must be fixed
