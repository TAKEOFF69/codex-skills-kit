---
name: codex-prompt-anti-patterns
description: "Battle-tested anti-patterns for delegating work to OpenAI Codex (and any agent that reads AGENTS.md / .agents/skills). A numbered taxonomy of real failure modes, each with how it happens, an illustrative incident, and the prompt-level guard that prevents it. Read when authoring a Codex task prompt, debugging why a delegated task shipped wrong, or hardening a prompt template. Companion reference to the codex-prompt skill; cross-references retro-distill."
metadata:
  version: 0.1.0
---

# Codex Anti-Patterns

Real mistakes distilled from many delegated Codex tasks. Every prompt should guard against the relevant ones. Each entry: how it happens, an illustrative incident (de-identified), and the prompt-level guard.

These guards are written for Codex but apply to any coding agent that runs locally with full repo access and executes without clarification turns.

---

## 1. Fabrication

### 1a. Feature fabrication
Happens: Codex adds features/sections/data sources that fit the pattern but don't exist. It fills gaps creatively instead of flagging them.
Example: a report section that "obviously belongs" gets re-added by Codex, but there's no adapter, no rules, and no data source behind it. Every generated report then renders an empty/placeholder value for that section.
Guard:
- `DO NOT add new sections, features, or data sources not explicitly listed in this prompt`
- `If a referenced data source does not exist, flag it as MISSING – do not create a placeholder`

### 1b. Stats-from-memory (prompt-author side)
Happens: the prompt's Context cites a statistic from recall. The live data store returns a different number. Codex either ships the wrong figure or wastes cycles flagging the discrepancy.
Example: a design doc claimed a headline count (e.g. "3.4M transactions") from memory; an audit against the live database found the real figure was far lower.
Guard: every Context/Constraints stat must either be marked "query live at render" OR include its producing query plus a timestamp.

### 1c. Phantom DB column / file path
Happens: the prompt cites a `table.column` or `path/file.ts` the author assumed existed. Codex trusts the prompt and hits a FROM/import error.
Example: a design doc cited two columns on a region table that didn't exist; the real source was a small locative-formatting helper module elsewhere.
Guard:
- Inspect the schema (`\d table`) for every cited column before writing the prompt
- `ls`/`glob` every path in the "Read first" list before writing
- Uncertain → wrap as `{EXISTS? verify}` and require Codex to audit before relying on it

---

## 2. Context-window buffer-then-write

Happens: a long audit buffers findings in context and intends to Write at the end. The context window fills and the run dies before the Write. Zero output.
Example: an audit ran for two minutes, hit the context ceiling, and produced zero output – all findings were lost.
Guard: require streaming write.
```
Write report straight to output file as you go – do NOT buffer in memory.
One table section per audit area, appended as each section completes.
```
Plus compress the prompt itself (tight-prompt marker, keep audit prompts to roughly 150 lines max).

---

## 3. Error propagation from design docs

Happens: Codex trusts a design-doc claim without verifying it. The design is wrong, so the implementation is wrong.
Example: a design doc cited the wrong legal/regulatory exemption rule; the error propagated through the whole first implementation phase and was caught only during a later fix phase.
Guard:
- Verify legal/regulatory citations against the source text (statute, spec, RFC), not the design doc
- If a design claim conflicts with the code, trust the code

---

## 3b. Scope creep

Happens: Codex "helpfully" refactors surrounding code, adds error handling, renames vars, or adds docstrings to files it only read.
Guard:
- Stay within the listed files. Extras only if required for correctness; report why.
- No comments/docstrings/type annotations on code you didn't change
- No refactor/rename/"improve" of adjacent code

---

## 4. Open-ended creative decisions

Happens: Codex produces inconsistent, low-quality results on "which approach is best?" or "what should we prioritize?". It needs rubrics, not open choice.
Example: an asset-ranking task didn't validate its recommendations against the actual rendering pipeline's capabilities – it recommended an output format the renderer couldn't produce.
Guard: give rubrics, not options.
- Score with: [specific criteria]
- PASS/FAIL, not "needs improvement"
- Priority: CRITICAL (data/security) > HIGH (wrong results) > MEDIUM (UX) > LOW (cosmetic)

---

## 5. Stale references

Happens: line numbers, signatures, and paths drift between sessions. Prompts written from memory (not fresh reads) reference outdated state.
Guard:
- Re-read every cited file before writing the prompt
- Include current code snippets, not paraphrased ones
- Never cite line numbers from a prior session

---

## 6. Preamble / status-update bloat

