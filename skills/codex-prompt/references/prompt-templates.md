---
name: codex-prompt-templates
description: "Copy-paste prompt templates for delegating work to OpenAI Codex (or any Agent-Skills-compatible agent), one per task type: fix (three modes), build, ops/tuning, audit, PR-series, refactor, and cross-layer refactor. Each template ships universal scaffolding plus type-specific sections, quality checklists, and battle-tested constraint blocks. Reference for the codex-prompt skill."
metadata:
  version: 0.1.0
---

# Codex Prompt Templates

Copy-paste per task type. Replace `{placeholders}`.

## Universal scaffolding

Every template inherits these sections. Don't re-spell them per template; paste the block below, fill in values.

```markdown
# Codex {Type}: {Short Title}

Goal: {one sentence – what changes when this prompt completes}

Success means:
  - {checkable criterion 1}
  - {checkable criterion 2}
  - {checkable criterion 3 if needed}

Stop when: {explicit stop condition}

> Mode: {Directive | Investigative}
> Reasoning: {medium|high|xhigh}
> Depends on: {optional prereqs}
> Verification level: {code read|local tests|browser pass|live DB check|production smoke}

## Context
{2-4 sentences. Link design docs. Current broken/missing state.}

Read `AGENTS.md` for project conventions.

## Assumptions
{Allowed assumptions. Ambiguous → list interpretations + safest choice.}

## Invariant
{What stays unchanged through this prompt.}

## Risk Gate
{Halt conditions. Prefer graceful-fallback.}

## Repo mismatch stop condition
If repo state differs (missing file/field/function/migration/export), stop and report the mismatch.

## Not in scope
{Adjacent files/cleanups outside this task's boundary.}

## Read these files FIRST
{Numbered list, grouped by purpose, 5-word annotation each.}
```

Below, each template shows only the **type-specific sections** that go between `## Not in scope` and the end.

---

## Fix – Minimal-diagnosis (trivially mechanical)

Use for rename, single-line null guard, typo, signature-only shift. Phase B is still mandatory – Codex sanity-checks the patch + greps for siblings before applying. Cost is near-zero; protects against the prompt-writer's overconfident "obvious" patches that turn out to need a broader sweep or land at the wrong file.

```markdown
## The Bug

Goal form: reproduce the bug, validate the patch matches the stated cause, sweep for siblings, apply when confirmed.

In `{file}` at line {N}, `{name}()` does:

\`\`\`{lang}
{exact current broken code}
\`\`\`

Causes {specific problem} because {root cause}.

## Proposed Fix (Phase A – Directive)

Replace with:

\`\`\`{lang}
{corrected code}
\`\`\`

{1-2 sentences why this fixes it.}

## Phase B – Codex diagnosis (mandatory)

Before applying Phase A, Codex executes:

1. **Sanity-check the proposed patch against the stated cause.** Read the function in full context; confirm the patch addresses the actual cause, not a downstream symptom. If patch and cause don't match, propose replacement and pause for confirmation.
2. **Grep for sibling occurrences.** `rg -n "{identifying pattern}"` across the module (or wider scope if pattern is generic). Report sibling count + locations.
3. **Decide sweep scope.** If siblings exist and share the same bug pattern: list them, propose remediation per sibling, pause for confirmation. If siblings differ in shape: report and proceed with Phase A only.
4. **Apply.** Once sanity-check passes and sibling decision is made, apply Phase A + any confirmed sibling fixes.

## Constraints
- Stay within listed files. Report and pause when correctness needs an out-of-scope file.
- Keep the diff to the named bug + confirmed siblings; ship cleanup separately.
- Phase B is non-negotiable even for "obvious" fixes – overconfidence on bug patches is a structural failure mode, not a situational one.
- {Project-specific constraints}

## Done when
- Phase B sanity-check + sibling-grep complete and reported
- Phase A patch applied
- Confirmed sibling patches applied (if any)
- `{your test command}` passes
- `{your build command}` passes
- {Specific behavior: "X handles Y without crashing"}

### Manual verification
```bash
rg -n "{pattern that should no longer appear}" {scope}
```
Expected: zero results.
```

