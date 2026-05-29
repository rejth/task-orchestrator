# Reconciliation sweep for stalled dispatch

## Parent

#1 — Event-driven task dispatch (replace the Celery-canvas coercion layer)

## What to build

A periodic background sweep that heals Jobs stalled by a crash between commit and enqueue. It finds Tasks left in PENDING whose predecessors are all satisfied but which are not actually running, and re-enqueues them idempotently (reusing the Launch id as the Celery task id, so a duplicate is a safe no-op). Failed and aborted Tasks are excluded so a stopped or cascade-failed Job is never resurrected.

## Acceptance criteria

- [ ] A scheduled periodic task runs the sweep on an interval
- [ ] A Task left runnable-but-not-running is re-enqueued
- [ ] Re-enqueue is idempotent (Launch id as task id; no duplicate execution)
- [ ] Failed/aborted Tasks are never re-enqueued
- [ ] The selection query is unit-tested; the re-enqueue behavior is covered

## Blocked by

- #4 — Event-driven dispatch behind a feature flag
