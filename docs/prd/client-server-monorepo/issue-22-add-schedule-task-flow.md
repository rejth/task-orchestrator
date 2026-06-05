# Add Schedule Task flow

## Parent

Parent PRD: #16

## What to build

Add the operator flow for Scheduling a Task from the Task console. The client should call the server schedule endpoint through the validated API client, show the affected Tasks returned by the server, and refresh the selected Scope's Job state so the operator can see what is now intended to Dispatch.

## Acceptance criteria

- [ ] Each eligible Task in the console exposes a clear Schedule action using the project's canonical Schedule term.
- [ ] Scheduling calls the server through the generated-contract API client and validates the Schedule response.
- [ ] The UI shows which Tasks were affected by the Schedule operation using the response returned by the server.
- [ ] The Task list refreshes or reconciles after scheduling so the selected Scope's Job state is current.
- [ ] Error states for unknown Task, missing Scope, authentication failure, validation failure, and dispatch-after-commit warning paths are handled clearly where observable through the API.
- [ ] Client behavior tests or documented verification cover successful scheduling and representative failure states.

## Blocked by

- #21
