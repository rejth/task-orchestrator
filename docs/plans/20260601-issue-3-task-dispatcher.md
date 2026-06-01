# Task dispatcher: enqueue runnable Tasks to Celery

## Overview

Build a component that takes runnable Tasks and hands them to Celery for execution, with no orchestration logic in the worker. Each Task is enqueued as a single immutable Celery signature carrying a per-Task expiry and using the Task's Launch id as the Celery task id. A duplicate enqueue is therefore an idempotent no-op — the existing Launch-id guard rejects a stale launch.

This replaces the signature-building part of the old chain builder, minus chain/group canvas construction.

## Context

- Impacted component: the dispatch layer that previously built a Celery chain/group canvas
- Constraint: no orchestration logic in the Celery worker — the dispatcher only enqueues
- Constraint: Launch id is the Celery task id and serves as the idempotency key
- Relies on the existing Launch-id guard to reject stale/duplicate launches
- Parent: #1 — Event-driven task dispatch (replace the Celery-canvas coercion layer)
- Adopted from docs/prd/event-driven-dispatch/issue-3-task-dispatcher.md
- Blocked by: none — can start immediately

## Development Approach

- Testing approach: TDD, red-green, vertical slices — one failing test, minimal code to pass, then next behavior. No writing all tests up front then all implementation.
- Complete each task fully before moving to the next
- Update this plan when scope changes during implementation

## Testing Strategy

Method: TDD, red-green, vertical slices (from the parent PRD Testing Decisions).

- Drive the dispatcher through its public interface; assert observable behavior, never internal structure
- Dispatcher unit suite: assert the set of enqueued Tasks and that each carries the Launch id as its idempotency key — without asserting Celery internals
- Assert per-Task expiry and signature immutability through observable enqueue behavior, not Celery canvas internals
- Run project tests after each Task before proceeding

## Technical Details

- Each runnable Task maps to exactly one Celery signature (no chain, no group)
- Signatures are immutable: no result is passed down a chain
- Each signature uses the Task's Launch id as the Celery task id (idempotency key)
- Each signature carries a per-Task expiry
- Duplicate enqueue of the same Launch id is an idempotent no-op via the existing Launch-id guard

## Implementation Steps

### Task 1: Build the dispatcher that enqueues runnable Tasks

- [ ] Add a dispatcher component that accepts a list of runnable Tasks
- [ ] Enqueue each Task as its own immutable Celery signature (no chain/group)
- [ ] Set the Celery task id to the Task's Launch id as the idempotency key
- [ ] Attach a per-Task expiry to each signature
- [ ] write tests for new functionality
- [ ] run project tests - must pass before next task

### Task 2: Confirm idempotent duplicate enqueue

- [ ] Ensure a duplicate enqueue of the same Launch id is a no-op via the existing Launch-id guard
- [ ] write tests asserting the enqueued set and idempotency key without asserting Celery internals
- [ ] run project tests - must pass before next task

### Task 3: Verify acceptance criteria

- [ ] verify each runnable Task is enqueued as its own Celery signature
- [ ] verify each signature uses the Task's Launch id as the Celery task id
- [ ] verify each signature carries a per-Task expiry
- [ ] verify signatures are immutable and no chain/group canvas is constructed
- [ ] run full project test suite
- [ ] run project linter - all issues must be fixed
