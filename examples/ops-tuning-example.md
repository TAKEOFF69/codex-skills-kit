# Example: ops-tuning (via codex-prompt)

**Skill:** `codex-prompt` · **Task type:** Ops/Tuning · **Mode:** Investigative

## What this demonstrates

A runtime-tuning task built the way the `codex-prompt` skill prescribes for ops work: **Investigative mode** (the live baseline drives the decision, not a number guessed up front), a **live-baseline-first** block that refuses to trust docs for operational metrics, mandatory **before/after metrics** with explicit rollback criteria, and the load-bearing **bandwidth-vs-connection classification** – the rule that says you must identify *which kind* of bottleneck you have before deciding whether raising or lowering parallelism helps. It also keeps the change surface tight (deny-list the deploy step) and demands a real two-point empirical sweep rather than a single confirming measurement.

## The generated prompt

```markdown
# Codex Ops/Tuning: Tune nightly export-job parallelism

Goal: Find the export job's real bottleneck (connection-bound vs bandwidth-bound), then set the worker concurrency to the value that minimizes wall-clock time without raising the DB error rate or breaching the connection pool.

Success means:
  - The bottleneck is classified from evidence (DB connection saturation vs network/disk bandwidth saturation), stated in one sentence.
  - A two-point empirical sweep (one low concurrency, one high) is run on a fixed dataset, with wall-clock + error counts recorded for each point.
  - `EXPORT_CONCURRENCY` is set to the value that wins the sweep, applied via config (no hardcoded literal in `packages/cli/src/export.ts`).
  - Before/after metrics are captured against the same fixed dataset: total duration, notes/sec throughput, error-bucket mix, peak DB connections.

Stop when: the winning concurrency is committed, the before/after table is filled in, and a bounded smoke run reproduces the after-numbers within ±10%.

> Mode: Investigative
> Reasoning: high
> Verification level: production smoke (bounded run on the live job host) + local tests

## Context
The nightly export job (`acme export --all`) walks every note, renders it to markdown, and writes a tarball. It has grown slow as the corpus has grown; a recent run took ~52 min on ~180k notes. Concurrency is currently a hardcoded `8` in the export worker pool. We do not yet know whether the job is bound by Postgres connections/round-trips, by disk/network bandwidth writing the archive, or by CPU in the markdown renderer – so the right direction to move the knob is unknown. Tune it from evidence, not intuition.

Read `AGENTS.md` for project conventions.

## Read these files FIRST
1. `packages/cli/src/export.ts` – worker pool + hardcoded concurrency
2. `packages/cli/src/config.ts` – where runtime config/env is read
3. `api/src/notes/repository.ts` – the per-note fetch the workers call
4. `apps/web/src/lib/search.ts` – ignore; lists the same notes API (out of scope, do not touch)
5. `infra/db/pool.ts` – Postgres pool size + max-connections setting

## Assumptions
Codex can rely on:
- The job is idempotent and re-runnable against the same dataset (it writes to a temp tarball then renames), so repeated sweep runs are safe.
- A fixed measurement dataset exists or can be pinned via `--limit 20000 --seed 1` so each sweep point processes the identical work.

Material ambiguity – where the concurrency value should live:
- **(a, safest, default)** Read `EXPORT_CONCURRENCY` from env via `config.ts`, defaulting to the current `8`. Pure plumbing, reversible.
- (b) Auto-derive concurrency from `pool.max`. Couples two settings; defer unless the sweep shows the pool is the binding constraint.
Default to (a) unless the evidence in the sweep makes (b) clearly correct, in which case surface it as a labeled choice and pause.

## Invariant
- Export output is byte-identical regardless of concurrency (ordering inside the tarball is already sorted by note id – keep it sorted).
- The job never opens more DB connections than `pool.max - 2` (headroom for the health check + migrations).
- No change to the export file format, CLI flags, or the notes API contract.

## Risk Gate
- Architectural fork (e.g. the sweep shows the renderer is CPU-bound and the real fix is a worker-thread pool, not a concurrency number) → stop and report as a labeled option; do not build the new architecture in this prompt.
- Any change that would raise `pool.max` on the shared Postgres instance → stop and report (shared-infra capacity decision).
- A failed sweep point (transient network error, host hiccup) → re-run that single point and log it; do NOT halt the session.

## Repo mismatch stop condition
If `EXPORT_CONCURRENCY` already exists, if the worker pool lives somewhere other than `export.ts`, or if `pool.max` is read from a different module than `infra/db/pool.ts`, stop and report the mismatch before tuning.

## Not in scope
- `apps/web/src/lib/search.ts` and any read-path UI. Report-only if a change there looks tempting.
- The markdown renderer's internals – measure its share of time, but do not optimize it here.

## Operating model to preserve
- Nightly cron contract: the job must still finish inside its 6-hour maintenance window with margin.
- Determinism: same dataset in → same tarball out.
- Connection safety: stay under the pool ceiling at peak.

## Live baseline to verify first
Refresh the live baseline before changing anything – do not trust this prompt's "~52 min" number, re-measure it.

Capture, on the job host, against the pinned dataset (`--limit 20000 --seed 1`):
- total wall-clock for one full run at the current concurrency (8)
- notes/sec throughput
- peak concurrent DB connections during the run (`SELECT count(*) FROM pg_stat_activity WHERE application_name = 'acme-export'` sampled, or pool metrics)
- error-bucket counts (DB timeout, connection refused, render error, write error)
- where time goes: rough split between DB-fetch wait, render CPU, and tarball-write I/O (add lightweight timing around each stage if not already instrumented)

Record the timestamp of the measurement. If the live numbers differ materially from "~52 min on ~180k notes", note it in the report and proceed from the live numbers.

## Classify the bottleneck (do this BEFORE choosing a direction)
This is the decision that determines whether to raise or lower concurrency. Get it from the baseline evidence:

- **Connection-bound** (raising concurrency HURTS, or is capped): DB-fetch wait dominates, peak connections sit at or near the pool ceiling, or errors are connection-refused/timeout. The pool, the per-query round-trip, or a server-side limit is the constraint. The fix is to stay at or below the pool ceiling – more workers just queue on connections.
- **Bandwidth/throughput-bound** (lowering concurrency HURTS – the pipe is under-utilized): tarball-write I/O or network egress dominates while DB connections sit well below the ceiling and CPU is idle. Here, *more* parallelism fills the pipe; lowering the knob "for headroom" starves a resource that was never contended.
- **CPU-bound** (the render stage dominates with DB + I/O both idle): more async workers in a single-threaded runtime won't help past core count. This is the architectural-fork case → report, don't build.

State the classification in one sentence with the evidence that supports it. Do not skip to a value before classifying – picking a direction without classifying is the exact way this kind of tuning regresses (lowering a knob on an under-utilized pipe adds latency, not headroom).

## Two-point sweep (required)
On the pinned dataset, run at least two concurrency points spanning the candidate range, e.g. one low and one high relative to the current 8 (such as 4 and 24 – adjust to straddle the pool ceiling found in the baseline). Capture wall-clock + error counts + peak connections per point. Add a third midpoint only if the two points disagree with the classification. Pick the value that minimizes wall-clock while keeping peak connections under `pool.max - 2` and the error mix no worse than baseline.

## Changes to apply
1. Plumb `EXPORT_CONCURRENCY` through `config.ts` (env, default 8); replace the hardcoded `8` in `export.ts` with the config read.
2. Set the chosen value in the job-host env (the cron's env file), not as a code literal.
3. If the winning value would exceed `pool.max - 2`, cap it at `pool.max - 2` and note the cap.

## Not allowed
- Do NOT raise `pool.max` on the shared Postgres instance to "make room" – that is a capacity decision (Risk Gate).
- Do NOT change the export format, flags, or tarball ordering.
- Do NOT treat this prompt's "~52 min" as the baseline – measure live.
- Do NOT deploy via any auto-deploy path. Commit + push only.

## Validation order
1. Local unit test: `EXPORT_CONCURRENCY` is read from env and falls back to 8 when unset.
2. Local smoke: `acme export --limit 200 --seed 1` produces a byte-identical tarball at concurrency 1 vs the chosen value (determinism invariant).
3. Bounded smoke on the job host at the chosen concurrency against the pinned 20k dataset.
4. Pull live metrics again; fill the before/after table.

## Report before/after
| Metric | Before (conc=8) | After (conc=N) | Δ |
|--------|-----------------|----------------|---|
| Wall-clock (20k dataset) | | | |
| Notes/sec | | | |
| Peak DB connections | | | |
| Error buckets (timeout/refused/render/write) | | | |
| Bottleneck classification | | | |

Include the per-point sweep numbers and the one-sentence rollback criterion.

## Constraints
- Stay within the listed files. Report and pause if correctness needs an out-of-scope file.
- Smallest runtime change that the metrics can measure clearly – one knob, plumbed through config.
- Record the exact verification level: bounded production smoke on the job host + local tests.
- Surface ambiguity (value placement, architectural fork) as labeled options with the safest default.
- en dashes only; no em dashes or double hyphens as punctuation.

## Done when
- Bottleneck classified from evidence, stated in one sentence.
- Two-point sweep run and tabulated; winning concurrency chosen against it.
- `EXPORT_CONCURRENCY` plumbed through `config.ts`, hardcoded `8` removed from `export.ts`: `rg -n "concurrency.*8|8.*concurrency" packages/cli/src/export.ts` returns no literal.
- Determinism smoke passes (byte-identical tarball at conc=1 vs chosen value).
- Before/after table filled; bounded host smoke reproduces the after-numbers within ±10%.
- Rollback criterion stated (e.g. "revert to 8 if peak connections breach pool.max - 2 or any error bucket rises above baseline").
```

