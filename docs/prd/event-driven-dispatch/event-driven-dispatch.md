## Problem Statement

When an operator schedules a Task from the front end, the system runs that Task and its downstream subgraph as a background Job. Today the Job translates the dependency DAG into a Celery `chain`/`group` canvas before execution. Because Celery's canvas can only express series-parallel structures, the Job has to reverse-engineer a series-parallel nesting out of a general fan-in/fan-out DAG. That coercion layer is the most complex and fragile part of the system: it is hard to reason about, hard to change, and the place defects concentrate (especially where a serial chain feeds into a fan-in alongside parallel siblings). It "works now," but every change to task topology risks breaking the graph reconstruction rather than the actual orchestration rules.

## Solution

Stop pre-baking an execution plan. The Job already knows the full DAG and already validates dependencies, so let execution be driven by completion events instead: when a Task finishes (succeeds or is skipped), ask the Job which successors are now runnable and hand exactly those to the executor. Celery becomes a dumb "run one Task" transport; PostgreSQL stays the single source of truth that the front end reads. The series-parallel coercion disappears entirely.

From the operator's perspective nothing about scheduling changes: scheduling a Task still re-runs that Task and its entire downstream subgraph, parallel branches still run in parallel, failures still cascade. What changes is that the system becomes simpler and more predictable internally, and a stalled run can self-heal instead of requiring manual recovery.

## User Stories

1. As an operator, I want to schedule a Task and have it plus its entire downstream subgraph re-run, so that a report is never internally inconsistent after upstream data changes.
2. As an operator, I want independent branches of the DAG to run in parallel, so that report generation completes as fast as the dependencies allow.
3. As an operator, I want a Task with multiple predecessors to start only after every predecessor has succeeded or been skipped, so that it never runs on incomplete inputs.
4. As an operator, I want a skipped predecessor to unblock its dependents exactly like a successful one, so that intentionally skipped steps do not stall the run.
5. As an operator, I want a failed Task to prevent everything downstream of it from running, so that no artifact is built on top of failed work.
6. As an operator, I want to stop a running Job, so that I can halt wasted work when I know the result is no longer needed.
7. As an operator, I want a Task that has been waiting in the queue too long to expire, so that a stuck Task does not block its branch forever.
8. As an operator, I want the front end to keep showing accurate per-Task and per-Launch status, so that I can see exactly where a Job is.
9. As an operator, I want to retry a Job that silently stalled, and have it resume on its own, so that I am not forced to manually re-trigger steps after an infrastructure hiccup.
10. As a developer, I want a single, well-tested way to ask "which Tasks are runnable right now," so that initial dispatch, successor dispatch, and stall recovery all share the same correct logic.
11. As a developer, I want the executor layer to contain no orchestration logic, so that changing task topology never requires touching worker code.
12. As a developer, I want dispatch decisions made under the existing per-Job lock, so that two predecessors finishing at the same instant can never double-dispatch or drop a successor.
13. As a developer, I want the old graph-coercion code removed once the new path is proven, so that the codebase stops carrying two execution models.
14. As an SRE, I want a periodic reconciliation that re-enqueues Tasks left runnable-but-not-running, so that a crash between commit and enqueue does not permanently stall a Job.
15. As an SRE, I want the new dispatch behind a flag during rollout, so that I can compare it against the current behavior and revert instantly if needed.
16. As a developer, I want characterization tests built from the existing graph fixtures, so that I can prove the new dispatch honors the same happens-before relationships as the old canvas before deleting it.

## Implementation Decisions

- **Keep Celery as transport, keep the Job + PostgreSQL as orchestrator and source of truth.** External workflow engines (Temporal, Airflow, Dagster, Prefect, Hatchet) were considered and rejected because they assume DAG-as-code run as whole pipelines with their own state store, which fights the per-Scope, API-triggered, PostgreSQL-as-truth model here. (See ADR 0001.)
- **Replace the pre-baked canvas with completion-driven dispatch.** On a Task reaching Success or Skipped, the Job computes which successors are now runnable and the service enqueues them. There is no `chain`/`group` and no series-parallel reconstruction.
- **Readiness definition.** A Task is runnable ("dispatchable") when it is in the PENDING (scheduled) state and every predecessor is Success or Skipped. A Failed predecessor blocks it; this is what produces cascade failure.
- **Job readiness query (deep module).** The Job exposes a single pure query that powers initial dispatch, successor dispatch, and reconciliation. From a TDD prototype, the decision-encoding interface is:

```python
def dispatchable_tasks(self) -> list[ScheduledScopedTask]:
    """PENDING tasks whose every predecessor is SUCCESS or SKIPPED — runnable now."""
```

