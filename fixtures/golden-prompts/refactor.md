# Codex Refactor: Extract note sharing service

Goal: move note sharing logic from the route handler into a service module with behavior unchanged.

Success means:
  - Existing share API tests pass unchanged.
  - Route handlers delegate to the new service.
  - `rg -n "createShare\\(|revokeShare\\(" api/src` shows the intended call sites only.

Stop when: imports are migrated, old inline logic is gone, and behavior is verified by existing tests.

> Mode: Directive
> Reasoning: medium
> Verification level: local tests

## Context
The route handler mixes HTTP parsing and share-token business logic. The target structure is already decided.

## Read these files FIRST
1. `api/src/notes/route.ts` – current inline logic
2. `api/src/notes/share-service.ts` – target module if present
3. `api/src/notes/route.test.ts` – invariant coverage

## Assumptions
This is a code-only refactor. If SQL, API payload names, docs, or templates need renaming, switch to cross-layer refactor.

## Invariant
Behavior unchanged. Public interfaces stable unless the prompt explicitly says otherwise.

## Risk Gate
If the refactor requires changing route contracts, auth checks, or DB schema, stop and report.

## Repo mismatch stop condition
If sharing logic already lives in a service, report the current structure and do not invent a second service.

## Not in scope
Token format changes, auth changes, UI changes, and cleanup unrelated to sharing.

## Current structure
`api/src/notes/route.ts` owns HTTP routing plus share-token generation and revocation.

## Target structure
`api/src/notes/share-service.ts` owns share-token generation and revocation; routes call the service.

## Consumers
Enumerate every import and call site with `rg -n "createShare|revokeShare|share-service" api/src`.

## Constraints
- Behavior unchanged.
- Move code before deleting old logic.
- Do not rename exported route payload fields.

## Done when
- Existing route tests pass unchanged.
- `rg -n "createHash|randomBytes" api/src/notes/route.ts` returns zero.
- All share logic has one service owner.
