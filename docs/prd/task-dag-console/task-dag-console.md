## Problem Statement

Operators currently inspect a selected Scope's Job through a list-based Task console. That list exposes Task status, dependencies, Launch summaries, Schedule, Stop Run, Abort Launch, and Journal workflows, but it does not make the Job's DAG shape visible. This makes it harder for an operator to understand why a Task is blocked, what upstream work it depends on, and what downstream work will be affected when they Schedule a Task.

The project also has a generated visual prototype in the client source tree that looks like a node-based runner, but it is not aligned with the domain model. It hardcodes Task data, simulates execution, uses non-project branding, and implies per-node "run" semantics. The real product needs a Task DAG console backed by the server contract and the project's glossary: the Job and PostgreSQL state are the source of truth, Schedule re-runs a Task and its downstream subgraph, and the console must not become an editor for Task topology.

## Solution

Replace the current list-based Task console with a Svelte Flow-based Task DAG console. The graph is derived entirely from the existing Task list returned by the server. Each returned Task becomes a node, each `depends_on` relationship becomes a directed edge, and the UI provides a selected Task inspector for Task-specific operations and context.

The console should use the visual direction of the prototype only as inspiration: a large pannable graph canvas, compact status-oriented Task nodes, upstream/downstream highlighting, search or selection affordances, and a right-side inspector. It must not copy prototype simulation, fake logs, fake durations, auto-run behavior, Manychat/Manyfest branding, custom branded fonts, or per-node Run/Stop controls.

The toolbar remains the Scope-level command surface: API key, Scope ID, Initialize Scope, Select Scope, Refresh, and Stop Run. The inspector becomes the Task-level command surface: Schedule, Abort Launch, Open Journal, direct dependencies, direct dependents, full downstream impact, Launch details, and Journal display.

## User Stories

