# Jobs / Task Orchestration

The background-processing context for building patient reports: each report (and similar entities) runs a fixed DAG of ~80 data-processing tasks (RELOAD / EXPORT / PUSH) that the user drives on demand via API. This document is a glossary, not a spec.

> Note: the ~80-task DAG topology (ids + `depends_on`) is fully defined in `src/infrastructure/fs/task_specifications.yml`, but after the stack migration all task *execution* is stubbed to a single `DemoHandler` (`src/handlers/demo.py`). Real per-task handler bodies are not yet ported.

## Language

**Scope**:
The entity a Job is built for and bound to (e.g. a Report / order). One Scope has exactly one Job.
_Avoid_: tenant, context, owner.

**Job**:
The per-Scope instance of the full task DAG. The aggregate root that owns DAG traversal, dependency validation, state transitions, and cascade failure. Job = state machine + DAG logic; it is not the executor.
_Avoid_: pipeline, workflow, run.

**Task** (ScopedTask):
A single node of a Job's DAG, modelled as a state machine (New -> Pending -> InProgress -> Success / Failed / Skipped).
_Avoid_: step, stage.

**TaskSpecification**:
The static, design-time definition of a task type and its `depends_on` edges. Shared across all Jobs.
_Avoid_: task template, task config.

**Launch**:
A single execution attempt of a Task. Carries the journal/logs and a `launch_id`. Re-running a Task creates a new Launch and pushes the previous one into launch history.
_Avoid_: run, attempt, execution.

**Schedule**:
Mark a Task and its entire downstream subgraph to (re-)run. Scheduling a Task that already succeeded re-runs it and everything derived from it.
_Avoid_: trigger, enqueue (enqueue is Dispatch).

**Retry** (not yet implemented):
Re-run a single failed/missing Task without re-running already-successful downstream. A deliberately narrower verb than Schedule, kept distinct to avoid overloading "schedule".

**Dispatch**:
Hand a ready Task to the executor (Celery) for execution. Distinct from Schedule: scheduling decides intent and state; dispatch is the act of enqueuing.

**Readiness**:
A Task is ready when all of its predecessors are Success or Skipped. A Failed predecessor blocks readiness (see Cascade fail).

**Cascade fail**:
Failing a Task fails its downstream Tasks, so nothing derived from a failed Task runs.

## Relationships

- A **Scope** has exactly one **Job**.
- A **Job** has many **Tasks**; their edges come from each **TaskSpecification**'s `depends_on`.
- A **Task** has one current **Launch** plus a history of past **Launches**.
- A **Task** is **Ready** only when every predecessor **Task** is Success or Skipped.
- **Schedule** selects a set of **Tasks**; **Dispatch** acts on the **Ready** subset of that set.

## Example dialogue

> **Dev:** "When the user schedules `EXPORT_TREATMENTS`, do we just run that one Task?"
> **Domain expert:** "No - scheduling re-runs `EXPORT_TREATMENTS` and its whole downstream subgraph, because its output may have changed and everything derived from it is now stale."
> **Dev:** "So how does the next Task start once `EXPORT_TREATMENTS` finishes?"
> **Domain expert:** "On success the Job is asked which successors are now Ready - all predecessors Success or Skipped - and only those are Dispatched."
> **Dev:** "And if one predecessor failed?"
> **Domain expert:** "Then the dependent Task never becomes Ready; failure cascades down so stale or partial work never ships."

## Flagged ambiguities

- "schedule" was used to mean both "re-run this and all downstream" and "retry just this one". Resolved: **Schedule** = re-run downstream; a future **Retry** covers the single-Task case.
- "run"/"execution"/"attempt" were used interchangeably for a Task's execution. Resolved: the canonical term is **Launch**.
