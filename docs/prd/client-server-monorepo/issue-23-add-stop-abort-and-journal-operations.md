# Add stop, abort, and Journal operations

## Parent

Parent PRD: #16

## What to build

Add the remaining operator controls to the Job/Task console: stop the current run for a Scope, abort an individual Launch when available, and open a Launch Journal. These flows should use the validated API client, keep the Task list current after mutations, and make operational error states clear.

## Acceptance criteria

- [ ] The console exposes a stop-run action for the selected Scope and updates the Job state after a successful stop.
- [ ] The console exposes an abort action for an individual Launch when Launch information is available and updates the Task view after a successful abort.
- [ ] The console can load and display a Launch Journal through the validated API client.
- [ ] Journal entries show message, level, type, and timestamp in a readable operator-facing view.
- [ ] Missing Scope, unknown Task, missing Launch, authentication failure, validation failure, and server error states are handled clearly.
- [ ] Client behavior tests or documented verification cover stop-run, Launch abort, Journal display, and representative failure states.

## Blocked by

- #22