---

## Fix – Hybrid (modal case)

Use when the broken surface is visible but the exact patch is open. Three common shapes: (1) known locus, open patch; (2) fix-and-sweep (known instance + sibling audit); (3) layered (Directive on visible layer + Investigative on root-vs-symptom). Codex proposes fix as labeled options; user/invariants gate the apply step. Protects against the prompt-writer's wrong-fix gamble.

```markdown
## Reproduction

\`\`\`bash
{exact command, URL, query that reproduces the symptom}
\`\`\`

Expected: {behavior X}
Observed: {behavior Y}
Error output:
\`\`\`
{paste verbatim from logs/stderr/UI}
\`\`\`

## What is known (Directive scaffold)

- Broken surface visible at: `{file}:{line range}` or `{module/function}`
- Suspected layer: {UI / API / cache / data store / derived view / ingestion / transform / model / …}
- Likely cause hypothesis: {one sentence – prompt-writer's best read}

## What needs investigation (Investigative scope)

Pick the shape that fits:

**Shape A – Known locus, open patch.** Confirm root cause at suspected layer; propose fix; apply once invariants stay safe.

**Shape B – Fix-and-sweep.** Apply Directive patch at known instance; grep across module/codebase for sibling occurrences; propose remediation per sibling; report sweep diff before applying.

**Shape C – Layered.** Patch visible layer (Directive); verify upstream/downstream layers via layer-ladder (`COUNT(*)` / value-check at raw source → canonical store → derived/cached view → API → UI); confirm fix lands at the root layer, not the symptom layer.

## Invariants (the safety net – these stay working)

- {invariant 1 – e.g., "existing /api/X endpoint contract unchanged"}
- {invariant 2}

## Phase A – Directive

{Exact step(s) Codex executes mechanically:}

1. {Apply patch at file:line – show before/after}
2. {Run reproduction; confirm symptom resolved at the surface}

## Phase B – Investigative

{What Codex investigates after Phase A:}

1. {Confirm root cause at correct layer (for Shape A/C) or enumerate siblings (for Shape B)}
2. {Propose fix(es) as labeled options with rationale}
3. {Pause for confirmation when invariants might shift; apply when safe}
4. {Capture regression test}

## Constraints
- Phase A diff stays minimal; Phase B proposes before applying broader changes
- Surface findings as labeled options; default the safest fix
- Codex's analytical edge lives in Phase B – give it room
- {Project-specific constraints}

## Done when
- Phase A patch applied and reproduction resolves at the surface
- Phase B confirms fix is at the root layer (not symptom mask) OR enumerates siblings with per-sibling remediation
- Regression test added and green
- `{your test command}` passes
- `{your build command}` passes

### Manual verification
```bash
{repro command}
```
Expected: {fixed behavior}.

```bash
rg -n "{pattern}" {scope}
```
Expected: {sibling count drops to 0 / matches only in expected files}.
```

---

## Fix – Investigative (root cause open)

Use when reproduction is given but root cause is open. Codex investigates, hypothesizes, proposes, then acts. Pair with a systematic-debugging rhythm (reproduce → minimise → hypothesise → instrument → fix → regression-test).

