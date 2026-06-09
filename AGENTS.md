# AGENTS.md – codex-skills-kit

Conventions for any agent (OpenAI Codex and other Agent-Skills-compatible tools) working in this repository. This is a content + tooling repo: prompt-engineering skills plus a small validation script and fixtures. There is no application runtime.

## What this repo is

A package of OpenAI Codex skills (`SKILL.md` files under `skills/`) that generate structured task prompts, plus worked examples, golden fixtures, a task-type registry, and a CI validator. The methodology is the product; keep its depth.

## Layout

- `.codex-plugin/plugin.json` – plugin manifest bundling the repo's skills.
- `.agents/plugins/marketplace.json` – repo marketplace catalog that points at the root plugin.
- `skills/<name>/SKILL.md` – a skill (Agent Skills standard: `name` + `description` frontmatter + Markdown body). `codex-prompt` also has `references/`.
- `skills/<name>/agents/openai.yaml` – optional Codex app metadata validated by `scripts/validate_skills.py`.
- `examples/<task-type>-example.md` – one worked prompt per task type, on the fictional "Acme Notes" project.
- `fixtures/golden-prompts/<task-type>.md` – compact canonical prompts validated against the task registry.
- `task-types.json` – source-of-truth registry linking task types to skill sections, templates, examples, and fixtures.
- `scripts/validate_skills.py` – skill, plugin, registry, fixture, and Markdown-link validator (stdlib only).
- `.github/workflows/validate-skills.yml` – runs the validator on every push/PR.

## Validate before committing

```bash
python scripts/validate_skills.py
```

Exit code 0 means every `SKILL.md` has valid frontmatter (`name` kebab = dir, `description` 20–1024 chars, `metadata.version` semver), every present `agents/openai.yaml` matches the skill, the plugin/marketplace metadata is coherent, `task-types.json` matches the prompt docs, golden fixtures contain their required blocks, and relative Markdown links resolve. CI enforces this; do not merge red.

## Conventions

- **Style:** en dashes (–) only in prose – never em dashes (—) or `--` as punctuation. Syntactic `--` (CLI flags, SQL comments, Markdown rules) is fine.
- **Project-neutral:** examples and skills reference only "Acme Notes" or generic placeholders – no real private-project names, infra, or paths.
- **Skill frontmatter is mandatory** and must match the validator (see `CONTRIBUTING.md` for the schema).
- **Task-type changes move together:** update `codex-prompt`, `prompt-templates.md`, the worked example, the golden fixture, `task-types.json`, and the README table in one PR.
- **Diff discipline:** every changed line traces to the task; no drive-by reformatting of untouched content.

## Do not

- Commit `AUDIT-REPORT.md` – it is a scratch audit artifact, gitignored, never published.
- Add runtime/network code to `scripts/` – the validator stays stdlib-only and read-only over `skills/`.

## Licensing

Code/scripts: MIT (`LICENSE`). Skill + prompt content under `skills/`, `examples/`, and `fixtures/`: CC BY 4.0 (`LICENSE-CONTENT`).