Happens: prompting Codex to "explain your plan" or "provide progress" generates long preambles, wastes tokens, and can cause an early stop.
Source: OpenAI prompting guidance.
Guard: never prompt for "first, explain your approach", "summarize what you'll do", or "update me on progress".

---

## 7. Cross-layer refactor scoped as code-only

Happens: a DB-column / shared-type / API-contract rename is scoped as a code-import refactor. The consumers list only enumerates code importers. It misses: upstream DB objects exposing the same identifier, generated-content templates that interpolate the token, design docs, glossaries, and analytics events. The code gets renamed; the DB, docs, and content stay on the old name.
Example: a column rename (`old_count → new_count`) was first scoped as a handful of downstream materialized views plus app code plus two docs. It missed an upstream context view, the project conventions file, an architecture doc, and content templates interpolating the token. A reviewer caught it before send.
Why: the default Refactor template assumes Consumers = code imports. It doesn't map to SQL FROM, doc prose, or template interpolation.
Guard: for refactors touching a DB column/table name, a shared type across layers, an API contract, OR an identifier embedded in generated content – use the Cross-Layer Refactor template (see references/prompt-templates.md). Its Phase 0 SCOPE AUDIT enumerates: A. DB objects (dependency-graph + migrations grep), B. App code, C. Docs, D. Content/templates, E. E2E baseline. Destructive phases gate on the Phase 0 live enumeration.
Heuristic: identifier appears in SQL, a doc, or a generated-content token → Cross-Layer. Code-only imports → plain Refactor.

---

## 8. Audit without prescribed format

Happens: no output format means free-form analysis – hard to compare across runs, bad for go/no-go decisions.
Guard: always prescribe exact table columns, section names, numeric rubrics, and PASS/FAIL gates.

---

## 9. DB operations without connection-pooler awareness

Happens: prepared statements, TRUNCATE, or COUNT(*) issued through a transaction-mode connection pooler (e.g. PgBouncer) silently break or drop connections.
Guard:
- Disable prepared statements at the driver (e.g. `prepare_threshold=None` in psycopg)
- Avoid TRUNCATE, avoid COUNT(*), avoid prepared statements through the pooler
- Set an explicit `connect_timeout`
- Copy current connection details from your project conventions file (e.g. AGENTS.md or an infra-access doc) after verifying them

---

## 10. Coordinate-system confusion

Happens: data in one CRS is sent to an API expecting another (e.g. WGS84 lat/lng to a service that wants a projected national grid), or vice versa. Elevation/terrain lookups silently return 0 for the wrong CRS.
Guard:
- Store all coordinates in one canonical CRS in the DB (WGS84 / EPSG:4326 is a common choice)
- Document, per external service, which CRS and axis order it expects (some projected grids use x=northing, y=easting)
- Pin the exact service host/endpoint when a provider has multiple that behave differently

(Generalize: any time data crosses a coordinate, unit, timezone, or encoding boundary, name the conversion explicitly rather than assuming the consumer matches the producer.)

---

## 11. Localized content without diacritics / correct character set

Happens: Codex writes ASCII first and plans to add diacritics/accents/non-Latin characters later. That never happens.
Guard: require the correct character set from the start (proper diacritics, accents, or script). Do not allow an "ASCII now, fix later" pass. If the project has a content/localization skill, point Codex at it.

---

## 12. Hardcoded CTA / pricing / config values

Happens: Codex hardcodes a call-to-action label or a price string instead of reading from centralized config.
Guard:
- Name the single config source for CTA labels and for pricing, and require Codex to read from it
- Never hardcode CTA text, hrefs, or prices in components/templates

---

## 13. Dual-implementation drift

Happens: the same logic lives in two places (e.g. SQL and application code, or Python and TypeScript). Codex updates one. They drift silently.
Example: a scoring routine existed as both an application-layer function and a database function; Codex updated the DB weights but not the application-side fallback.
Guard:
- State the single truth source: "Truth for {X} is {file}. All other implementations MUST match."
- After changes, diff the two implementations to confirm they agree.

---

## 14. Missing prerequisite state

Happens: Codex assumes a prior PR/migration/task was applied. It wasn't. Codex builds on non-existent state and fails silently or returns wrong results.
Example: task B3 depended on task B2 introducing a field; running B3 without B2 produced type errors because the field didn't exist yet.
Guard:
- `Depends on: {list prior tasks}. Verify applied before starting.`
- If a referenced field/function doesn't exist: STOP, report, don't create it
- If the task relies on local worktree state, do a `git status` check before writing the prompt

