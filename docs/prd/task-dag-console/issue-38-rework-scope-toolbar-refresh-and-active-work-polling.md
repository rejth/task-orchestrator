# Rework Scope toolbar, refresh, and active-work polling

## Parent

#33

## What to build

Rework the Task DAG console toolbar so it owns Scope-level actions and active-work refresh behavior. The toolbar should contain API key, Scope ID, Initialize Scope, Select Scope, Refresh, and Stop Run. Refresh should reload the selected Scope's full Task graph and preserve the selected Task when possible. Stop Run should remain clearly Scope-wide.

The console should also poll while the selected Scope has active work, pause polling while the browser tab is hidden, and refresh once when the tab becomes visible again.

## Acceptance criteria

- [ ] The toolbar exposes API key, Scope ID, Initialize Scope, Select Scope, Refresh, and Stop Run.
- [ ] Stop Run is presented as a Scope-wide action, not a Task inspector action.
- [ ] Refresh reloads the selected Scope's full Task graph.
- [ ] Refresh preserves the selected Task when that Task still exists after reload.
- [ ] Initialize Scope and Select Scope continue to load the graph through the existing API client behavior.
- [ ] Stop Run calls the existing Scope-wide endpoint and refreshes the graph afterward.
- [ ] Polling runs only while the selected Scope has Tasks in active states.
- [ ] Polling pauses while the browser tab is hidden.
- [ ] The console refreshes once when the browser tab becomes visible again and resumes conditional polling if active work remains.
- [ ] Existing authentication, empty state, API error, and response validation behavior remain visible.
- [ ] Tests use fake timers and visibility events to verify active-work polling and hidden-tab pause behavior.

## Blocked by

- #34
- #35
