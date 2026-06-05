---
name: codex-prompt
description: "Generate structured Codex task prompts for delegating work to OpenAI Codex. Use when the user says 'codex prompt,' 'write a codex task,' 'delegate to codex,' 'codex fix,' 'codex build,' 'codex audit,' 'codex tuning,' or asks you to prepare a task for Codex. Covers 6 task types: fix, build, ops/tuning, audit, PR-series, refactor. For retrospectives that fold lessons back into these rules, see retro-distill."
metadata:
  version: 0.1.0
---

# Codex Prompt Generator

Generates copy-paste-ready Codex prompts that ship self-contained – Codex runs locally with full repo access and executes without clarification turns.

## Foundations

These two principles outrank the category templates below. When a category rule and a foundation tension, follow the foundation.

**Karpathy (higher authority).** State assumptions; present interpretations when ambiguous; push back when a simpler path exists; stop and ask when confused. Ship the minimum code that solves the problem – every line traces back to the request. Transform tasks into verifiable goals: success criteria + stop condition, let Codex loop until verified.

**Directional.** Open every prompt with Goal + Success means + Stop when. Lead each instruction with a positive verb naming the correct action. Demote decorative ALWAYS/NEVER/MUST to plain prose; reserve them for true invariants (safety boundaries, hard limits, required output fields). Negation survives in four narrow cases: hard safety, near-identical-path disambiguation, acceptable-space too large to enumerate, narrower-than-any-positive-paraphrase (incident-derived rules tagged `Past incident:` qualify under case 4).

## Task types

| Type | Use | Key trait |
|------|-----|-----------|
| Fix | Known-root-cause bug | Broken code + corrected code |
| Build | Feature from design doc | Phased + schemas |
| Ops/Tuning | Runtime/deploy/infra/measurement | Live baseline + before/after metrics |
| Audit | Read-only analysis | PASS/FAIL tables + output format |
| PR-series | Multi-PR feature | Numbered PRs + deps |
| Refactor | Restructure w/o behavior change | Before/after + invariant |

## Task mode (orthogonal to task type)

Every prompt picks one mode. The mode shapes what the prompt ships and how much room Codex has to think.

| Mode | When | Prompt ships |
|------|------|--------------|
| **Directive** | HOW is known (mechanical sweep, known-root-cause fix, target structure decided) | Exact steps, before/after code, target schema. Codex executes the spec. |
| **Investigative** | HOW is open (root-cause hunt, novel bug, ambiguous design space, finding all the ways a thing breaks) | Goal + success criteria + invariants + stop condition. Codex investigates, proposes, then acts. |

Default by task type:

- **Fix:** **Every Fix prompt ships Codex-diagnosis Phase B.** No exceptions. Claude's code-analysis depth is structurally thinner than Codex's; pure-Directive Fix gambles on Claude's fix being correct, and Claude is reliably overconfident. Hybrid is the modal default. Minimal-diagnosis (rename/null-guard/typo) still ships Phase B as sanity check + sibling-grep before apply. Pure Investigative when reproduction is given but root cause is fully open
- **Build:** Directive for well-spec'd phases; Investigative for design-doc gaps; Hybrid when some phases are spec'd and others open
- **Ops/Tuning:** Investigative by default (live baseline drives the decision)
- **Audit:** Investigative (PASS/FAIL gates frame the destination; methodology open)
- **PR-series:** Directive (PR boundaries pre-decided)
- **Refactor:** Directive when target structure stated; Investigative when "build inventory first" is part of the ask

Investigative prompts give Codex room to use its analysis and coding intelligence. Directive prompts protect against drift on mechanical work. Hybrid combines both per-phase. Mis-picking cost: Directive on novel territory forecloses better paths Codex would otherwise find; Investigative on mechanical sweeps invites scope creep; pure-Directive Fix on a real bug gambles on the prompt-writer's fix being correct (Codex usually has deeper code-analysis depth).

## Four essentials (OpenAI framework)

1. **Goal** – what changes
2. **Context** – files, docs, errors
3. **Constraints** – standards, hard limits
4. **Done when** – testable completion

## Five control fields

