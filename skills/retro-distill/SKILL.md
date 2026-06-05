---
name: retro-distill
description: "Run a self-distillation retrospective on recent OpenAI Codex sessions (or any Agent-Skills-compatible agent). Use when the user says 'retro,' 'retrospective,' 'distill,' 'what did we learn,' 'review sessions,' 'self-improve,' or after completing a major chunk of work. Covers three modes: quick retro (single session), deep distillation (batch review), and failure analysis. Outputs updates to skills, memories, AGENTS.md, and anti-pattern lists."
metadata:
  version: 0.1.0
---

# Self-Distillation Retrospective

You run structured retrospectives on recent AI coding-agent sessions to extract reusable patterns, anti-patterns, and workflow improvements. This is your self-improvement loop – inspired by simple self-distillation (SSD), where a model improves by sampling its own outputs, truncating the bad tails, and reshaping what remains.

**The loop:** Sessions produce outputs (samples) --> retro identifies what worked and what didn't (truncation) --> learnings get codified into skills, memories, and rules (reshaping) --> future sessions benefit.

## Before Starting

### 1. Determine retro mode

| Mode | Trigger | Depth | Time |
|------|---------|-------|------|
| **Quick** | End of a session, user says "retro" | Review current session only | 2-3 min |
| **Deep** | After 5-10 sessions, user says "deep retro" or "distill" | Batch review of recent session logs | 10-15 min |
| **Failure** | Something went wrong, user says "failure retro" or "what went wrong" | Root-cause analysis of a specific failure | 5-10 min |

Default to **Quick** unless the user specifies otherwise.

### 2. Gather inputs

**Quick mode:**
- Review the current conversation context
- Check recent git log for what was committed

**Deep mode:**
- Read the last 5-10 session logs from your session-logs directory (e.g. `{your session-logs dir}`)
- Read all feedback memories from the memory system
- Read the current anti-pattern lists in any skill `references/`

**Failure mode:**
- Get the specific failure context (error, bad output, wasted effort)
- Read the session log where it happened
- Read the relevant skill/prompt that produced the failure

## Quick Retro Protocol

Run through these four questions for the current session:

### Q1: What worked? (Fork preservation)

Identify approaches that produced good results – especially non-obvious ones the system doesn't already codify. These are "forks" that led to correct solutions.

- Was there a skill that worked well?
- Did a specific prompt structure produce good Codex output?
- Did a debugging approach find the root cause quickly?
- Was there a convention that prevented a mistake?

### Q2: What didn't work? (Support compression)

Identify approaches that wasted time or produced bad results. These are "distractor tails" to suppress.

- Did Codex go down a wrong path? Why?
- Was there a missing constraint that caused scope creep?
- Was there a stale reference that caused confusion?
- Did a skill fail to trigger or produce poor output?

### Q3: Lock or fork misclassification?

The most common failure mode. Check if any part of the session:

- **Treated a lock as a fork** – left something open-ended that should have been constrained (e.g., "choose the best approach" for something with one right answer)
- **Treated a fork as a lock** – over-constrained something that needed exploration (e.g., specifying exact implementation for a design decision)

### Q4: What should change?

**Before picking an artifact, run the skill-update triage.** Memory is the easy default but often the wrong one – memories are passive context whereas skills are active templates that ship their rules into every invocation. If a finding describes a *how-to-do-this-kind-of-work* pattern, it belongs in a skill, not a memory.

**Skill-update triggers (check these first):**

- A prompt this session used a pattern the skill template didn't enforce → **update the skill**, not just memory. Memory won't auto-apply to future prompts; skill content will.
- A prompt template missed a constraint that had to be added inline (e.g., "use a non-destructive swap, not DROP CASCADE", "verify at every dependent view layer", "check internal sources before external") → update the relevant skill's task-type section.
- A workflow produced a pre-commit hook block, lint warning, or CI failure that a better template would have avoided → update the skill.
- A pattern appeared in 2+ sessions in the last week → promote to skill content even if each individual session fixed it with memory.
- A claim the skill makes turned out false or stale (referenced file moved, command renamed) → update the skill.

If a finding passes *any* of the above, default target is skill content. Memory is for project/user/feedback context that applies across many skills, not for skill-internal rules.

Then classify each finding into an action:

| Finding type | Action | Target artifact |
|---|---|---|
| **New reusable pattern (how-to)** | **Add to relevant skill** | `{your skills dir}/{skill}/SKILL.md` or `references/` |
| **New anti-pattern** | **Add to anti-pattern list in skill** | `{your skills dir}/{skill}/references/anti-patterns.md` |
| **Skill template missed a constraint** | **Edit the template section in the skill** | `{your skills dir}/{skill}/SKILL.md` |
| **Stale skill claim (wrong file path, wrong command)** | **Fix the skill** | `{your skills dir}/{skill}/SKILL.md` or `references/` |
| Workflow correction (general, cross-skill) | Save feedback memory | Memory system |
| Project context learned (data, infra, business) | Save project memory | Memory system |
| Convention change (global rules) | Update rules | `AGENTS.md` |
| Stale reference in docs (not in a skill) | Fix or remove | The referenced doc |

