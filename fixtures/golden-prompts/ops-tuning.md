# Codex Ops/Tuning: Reduce export queue latency

Goal: reduce Acme Notes export queue p95 latency without lowering successful export yield.

Success means:
  - Live baseline is captured before edits.
  - p95 latency improves by at least 20 percent on the same profile.
  - Success rate and error buckets do not regress.

Stop when: before/after metrics are captured from live-equivalent smoke and rollback criteria are documented.

> Mode: Investigative
> Reasoning: high
> Verification level: production smoke

## Context
Exports are slow during peak usage. The queue worker and retry profile are suspected, but the bottleneck is not confirmed.

## Read these files FIRST
1. `workers/export-queue.ts` – worker concurrency
2. `api/src/export/status.ts` – user-visible status
3. `ops/export-dashboard.md` – current metric definitions

## Live baseline
Capture p50, p95, success rate, error buckets, queue depth, and timestamp from the live-equivalent environment before changing code.

## Assumptions
Latency tuning cannot reduce correctness, retry safety, or delivered export count.

## Invariant
Export output bytes and authorization behavior stay unchanged.

## Risk Gate
Stop for changes that drop retries, bypass auth, or require production deploy authority not documented in `AGENTS.md`.

## Repo mismatch stop condition
If queue metrics or worker files differ, report the real observability path and continue only with verified metrics.

## Not in scope
New export formats, UI redesign, and pricing changes.

## Changes to investigate
Test whether the bottleneck is bandwidth, connection count, worker CPU, or retry backoff before tuning.

## Report before/after
Report p50, p95, success rate, error buckets, queue depth, changed knobs, and rollback trigger.

## Constraints
- Refresh the live baseline first.
- Make the smallest measurable runtime change.
- Keep rollback instructions executable.

## Done when
- Baseline and after metrics use the same profile.
- Focused tests pass.
- Production smoke or live-equivalent smoke proves the latency improvement.
