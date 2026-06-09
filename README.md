# codex-skills-kit

**A task-typed prompt-engineering toolkit for OpenAI Codex, shipped as portable [Agent Skills](https://developers.openai.com/codex/skills).**

[![License: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](./LICENSE)
[![Content: CC BY 4.0](https://img.shields.io/badge/content-CC--BY--4.0-lightgrey.svg)](./LICENSE-CONTENT)
[![Tag](https://img.shields.io/github/v/tag/TAKEOFF69/codex-skills-kit?sort=semver)](https://github.com/TAKEOFF69/codex-skills-kit/tags)
[![Stars](https://img.shields.io/github/stars/TAKEOFF69/codex-skills-kit?style=social)](https://github.com/TAKEOFF69/codex-skills-kit/stargazers)

Most "prompt libraries" are a pile of one-off snippets. This is the opposite: an opinionated **operating system for delegating work to Codex** – the same methodology a senior engineer uses to hand off a task so it comes back done, not half-done.

It ships two Codex skills that work together as a loop:

| Skill | What it does | When it fires |
|-------|--------------|---------------|
| **[codex-prompt](./skills/codex-prompt/)** | Generates copy-paste-ready, self-contained Codex task prompts across 6 task types | You're delegating async work to Codex |
| **[retro-distill](./skills/retro-distill/)** | Runs a self-distillation retrospective that writes lessons *back into the skills* | After a chunk of work – closes the improvement loop |

The combination – **a typed generator + a feedback loop that improves it** – is what makes this more than a snippet dump. Every prompt Codex runs teaches the next one.

---

## The idea in 30 seconds

A good agent task is a **verifiable goal**, not a wish. Every prompt this kit produces opens with the same spine:

```
Goal: {one sentence – what changes when this completes}
Success means:
  - {checkable criterion}
Stop when: {explicit stop condition}
```

…then it picks the right **scaffold for the task type** (a Fix prompt ≠ an Audit prompt ≠ a Refactor prompt), classifies each section as **Lock** (one right answer – be exact) or **Fork** (many valid answers – leave room), and sets the control fields that keep Codex honest: assumptions, invariants, a narrow risk gate, the verification level, and a repo-mismatch stop condition.

See [`examples/`](./examples/) for a full worked prompt per task type, on a single fictional project (Acme Notes), so you can read the shape before you adopt it.

The task-type contract is now checked in as [`task-types.json`](./task-types.json). It maps each supported task type to its skill section, prompt-template section, worked example, and golden prompt fixture under [`fixtures/golden-prompts/`](./fixtures/golden-prompts/). CI uses that registry to catch drift between the methodology docs and the prompts users actually copy.

---

## Install (OpenAI Codex)

Codex Skills use the open [Agent Skills](https://developers.openai.com/codex/skills) standard. The recommended install path is the plugin package, which bundles both skills together.

### Install as a plugin

Add this repo as a Codex plugin marketplace:

```bash
codex plugin marketplace add TAKEOFF69/codex-skills-kit
```

Then open the plugin directory with `/plugins`, switch to the **Codex Skills Kit** marketplace, and install **Codex Skills Kit**. Start a new thread after installation so Codex picks up the bundled skills.

For a local clone, use the clone path instead:

```bash
codex plugin marketplace add ./path/to/codex-skills-kit
```

### Install individual skills

**Inside Codex** – the built-in installer accepts a GitHub tree URL:

```
$skill-installer install https://github.com/TAKEOFF69/codex-skills-kit/tree/main/skills/codex-prompt
$skill-installer install https://github.com/TAKEOFF69/codex-skills-kit/tree/main/skills/retro-distill
```

Codex auto-detects newly installed skills; restart Codex if one doesn't appear in `/skills`.

**Manual** – copy a skill folder into whichever scope you want Codex to read:

- Repo-scoped: `./.agents/skills/` (discovered from the working directory up to the repo root)
- User-scoped: `$HOME/.agents/skills/`
- Installer default: `$CODEX_HOME/skills` (defaults to `$HOME/.codex/skills`) – where `$skill-installer` writes

```bash
git clone https://github.com/TAKEOFF69/codex-skills-kit
cp -r codex-skills-kit/skills/codex-prompt .agents/skills/
```

> Portable by design: these are standard `SKILL.md` skills, so they also load in any other Agent-Skills-compatible agent without modification.

---

## Use

Skills load by **progressive disclosure** – Codex reads the short `description`, and pulls in the full body only when your task matches. Trigger them implicitly or explicitly:

- **Implicitly:** "Write me a Codex prompt to fix the stale-search bug" → `codex-prompt` fires on the description match.
- **Explicitly:** invoke from the `/skills` menu, or `$codex-prompt`.

The skill then interviews the task, picks the scaffold, and emits a prompt you can paste into a fresh Codex run. Pair it with `retro-distill` after the work lands to fold what you learned back into your own copy of the skills.

---

## What's inside

```
codex-skills-kit/
├── .codex-plugin/plugin.json  # Codex plugin manifest
├── .agents/plugins/           # marketplace catalog for plugin install
├── AGENTS.md                  # repo conventions Codex reads automatically
├── skills/
│   ├── codex-prompt/          # flagship – 6 task types + 2 reference files
│   │   ├── SKILL.md
│   │   ├── agents/openai.yaml # Codex app metadata
│   │   └── references/
│   │       ├── anti-patterns.md
│   │       └── prompt-templates.md
│   └── retro-distill/         # the self-improvement loop
│       ├── SKILL.md
│       └── agents/openai.yaml
├── examples/                  # one worked prompt per task type
├── fixtures/golden-prompts/   # compact canonical prompt fixtures for CI
├── task-types.json            # task registry: skill sections, templates, examples
├── scripts/validate_skills.py # skill + plugin + content validator (run in CI)
├── CHANGELOG.md
└── .github/workflows/         # CI: validates skills, fixtures, links, metadata
```

### codex-prompt task types

`codex-prompt` ships a distinct scaffold, category rules, and anti-pattern guards per task type – not a generic template with the words swapped:

| Fix | Build | Ops/Tuning | Audit | Refactor | PR-series |
|-----|-------|------------|-------|----------|-----------|
| known-root-cause bug, mandatory diagnosis phase | feature from a spec, phased | runtime/infra, before/after metrics | read-only PASS/FAIL review | structure-only, cross-layer aware | numbered multi-PR feature |

`retro-distill` is task-type-agnostic: it runs in quick, deep, or failure mode and turns finished sessions into updates to your skills, conventions, and anti-pattern lists.

---

## Why it's shaped this way

These skills were extracted from heavy real-world use driving Codex on a production codebase: thousands of delegated tasks, distilled down to the patterns that consistently produced correct, single-pass results. The project-specific scaffolding has been stripped; the methodology – and the hard-won anti-patterns behind it – is what remains.

A few load-bearing principles:

- **Every Fix prompt ships a diagnosis phase.** Prompt-writers are reliably overconfident about root causes; the scaffold forces Codex to confirm the cause and grep for siblings *before* it edits.
- **Directive vs Investigative mode.** When *how* is known, ship the exact steps. When *how* is open, ship the goal + guardrails and let Codex investigate. Mis-picking forecloses better solutions or invites scope creep.
- **Narrow risk gates.** Halt only for genuinely destructive or architectural decisions; skip-and-log everything else. Over-broad "stop the session" gates strand good work.
- **The retro loop is the point.** Skills that don't evolve rot. `retro-distill` is the mechanism that keeps yours current.

---

## Contributing

New task types, anti-patterns, and worked examples are welcome. Every `SKILL.md`, `agents/openai.yaml`, plugin manifest, task registry, and fixture change must pass the validator (`python scripts/validate_skills.py`), which CI enforces on every PR. See [CONTRIBUTING.md](./CONTRIBUTING.md) for the skill schema and conventions, and [AGENTS.md](./AGENTS.md) for the repo conventions Codex itself reads.

## License

- **Code / scripts:** [MIT](./LICENSE)
- **Skill + prompt content** (`skills/`, `examples/`, `fixtures/`): [CC BY 4.0](./LICENSE-CONTENT)

Use it, fork it, adapt it to your stack. Attribution appreciated.