---

## 15. Architecture churn / revisiting settled decisions

Happens: Codex reconsiders locked architectural decisions. It proposes alternatives and restructures deliberate design.
Guard: list locked decisions explicitly.
```
Decisions already made (DO NOT revisit):
- {Decision 1}: {rationale}
- {Decision 2}: {rationale}
```

---

## 16. Silent success without observable proof

Happens: Codex reports "done" after a build passes without verifying that behavior actually changed. A passing build is not a working feature.
Example: the build passed but a new chart filter was never wired to the UI; Codex stopped at "build passes" without a render check.
Guard: after build, verify something observable.
- `rg -n "{expected}" {scope}` shows N matches
- `rg -c "{pattern}" {file}` returns N
- a `curl`/query command that exercises the new behavior

---

## 17. Verification overclaim

Happens: Codex reports "verified" when only one layer completed (code read or typecheck). Browser, live DB, and production stay unverified.
Example: a change was structurally verified against code and a test run was cited, but the session never did a local browser pass – yet it was reported as verified.
Guard: state the exact level reached: code read | local tests | browser pass | live DB check | production smoke. Never collapse to a generic "verified".

---

## 18. Stale operational metrics

Happens: the prompt reuses counts/durations/status from docs without refreshing from live state. The session starts stale.
Example: a buildout doc carried counts from weeks earlier; the figures were refreshed from the live source-of-truth before the handoff prompt was written.
Guard:
- Live counts/durations/status → refresh from the source-of-truth before writing the prompt
- Record when the baseline was checked
- If docs differ from live, update the docs in the same session

---

## 19. Schema assumptions without verification

Happens: the Codex prompt assumes column names, key formats, or table shape. The implementation hits a mismatch.
Examples:
- a renderer assumed a top-level `category` column existed, but the data lived inside a JSONB `properties` blob
- a blending join used short region codes while the context table used full codes – a full rebuild was required to fix it
- a spatial-inference query ran for 40+ minutes before being killed because the join strategy was wrong
Guard:
- Add a "Verify schema first" step: `\d table_name`, `SELECT col FROM table LIMIT 3`
- Include the expected shape plus "If actual differs, STOP and report the mismatch"
- For JOINs: verify key-format compatibility with a sample query before the main logic

---

## 20. UI sign-off without browser verification

Happens: the Done-when only requires a build/typecheck, with no visual/browser proof. It "passes" but the bugs are invisible to the build.
Examples: multiple UI workspace sessions shipped without browser verification; a header-removal was signed off as complete but never actually implemented; a prerendered/cached route variant blocked a rollout and was caught only by live browser QA. A separate "align fills with legend swatches" change passed its paint-expression unit test (hex parity with the legend) yet shipped opacity stops that produced a dark veil over the map at low zoom – the regression lived for days until a human noticed.
Guard: any UI task's Done-when MUST include at least one of:
- a Playwright / browser-automation screenshot of the changed route
- manual verification via a running dev/prod server
- a production smoke via the deployed URL
Build-passes is necessary but never sufficient for UI.

Sharper sub-rule – **visual-output generators give false green from unit tests.** Paint expressions, SVG builders, CSS-in-JS, map style expressions, and color/legend generators: unit tests verify the contract (hex parity, expression structure) but NOT the composed visual result (opacity × basemap × zoom × adjacent layers). Never close out a change to one of these files on unit-test evidence alone – pair it with a screenshot at the specific zoom/mode/viewport the code runs at.

---

## 21. Silent ambiguity

Happens: Codex silently picks one of several materially-different interpretations and implements the wrong thing cleanly.
Guard:
- State allowed assumptions explicitly
- Ambiguity that changes behavior / data shape / API contracts / architecture → list the interpretations before coding
- Can't safely choose → STOP and report the blocker

---

## 22. Overbuilt abstractions

Happens: Codex adds wrappers, indirection, and future-facing config the task doesn't need now.
Guard:
- Prefer deletion/consolidation/narrowing over abstraction
- No wrappers/extension points/configuration unless the task requires it NOW
- A 50-line solution solves it → ship that, not the 200-line version

---

## 23. Adjacent cleanup churn

Happens: Codex uses the task as an excuse to rewrite nearby comments/naming/formatting that aren't required for correctness.
Guard:
- Every changed line traces to the task
- No adjacent comment/format/naming rewrite unless required for correctness
- Unrelated cleanup found → report it separately, don't bundle it

---