```markdown
## Reproduction

\`\`\`bash
{exact command, URL, query that reproduces the symptom}
\`\`\`

Expected: {behavior X}
Observed: {behavior Y}
Error output:
\`\`\`
{paste verbatim from logs/stderr/UI}
\`\`\`

## Symptoms

- {observable symptom 1}
- {observable symptom 2}
- {timing/frequency/scope notes}

## What is known

- {fact 1 – verified, not assumed}
- {fact 2}

## What is unknown (Codex investigates)

- {open question 1 – likely root cause hypothesis space}
- {open question 2}

## Hypotheses to test (ordered by likelihood)

1. {hypothesis} → test via {instrumentation/query/log read}
2. {hypothesis} → test via {...}
3. {hypothesis} → test via {...}

Codex extends this list as evidence comes in.

## Invariants (the safety net – these stay working)

- {invariant 1 – e.g., "existing /api/X endpoint contract unchanged"}
- {invariant 2}

## Investigation rhythm

1. Reproduce locally; confirm the symptom matches
2. Walk the data path layer by layer (raw source → canonical store → derived/cached view → API → UI), capturing counts/values at each layer
3. Identify the layer where expected diverges from observed
4. Form root-cause hypothesis; instrument or query to confirm
5. Propose fix as a labeled option with rationale
6. Apply when invariants stay safe; capture a regression test

## Constraints
- Investigate before patching. Codex's analytical edge is the point of this mode.
- Surface findings as labeled options; default to the safest fix.
- Capture the regression test as part of the fix.
- {Project-specific constraints}

## Done when
- Root cause identified and stated in one sentence
- Fix applied at the right layer (not a symptom mask one layer up)
- Regression test added and green
- `{your test command}` passes
- `{your build command}` passes
- {Specific behavior: "X handles Y without crashing"}

### Manual verification
```bash
{repro command}
```
Expected: {fixed behavior}.
```

---

## Build

```markdown
## Database / service connection
{Include ONLY if Codex needs DB or external-service access. Copy current values from `AGENTS.md` or your infra-access doc after verifying.}

## Phase A: {Data / SQL / Schema}

### Step 1: {Task}
File: `{path}`
{Exact schemas, interfaces, or SQL.}
\`\`\`{lang}
{exact code or schema}
\`\`\`

### Step 2: {Task}
{...}

## Phase B: {API / Backend}
{...}

## Phase C: {UI / Frontend}
{...}

## Constraints
- Read the design doc at `{your design-docs dir}/{feature}.md` before writing code
- Stay within listed files. Extras only if required; report why.
- DO NOT add features beyond the design doc
- {DB gotchas: connection-pooler quirks, batch limits, statement restrictions}
- {API gotchas: coordinate systems, rate limits, auth}
- {UI: existing design system, no new colors/fonts}

## Done when
- `{your build command}` succeeds
- `{your check/lint command}` passes
- `{your test suite}` passes (if test-covered code changed)
- {Specific behavior verification}
- UI changes → observable check (browser/curl/screenshot)

### Manual verification
```bash
rg -n "{key identifier from new feature}" {your source dir}
```
Expected: matches in {N} files: {list}.
```

---

## Ops / Tuning

```markdown
## Operating model to preserve
- {Invariant 1 that must not weaken}
- {Invariant 2 that must not change}
- {Invariant 3 about truth model / user-visible behavior / deploy safety}

## Live baseline to verify first

Refresh live baseline before any change.

Expected baseline:
- {count/status metric}
- {duration metric}
- {yield metric}

Verify from:
- {host log path}
- {DB table or query}
- {API endpoint or admin surface}

Live differs from docs → update docs in the same session.

## Changes to apply

### 1. {Low-risk tuning}
{Exact parameters/flags/code path.}

### 2. {Second change}
{Exact runtime behavior improvement.}

### 3. {Optional targeted optimization}
{One concrete traversal/queue/retry/filter improvement.}

## Not allowed
- DO NOT weaken truth model
- DO NOT broaden promotion rules unless requested
- DO NOT change user-facing copy/UI unless requested
- DO NOT treat docs as source-of-truth for live numbers

## Validation order
1. Focused local tests for touched modules
2. Local compile or smoke check
3. Deploy to live host
4. Bounded smoke with updated profile
5. Pull live metrics again

## Report before/after
- duration before/after
- yield before/after
- error bucket / status mix before/after
- side effects before/after
- rejection criteria for rollback

## Constraints
- Preserve the operating model above
- Smallest runtime change measurable clearly
- Record exact verification level: local tests / live deploy / smoke / live metric pull

## Done when
- focused tests pass
- live deploy complete
- bounded smoke successful
- before/after metrics captured
- docs + session log updated if the runtime description changed
```