> Note on skills directories: OpenAI Codex reads `.agents/skills/` (repo-scoped) and `$HOME/.agents/skills/` (user-scoped); other Agent-Skills-compatible agents use their own conventions. Substitute `{your skills dir}` with whatever your agent loads.

**When in doubt between skill vs memory**: ask *"will future sessions need this as part of doing the work, or as context before doing the work?"* Part-of-the-work → skill. Context-before → memory.

### Quick Retro Output

Produce a brief summary:

```markdown
## Quick Retro: {date}

**Session:** {session description}

**Worked well:**
- {pattern} --> {already codified / NEW: save to X}

**Didn't work:**
- {anti-pattern} --> {already known / NEW: add to X}

**Lock/fork misclassification:**
- {none / description}

**Actions taken:**
- {list of actual changes made}
```

Then **execute the actions** – don't just list them. Update the artifacts.

**Bias correction**: if every action in the retro targets memory and none targets a skill, reconsider. Memory-only retros mean skills stop evolving. At least 1 in 3 quick retros should touch a skill; deep distillations should touch 2+ skills on average.

## Deep Distillation Protocol

### Step 1: Collect session data

Read the last N session logs (default 10, or since last deep retro). For each, extract:

- **Task type** (fix, build, ops, audit, refactor, content, design)
- **Outcome** (success, partial, failure, abandoned)
- **Time spent** (if noted)
- **Tools/skills used**
- **Surprises** (anything unexpected)

### Step 2: Pattern mining

Look across the batch for:

1. **Recurring successes** – patterns that appear in 3+ successful sessions
2. **Recurring failures** – anti-patterns that appear in 2+ sessions
3. **Drift** – skills or rules that sessions are working around (sign they need updating)
4. **Gaps** – situations where no skill existed and the session had to improvise

### Step 3: Frequency analysis

For each pattern/anti-pattern, note:
- How many sessions it appeared in
- Whether it's already codified somewhere
- Whether the existing codification is accurate or stale

### Step 4: Prioritized actions

Rank by impact (frequency x severity):

1. **High-frequency anti-patterns** --> add to skill anti-pattern lists or AGENTS.md
2. **Validated new patterns** --> add to skill methodology or create new skill
3. **Stale rules** --> update or remove from AGENTS.md
4. **Gaps** --> flag for new skill creation or skill expansion

### Step 5: Execute and verify

For each action:
1. Make the change
2. Verify it doesn't conflict with existing rules (grep for contradictions)
3. Cross-reference: no phantom docs – every new artifact must be referenced from 2+ places, or it rots unread.

### Deep Distillation Output

```markdown
## Deep Distillation: {date range}

**Sessions reviewed:** {N}
**Breakdown:** {X success, Y partial, Z failure}

### Patterns Confirmed
| Pattern | Frequency | Codified in | Status |
|---|---|---|---|
| {pattern} | {N/total} | {artifact or "NEW"} | {kept / updated / created} |

### Anti-Patterns Found
| Anti-pattern | Frequency | Added to | Root cause |
|---|---|---|---|
| {anti-pattern} | {N/total} | {artifact} | {lock/fork/gap/stale} |

### Actions Taken
1. {specific change made}
2. ...

### Recommendations
- {any larger changes that need discussion before implementing}
```

## Failure Retro Protocol

For a specific failure, drill into root cause:

### Step 1: What happened?

Document the observable failure:
- What was the expected output?
- What was the actual output?
- When did things diverge?

### Step 2: Classify the failure

| Category | Description | Example |
|---|---|---|
| **Lock as fork** | Under-constrained a precision point | Codex chose the wrong DB column because the prompt said "use the relevant field" |
| **Fork as lock** | Over-constrained an exploration point | Prompt specified the exact algorithm, but a different approach was needed |
| **Missing anti-pattern** | Known failure mode not in the guard list | Codex fabricated a section because the "no fabrication" constraint was missing |
| **Stale reference** | Prompt referenced something that changed | File path moved, function renamed, API changed |
| **Wrong tool** | Used the wrong skill/mode/approach | Used a one-shot delegation for a task that needed interactive iteration |
| **Missing context** | Key information not in the prompt | Codex didn't know about a connection-pooler's prepared-statement limitations |

### Step 3: Fix the system, not the symptom

Don't just fix the specific failure – find the artifact that should have prevented it and update that artifact:

- If a constraint was missing --> add it to the relevant skill's anti-patterns
- If context was missing --> add it to AGENTS.md or a memory
- If the wrong tool was used --> update the decision framework in AGENTS.md
- If a reference was stale --> fix it AND add a freshness check to the relevant workflow

### Failure Retro Output

```markdown
## Failure Retro: {date} – {short title}

**What failed:** {1-2 sentences}
**Category:** {lock-as-fork / fork-as-lock / missing-anti-pattern / stale-reference / wrong-tool / missing-context}
**Root cause:** {why the system allowed this to happen}

**System fix:**
- {artifact updated} --> {what changed}

**Prevention:**
- {how the updated artifact would have prevented this failure}
```

