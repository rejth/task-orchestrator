# Move Schedule into the Task inspector

## Parent

#33

## What to build

Move the Task Schedule workflow into the selected Task inspector. The Schedule action should use precise domain language, call the existing Schedule endpoint for the selected Task, show the affected Tasks returned by the server, and refresh the Task graph afterward. The UI should not use Run language for this operation and should not require a confirmation modal.

This slice preserves existing Schedule semantics: scheduling a Task re-runs that Task and its downstream subgraph. The inspector should make the downstream impact visible before the operator clicks Schedule.

## Acceptance criteria

- [ ] The selected Task inspector exposes a Schedule action for Tasks that can be Scheduled.
- [ ] The UI uses Schedule language and does not label the Task action as Run.
- [ ] The inspector shows downstream impact before the operator clicks Schedule.
- [ ] Clicking Schedule calls the existing Schedule endpoint for the selected Task.
- [ ] Schedule does not require a confirmation modal.
- [ ] The affected Tasks returned by the server are shown after Schedule succeeds.
- [ ] The Task graph refreshes after Schedule succeeds.
- [ ] Existing authentication, API error, and response validation behavior remain visible for Schedule failures.
- [ ] Tests verify the inspector Schedule workflow, endpoint call, affected Tasks display, graph refresh, and domain vocabulary.

## Blocked by

- #35