Past incident: tuning down a shared parallelism/throughput knob to "add headroom" on a bandwidth-throttled path regressed latency – the pipe was under-utilized, not contended. Measure the real bottleneck before lowering a runtime knob; "more headroom" is not free when the resource was never the constraint.

---

## Audit

```markdown
## Database / service access (if needed)
{Include ONLY if the audit requires live queries. Copy current values from `AGENTS.md` or your infra-access doc.}

## Task 1: {First analysis}
{What to analyze + how.}

Output format:
| {Col 1} | {Col 2} | {Col 3} | Status |
|---------|---------|---------|--------|
| {desc}  | {metric}| {thresh}| PASS/FAIL |

## Task 2: {Second analysis}
{What + how.}

Scoring rubric:
- {Metric}: {threshold}+ = PASS, below = FAIL
- {Metric}: {threshold}+ = PASS, below = FAIL

## Task 3: Prioritized findings

| # | Finding | Severity | Fix |
|---|---------|----------|-----|
| 1 | {desc}  | CRITICAL/HIGH/MEDIUM/LOW | {specific action} |

## Output format

Write the report straight to the output file as you go – do NOT buffer in memory.
One table section per task, appended as each completes.
Path: `{your reports dir}/{date}-{audit-name}.md`.

## Anchor capture

Capture `git rev-parse HEAD` at audit start AND end. If HEAD changed, re-verify every source-file finding against the new HEAD. Annotate each finding with its anchor commit.

## Constraints
- DO NOT edit any files – read-only audit
- Every finding has a specific actionable fix – no "needs improvement"
- PASS/FAIL gates, not subjective ratings

## Done when
- All {N} files audited
- Output tables complete, no empty cells
- Findings list with severity + fix each
- Report committed at the output path
```

Audit discipline: enumerate internal/first-party sources before reaching for external probes – the answer is usually already in the repo or the live data, and an external round-trip adds noise and latency you may not need.

---

## PR-Series

```markdown
## PR Overview

| PR | Title | Status | Depends on |
|----|-------|--------|------------|
| 1  | {Data layer prep} | {done/this/pending} | – |
| 2  | {Type updates} | {done/this/pending} | PR 1 |
| 3  | {API changes} | {done/this/pending} | PR 2 |
| 4  | {Route migration} | {done/this/pending} | PR 3 |
| 5  | {Cleanup + redirects} | {done/this/pending} | PR 4 |

## Context
Read `{your design-docs dir}/{feature}.md`. This is PR {N} of {Total}.
{1-2 sentences on this PR specifically.}

## Task 1: {Specific change}
File: `{path}`
{Current code + desired code.}

## Task 2: {Next}
{...}

## Commit protocol (if the prompt covers N ordered commits)
Commits are independent. A risk gate on one = skip + continue, not halt the session. Reserve session-halt for destructive/irreversible ops only.

## Constraints
- This PR ONLY does {X} – DO NOT touch {Y}
- Zero user-visible impact
- DO NOT modify routes/URLs/page components
- {PR-specific}

## Done when
- `{your build command}` succeeds
- `{your check/lint command}` passes
- {Specific verification for this PR's scope}

### Manual verification
```bash
rg -n "{old pattern this PR replaces}" {your source dir}
```
Expected: {0 results | only in files not yet migrated by later PRs}.
```

Past incident: running multiple agents in parallel on one working tree stranded part of a multi-file task – the commits looked clean, but a sibling file's hunk was left uncommitted. When a task spans several files, verify the full fileset is committed per task, not just that "a commit happened."

---

## Refactor

