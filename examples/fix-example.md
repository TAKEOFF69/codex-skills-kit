# Example: fix (via codex-prompt)

## What this demonstrates

A Hybrid Fix prompt for a cache-invalidation bug, showing the methodology features specific to Fix tasks: the **mandatory Phase B (Codex diagnosis)** that no Fix prompt may skip, the **Directive Phase A / Investigative Phase B** split, a **layer-ladder** for a stale-data bug (read → source-of-truth → cache), before/after invariants, and the standard control-field header block (Mode, Reasoning, Verification level, Risk gate, Repo-mismatch stop). Sections are tagged **[LOCK]** (one right answer – be exact) or **[FORK]** (many valid answers – leave the agent room) the way the kit classifies them.

The task: full-text note search keeps returning a note's pre-edit body after the note is edited – a stale-cache / invalidation bug. The prompt-writer can see the broken surface (search reads a cache that edits don't bust) but is not confident which layer owns the miss, so Phase B is load-bearing rather than ceremonial.

## The generated prompt

```markdown
# Codex Fix: Stale full-text search results after note edit

Goal: Editing a note's body updates what full-text search returns for that note, with no pre-edit hit surviving the edit.

Success means:
  - A new regression test reproduces the staleness (edit a note, search the old term – currently still matches) and turns green after the fix.
  - Searching an edited note by a removed term returns no match; searching by an added term returns the note.
  - Every write path that mutates a note body invalidates that note's search entry (API update, bulk import, CLI import).

Stop when: the regression test passes locally, all body-write paths are confirmed to invalidate, and the diff is limited to the invalidation seam plus the test.

> Mode: Hybrid (Phase A Directive / Phase B Investigative)
> Reasoning: high
> Verification level: local tests + live DB check (local Postgres)

## Context

Acme Notes runs full-text search over note bodies. After a user edits a note, search still returns the pre-edit text: a deleted term keeps matching and a newly added term does not match until the process restarts. The restart-clears-it behavior points at an in-memory or query-cache layer that note writes never invalidate, not at Postgres FTS-index lag – Phase B confirms this rather than assuming it. Search reads live in `apps/web/src/lib/search.ts`; note writes land via the API (`api/src/notes/route.ts`) and the `acme` CLI importer. The fix should invalidate on write, not paper over it with a TTL.

Read `CONTRIBUTING.md` for project conventions and the local test command.

## Reproduction [LOCK]

1. Create a note whose body contains the word `alpha`.
2. `GET /api/notes/search?q=alpha` → returns the note. (Correct.)
3. Edit the note: replace `alpha` with `omega` (PATCH via the web client, handled in `api/src/notes/route.ts`).
4. `GET /api/notes/search?q=alpha` → BUG: still returns the note.
5. `GET /api/notes/search?q=omega` → BUG: returns nothing until the server restarts.

Expected after fix: step 4 returns no match; step 5 returns the note.

## Read these files FIRST

1. `apps/web/src/lib/search.ts` – search read + any cache/index
2. `api/src/notes/route.ts` – note create/update/delete handlers
3. `packages/cli/src/export.ts` + its import sibling – CLI write path
4. `apps/web/tests/search.test.ts` (or nearest) – existing search tests
5. Any module exporting an invalidate/clear helper used by writes

## Assumptions

- The stale value lives in the search/index layer (an in-process map, or a query cache keyed by query string or note id), not in Postgres' own FTS index. If a live DB check shows the DB row is also stale (an MV/GIN index never refreshed on write), treat THAT as the root cause instead and say so before patching – do not lock in the in-memory interpretation.
- Note body is the only edited field that must invalidate search. Title is in scope only if the indexer also indexes it (confirm by reading `search.ts`).

## Invariant [LOCK]

- Search results for UNedited notes stay byte-identical – no full-cache flush that needlessly evicts warm, correct entries.
- The `GET /api/notes/search` response shape and contract are unchanged.
- No TTL/polling fallback is introduced; invalidation is event-driven on the write.

## Risk Gate

- Halt and ask only if the correct fix requires a schema/migration change (e.g. adding or rebuilding a Postgres FTS index) – that is an architectural fork for the user.
- Mechanical surprises (a fourth write path, a missing test helper, a misnamed export) → log and continue; do not stop the session.

## Repo mismatch stop condition

If a cited file/function/export is missing or differs (no cache in `search.ts`, no CLI import path, a different test location), stop and report what you found instead, before editing.

## Not in scope

- Search ranking/relevance, pagination, query parsing. Touch only on a report-only basis if they block the fix.
- Delete-path behavior beyond confirming it already invalidates; fix it only if it shares the same miss.

## Phase A (Directive) – pin the surface + the suspected patch [LOCK]

1. Run the reproduction above; capture the exact stale response body.
2. Read `search.ts`: identify the cache – its type, its key, and where reads populate it.
3. Suspected patch: every note write that changes body should invalidate that note id in the search layer (or clear the affected query entries) inside the same write path, before responding.

## Phase B (Investigative) – CONFIRM cause, sweep siblings, then apply [FORK]

Phase B is mandatory. Do not apply Phase A's patch on faith.

1. Confirm the root cause by climbing the layer ladder for this stale-data bug, and report which layer holds the stale value before patching:
   - read path: does `search.ts` serve from a cache? keyed how – query string, note id, or both?
   - write path: does the API update handler call any invalidation? does the CLI import path?
   - source of truth: `SELECT body FROM notes WHERE id = <anchor>` after the edit, to prove the DB row is correct and the staleness is above it (cache), not in the FTS index.
2. Grep for every write path that mutates a note body, so the fix covers all of them:
   `rg -n "UPDATE .*notes|notes\.update|update\(.*note|import.*note|INSERT INTO notes" apps api packages`
   Expect at least: API update, bulk/batch update, CLI import. List what you find.
3. Validate or replace the Phase A patch: confirm a per-note-id invalidation actually evicts the entries that caused the miss (a query-string-keyed cache may need clearing differently than a note-id-keyed one). Present the chosen fix as a labeled option – A: targeted invalidation / B: the alternative you found – with the safest defaulted, then apply once the invariants above stay safe.
4. Add the regression test from Success means: edited term no longer matches, added term matches, an unedited note is unaffected.

## Constraints

- Stay within the files listed. Report and pause if correctness needs an out-of-scope file (e.g. a shared cache module both web and API import).
- Surface ambiguity as a labeled choice with 2-3 interpretations and the safest default.
- Scope to this one bug; ship any adjacent cleanup separately. No renames, no reformatting of untouched lines.
- Use en dashes (–) in any prose you write; never em dashes or double hyphens.
- DO NOT deploy. Commit + push only; never use a deploy command as verification.
- Verify via the project's local test command (e.g. `vitest run`) + typecheck. Local tests are the gate here, not a build pass.

## Done when

- `vitest run apps/web/tests/search.test.ts` (or the repo's search test) is green, including the new regression case.
- Reproduction step 4 returns no match; step 5 returns the note – pasted as command + output.
- The Phase B layer-ladder result and the `rg` write-path list are in the summary, naming every path the fix touches.
- `git diff --stat` shows only the search/invalidation seam plus the test file.
```