1. **Assumptions** – surface material ambiguity (2-3 interpretations)
2. **Invariant** – what stays unchanged
3. **Risk gate** – when to stop. Scope narrowly (commit/phase, not session). Prefer graceful-fallback over hard-stop. **Halt criteria narrowed to: (a) destructive op on shared infra, (b) architectural fork needing user input, (c) novel auth/privilege boundary.** Mechanical issues (missing files, scope drift, transient errors) → skip-and-log + continue, NOT halt. Phases + halts only when multi-stage user decisions are required; routine fix/audit/ops prompts skip phase numbering. Past incident: a multi-stage arc shipped 7 halt conditions where 2 would have sufficed; reruns with the narrowed criteria finished in under 40 min with 0 halts. Over-gating turns autonomous work into a clarification-turn treadmill.
4. **Verification level** – `code read` | `local tests` | `browser pass` | `live DB check` | `production smoke`
5. **Repo mismatch stop condition** – explicit: stop on missing file/field/function/migration

## Read the code FIRST

Open every file, function, and line you plan to cite. Cite only what you have read. Codex trusts the prompt; wrong refs cascade.

## Reasoning effort

- Medium: well-scoped fixes
- High: multi-file, debugging
- Extra high: long agentic, architecture

Note `> Reasoning: high` at top.

## Tight-prompt marker

For mirror/additive tasks (precedent exists), add `<!-- tight-prompt -->` as line 1. Lets a pre-commit validator (if your repo runs one) downgrade missing-ceremony errors to warnings. Allows under-40-line prompts. Full ceremony still applies for: from-scratch features, large refactors, destructive schema ops, novel audits.

## Execution style (orthogonal to Mode)

How the work unfolds inside the prompt. Pick one independent of Directive/Investigative Mode.

| Style | When | Output |
|-------|------|--------|
| Direct | Well-defined fix/refactor | Single executable prompt |
| Plan | "figure out", "decide", "best way" | Codex plans first, then executes |
| PLANS.md | >30min task, 5+ files, restart-capable | Self-contained execution plan |

Default direct. Escalate on ambiguity or duration.

## Skeleton

```markdown
# Codex {Type}: {Short Title}

Goal: {one sentence – what changes when this prompt completes}

Success means:
  - {checkable criterion 1}
  - {checkable criterion 2}
  - {checkable criterion 3 if needed}

Stop when: {explicit stop condition – verdict issued, test passes, metric captured}

> Mode: {Directive | Investigative}
> Reasoning: {medium|high|xhigh}
> Depends on: {optional prereqs}
> Verification level: {code read|local tests|browser pass|live DB check|production smoke}

## Context
{2-4 sentences. Link design docs. State current broken/missing state.}

Read `AGENTS.md` for project conventions.

## Read these files FIRST
{Numbered list. 5-word annotation each.}

## Assumptions
{What Codex can rely on. If ambiguous, list interpretations + safest choice.}

## Invariant
{What stays unchanged through this prompt.}

## Risk Gate
{Halt conditions. Prefer graceful-fallback.}

## Repo mismatch stop condition
If repo differs (missing file/field/function/migration/export), stop and report the mismatch.

## Not in scope
{Adjacent files outside this task's boundary. Touch on report-only basis.}

## {Task sections vary by type}
{Phases for builds. Current+desired for fixes. Output format for audits.}

## Constraints
- Stay within listed files. Report and pause when correctness needs an out-of-scope file.
- Surface ambiguity as a labeled choice; offer 2-3 interpretations with the safest one defaulted.
- {Deploy boundary, if any: e.g. commit+push only, no deploy commands – see AGENTS.md}
- Verify via: {your build command} / {your test suite} / {your typecheck}. Never deploy as verification.
- {Project constraints from AGENTS.md}
- {Anti-patterns: see references/anti-patterns.md}

## Done when
- {Testable criteria}
- {Runnable commands with expected output}
```

## Category rules

### Fix

**Structural rule – Phase B (Codex diagnosis) is mandatory in every Fix prompt.** No exceptions, regardless of how "obvious" the fix looks. Claude is reliably overconfident on bug diagnosis; this rule structurally protects against it without relying on Claude's self-assessment.

**All modes:**
- Lead with reproduction (command, URL, query) + exact error output
- State the invariant (what stays working as the safety net)
- Scope each prompt to one bug; ship cleanup separately
- Phase B always present: Codex confirms cause + greps for siblings + proposes fix as labeled option(s) before applying