## 24. Unilateral cross-taxonomy mapping

Happens: the prompt maps values between two domain taxonomies (one classification system → another, region-code schemes, category systems). The author picks the mapping silently. Codex executes it. Later a user discovers the mapping distorts a user-facing metric – the mapping was a product call, not a mechanical one.
Example: a phase mapped one category into another bucket (an `investment → buildable`-style collapse); because the two categories have distinct price regimes, it inflated a per-area count for an affected location. The fix re-pointed it to a neutral "other" bucket.
Root: a precision point treated as a fork. Cross-taxonomy mappings have ONE right answer per product narrative, and the prompt author is rarely the authority on it.
Guard: if the prompt writes ANY of:
- a `CASE x WHEN 'a' THEN 'b'` crossing two named taxonomies
- a generated column with a mapping expression
- a `TAXONOMY_MAP = {...}` dict

then either paste the mapping table row-by-row with the domain reasoning per row (so Codex can flag wrong bucketing), OR add a "Phase 0: confirm mapping" gate. Add to Assumptions:
```
Cross-taxonomy mapping {source}→{target} is a product decision. If any row feels domain-wrong (category X between buckets Y and Z), stop and surface for confirmation before writing code.
```

---

## 25. Audit anchor drift during parallel execution

Happens: a multi-hour read-only audit anchors its findings to the HEAD captured at START. Other sessions land commits on the main branch DURING the audit. Findings referencing superseded state look real but are stale.
Example: an audit anchored at one HEAD; mid-audit, fix commits landed on main. The report flagged several HIGH findings as real, but the files had already been rewritten – yielding multiple false positives in the report.
Root: a missing repo-freshness check at audit completion.
Guard:
- Capture `git rev-parse HEAD` at audit start AND end
- HEAD changed → re-verify every source-file finding against the new HEAD
- Annotate each finding with the commit hash it reflects
- Source-file findings straddling commits landed during the window → mark "uncertain – verify against HEAD <new-hash>"

Also belongs in the Audit category rules of the codex-prompt skill.

---

## 26. Incremental-render-path dynamic-API break

Happens: a route opts into incremental/static caching (e.g. exports a `revalidate` plus an empty `generateStaticParams()` in Next.js). Some module in the render subtree calls a dynamic runtime API (request cookies/headers, query params, no-store hints, draft mode), directly or transitively. The production render throws a dynamic-usage error, ships an uncacheable response, and returns HTTP 500 for crawlers.
Example: listing/filter routes were deployed with incremental caching plus a revalidate window. Reading query params in a server component broke every URL in production; the local dev server did not reproduce it.
Root: dynamic APIs are build-time legal but runtime-enforced under incremental caching; no static check catches it.
Guard:
- Any prompt flipping a route from dynamic to incrementally-cached MUST include a render-subtree grep step for dynamic-API calls (request cookies/headers, draft mode, no-store hints, query-param reads, force-dynamic) across the route dir and its lib imports
- Done-when must include a production cache-HIT check on a second crawler fetch
- For listing aggregators / filter pages: keep URL query state on the client, never read query params in a server component on a cached route
- Risk Gate: if the fix would touch a shared lib that several route families import, stop and report the blast radius before patching

---

## 27. Threshold guard hides a data-integrity root cause

Happens: a sitemap / page / aggregate shows "N zero items." The reflex is a threshold gate (`count >= 3`). The gate ships crawl-budget relief but masks the real bug: a broken join, a canonical-code mismatch, or a scraper attachment gap. The root bug keeps corrupting data while the sitemap looks clean.
Example: hundreds of regions were flagged zero-item, so a `count >= 3` guard shipped in hours. A later data-integrity diagnosis found that almost all of them actually had items attached under sibling region codes (an aggregate code vs its variant codes). The real fix was a code-family rollup, and most of the flagged regions were recoverable.
Root: symptom-level fixes ship in hours; structural fixes need an audit-then-fix arc. Convenience wins.
Guard:
- When a threshold/guard prompt is drafted, file a parallel read-only diagnostic prompt that answers "why is the count low?" – sample the filtered rows, check for surprises like active markets being excluded
- The threshold gate and the root-cause fix can land in the same session, but MUST be two separate prompts so the root cause is forced to air
- General lesson: when an identifier scheme has variant/aggregate forms (a parent code plus suffixed children), one record can be filed under any of them – a join that picks one form silently loses the rest

---

## 28. Dead instrumentation – observability without wired behavior

