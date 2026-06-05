# Example: retro (via retro-distill)

## What this demonstrates

A **Quick Retro** run immediately after a Fix prompt landed – the stale-search-cache fix in Acme Notes. It shows the full four-question protocol filled in (Q1 fork-preservation, Q2 support-compression, Q3 lock/fork misclassification, Q4 skill-update triage), a concrete **lock-as-fork** misclassification call on the Fix prompt that was just reviewed, and – the load-bearing part – it routes the lesson into **skill edits and an anti-pattern entry**, not a passive memory. It also exercises the skill's bias-correction rule that at least 1 in 3 quick retros must touch a skill.

The session under review: a `codex-prompt` Fix prompt told Codex to fix Acme Notes returning stale results after a note edit. Codex's diagnosis phase (Phase B) correctly found the bug in `apps/web/src/lib/search.ts` – the search index cache keyed on `userId` only, so edits within a session never invalidated it – but the prompt had left the cache key as an open design choice, and Codex's first pass picked a coarse fix (drop the cache entirely) before the reviewer redirected it to a targeted key change. The fix shipped, but a round-trip was wasted.

## The generated prompt

```markdown
## Quick Retro: 2026-06-05

**Session:** Fix – Acme Notes returned stale search results after a note edit.
A `codex-prompt` Fix prompt was run against Codex; it patched the index cache in
`apps/web/src/lib/search.ts`. Shipped, but one wasted round-trip on the cache-key choice.

---

### Q1: What worked? (Fork preservation)

- **Phase B diagnosis caught the real root cause before any edit.** The Fix scaffold's
  mandatory "confirm the cause + grep for siblings first" step paid off: Codex traced the
  staleness to the cache being keyed on `userId` only (no edit-time invalidation), and the
  grep surfaced a sibling – `packages/cli/src/export.ts` reads the same cached index, so a
  CLI export right after an edit had the identical staleness. Both got fixed in one arc.
- **Naming the exact invariant in the prompt held the fix honest.** The prompt's invariant
  ("a note edit must be reflected in the very next search within the same session") gave
  Codex a checkable target and shaped the regression test it added in
  `apps/web/src/lib/search.test.ts`.
- Status of both: the Phase-B-finds-siblings behavior is **already codified** in the
  codex-prompt Fix scaffold. Keep.

### Q2: What didn't work? (Support compression)

- **The prompt left the cache strategy fully open**, so Codex's first pass deleted the cache
  outright ("simplest way to never be stale") – correct on correctness, wrong on the perf
  budget the cache existed for. A reviewer round-trip was spent steering it back to a
  targeted fix (add edit-version to the cache key + invalidate on write).
- Root cause: the prompt phrased the cache section as "fix the caching so results aren't
  stale" – an open Fork – when the desired outcome was actually a narrow Lock (preserve the
  cache, fix its key/invalidation). The exploration room invited a heavier change than wanted.

### Q3: Lock or fork misclassification?

- **Lock treated as a fork.** Cache *invalidation correctness* here was a Lock – there was
  one acceptable shape (keep the cache, key it so edits bust it), driven by an existing perf
  budget. The Fix prompt phrased it open-endedly, so Codex explored a coarser branch (drop
  the cache) that violated an unstated invariant. Had the prompt stated "preserve the index
  cache; the fix is its key/invalidation, not its removal" as a Lock, the round-trip is saved.
- Note: the *root-cause hunt* in Phase B was correctly a Fork (let Codex investigate where
  staleness comes from) – that part was classified right.

### Q4: What should change?

Skill-update triage first. The miss was a constraint the Fix template didn't enforce
(a perf-sensitive structure must be preserved, not removed, when fixing its correctness).
That is a *how-to-write-the-prompt* pattern → it belongs in the skill, not a memory.

- **[FIX] codex-prompt Fix scaffold – add a "preserve-don't-remove" Lock prompt.**
  Add to the Fix task-type section a guard: *"If the bug lives in a cache, index, debounce,
  pool, or other perf/structure-bearing component, state explicitly whether that component
  must be preserved. A correctness fix that removes it is usually a regression in disguise –
  make 'fix it, don't delete it' a Lock unless removal is genuinely intended."* This is a
  skill edit because memory won't auto-apply to the next Fix prompt; the template will.
- **[FIX] codex-prompt anti-patterns.md – new entry.**
  Add: *"Correctness fix silently removes the thing it should repair. Deleting a cache to
  stop stale reads, dropping a debounce to stop a double-fire, etc. – fixes the symptom,
  drops the reason the component existed. Guard: name the component's job as an invariant
  the fix must keep."*
- **[KEEP] Phase B diagnosis + sibling grep.** Worked exactly as designed; no change. (Logged
  here only to record that the win came from existing skill content, per the fork-preservation
  question – not everything in Q1 becomes an edit.)
- **No memory written.** The lesson is skill-internal prompt craft, not cross-skill project
  context. (Memory would be the wrong default here – see bias-correction note below.)

**Lock/fork misclassification:**
- Yes – cache invalidation correctness was a Lock phrased as a Fork (Q3).

**Actions taken:**
1. Edited `.agents/skills/codex-prompt/SKILL.md` Fix section – added the
   "preserve-don't-remove" Lock guard for perf/structure-bearing components.
2. Edited `.agents/skills/codex-prompt/references/anti-patterns.md` – added the
   "correctness fix silently removes the component" anti-pattern with its guard.
3. Verified no contradiction with the existing Fix-scaffold "narrow risk gate" rule
   (grepped the skill; preserve-don't-remove is additive, not conflicting).

> Bias-correction check (per skill): this retro touches **2 skill artifacts and 0 memories**,
> satisfying the "at least 1 in 3 quick retros must touch a skill" rule. A memory-only version
> of this retro ("remember not to delete caches") would have rotted unread and never reached
> the next Fix prompt.
```

## Why it's shaped this way

- **The lock/fork call targets the *reviewed* Fix prompt, not the retro itself.** A retro is a process, not a code edit – so Q3's classification is applied to the artifact under review (the search-cache Fix prompt), which is exactly where misclassification does its damage.
- **Q1 records a win without forcing an edit.** Fork-preservation is about noticing what already works (Phase B + sibling grep) and *keeping* it; the skill explicitly says not every Q1 item becomes a change. Logging "already codified – keep" is a valid, deliberate outcome.
- **The finding is routed to a skill, not a memory, because the triage demanded it.** It is a how-to-write-the-prompt pattern that must auto-apply to the next Fix prompt – the skill's Q4 rule is blunt that memory is passive context while skill content ships into every invocation. Picking memory here would have been the common mistake the skill warns against.
- **It splits the action into a scaffold edit and an anti-pattern entry.** The positive rule ("state preserve-vs-remove as a Lock") lives in the Fix scaffold so it's authored proactively; the failure shape ("fix silently deletes the component") lives in anti-patterns.md so it's caught on review – two surfaces, two homes.
- **The bias-correction footer is shown working, not just cited.** The skill mandates that skills keep evolving and that at least 1 in 3 quick retros touch a skill; the retro closes by counting its own artifacts (2 skills, 0 memories) against that rule – the self-distillation loop checking itself.
```
