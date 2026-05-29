# Job readiness query: dispatchable_tasks()

## Parent

#1 — Event-driven task dispatch (replace the Celery-canvas coercion layer)

## What to build

Add a pure query to the Job that answers "which Tasks are runnable right now": the PENDING (scheduled) Tasks whose every predecessor is Success or Skipped. This is the single source of truth that initial dispatch, successor dispatch, and the reconciliation sweep all build on. It takes no collaborators (no Celery, no DB) and does not mutate state.

From a TDD prototype, the decision-encoding interface is:

```python
def dispatchable_tasks(self) -> list[ScheduledScopedTask]:
    """PENDING tasks whose every predecessor is SUCCESS or SKIPPED — runnable now."""
```

Build it test-first as vertical red-green slices, one behavior per cycle, asserting behavior through the public method only (tests must survive deletion of the graph-coercion code).

## Acceptance criteria

- [ ] A freshly scheduled linear Job exposes only the root as dispatchable, not its pending successors (tracer bullet)
- [ ] A fan-in successor is not dispatchable until the last predecessor is satisfied
- [ ] A SKIPPED predecessor unblocks a successor exactly like SUCCESS
- [ ] A FAILED predecessor keeps the dependent permanently non-dispatchable
- [ ] A New (un-scheduled) Task is never dispatchable even with all predecessors satisfied
- [ ] Multiple independent ready children are all returned (parallelism preserved)
- [ ] Tests assert observable behavior via the public method, no internal-structure assertions

## Blocked by

None - can start immediately