1. As an operator, I want to see a selected Scope's Job as a DAG, so that I can understand Task relationships at a glance.
2. As an operator, I want each Task node to show its label and primary status, so that I can scan the Job's current state quickly.
3. As an operator, I want Task statuses to use the API/domain vocabulary, so that the UI matches server state without translation drift.
4. As an operator, I want dependency edges to point from predecessor Tasks to dependent Tasks, so that the direction of derivation is clear.
5. As an operator, I want the graph to be built from the server Task list, so that the UI reflects the selected Scope's actual Job state.
6. As an operator, I want the graph to avoid fake execution state, so that I do not confuse simulation with real background work.
7. As an operator, I want to select a Task node, so that I can inspect its details without leaving the graph.
8. As an operator, I want the selected Task to be visually distinct, so that I can keep my place in a dense DAG.
9. As an operator, I want selecting a Task to highlight its full upstream subgraph, so that I can understand what must be complete before it is Ready.
10. As an operator, I want selecting a Task to highlight its full downstream subgraph, so that I can understand what Schedule may affect.
11. As an operator, I want direct dependencies listed in the inspector, so that I can see the immediate predecessors that gate Readiness.
12. As an operator, I want direct dependents listed in the inspector, so that I can see the immediate Tasks unblocked by the selected Task.
13. As an operator, I want downstream impact shown before Scheduling, so that I understand that Schedule affects more than the selected Task.
14. As an operator, I want Schedule to remain a Task-specific inspector action, so that the graph nodes do not imply a harmless one-node run.
15. As an operator, I want no confirmation modal for Schedule, so that the workflow stays fast once the inspector has shown the affected Tasks.
16. As an operator, I want the Schedule button to use precise Schedule language, so that it does not imply a separate Run operation.
17. As an operator, I want the Schedule action to call the existing server endpoint, so that the domain remains the source of orchestration behavior.
18. As an operator, I want scheduling to refresh the Task graph afterward, so that I see the server-accepted state.
19. As an operator, I want scheduling to show the affected Tasks returned by the server, so that I can verify what the Job marked for work.
20. As an operator, I want an active Launch to expose an Abort Launch action in the inspector, so that I can intervene in a specific Task's current work.
21. As an operator, I want Abort Launch to refresh the Task graph afterward, so that I see the updated server state.
22. As an operator, I want Launch details in the inspector, so that I can distinguish current active work from latest terminal work.
23. As an operator, I want Open Journal in the inspector when a Task has a Launch, so that I can inspect the Launch's log entries.
24. As an operator, I want the Journal display to stay tied to the selected Task and Launch, so that logs are not detached from graph context.
25. As an operator, I want Stop Run to remain Scope-wide, so that it is not mistaken for a Task-specific action.
26. As an operator, I want Stop Run in the toolbar, so that global run control is clearly separated from Task actions.
27. As an operator, I want Refresh in the toolbar, so that reloading the whole selected Scope's Task graph is clearly global.
28. As an operator, I want Refresh to preserve the selected Task when it still exists, so that I do not lose context while watching progress.
29. As an operator, I want the console to poll while Tasks are Pending or In Progress, so that active work updates without manual refresh.
30. As an operator, I want polling to pause while the browser tab is hidden, so that the client avoids needless background requests.
31. As an operator, I want the console to refresh when the tab becomes visible again, so that it catches up after polling was paused.
32. As an operator, I want the graph layout to be deterministic, so that the DAG does not jump around between refreshes.
33. As an operator, I want root Tasks in an early column and dependent Tasks in later columns, so that dependency direction is readable.
34. As an operator, I want local node dragging, so that I can temporarily inspect dense parts of the graph.
35. As an operator, I want node dragging to be local-only, so that I do not create or imply persisted topology or layout changes.
36. As an operator, I want Fit View and normal graph navigation controls, so that I can recover from panning, zooming, or dragging.
37. As an operator, I want missing dependency endpoints surfaced as a warning, so that server/spec drift is visible without crashing the console.
38. As an operator, I want the UI to render all returned Tasks even if some dependencies are missing, so that partial data remains inspectable.
39. As an operator, I want authentication failures to clear the stored API key as they do today, so that stale credentials do not keep failing silently.
40. As an operator, I want API and validation errors to remain prominent, so that graph rendering does not hide server contract problems.
41. As an operator, I want the empty Scope state to remain clear, so that I know whether to initialize or select a Scope.
42. As an operator, I want the console to remain usable on laptop-sized screens, so that everyday operation is comfortable.
43. As an operator, I want the console to avoid Manychat or Manyfest names, fonts, and visual branding, so that the UI belongs to this project.
44. As a maintainer, I want the feature described as a Task DAG console, so that future work does not accidentally turn it into a topology editor.
45. As a maintainer, I want Task topology to remain defined by TaskSpecifications, so that the browser does not become another source of truth.
46. As a maintainer, I want the implementation to use the existing Task API contract, so that the backend does not grow presentation-specific fields prematurely.
47. As a maintainer, I want no phase/lane API addition in the first pass, so that presentation grouping is not mistaken for domain language.
48. As a maintainer, I want no graph-editing affordances in the first pass, so that users cannot add, remove, or reconnect Tasks.
49. As a maintainer, I want no Retry operation in the first pass, so that Schedule semantics stay distinct and unchanged.
50. As a maintainer, I want graph transformation logic isolated from Svelte components, so that it can be tested without UI rendering.
51. As a maintainer, I want local graph helpers instead of a graph library dependency in the first pass, so that dependency weight stays justified by actual need.
52. As a maintainer, I want Svelte Flow used only as the rendering surface, so that domain behavior remains in application code and the server.
53. As a maintainer, I want the current list console replaced directly, so that the UI does not carry two competing Task surfaces.
54. As a developer, I want a small Task graph module with a stable interface, so that upstream/downstream queries and layout can evolve without rewriting components.
55. As a developer, I want focused graph module tests, so that graph behavior is verified without brittle DOM or SVG assertions.
56. As a developer, I want app interaction tests updated for graph selection and inspector actions, so that existing workflows stay covered.
57. As a developer, I want tests to assert user-visible behavior and API calls, so that Svelte Flow internals do not make the test suite fragile.
58. As a developer, I want type checking and build verification to cover the Svelte Flow integration, so that component typing problems are caught early.
59. As a developer, I want generated prototype artifacts removed from the real client source tree, so that future search and tooling do not confuse them with production code.
60. As an AFK agent, I want this work expressed as a PRD before implementation, so that the large UI change can be sliced and implemented deliberately.