```markdown
## Invariant
Behavior unchanged. Public interfaces stable unless explicitly stated.

## Risk Gate
Refactor stops being low-risk → stop and report, don't broaden the diff.

## Current structure
\`\`\`
{current file/module layout}
\`\`\`

## Target structure
\`\`\`
{desired file/module layout}
\`\`\`

## Consumers (files importing refactored code)
Exhaustive list:
1. `{path/consumer1.ts}` – imports `{what}`
2. `{path/consumer2.ts}` – imports `{what}`
{...}

## Steps

Goal form: build inventory, rank by confidence/risk, implement low-risk structural changes only.

### Step 1: Create new structure
{New files/modules with the target org.}

### Step 2: Migrate consumers
{Update all imports. Show find-and-replace pattern.}

### Step 3: Remove old structure
{Delete old files only after all consumers are migrated.}

## Constraints
- Behavior MUST NOT change – only file org + import paths
- DO NOT rename exported functions/types/variables
- DO NOT "improve" any code – pure structural
- Tests pass at every step

## Done when
- `{your build command}` passes
- `{your check/lint command}` passes
- `rg -n "{old-import-path}" {your source dir}` returns zero
- All existing tests pass unchanged
```

---

## Cross-Layer Refactor

Use for: DB column/table rename, a shared type crossing layers, an API contract, an identifier propagating into generated content (templated pages, articles, exported documents). Plain Refactor assumes import-graph scope; this forces enumeration across every layer before destructive steps.

```markdown
## Phase 0 – SCOPE AUDIT (read-only, gate all destructive phases)

Do NOT modify anything. Produce one markdown report covering every layer. Enumerate from live state, not an assumed list.

### A. DB layer
- Column renames: enumerate every view/table exposing the column (`information_schema` or the engine's catalog)
- Dependency graph: upstream (reads from) + downstream (read by) per hit. On Postgres, walk `pg_rewrite` for materialized-view-to-view edges – `pg_depend` by name misses MV-to-MV deps, and OID binding survives a RENAME.
- Grep your schema/migration files (e.g. `{your sql dir}/*.sql`) for the identifier
- FLAG hits not in the assumed scope – that drift is exactly what this catches

### B. App layer
- Grep `{your source dir}` for the identifier (snake + camel + pascal)
- Classify each: API route param, repository alias, type def, component prop, analytics event, test fixture
- For consumers surfacing to users, note old vs new semantics

### C. Docs layer
- Grep `AGENTS.md`, `{your agent-instructions file}`
- Grep `{your design-docs dir}/**/*.md` (architecture + field glossary)
- Schema docs or field glossary

### D. Content / template layer
- Grep `{your content dir}`, `{your app dir}` for literal interpolation tokens
- Templated-page variant libraries, article templates, exported-document templates
- Any generated-output template surfacing the token

### E. E2E baseline (one anchor entity)
Pick an anchor (record/entity/key). Capture pre-refactor values across the chain: source table → derived view → API JSON → rendered surface → analytics payload. Byte-equal asserts that Phase 4 re-checks.

Report: tabulate A/B/C/D hits + the E baseline. GO only if the Phase 1 scope ⊆ the Phase 0 enumerated set.

## Phase 1 – DB (destructive, one object at a time, dep-leaves-first)
Per object: capture DDL + indexes, snapshot counts, DROP + recreate, refresh dependent views, re-assert the dependency graph, commit.

## Phase 2 – App code
Apply the renames from Phase 0.B. Typecheck + build green. Commit.

## Phase 3 – Docs + content
Apply the renames from Phase 0.C + 0.D. Close any tripwires/monitors. Commit.

## Phase 4 – E2E verification
Re-run Phase 0.E on the anchor + a second anchor. Byte-equal on unchanged-semantic values. Browser spot-check the product surfaces.

## Don't
- Skip Phase 0 – the scope audit is the cross-layer-drift gate
- Assume scope = code-only for a DB-touching refactor
- DROP any view/MV without capturing its dependency graph first (on Postgres, use `pg_rewrite`, not `pg_depend` by name; OID binding survives a RENAME)
- Rename via `ALTER` on a materialized view where the engine forbids it (Postgres rejects this – DROP+CREATE)
- Change product behavior inside a rename – semantic changes are separate prompts
```

Heuristic plain-vs-cross-layer: the identifier appears in SQL, a doc, or a generated-content token → cross-layer. Code-only imports → plain Refactor.