Happens: a prompt (or a prior round) adds an observability hook (a `data-*` attribute, a counter variable, a badge slot) but never wires the underlying behavior change. The hook reads zero forever. A future round assumes the feature works because the instrumentation exists.
Example: a chart shipped a `data-clipped-points={clippedPointCount}` attribute plus `const clippedPointCount = rows.length - drawableRows.length`, but `drawableRows = rows` (identity assignment), so the counter always read 0. The next round didn't catch it because the contract checked attribute presence, not the value-vs-cap. A later round had to add the actual filter that the instrumentation had already been shaped for.
Root: hook-then-feature ordering, with the feature step skipped or deferred. The observability promises a behavior that doesn't exist.
Guard:
- For any prompt that adds a `data-*` count/flag attribute: pair it with a contract assertion that the value is non-zero / positive / within range, not just "attribute present"
- For "filter / clip / cap" features: name the actual filter location explicitly (`drawableRows = rows.filter(...)`) – don't leave it as renaming `rows → drawableRows` with an identity assignment
- Done-when must read the attribute and assert against the cap, not just check that the attribute renders

---

## 29. Forked UI component without canonical-parity audit

Happens: a simplified/embed/mini variant is forked from a canonical component. The prompt scopes it as "render the same data, simpler". The fork drops layer registrations, paint expressions, label/overlay layers, or interaction handlers without listing what was intentionally dropped. A user notices the missing parity in a later QA round.
Example: a forked map component shipped only fill and line layers. It missed the canonical's filter on the base fill layer, a dashed special overlay, and a symbol layer carrying code labels. The next round had to re-port all three from the canonical.
Root: the fork prompt treats the canonical as a reference (use as inspiration), but layer/handler/expression registrations are locks (port verbatim or explicitly drop with a reason).
Guard: for any prompt that creates or edits a forked UI variant, include a "Parity audit" subsection.
```
Read canonical: <path-to-canonical-component-or-layer-module>
Enumerate every: layer registered, paint expression used, event handler attached, effect run.
For each, mark: PORT / DROP (with reason) / SIMPLIFY (with diff).
Anything not listed = port-verbatim.
```
Heuristic: when the fork sits next to the canonical in the same directory tree (e.g. `components/map/*`, `components/charts/*`), the canonical is a lock to mirror, not a fork to draw from.

---

## 30. Wiring-blind file selection – "add to existing X file" without verifying X is reachable at runtime

Happens: the prompt says "add a helper to existing `src/proxy.ts`" because the file already has related logic. Codex obeys and ships dead code: that file was an orphan from a prior platform migration and is never imported by the actual edge/middleware entry point. The helper exports correctly, tests pass, the build succeeds – but at runtime the function is unreachable and production behavior is unchanged.
Example: a redirect helper was added to an orphaned proxy module that had been stranded during a hosting-platform migration but never deleted. A live request kept returning 404 after deploy. Two follow-up commits were needed to wire the helper into the real middleware entry point, after time was wasted chasing a deploy-lag hypothesis before realizing the module was dead code.
Root: pre-existing files after a refactor are not always reachable. Prompts that say "extend X" assume X is wired; Codex doesn't verify.
Guard: for middleware / edge / route-handler / API additions, the prompt MUST lock the entry-point file by its framework convention name AND require Codex to grep for at least one runtime import before extending.
```
## Wiring verification (REQUIRED before edits)
This change must reach the request path. Before editing:
1. Grep for runtime imports of the target file (exclude test dirs).
2. If 0 runtime importers, the file is dead code post-refactor – STOP and report.
   Use the framework convention path (the real middleware / route-handler / entry file) instead.
3. For middleware / edge runtime: keep helpers inline OR import only from pure-function
   and generated modules. Heavier modules tree-shake unpredictably at the edge.
```
Heuristic: anytime a prompt names a file outside the framework's standard convention paths (the canonical page/route/middleware/layout files), require explicit wiring proof.

---

## 31. Numeric threshold change without live calibration