## Why it's shaped this way

- **Investigative mode, not Directive.** The skill defaults ops/tuning to Investigative because the right *direction* to move the knob is unknown until the live data is in. A Directive prompt that just said "set concurrency to 16" would forfeit exactly the analysis the agent is good at – and could move the knob the wrong way.
- **Live baseline is [LOCK]; the chosen value is [FORK].** "Re-measure before tuning" has one correct answer, so it is pinned hard (down to the sample query). The final concurrency number has many candidate answers, so it is left to the two-point sweep rather than guessed – the prompt locks the *method*, forks the *value*.
- **Bandwidth-vs-connection classification is mandatory and front-loaded.** This is the load-bearing ops lesson: the same action (lowering parallelism) *helps* a connection-throttled path and *hurts* a bandwidth-throttled one. The prompt forces the classification before any direction is chosen, because picking a direction first is precisely how this class of tuning regresses ("more headroom" is not free when the resource was never the constraint).
- **A two-point sweep, not a single confirming run.** Before/after on one value can look like a win while a different value was strictly better. Requiring a low + high point makes the decision empirical and falsifiable, which is why "before/after metrics" sits in the success criteria, not just the done-when.
- **The risk gate is narrow on purpose.** Only a genuine architectural fork (CPU-bound → needs a worker-thread redesign) or a shared-infra capacity change (raising `pool.max`) halts the session. A flaky sweep point is skip-and-retry, not a stop – over-broad gates strand good work, so the gate guards the two decisions that actually need a human.
