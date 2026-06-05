# Move Launch actions and Journal into the Task inspector

## Parent

#33

## What to build

Move Launch-specific workflows into the selected Task inspector. The inspector should show current or latest Launch details for the selected Task, expose Abort Launch only when there is a current Launch the server can abort, and expose Open Journal when there is an eligible Launch. Journal entries should stay visually tied to the selected Task and Launch.

This slice preserves existing server-backed behavior for Launch aborts and Journals while relocating the actions from the list console into the Task inspector.

## Acceptance criteria

- [ ] The selected Task inspector distinguishes current Launch information from latest terminal Launch information.
- [ ] Abort Launch appears for a Task with a current Launch and calls the existing abort endpoint.
- [ ] The Task graph refreshes after Abort Launch succeeds.
- [ ] Open Journal appears for an eligible Launch and calls the existing Journal endpoint.
- [ ] Journal entries are displayed in the inspector or an inspector-attached panel with the selected Task and Launch context visible.
- [ ] Existing authentication, API error, and response validation behavior remain visible for Abort Launch and Journal failures.
- [ ] Tests verify Launch details, Abort Launch, graph refresh after abort, Open Journal, and Journal display through user-visible behavior and API calls.

## Blocked by

- #35