Happens: the prompt locks a threshold (gate, retry count, batch size, score floor) based on intuition or stale memory. The number turns out wildly off when applied to real data – e.g. it drops 70% of rows when 30% was intended. It either ships and degrades the product, or trips a sanity check and burns a roundtrip.
Example: intuition said a minimum-datapoints gate should be 20. A reviewer flagged "calibrate empirically". A query on live data showed 23% survival at 20 vs 28% at 15, so it was locked at 15 – shipping at 20 would have dropped an extra few percent of the universe for marginal gain.
Root: thresholds are locks that look like forks. Without live data, a "reasonable-sounding" number passes review but produces emergent behavior at scale.
Guard: for any prompt that locks a numeric threshold against live data, include a calibration step BEFORE implementation.
```
## Calibration (REQUIRED before locking threshold)
Run on live data, paste output in the commit message:
SELECT
  COUNT(*) FILTER (WHERE <condition with N=15>) * 100.0 / COUNT(*) AS pct_15,
  COUNT(*) FILTER (WHERE <condition with N=20>) * 100.0 / COUNT(*) AS pct_20,
  COUNT(*) FILTER (WHERE <condition with N=25>) * 100.0 / COUNT(*) AS pct_25
FROM <relevant table>;

Healthy survival: 50-70%. Below 30% = too brutal, raise N. Above 85% = too lenient, lower N.
```
Bias: when a reviewer asks for the survival query and the prompt assumes the answer ("expect 50%+"), still surface the actual numbers.
Past incident: thresholds locked from intuition (a sampling-rate tune and a content gate) both needed a live survival query to land safely.

---

## §29 Network-throttling tuning: direction-of-effect

When tuning parallelism knobs (`maxParallelImageRequests`, fetch concurrency, worker pool) for a throttled-network target: **classify the throttling axis before picking the direction of effect.**

- **Bandwidth-throttled** (e.g. a Fast 3G profile capping ~1.6 Mbps, Slow 3G ~400 Kbps): the pipe is the bottleneck. Lowering parallelism = pipe under-utilized = SLOWER. Raise parallelism to fill the pipe.
- **Connection-throttled** (HTTP/1.1 6-connection limit, a server pool, CDN edge contention): connections are the bottleneck. Lowering parallelism = better per-request latency = FASTER.

Don't infer from intuition ("lower for headroom"). For Codex Ops/Tuning prompts on throttled networks, **require a 2-point empirical sweep (low + high parallelism on the same profile) in the Acceptance/Done-when section** – never a single point picked from theory.

Past incident: raising parallelism was confused for "adding headroom" by lowering it on a bandwidth-capped profile, which regressed first-tile latency by over a second. The fix was to raise parallelism, because the profile was bandwidth-capped, not connection-capped – the pipe was under-utilized, not contended.

---

## §30 Real-device gate before architectural perf prompts (gesture/animation/touch)

Before authoring architectural perf prompts (gesture rewrite, animation overhaul, touch-handler refactor) triggered by **headless browser-automation** findings: **insert a 5-minute real-device informal test as the gate.**

- Headless browser automation is **bandwidth-accurate** but **gesture-inaccurate**. Touch-event simulation, GPU compositing, and frame pacing diverge from real mobile WebKit/iOS and real Android.
- Findings on bundle KB / network waterfall / paint timing / layout shift remain trustworthy – the gate applies only to gesture/animation/touch/scroll feel.
- Decision rule: if the real device PASSES, mark the headless finding as "headless artifact" in the audit caveats and SKIP the architectural prompt. If it FAILS, the prompt is justified.
- Document the gate result in the audit caveats with PASS/FAIL evidence (timestamp, device, brief observation).

Past incident: a "gesture jank" finding from headless automation turned out to be a headless artifact – the real phone scrolled smoothly. The real-device gate saved an entire gesture-investigation arc (one to two prompts plus several measurement cycles).

---

## §31 Plan → audit → revise → execute for multi-phase Codex arcs

For any spec longer than ~40 lines that drives multi-phase Codex execution (two or more sequential prompts touching shared files): **run a Codex spec-audit pass against the spec BEFORE writing the first execution prompt.**

Pattern:
1. Write the spec (in your design-docs dir, e.g. `{your design-docs dir}/{arc}-spec.md`)
2. Audit-only Codex prompt against the spec – verify file refs, function signatures, data-shape claims, locked-decisions consistency, baseline math, and any fictional API surface
3. Revise the spec (`{arc}-spec-vN.md` or in place) absorbing the audit findings
4. Execute the phased Codex prompts against the revised spec

Why: an audit before code is cheap (one read-only Codex run, ~10-15 min). Rework after Codex shipped wrong code is expensive (revert, re-prompt, re-test, regression-audit). Validated repeatedly – spec audits have caught fictional APIs, references to fields that don't exist, duplicated sources-of-truth, and stale baselines before any code was written.

Threshold for audit-skip: a single-prompt mirror/additive task with the `<!-- tight-prompt -->` marker – no audit needed. A multi-prompt arc with novel data shapes / new source-of-truth files / new registry entries – audit mandatory.