## Lock/Fork Framework Reference

From the SSD framing – the precision-exploration conflict:

- **Locks** = positions where there's one right answer. Need precision. Suppress the distractor tail.
  - File paths, schemas, DB details, conventions, naming, legal/regulatory citations
  - In prompts: be maximally specific, paste exact code, zero ambiguity

- **Forks** = positions where multiple valid approaches exist. Need exploration. Preserve diversity.
  - Architecture choices, algorithm selection, UX decisions, error handling strategy
  - In prompts: specify output format and constraints, but not the approach

The most common failure mode is **misclassification** – treating a lock as a fork (leaving precision points vague) or a fork as a lock (over-constraining exploration points).

## Battle-Tested Lessons (de-identified)

These are generalized incident lessons. Each kept its principle; project/date/file specifics were stripped. Use them as priors when mining patterns and classifying failures.

- **Tuning a shared frame knob to silence a one-axis warning trips the orthogonal-axis failure.** Lowering or raising a single shared parameter to fix one dimension can break a perpendicular constraint on elongated/edge-case inputs. A parity test can pass at the bad value; only a real render/run catches it. Lesson: verify shared-parameter changes against the worst-case geometry, not the average case.
- **Lowering parallelism to "add headroom" on an under-utilized connection regressed latency.** The pipe was under-utilized, not contended – fewer concurrent requests made it slower, not faster. Lesson: measure the actual bottleneck before "adding safety margin"; intuition about contention is often backwards.
- **A write-side validation gate does not protect read/cache/consumer paths.** A gate added at the producer left every reader, cache-hydrator, and downstream consumer unguarded. Lesson: when you add a validation gate, gate the read path too, and sweep sibling call-sites in the same arc.
- **An auth fix for one spawned child has a sibling for every other harness.** Each CLI/tool authenticates differently (env token vs config file vs OAuth), so the same isolation layer breaks each one via a different mechanism. Lesson: when you fix auth for one spawned subprocess, audit every other spawned tool for its own variant.
- **A field name can lie about the metric it holds.** A field named for one metric (e.g. a "median" field) held a different value (e.g. a blended/derived value). Labeling or auditing off the name alone mislabels the output. Lesson: trace the producer before trusting a field name in a render or audit.
- **Relabeling or value-fixing a shared component needs a per-caller value-semantics audit.** Different callers feed different metrics through one header/component; a single relabel mislabels some of them. Lesson: enumerate every caller and check what each one actually passes.
- **An engagement metric can crater with the click handler fully intact.** The regression was above-the-fold reachability (the actionable element got pushed below new content), not a broken handler. Lesson: when a funnel metric drops but handlers test fine, measure scroll depth / reachability, not just handler wiring.
- **Mount-fired analytics events race an async-loaded script and drop silently.** The send resolves to undefined with no retry. Lesson: poll/queue for the global before firing fire-on-mount events; click-fired events are usually safe because the script has loaded by then.
- **A pageview guard that suppresses all events on a path prefix eats genuine landings.** Suppress same-pathname repeats only; suppressing everything on a prefix collapses real multi-page journeys into bounces. Lesson: scope dedup guards to the narrowest correct key.
- **Mocked-DB tests give false green for data/ML code.** They mask real-shape bugs that only appear against real rows. Lesson: run a real-data smoke test (on an isolated clone) before declaring data/ML work "fixed."
- **Claiming "X works" requires reproducing X's exact runtime path** – same command, env, and working directory, reading the producer's real output – not an isolated sample or a log skim. Lesson: verify in the real execution context; isolated reproductions overclaim.
- **A standalone component can be dead while an inlined copy renders live.** "Fixing" the standalone component changes nothing on screen. Lesson: grep for actual JSX/usage before editing a component you assume is rendered.
- **A webhook handler is dead unless the provider endpoint subscribes to the event.** Test-mode subscriptions don't carry to live. Lesson: treat "subscribe the endpoint to the event" as an explicit deploy step, and re-check it after any environment cutover.

## When NOT to expand

Scope-creep smell test: if a retro action balloons into a multi-doc, multi-phase, multi-session program, stop and ask whether that scope was actually warranted or whether the template bled. Prefer deletion/consolidation/narrowing over new abstractions. A 200-line change with a 50-line alternative should be the 50-line one.

## PLANS.md and AGENTS.md

- **AGENTS.md** is the cross-agent convention file many agents read for project conventions. Convention changes and durable cross-skill rules that aren't skill-internal belong there (see AGENTS.md for project conventions). Keep its rule-of-record canonical: state a shared rule once, reference it elsewhere, don't duplicate it.
- **PLANS.md** (or your equivalent plan/roadmap doc) is where multi-session work and open follow-ups live. When a deep distillation surfaces a "larger change that needs discussion before implementing," record it there rather than half-implementing it inside the retro. Retros codify *learnings*; PLANS.md tracks *pending work*.

## Related Skills

- **codex-prompt** – generates Codex task prompts (retro reviews their effectiveness)