**Hybrid Fix** (modal default – known locus + open patch, fix-and-sweep, or layered):
- Phase A (Directive): nail down reproduction + suspected layer/file:line + symptoms + Claude's proposed patch
- Phase B (Investigative): Codex confirms root cause via layer-ladder or grep-for-siblings, validates or replaces Claude's proposed patch, applies once invariants stay safe
- Use this shape when prompt-writer sees the broken surface but lacks confidence in the exact patch (most real bugs)
- Example phase labels: "Phase A (Directive): patch at file:line. Phase B (Investigative): grep for sibling occurrences across module, propose remediation."
- Codex proposal step is load-bearing – protects against prompt-writer's wrong-fix gamble

**Minimal-diagnosis Fix** (trivially mechanical: rename, single-line null guard, typo, signature-only shift):
- Phase A: broken/corrected code side-by-side at file:line
- Phase B (still mandatory): Codex sanity-checks patch against stated cause + greps for sibling occurrences (10-line scope is fine) + reports before applying
- Goal form: "validate the patch matches the stated cause, sweep for siblings, apply when confirmed"
- Cost of Phase B here is near-zero; benefit is catching Claude's "obvious" patches that aren't

**Investigative Fix** (symptoms given, root cause fully open):
- Ship reproduction + symptoms + invariants + done-when, leave HOW open
- Goal form: "reproduce the bug, find root cause, propose fix, apply once user confirms or invariants stay safe"
- For systematic root-cause work: pair with a systematic-debugging flavor – hypothesis → instrumentation → fix → regression test
- Data-surface bugs (materialized view / cache / snapshot): layer-ladder verification (`COUNT(*)` at raw → canonical → dedup → MV → API) becomes the investigation skeleton. Past incident: rebuilding the dedup layer alone left a downstream aggregate stuck at the wrong count because the real root was a pricing-drift one layer deeper (canonical vs base table). Climb every layer of a data pipeline before declaring the surface fixed.

### Build
- Cite design doc
- Phase: A (data/SQL) → B (API) → C (UI)
- Paste schemas verbatim from codebase
- Include gotchas: naming quirks, connection-pooler limits (e.g. PgBouncer prepared-statement caveats), coordinate systems
- Surface material ambiguity as labeled options with safest default
- Done-when: specific API/UI output
- UI work requires observable proof (browser/curl/screenshot) beyond build success
- Runtime tuning requires before/after metrics
- **Plan→audit→revise→execute for multi-phase arcs.** Spec over 40 lines driving 2 or more sequential prompts on shared files: run an audit-only Codex pass against the spec BEFORE the first execution prompt. Catches fictional APIs, wrong schemas, duplicated source-of-truth, stale baselines. Validated repeatedly – a pre-execution audit pass on large UI specs routinely catches 10+ P1 issues before a single line is written. See anti-patterns.md.
- **UI work (page/template/component/layout): embed a Mobile UX checklist verbatim.** Paste your mobile-UX checklist as a `## Mobile UX (required)` section in the prompt. Add a small-viewport (e.g. 375×667) before/after screenshot capture to Done-when. Verification: screenshot diff is the gate, NOT dimension-based pass-rate. Past incident: a mobile-UX arc shipped 23 retrofit commits across 19 templates because the checklist wasn't enforced upfront; a later visual-chrome diet reclaimed ~350px of above-fold space on the top templates – work no per-cell dimension audit could have surfaced. Enforce the checklist before the first build prompt, not after.

