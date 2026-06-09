# Codex Fix: Repair stale search cache

Goal: fix Acme Notes search so an edited note appears in the next search result without removing the cache.

Success means:
  - The stale-search reproduction fails before the fix and passes after it.
  - The cache remains present and is invalidated by edit version, not removed.
  - Sibling cache readers are grepped and either fixed or reported.

Stop when: the regression test passes, sibling sweep is reported, and the cache-preservation invariant is verified.

> Mode: Hybrid
> Reasoning: high
> Verification level: local tests

## Context
Search results currently stay stale after editing a note. The suspected layer is `apps/web/src/lib/search.ts`, but Codex must confirm the cause before applying the patch.

## Read these files FIRST
1. `apps/web/src/lib/search.ts` – cache key and invalidation
2. `apps/web/src/lib/search.test.ts` – regression-test shape
3. `packages/cli/src/export.ts` – sibling cached reader

## Reproduction

```bash
pnpm test apps/web/src/lib/search.test.ts -- stale
```

Expected: edited note appears in search. Observed: old title remains.

## Assumptions
The search cache is performance-bearing and must be repaired, not deleted. If the repo uses a different cache owner, report that mismatch.

## Invariant
Search remains cached for unchanged notes; only edits invalidate the affected cache entry.

## Risk Gate
Halt only if preserving the cache conflicts with the real architecture or requires changing the public search API.

## Repo mismatch stop condition
If the listed cache function or test file is missing, stop and report the real search structure.

## Not in scope
Ranking, highlighting, query parsing, and UI copy.

## Phase A – Directive
Add an edit-version value to the cache key where the current key only uses `userId`.

## Phase B – Codex diagnosis
Before editing, confirm the stale-cache root cause in context, then grep for siblings with `rg -n "searchCache|buildSearchIndex|cacheKey" apps packages`. Report every sibling and decide whether it shares the bug.

## Constraints
- Keep the diff to the stale-cache bug and confirmed siblings.
- Preserve the cache; do not remove it as the correctness fix.
- Verify via the focused test command.

## Done when
- Phase B confirms the cause and sibling sweep.
- Regression test proves edit invalidation.
- `pnpm test apps/web/src/lib/search.test.ts` passes.