## Implementation Decisions

- The canonical product term is Task DAG console, not node editor, graph editor, or workflow editor.
- The Task DAG console is an operator-facing view of a Job's existing Task DAG; it does not define or edit topology.
- The current list-based console is replaced directly rather than kept beside the graph.
- Svelte Flow is the graph rendering library for the first implementation.
- Svelte Flow is used to render nodes, edges, viewport controls, fit view, dragging, and graph interaction; it is not the source of domain truth.
- The graph is represented from the existing Task list response only.
- Each Task becomes one graph node keyed by `spec_id`.
- Each dependency in `depends_on` becomes a directed edge from predecessor Task to dependent Task when both endpoints exist.
- Missing dependency endpoints are not rendered as phantom nodes.
- Missing dependency endpoints are surfaced as non-blocking data warnings.
- The first implementation does not add server schema fields for phase, lane, group, or presentation hints.
- The first implementation does not infer durable domain phases from Task ID prefixes.
- The first implementation does not use grapherx.
- Local graph helper functions are used for the first pass because the needed graph operations are small and specific.
- The local graph helper module is a deep module candidate. Its stable interface should cover graph construction, adjacency maps, upstream traversal, downstream traversal, missing dependency detection, conversion to renderable graph data, and deterministic layout.
- Svelte components should not reimplement graph traversal or layout rules inline.
- The first layout algorithm is deterministic and explicit.
- The first layout algorithm uses dependency layering: roots appear in the first column, dependents appear in later columns, and nodes within a layer are ordered stably.
- A later layout library such as dagre or ELK remains possible if the first deterministic layout is too tangled.
- Nodes may be draggable, but dragged positions are local UI state only.
- Node positions are not persisted.
- Refresh or reload can restore deterministic positions.
- The generated visual prototype is design inspiration only.
- Prototype simulation, fake durations, fake logs, auto-run, play/pause/reset behavior, and per-node Run/Stop controls are removed from the real implementation.
- Manychat, Manyfest, generated branded fonts, generated branded token files, and prototype brand copy are not used.
- The prototype folder should not remain inside the compiled client source tree after implementation.
- Primary status chips use the API/domain vocabulary: `NEW`, `PENDING`, `IN_PROGRESS`, `SUCCESS`, `FAILED`, and `SKIPPED`.
- The UI may format underscores in secondary text, but it should not introduce a competing status vocabulary such as Finished for primary Task status.
- The toolbar is the Scope-level command surface.
- Toolbar commands include API key, Scope ID, Initialize Scope, Select Scope, Refresh, and Stop Run.
- Stop Run remains Scope-wide because the current server operation stops all pending and in-progress work for the selected Scope.
- Refresh remains Scope-wide because the current refresh operation reloads the whole selected Scope's Task graph.
- The inspector is the Task-level command surface.
- Inspector actions include Schedule, Abort Launch when there is a current Launch, and Open Journal when there is an eligible Launch.
- The inspector shows the selected Task's label, `spec_id`, description, primary status, direct dependencies, direct dependents, downstream impact, and Launch information.
- The inspector should show full downstream impact before Schedule, but Schedule does not require a confirmation modal.
- Schedule language must be used for Task actions. The UI should avoid "Run Task" or "Run node" for the Schedule operation.
- Schedule continues to call the existing server endpoint and preserve existing domain semantics: scheduling a Task re-runs that Task and its downstream subgraph.
- Abort Launch continues to call the existing Launch abort endpoint.
- Open Journal continues to call the existing Journal endpoint.
- Stop Run continues to call the existing Scope run stop endpoint.
- Initialize Scope and Select Scope continue to call the existing Scope and Task endpoints.
- No backend API changes are required for the first graph implementation.
- No Task topology mutation endpoints are added.
- No Retry operation is added.
- Explicit refresh is available.
- After Initialize, Select, Schedule, Abort Launch, and Stop Run, the Task graph refreshes from the server.
- Polling runs only while the selected Scope has Tasks in `PENDING` or `IN_PROGRESS`.
- Polling pauses when the browser tab is hidden.
- When the browser tab becomes visible, the console refreshes once and resumes conditional polling if active work remains.
- If the selected Task still exists after refresh, selection should be preserved.
- If the selected Task no longer exists after refresh, the inspector should close or show a clear stale-selection state.
- Existing API key storage and unauthorized-response clearing behavior remain.
- Existing response validation remains based on generated Zod schemas.
- Existing error normalization remains visible in the graph console.