### Ops / Tuning
- Refresh live baseline first – never tune against stale docs/memory
- Constrain change surface: list allow/deny explicitly
- State invariants tuning must not weaken
- Before/after metrics: duration, yield, error buckets, queue depth
- Deploy + smoke required (local not enough)
- Rejection criteria: when to narrow or rollback
- **Seed tables with materialized-view deps: CREATE+RENAME swap, never DROP CASCADE.** One transaction. On Postgres, verify dependencies via `pg_rewrite` (the rule that binds the view to the table), not `pg_depend` by name – name-based checks miss MV-to-MV chains.
- **View→MV cutover with backup snapshots: legacy bridge pattern.** `CREATE MV X_new; CREATE INDEX; ALTER X RENAME TO X__legacy_DATE; ALTER X_new RENAME TO X; CREATE OR REPLACE VIEW X__legacy_DATE AS SELECT * FROM X;`. Preserves object IDs for dependency-bound consumers.
- **Ingest/write patches: audit ALL insert paths.** `grep -rn "INSERT INTO {table}\|COPY .* {table}"`. The obvious cleaning/loading script is rarely the only writer. Past incident: a pricing-persistence patch re-regressed twice because a second insert path was never audited; the persistence contract has to be enforced at every writer.
- **Parallel-fire matrix in Risks** when 2+ prompts fire together. Defaults: base-table write × MV refresh = serialize; UPDATE on A × CREATE on B = parallel.
- **Deploy chains: prefer server-side `git fetch + reset --hard origin/main` over rsync-from-local** when parallel sessions may edit the local working tree. Rsync ships mid-edits. Server-pull-from-origin decouples deploy from local state – only origin matters. Requires an SSH deploy key on the server (not HTTPS – no creds). Past incident: a v1 deploy chain specified rsync and halted on a mid-edit file during a parallel session; switching to server-pull-from-origin made it immune.
- **Throttled-network parallelism: classify bandwidth-vs-connection BEFORE picking direction.** Bandwidth-throttled profiles (e.g. emulated Fast 3G / Slow 3G with hard Mbps caps) mean lowering parallelism HURTS (pipe under-utilized). Connection-throttled limits (HTTP/1.1 6-conn cap, server connection pool, CDN-edge fan-out) mean lowering parallelism HELPS. Require a 2-point empirical sweep (low + high) in Done-when. Past incident: lowering image-request parallelism to "add headroom" on a bandwidth-throttled connection regressed latency by over a second – the pipe was under-utilized, not contended; raising it fixed it. See anti-patterns.md.
- **Real-device gate before architectural perf prompts (gesture/animation/touch).** Run a 5-min real-device informal test before authoring any architectural perf prompt triggered by a headless-browser finding on gesture/animation/touch/scroll. Headless is bandwidth-accurate but gesture-inaccurate. Bundle KB / network waterfall / paint timing remain trustworthy. Past incident: a "gesture jank" finding from a headless run was a headless artifact; the same interaction was smooth on a real phone – the real-device check saved an entire wasted perf arc. See anti-patterns.md.

