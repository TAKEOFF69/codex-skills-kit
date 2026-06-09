# Codex Build: Add read-only share links

Goal: let Acme Notes owners create and revoke read-only public links for notes.

Success means:
  - Owners can create one active share link per note.
  - Revoked or unknown links return 404.
  - The public page renders note content with no editor affordances.

Stop when: data, API, and UI phases land with tests green and the public page verified in a browser.

> Mode: Hybrid
> Reasoning: high
> Verification level: local tests + browser pass

## Context
The design doc is `docs/design/share-links.md`. This is an additive feature across schema, API, and UI.

## Read these files FIRST
1. `db/migrations/` – migration naming style
2. `api/src/notes/route.ts` – owner route pattern
3. `apps/web/src/components/note-toolbar.tsx` – share button home

## Assumptions
A note has one active share link. Store only a hash of the raw token.

## Invariant
Owner-authenticated note read/write behavior stays unchanged.

## Risk Gate
Pause for a storage-model fork if existing schema already has share-link support. Stop for any public write path.

## Repo mismatch stop condition
If routes, schema, or toolbar files differ materially, report the real structure before implementing.

## Not in scope
Link analytics, expiry, email sharing, and CLI export changes.

## Phase A: Data / SQL
Add a `note_shares` table with `note_id`, `token_hash`, `created_at`, and `revoked_at`.

## Phase B: API
Add owner-only create/revoke endpoints and an unauthenticated read endpoint for live tokens.

## Phase C: UI
Add a Share control and a public read-only route. UI completion needs observable browser proof, not only a build.

## Constraints
- Read the design doc before coding.
- Stay within the listed files plus the new migration and public route.
- Keep UI on existing design-system primitives.

## Done when
- Migration and schema compile.
- API tests cover create, read, revoke, and random-token 404.
- Browser check shows a seeded shared note and no editor affordances.