Past incident: a value-source swap shipped without renaming the field that carried it, leaving a sort key and a comparison reading the old semantics one layer up – a silent rank-flip. When you change what a value means, rename the field in the same commit so every consumer is forced to acknowledge the new semantics. And before labeling or auditing a metric, trace it to its producer: a field name can lie about its value (a column called `median_*` may actually hold a blended/derived number).

---

## Reusable add-on blocks

These are project-agnostic block shapes you paste in when a prompt touches the relevant surface. Adapt the placeholders to your stack. The point of the pattern: encode your project's recurring footguns once as a block, then include the block by reference instead of re-deriving the constraint each prompt.

### DB access block

```markdown
## Database connection

Copy current values from `AGENTS.md` or your infra-access doc after verifying:
Host: {host}, Port: {port}, DB: {db}, User: {user}, Password: {pass}
Access: {ssh/tunnel/connection command}

**Connection pooler gotchas** (if you front the DB with a transaction-mode pooler): disable client-side prepared statements (e.g. psycopg `prepare_threshold=None`), avoid session-scoped statements that the pooler can't route, set a sane `connect_timeout`. Capture your pooler's specific limits here once.
```

### Derived-view / cache refresh block

Include whenever a prompt triggers a refresh of an expensive derived view, materialized view, or cache. Capture your project's specific refresh syntax and timing baselines here so prompts don't regress them.

Past incident: a bare `REFRESH MATERIALIZED VIEW CONCURRENTLY` on a few heavy views ran several times slower than the wrapped form, and one unwrapped refresh burned ~40 minutes. The fix was a per-engine wrapper that tunes planner flags for the refresh transaction. Record the wrapper and the per-view baseline timings as a block so future prompts paste the fast path by default.

```markdown
## Refresh syntax (adapt to your engine)

```sql
BEGIN;
SET LOCAL {planner-flag} = {value};   -- transaction-scoped; pooler-safe
REFRESH MATERIALIZED VIEW CONCURRENTLY <view>;
COMMIT;
```

Use `SET LOCAL` (transaction-scoped), not a session `SET`, so a transaction-mode connection pooler stays safe. Views that refresh fast can use the bare statement – no wrapper. Record which views need the wrapper and their baseline timings.
```

### Standard Done-when

```markdown
## Done when
- `{your build command}` succeeds
- `{your check/lint command}` passes (types + lint)
- `{your test suite}` passes (if test-covered code changed)
- State the exact verification level: code read / local tests / browser pass / live DB check / production smoke
- UI changes → one observable check (route loads, exact text visible, screenshot, browser)
- No hardcoded CTA/href/prices – grep your config-bypass patterns: `rg -n "{your hardcoded-CTA pattern}" {your source dir}`
```

### Live-metrics ops add-on

```markdown
## Live baseline to verify first
Refresh live counts + durations before editing. Don't trust docs for operational numbers.
- Capture current values from logs/DB/API/runtime host
- Record when checked
- Live differs from docs → update docs in the same session

## Report before/after
- duration
- yield
- error bucket / status mix
- rejection criteria for revert/narrow
```

### Standard constraints block

```markdown
## Constraints
- Read `AGENTS.md` for all project conventions
- Stay within listed files. Extras only if required; report why.
- Repo differs from the prompt → stop and report the mismatch, don't invent
- DO NOT use em dashes – en dashes for ranges/clauses
- DO NOT hardcode CTA labels/hrefs/prices – use your shared config (CTA component + pricing constants)
- DO NOT add comments/docstrings/types to code you didn't change
- {Coordinate/units convention, if your data has one – e.g. WGS84 (EPSG:4326) in DB}
- {Localization: correct diacritics/encoding from the start, if you serve non-ASCII content}
```

---

These templates are deliberately depth-first: the scaffolding, the Directive/Investigative split, the Phase A/Phase B diagnosis gate, and the cross-layer Phase 0 audit are the methodology – keep them intact when you adapt. For distilling lessons from finished sessions back into your skills and conventions, see the `retro-distill` skill.