**Spec-audit findings must land in the spec, not in the first execution prompt.** When a revise absorbs most of a spec audit's findings but lets one drift into an execution-prompt addendum, that one missed finding tends to re-surface across multiple fix waves. Letting spec-audit findings drift into execution-prompt addenda re-introduces the original error pattern at the prompt layer. Always revise the spec BEFORE drafting the first execution prompt.

---

## §32 State-sync refactor: `rg` enumeration BEFORE a curated file list

For ANY refactor touching a shared state slice / URL schema / event-marker contract: **the spec MUST include `rg` output enumerating all writer paths before any file:line edits**. Curated file lists drafted from re-audit RESULTS will miss adjacent writer paths.

Past incident: a state-sync phase listed 8 files for a selection state-sync. The first wave ran an `rg` across all the relevant setters/writers and found 20 distinct URL writers. The true root writer was not in the spec at all. Cost: four fix waves to fully resolve.

**Required `rg` patterns for state-sync prompts (adapt KEY / KIND to your codebase):**
```bash
rg -n "searchParams\.set\(['\"]<KEY>['\"]" <src dir>
rg -n "router\.(push|replace).*<KEY>|history\.(push|replace).*<KEY>" <src dir>
rg -n "kind:\s*['\"]<KIND>['\"]" <src dir>
rg -n "deriveX|XFromCoords|XFromViewport" <src dir>
rg -n "useEffect.*<state-slice>" <src dir>
```

Classify each match: WRITER_DIRECT / WRITER_DERIVED / WRITER_REACTIVE / DISPATCH / LEGITIMATE. Document the classification in the commit message of state-sync refactor commits.

Codex prompts for state-sync MUST include the classification step in the Done-when section.

**§32b – HEAD-pin spec refs.** Capture `git rev-parse HEAD` at spec drafting. Re-anchor at every revise. Line drift of ±3-10 lines is normal between spec drafting and code state – don't let it surprise execution. Repeated drift across waves (e.g. a citation moving `:310-331` → `:357-382` → `:354-368`) is common. Solution: include drift-tolerance in prompts ("if a cited line is ±10 from the spec ref, verify by surrounding context, not the exact line").

---

## §33 Marker pattern across multi-bound handlers – grep ALL bindings

When introducing an event-marker pattern (e.g. `event.originalEvent.__handlerNameClickHandled`) for catch-all suppression: **grep ALL handlers binding to the same event BEFORE claiming the marker contract is complete.**

Past incident: a wave guarded one region-fallback catch-all handler via a marker check, but a separate handler bound to the same fill click event was missed. The next wave added the marker check at the second handler. A later wave found a third writer via a different selection function. Three discoveries, four waves.

**Required pre-edit step (adapt to your map/event library):**
```bash
rg -n "addLayerHandler|map\.on\(['\"]click['\"]|onLayerClick" <map components dir>
```

Enumerate every handler binding to the target event. For each:
- Setter handlers MUST set the marker BEFORE flyTo/dispatch (top of the body, not after async work)
- Catch-all handlers MUST check ALL markers (not a subset)
- Extract a shared `hasPointMarker(event)` util to prevent drift across handler bodies

Codex prompts introducing a marker pattern: include the enumeration command plus a classification (setter / catch-all / passthrough) in Done-when.

---

## §34 Diagnostic-before-fix after 2 partial waves

If fix wave 1 lifts the score but doesn't close the target regressions, and fix wave 2 also lifts but doesn't close → **STOP fix-prompts.** Pivot to a diagnostic.

Past incident: two waves chased symptoms (each wave found a new writer site, fixed it, ran the audit, found another). That pattern indicated a systematic blind spot. The next wave used a browser timeline trace that patched `window.history.pushState` and `replaceState` to capture the call stack; it identified ranked root causes per regression immediately, and the following wave found the final writer the same way. Trace overhead was one prompt and ~30 minutes; it likely saved two to three more partial waves.

**Diagnostic prompt template (state-sync surface):**
1. Phase 1 source enumeration via `rg` (per §32)
2. Phase 2 browser timeline trace: patch `history.pushState` + `replaceState` inside `page.evaluate()` for stack capture per URL change; perform the trigger interaction; output the ordered changes with the top 3 stack frames each
3. Phase 3 root-cause ranking per regression with confidence (high/med/low)
4. Output fix recommendations (NOT applied – informational only)

Then write ONE comprehensive fix wave covering the ranked roots. NOT another fix-prompt-then-audit cycle.

