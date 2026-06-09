# Codex PR-series: Split share-link rollout

Goal: prepare PR 2 of 4 for the Acme Notes share-link rollout, limited to API types and repository helpers.

Success means:
  - This PR adds typed repository helpers only.
  - It depends on PR 1's schema and does not touch UI or routes.
  - Tests for helper behavior pass.

Stop when: PR 2 is committed with its scoped tests green and later-PR work untouched.

> Mode: Directive
> Reasoning: medium
> Depends on: PR 1 schema migration merged
> Verification level: local tests

## Context
The rollout is split into data, repository, API routes, and UI PRs. This prompt covers only PR 2.

## Read these files FIRST
1. `api/src/db/schema.ts` – PR 1 schema
2. `api/src/notes/repository.ts` – helper home
3. `api/src/notes/repository.test.ts` – helper tests

## PR Overview

| PR | Title | Status | Depends on |
|----|-------|--------|------------|
| 1 | Schema | done | none |
| 2 | Repository helpers | this | PR 1 |
| 3 | API routes | pending | PR 2 |
| 4 | UI | pending | PR 3 |

## Assumptions
PR 1 is already merged and the `note_shares` table exists in generated schema.

## Invariant
Zero user-visible behavior in this PR.

## Risk Gate
If PR 1 schema is absent, stop. If one helper test fails from a fixture mismatch, skip + continue to the next independent helper and report it.

## Repo mismatch stop condition
If repository helpers live outside `api/src/notes/repository.ts`, report the real path before editing.

## Not in scope
Routes, UI, public pages, analytics, and copy changes.

## Tasks
Add `createShare`, `revokeShare`, and `findNoteByShareToken` repository helpers.

## Constraints
- This PR ONLY touches repository helper files and their tests.
- Commits are independent; risk gate on one helper means skip + continue, not session halt.
- Do not modify route handlers.

## Done when
- Focused repository tests pass.
- `rg -n "share" apps/web api/src/notes/route.ts` shows no UI or route changes from this PR.
- Commit message identifies `PR 2 of 4`.
