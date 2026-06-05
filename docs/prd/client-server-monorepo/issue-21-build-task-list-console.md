# Build Task list console

## Parent

Parent PRD: #16

## What to build

Build the first Task-focused console view for a selected Scope. The UI should load the Scope's Job Tasks through the validated API client and present the information an operator needs to understand Job state: Task labels, descriptions, statuses, dependencies, and current or latest Launch summaries. Use glossary language consistently and keep the view usable for repeated operational scanning.

## Acceptance criteria

- [x] For a selected Scope, the client loads Tasks through the generated-contract API client and validates the response.
- [x] The Task list displays each Task label, description, status, dependency IDs, and current/latest Launch summary where available.
- [x] The UI clearly distinguishes active Launch information from terminal latest Launch information.
- [x] Loading, empty, missing Scope, validation failure, and server error states are visible and understandable.
- [x] The interface uses canonical terms such as Scope, Job, Task, Launch, Schedule, Dispatch, and Journal, and avoids rejected glossary synonyms where those terms apply.
- [x] Client tests or documented verification cover the Task list behavior and key error states.

## Blocked by

- #20