Decision rule: count partial-fix waves. After 2, halt fix waves; a diagnostic is mandatory before the next prompt.

---

## §35 Local audit beats prod-deploy-wait for HEAD-pinned verification

When deploy is gated (manual approval, "apply N changes", deploy-after-pipeline-commits), prefer a localhost audit for verification cycles whose turnaround is shorter than the deploy wait.

Past incident: final re-audits ran against a local dev server instead of production. HEAD was pinned to the commit (no CDN cache, no deploy lag, no drift between the audited HEAD and the audited behavior). It saved roughly five minutes per cycle and eliminated CDN-cached-old-behavior false positives.

**Local audit setup template for the Codex prompt:**
```bash
{your dev-server command}   # serve the build locally at a pinned HEAD
```

The audit prompt swaps the production URL for the localhost URL. Use your project's documented dev-server invocation (some bundlers corrupt manifests under certain dev modes – use the mode your project documents as safe). On a stuck port, tree-kill the zombie process before retrying. Cleanup: kill the dev server after the audit.

Tradeoff: edge-middleware and CDN-edge behavior differ between prod and local. For state-sync / click-handler / URL-writer verification, the behavior is identical. For caching / CSP / edge-rules, production is required. Pick local for state and UX flows; pick prod for infra/edge.

---

## §36 Mocked-data unit tests give false green for data-shape-dependent code

Data/ML code (DB → DataFrame → model/transform) has bugs that live in the **real data distribution**, not in the logic. Unit tests that mock the data source verify the *contract* but never reproduce the shapes that actually break: empty categoricals, all-NaN columns, zero-comparable result sets, degenerate frames. "Tests pass" is NOT "fixed" for this code class.

Past incident: a fix resolved a model's categorical-dtype error, and three targeted unit tests reproduced the exact failure and passed – but every test mocked the transaction count and stubbed the feature-fill helpers. After shipping and reporting done, a live test against the real models and DB found that minimal requests (no coordinates, all optional fields NULL → all-missing categoricals → an empty category index) STILL crashed (a vectorize-on-size-0 error). Worse, the new error-to-422 mapping would have masked it as "not enough data" – exactly what the fix was meant to prevent. A second commit was required. The mocks hid it; real data exposed it in one run.

Sharper rule – **for any fix touching a DB-read → feature-frame → model/transform path, Done-when MUST include a real-data smoke, not just unit tests.** The cheap, zero-deploy harness pattern:

```bash
# isolated throwaway clone on the box that has the models + DB, at the exact commit
D=/tmp/verify-$(date +%s); git clone -q <repo> $D && cd $D && git checkout -q <commit>
ln -s <real models dir> $D/<models path>     # symlink the real model artifacts
set -a; . <real env file>; set +a            # real DSN / credentials
PYTHONPATH=$D <python> -c "...call the real entrypoint against the real DB..."
```

This runs the NEW code against the REAL models and REAL DB without deploying (the live service stays untouched). Exercise the degenerate inputs explicitly: empty/NULL optional fields, the smallest-data entity, the missing-coordinates path.

Guard lines for prompts touching this code class:
- `Done-when: real-data smoke against the prod data distribution – run the actual entrypoint, not just mocked unit tests. Exercise: NULL optional fields, zero-comparable entity, missing-coords path.`
- `Error handlers that map multiple failure modes to one user message (e.g. a broad except → "not enough data") MUST log the original exception; a masked code bug looks identical to a data gap.`

---

## Quick reference: standard constraint block

Copy-paste into any Codex prompt; remove non-applicable lines.

```markdown
## Constraints

- Read AGENTS.md for project conventions
- Stay within listed files. Extras only if required for correctness; report why.
- DO NOT add features/sections/data sources not in spec
- DO NOT refactor/rename/"improve" adjacent code
- DO NOT add comments/docstrings to code you didn't change
- DO NOT use em dashes – use en dashes for ranges/clauses
- DO NOT hardcode CTA labels/hrefs/prices; read from centralized config
- Connection pooler: disable prepared statements, no TRUNCATE, no COUNT(*)
- Coordinates: one canonical CRS in the DB (e.g. WGS84 / EPSG:4326)
- Localized content: correct character set / diacritics from the start
- Data source missing → flag as MISSING, don't fabricate
- Repo state differs from prompt → stop and report mismatch
- Verify legal/spec citations against the source text, not the design doc
- Single truth source for {X} is {file}. No parallel implementations.
- Locked decisions: {list} – DO NOT revisit
```