### Audit
- Prescribe output format: exact table columns, section names, rubrics
- PASS/FAIL gates (not "needs improvement")
- List every file in scope, grouped
- Read-only: add `DO NOT edit files` constraint
- Numbered scoring rubric with thresholds
- Label verification level explicitly – no generic "verified"
- **Internal sources first.** Audit your own tables/views/APIs/renderers BEFORE external probes. Past incident: a naming audit probed 4 external sources and missed an internal lookup table and an internal lookup API that held the answer.
- **Lock schema verification.** Include `\d table_name` (or your DB's describe command) + sample rows + column-dominance upfront. A wrong schema assumption becomes an audit-wide false positive. Past incident: a check filtered on a code column that was actually stored as text in a differently-named column, invalidating the whole pass.
- **Re-anchor HEAD on completion.** Capture `git rev-parse HEAD` at start AND end. If different, re-verify source-file findings against the new HEAD. Past incident: an audit anchored at a stale commit and reported 3 of 7 HIGH findings that were already fixed on the current HEAD. See anti-patterns.md.
- **Stream report writes; don't buffer.** Require "write report as you go, do NOT buffer in memory" to survive the context ceiling. Past incident: a long audit ran for two minutes and died before its single buffered Write, losing the whole report. See anti-patterns.md.

### PR-series
- Number PRs: "PR 1 of 5" + summary table
- State boundary: this PR touches / doesn't touch
- Zero user-visible impact for early PRs: data → types → API → routes
- Merge order: which PR depends on which
- One prompt per PR
- **Skip-and-continue on per-commit gate trips.** When a prompt covers N ordered commits: "Commits independent. Risk gate on one = skip that commit, continue with the next." Reserve session-halt for destructive/irreversible ops only. Past incident: a multi-commit UX wave lost its last several commits because one mid-series risk gate was worded as a session-stop instead of a skip-and-continue.

### Refactor
- State invariant: "behavior unchanged, only structure"
- Rewrite cleanup asks: "build inventory, rank by confidence/risk, implement low-risk only"
- Default low-risk; report medium/high separately
- Show before/after structure
- List all consumers (every import)
- Verify with `rg` pattern + tests
- **Cross-layer check:** if the refactor touches a DB column, a shared type spanning layers, an API contract, OR an identifier propagated into generated content (templated pages/articles/PDFs) → use the Cross-Layer Refactor Template (references/prompt-templates.md). The plain template assumes consumers = code imports; it misses SQL `FROM`, doc prose, and template interpolation. A Phase 0 SCOPE AUDIT enumerates all such layers before the destructive step. See anti-patterns.md.
- **State-sync refactor: rg enumeration, NOT a curated file list.** For shared state slice / URL schema / event marker contract refactors, the prompt MUST include an `rg` enumeration of all writer paths in Phase 0. Curated file lists drafted from a prior audit's RESULTS miss adjacent writer paths. Past incident: a spec listed 8 files for a URL-writer refactor; `rg` found 20 writers and the true root file wasn't in the spec at all, costing 4 fix waves. See anti-patterns.md.
- **Marker pattern: grep ALL handlers binding the same event.** When introducing a catch-all suppression marker (e.g. an `event.__xHandled` flag), enumerate every handler binding to that event before claiming the marker contract complete. Past incident: a marker rollout took 3 waves to find 3 separate handlers and writers on the same event. See anti-patterns.md.
- **Diagnostic-before-fix after 2 partial waves.** If fix wave 1 lifts the score but doesn't close + wave 2 also lifts but doesn't close → STOP fix prompts; pivot to a diagnostic (e.g. a timeline trace that captures the call stack at the offending mutation). Past incident: waves 1 and 2 chased symptoms; a trace in wave 3 identified the ranked root causes immediately. See anti-patterns.md.
- **Local audit beats prod-deploy-wait for state/UX verification.** When deploy is user-gated, prefer a local dev-server audit for cycles shorter than the deploy-wait time. It's HEAD-pinned with no CDN cache. Past incident: the final re-audits of a refactor ran on localhost, saving deploy lag and eliminating cached-old-behavior false positives. See anti-patterns.md.

## PLANS.md (for multi-hour tasks)

Required sections:
1. **Context** – fully self-contained
2. **Progress** – checkboxes with timestamps `- [x] (2026-04-02 14:00Z) Created migration`
3. **Steps** – prose narrative + full repo-relative paths + explicit cwd
4. **Decisions already made** – locked choices; honor them as load-bearing
5. **Surprises & discoveries** – Codex updates as it finds unexpected
6. **Validation** – observable proof per checkpoint (transcripts, expected output, `rg` counts)

Rules: additive-then-subtractive steps, tests pass at each step. Each step independently verifiable for restart. Full repo-relative paths only.

## Quality checklist

Before outputting:
- [ ] Goal + Success means + Stop when block at the top
- [ ] Mode (Directive | Investigative) chosen and noted
- [ ] Every file path verified (read it)
- [ ] Every function/variable verified at stated location
- [ ] Code snippets pasted from current file state
- [ ] DB connection details from AGENTS.md / your infra-access notes if needed
- [ ] Exact error/output pasted for bugs
- [ ] Prerequisite state check if prompt depends on worktree/branch/prior task
- [ ] Assumptions + Invariant + Risk Gate + Repo-mismatch explicit
- [ ] Material ambiguity surfaced as labeled options
- [ ] Not-in-scope stated
- [ ] Asks phrased as actions Codex executes next (open-ended phrasing rewritten as concrete steps)
- [ ] Constraints cover project gotchas (references/anti-patterns.md)
- [ ] Done-when runnable with expected output
- [ ] UI work → observable verification beyond build success
- [ ] Live counts/durations/status → fresh measurement + timestamp
- [ ] Verification level stated explicitly
- [ ] Commands use `rg` or exact repo-validated values
- [ ] Reasoning level noted for complex tasks
- [ ] Output saved to your design-docs dir as `codex-{kebab-name}.md`
- [ ] Read-back pass: every sentence names a destination or step toward it; decorative ALWAYS/NEVER/MUST demoted

## Anti-patterns (full list: references/anti-patterns.md)

1. Fabrication – citing features/data sources that don't exist
2. Error propagation – trusting design doc without verify
3. Scope creep – "helpful" refactor of unrelated code
4. Subjective product calls – Codex executes analysis and coding well; route final UX/copy/branding judgment calls to user or Claude
5. Stale references – lines/signatures drift between sessions
6. Preamble bloat – narration in the task body
7. Directive prescription on novel territory – choosing Directive mode when HOW is genuinely open forecloses better paths Codex would find

## Output

Save to your design-docs directory as `codex-{kebab-case-name}.md`. Self-contained – paste-and-run.

## Related skills

- **retro-distill** – run a self-distillation retrospective after a major chunk of Codex work to feed lessons back into these category rules
