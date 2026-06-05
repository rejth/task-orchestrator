# Generate OpenAPI TypeScript and Zod contract

## Parent

Parent PRD: #16

## What to build

Generate the client API contract from FastAPI OpenAPI using `@hey-api/openapi-ts`, producing TypeScript types and Zod schemas. Add a small hand-written API client module that calls relative `/api` URLs, attaches the operator API key, validates responses with generated Zod schemas, and normalizes errors for UI flows.

## Acceptance criteria

- [x] A reproducible command exports or reads the FastAPI OpenAPI schema and generates TypeScript types plus Zod schemas for the client.
- [x] Generated artifacts are placed in a clear client API contract area and are refreshed by the root API generation/check workflow.
- [x] The hand-written API client wraps fetch, `X-API-Key` handling, Zod response validation, and normalized error handling behind a small stable interface.
- [x] Existing client calls from the Scope tracer flow use the generated contract and validated API client rather than unvalidated ad hoc parsing.
- [x] Tests cover successful parsing, validation failure, HTTP error handling, and 401 credential clearing at the API client boundary.

## Blocked by

- #19