## Testing Decisions

- Good tests assert externally observable behavior, not implementation details.
- Graph module tests should verify Task-to-node mapping, dependency-to-edge mapping, adjacency maps, upstream traversal, downstream traversal, missing dependency warnings, stable topological layering, and deterministic positions.
- Graph module tests should use small representative DAGs, including roots, fan-out, fan-in, a chain, a missing dependency, and an empty graph.
- Graph module tests should not assert exact visual pixels or SVG paths.
- App interaction tests should verify that Initialize Scope and Select Scope load the graph from the API and display Task nodes.
- App interaction tests should verify that selecting a node opens the inspector.
- App interaction tests should verify that the inspector shows Task status, dependencies, dependents, downstream impact, and Launch details.
- App interaction tests should verify that Schedule calls the existing Schedule endpoint and refreshes the graph.
- App interaction tests should verify that Schedule uses Schedule language rather than Run language.
- App interaction tests should verify that Abort Launch remains available for a Task with a current Launch and calls the existing endpoint.
- App interaction tests should verify that Open Journal loads and displays Journal entries.
- App interaction tests should verify that Stop Run remains a toolbar action and calls the existing Scope-wide endpoint.
- App interaction tests should verify that Refresh remains a toolbar action and reloads the selected Scope's Task graph.
- App interaction tests should verify that missing dependency warnings are displayed without preventing returned Tasks from rendering.
- App interaction tests should verify empty, loading, API error, validation error, and unauthorized states.
- Polling tests should use fake timers and verify polling only while active work exists.
- Polling tests should verify that hidden-tab polling pauses and visible-tab refresh resumes the correct behavior.
- Existing API client tests are prior art for fetch, authentication headers, response validation, HTTP error normalization, and unauthorized credential clearing.
- Existing app tests are prior art for operator workflow tests around Scope selection, Schedule, Stop Run, Abort Launch, Journal, and error display.
- Svelte Flow-specific tests should avoid relying on library internals. Prefer roles, text, selected inspector state, and API calls.
- Typecheck and build verification should run after the Svelte Flow integration to catch component and package integration issues.

## Out of Scope

- Editing Task topology in the browser.
- Adding, deleting, reconnecting, or reordering Tasks.
- Persisting node positions.
- Adding server-side layout, phase, lane, or presentation metadata.
- Introducing grapherx in the first implementation.
- Introducing dagre, ELK, or another layout engine in the first implementation.
- Adding WebSocket or Server-Sent Events push updates.
- Adding the future narrower Retry operation.
- Changing Schedule semantics.
- Changing Readiness, Dispatch, Launch, cascade failure, reconciliation, or executor behavior.
- Changing the generated API contract except as required by unrelated server changes.
- Replacing the existing API key authentication flow.
- Keeping the prototype as production code.
- Copying Manychat or Manyfest branding, fonts, token names, or generated copy.
- Building a marketing page or a separate route.
- Building a mobile-first graph editor experience.

## Further Notes

- This PRD follows the project's glossary and the decisions captured during the grilling session.
- The glossary now clarifies Task DAG console as the canonical term and flags node editor / graph editor / workflow editor as avoid terms for this context.
- ADR 0001 remains relevant: the Job and PostgreSQL are the orchestrator/source of truth, and the browser should read server state rather than simulate orchestration.
- ADR 0002 remains relevant: Schedule re-runs a Task and its entire downstream subgraph, which is why the inspector must expose downstream impact before the action.
- The generated prototype was useful as design inspiration for a graph canvas and inspector, but it conflicts with the production domain model and should not be treated as a starting implementation.
- A partial implementation pivot happened before this PRD request: the Svelte Flow dependency was added and the untracked prototype folder was removed from the client source tree. Review the working tree before starting implementation.
