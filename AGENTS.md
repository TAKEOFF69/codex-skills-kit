# AGENTS.md – codex-skills-kit

Conventions for any agent (OpenAI Codex and other Agent-Skills-compatible tools) working in this repository. This is a content + tooling repo: prompt-engineering skills plus a small validation script. There is no application runtime.

## What this repo is

A package of OpenAI Codex skills (`SKILL.md` files under `skills/`) that generate structured task prompts, plus worked examples and a CI frontmatter validator. The methodology is the product; keep its depth.

## Layout

- `skills/<name>/SKILL.md` – a skill (Agent Skills standard: `name` + `description` frontmatter + Markdown body). `codex-prompt` also has `references/`.
- `examples/<task-type>-example.md` – one worked prompt per task type, on the fictional "Acme Notes" project.
- `scripts/validate_skills.py` – frontmatter linter (stdlib only).
- `.github/workflows/validate-skills.yml` – runs the linter on every push/PR.

## Validate before committing

```bash
python scripts/validate_skills.py
```

Exit code 0 means every `SKILL.md` has valid frontmatter (`name` kebab = dir, `description` 20–1024 chars, `metadata.version` semver). CI enforces this; do not merge red.

## Conventions

- **Style:** en dashes (–) only in prose – never em dashes (—) or `--` as punctuation. Syntactic `--` (CLI flags, SQL comments, Markdown rules) is fine.
- **Project-neutral:** examples and skills reference only "Acme Notes" or generic placeholders – no real private-project names, infra, or paths.
- **Skill frontmatter is mandatory** and must match the validator (see `CONTRIBUTING.md` for the schema).
- **Diff discipline:** every changed line traces to the task; no drive-by reformatting of untouched content.

## Do not

- Commit `AUDIT-REPORT.md` – it is a scratch audit artifact, gitignored, never published.
- Add runtime/network code to `scripts/` – the validator stays stdlib-only and read-only over `skills/`.

## Licensing

Code/scripts: MIT (`LICENSE`). Skill + prompt content under `skills/` and `examples/`: CC BY 4.0 (`LICENSE-CONTENT`).