- **Task dispatcher (deep module).** A component that turns runnable Tasks into Celery signatures (per-Task expiry, the Launch id used as the Celery task id for idempotency, immutable signatures) and enqueues them. Replaces the chain builder minus chain/group.
- **Dispatch orchestration in the tasks-management service.** The success and skip operations compute runnable successors and transition them to PENDING inside the same locked transaction as the state change; enqueueing to Celery happens after commit. This is the same ordering already used for the initial schedule today.
- **Exactly-once fan-in via the existing per-Job row lock.** Completions for one Scope are already serialized by a `SELECT ... FOR UPDATE` on the Job row; the last predecessor to commit is the sole one that sees all siblings satisfied and schedules the successor.
- **Reconciliation sweep.** A periodic Celery-beat task re-enqueues any Task stuck in PENDING whose predecessors are all satisfied, idempotently (reusing the Launch id as the Celery task id; the Launch-id guard makes a duplicate dispatch a safe no-op). It must exclude failed/aborted Tasks.
- **Scheduling semantics preserved.** `schedule(X)` continues to re-run X and its entire downstream subgraph (chosen for stale-data safety over the cheaper "only missing/failed"). (See ADR 0002.) A narrower single-Task "retry" is intentionally left as a possible future, separate operation, not a weakening of schedule.
- **Run cancellation.** Per-Task expiry plus an explicit "stop run" (cascade-abort all non-terminal Tasks and revoke any running Launches). No whole-run auto-kill deadline; the chain-level expiry that previously provided it is dropped deliberately.
- **Feature flag.** A flag selects the old canvas path versus the new event-driven path during rollout; the old graph-coercion modules and the chain-expiry wiring are deleted only after the flag is fully on.

## Testing Decisions

**Method: TDD, red-green, vertical slices.** Build the readiness query test-first, one behavior at a time: write one failing test, write the minimal code to pass it, then move to the next. Do not write all the tests up front and then all the implementation (horizontal slicing produces tests that assert imagined shape rather than real behavior). Each cycle responds to what the previous one revealed.

**What makes a good test here:** it drives the Job through its public methods and asserts observable orchestration behavior (which Tasks are runnable, which are blocked, which run in parallel), never internal traversal structure. The litmus test: these tests must pass unchanged after the graph-coercion code is deleted. If renaming an internal helper breaks a test, that test was wrong.

**Primary deep module under test: the Job readiness query.** It is the heart of event-driven dispatch, and a single pure method powers initial dispatch, successor dispatch, and the reconciliation sweep:

```python
def dispatchable_tasks(self) -> list[ScheduledScopedTask]:
    """PENDING tasks whose every predecessor is SUCCESS or SKIPPED — runnable now."""
```

It takes no collaborators (no Celery, no DB), so it is tested in isolation with in-memory Jobs and no mocks.

**Behaviors as prioritized vertical slices** (each its own red-green cycle, in order):

1. **Tracer bullet** — a freshly scheduled linear Job exposes only the root as dispatchable, not its pending successors.
2. **Fan-in blocks** — a successor with multiple predecessors is not dispatchable until the last predecessor is satisfied (the correctness crux).
3. **Skip satisfies** — a SKIPPED predecessor unblocks a successor, exactly like SUCCESS.
4. **Fail blocks** — a FAILED predecessor keeps the dependent permanently non-dispatchable.
5. **Only PENDING are candidates** — a New (un-scheduled) Task is never dispatchable, even with all predecessors satisfied.
6. **Fan-out** — multiple independent ready children are all returned (parallelism preserved).

**Secondary suites** (after the readiness query is green; same behavior-through-interface discipline):

- **Task dispatcher (unit):** asserts the set of enqueued Tasks and that each carries the Launch id as its idempotency key, without asserting Celery internals.
- **Dispatch orchestration (integration):** success and skip of a Task enqueue its now-runnable successors; failure enqueues nothing downstream. Prior art: the existing tasks-management service integration tests.
- **Reconciliation sweep (unit + behavior):** a Task left runnable-but-not-running is selected for re-enqueue; failed/aborted Tasks are excluded.
- **Stop-run (integration):** stopping a Job leaves no non-terminal Tasks and triggers no further dispatches.

**Characterization tests (equivalence gate before deleting the old layer):** reuse the existing linear and parallel graph fixtures as the oracle and assert the new dispatch honors the same happens-before relationships and dispatches the same set of Tasks as the current canvas.

**Must-haves vs optional:** the readiness-query vertical slices (1-6) and the characterization tests are non-negotiable; the secondary suites are recommended and may be trimmed if time-boxed.

## Out of Scope

- Adopting any external workflow/orchestration engine.
- Changing the task catalog or the dependency definitions.
- A transactional-outbox dispatch mechanism (the reconciliation sweep is the chosen first cut; outbox is only revisited if a lost dispatch proves unacceptable in production).
- A user-facing single-Task "retry" operation (noted as possible future work).
- A whole-run auto-kill deadline.
- Front-end changes; the API contract and the status the front end reads are unchanged.

## Further Notes

- Domain vocabulary follows the project glossary (Scope, Job, Task, TaskSpecification, Launch, schedule, dispatch, readiness, cascade fail).
- Two ADRs already capture the load-bearing decisions: event-driven dispatch over the Celery canvas, and schedule re-running the entire downstream subgraph.
- The per-Job `FOR UPDATE` lock must be held across the readiness computation, not just the single state transition — this is the property that makes fan-in exactly-once.
