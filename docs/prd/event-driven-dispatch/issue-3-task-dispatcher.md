# Task dispatcher: enqueue runnable Tasks to Celery

## Parent

#1 — Event-driven task dispatch (replace the Celery-canvas coercion layer)

## What to build

A component that takes runnable Tasks and hands them to Celery for execution, with no orchestration logic in the worker. Each Task is enqueued as a single immutable Celery signature carrying a per-Task expiry and using the Task's Launch id as the Celery task id, so a duplicate enqueue is an idempotent no-op (the existing Launch-id guard rejects a stale launch). This replaces the signature-building part of the old chain builder, minus chain/group.

## Acceptance criteria

- [ ] Given a list of runnable Tasks, each is enqueued as its own Celery signature
- [ ] Each signature uses the Task's Launch id as the Celery task id (idempotency key)
- [ ] Each signature carries a per-Task expiry
- [ ] Signatures are immutable (no result is passed down a chain)
- [ ] No chain/group canvas is constructed
- [ ] Unit tests assert the enqueued set and idempotency key without asserting Celery internals

## Blocked by

None - can start immediately
