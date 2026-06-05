# Render the server-backed Task DAG canvas

## Parent

#33

## What to build

Replace the current list-first Task view with a server-backed Task DAG canvas. The selected Scope's Task list should become a graph where every returned Task is rendered as a node and every valid `depends_on` relationship is rendered as a directed edge from predecessor Task to dependent Task. The graph should use a deterministic local layout and should surface missing dependency endpoints as a non-blocking warning rather than inventing phantom nodes or crashing.

This slice establishes the vertical skeleton for the Task DAG console: server Task data flows through a small local graph helper module into the Svelte Flow rendering surface, with focused graph-helper tests and app-level behavior tests proving that a selected Scope displays as a graph.

## Acceptance criteria

- [ ] Selecting or initializing a Scope loads Tasks from the existing API and renders them as a DAG canvas.
- [ ] Each returned Task appears as exactly one graph node keyed by its Task specification id.
- [ ] Each dependency edge is rendered only when both endpoint Tasks are present in the response.
- [ ] Missing dependency endpoints are shown as a non-blocking warning while all returned Tasks remain inspectable.
- [ ] Primary Task status chips use the API/domain status vocabulary.
- [ ] The graph uses a deterministic dependency-layered layout with roots in an early column and dependents in later columns.
- [ ] Local graph helpers cover graph construction, adjacency maps, missing dependency detection, and layout behind a small testable interface.
- [ ] Tests cover representative graph shapes including empty graph, chain, fan-out, fan-in, and missing dependency data.
- [ ] The UI does not include prototype simulation, fake execution state, Manychat/Manyfest branding, or graph topology editing affordances.

## Blocked by

None - can start immediately