## Why it's shaped this way

- **Phase B is mandatory, not optional.** The kit's hardest Fix rule is that every Fix prompt ships a Codex-diagnosis phase, because prompt-writers are reliably overconfident about root causes. Here the writer sees the symptom but does not actually know whether the stale value lives in an in-process cache or the Postgres FTS index – so Phase B's layer-ladder + sibling grep is load-bearing, and Phase A's suspected patch is explicitly forbidden from being applied on faith.
- **Hybrid mode (Directive A / Investigative B), not pure Directive.** The locus is known (search reads a cache writes don't bust) but the exact patch is open, which is the modal real-world Fix shape. Phase A pins the surface so the agent isn't re-deriving the bug; Phase B leaves the *how* open so it can find the right invalidation seam instead of being railroaded into the writer's guess.
- **[LOCK] on Reproduction, Invariant, and Phase A; [FORK] on the diagnosis.** The reproduction has one correct sequence and the invariant one acceptable answer, so they are locked and exact. The confirm-cause-and-patch step has many valid routes, so it is forked – it ships criteria and room rather than dictating the line to change.
- **A layer-ladder because it's a data-surface bug.** Cache/index/snapshot staleness is the kit's canonical case for climbing read → source-of-truth → cache before declaring the surface fixed; baking the ladder into Phase B forces the agent to prove *which* layer holds the stale value rather than patching the first plausible one.
- **A narrow risk gate plus before/after proof.** The only halt is a schema/migration fork – a genuine user decision; a fourth write path or a missing helper is skip-and-log, not a session stop. And success is a failing-then-green regression test plus pasted reproduction output, so the fix is proven by a verifiable goal, not asserted.
