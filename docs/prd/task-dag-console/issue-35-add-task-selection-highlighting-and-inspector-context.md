# Add Task selection, highlighting, and inspector context

## Parent

#33

## What to build

Add Task selection and inspector context on top of the DAG canvas. Selecting a Task node should open a Task inspector, visually distinguish the selected Task, highlight the selected Task's full upstream and downstream subgraphs, and present the selected Task's direct dependencies, direct dependents, downstream impact, description, status, and identifiers.

This slice should make the graph operationally understandable without adding mutating actions yet. It should help an operator answer two core questions: what does this Task depend on, and what is derived from it?

## Acceptance criteria

- [ ] Clicking a Task node selects it and opens a Task inspector.
- [ ] The selected Task node is visually distinct from unselected Tasks.
- [ ] The full upstream subgraph and full downstream subgraph are highlighted when a Task is selected.
- [ ] Direct dependencies are listed separately in the inspector.
- [ ] Direct dependents are listed separately in the inspector.
- [ ] Downstream impact is visible in the inspector so the operator can understand what Schedule would affect later.
- [ ] Refreshing graph data preserves the selected Task when that Task still exists.
- [ ] If the selected Task no longer exists after refresh, the inspector closes or shows a clear stale-selection state.
- [ ] Tests verify selection, inspector contents, and upstream/downstream highlighting through user-visible behavior rather than Svelte Flow internals.

## Blocked by

- #34
