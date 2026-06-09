# Contributing to codex-skills-kit

Thanks for helping make agent delegation less of a guessing game. Contributions of new task types, anti-patterns, worked examples, and skill improvements are all welcome.

## Ground rules

- **The methodology is the product.** Depth and specificity beat breadth. A new rule should earn its place by preventing a real failure mode – ideally one you hit yourself.
- **Keep it project-neutral.** Examples reference the fictional "Acme Notes" app, never a real private codebase. Strip brand names, infra specifics, and internal paths.
- **Style:** en dashes (–) only, never em dashes (—) or double hyphens (--) as punctuation.

## Skill format

Every skill is a directory under `skills/` containing a `SKILL.md` built on the open [Agent Skills](https://agentskills.io) standard:

```
skills/
  your-skill-name/
    SKILL.md            # required
    agents/openai.yaml  # recommended – Codex app metadata
    references/         # optional – deep-dive docs loaded on demand
    scripts/            # optional – helper scripts
```

### Required `SKILL.md` frontmatter

```yaml
---
name: your-skill-name          # kebab-case, must match the directory name
description: "One or two sentences describing what the skill does and when it fires. This is what the agent matches against, so make it discovery-friendly."
metadata:
  version: 0.1.0               # semver
---
```

Rules enforced by CI (`scripts/validate_skills.py`):

- Frontmatter block present and well-formed (opens and closes with `---`).
- `name` present, kebab-case, and equal to the directory name.
- `description` present, between 20 and 1024 characters.
- `metadata.version` present and valid semver (`MAJOR.MINOR.PATCH`).
- If `agents/openai.yaml` exists, it includes `interface.display_name`, a 25..64 character `interface.short_description`, a `default_prompt` that mentions `$your-skill-name`, a valid hex `brand_color`, and a boolean `policy.allow_implicit_invocation`.
- If `.codex-plugin/plugin.json` exists, it points at `./skills/`, uses strict semver, and includes required plugin interface metadata.
- If `.agents/plugins/marketplace.json` exists, it exposes the root plugin as `codex-skills-kit` with an available local marketplace entry.
- `task-types.json` stays in sync with the `codex-prompt` skill body, `references/prompt-templates.md`, worked examples, and golden prompt fixtures.
- Every golden prompt fixture contains the universal prompt spine plus the task-specific required blocks from `task-types.json`.
- Relative Markdown links point at files or directories that exist.

Run the validator locally before opening a PR:

```bash
python scripts/validate_skills.py
```

## Adding a worked example

Drop a Markdown file in `examples/` named `<task-type>-example.md`. It must:

1. State which skill and task type it demonstrates.
2. Show the full, copy-paste-ready generated prompt following that skill's real skeleton.
3. Close with a short "why it's shaped this way" section tying choices back to the methodology.

If you add or rename a `codex-prompt` task type, update `task-types.json` in the same PR. The registry must point at:

1. The corresponding `###` task section in `skills/codex-prompt/SKILL.md`.
2. One or more `##` template sections in `skills/codex-prompt/references/prompt-templates.md`.
3. The worked example under `examples/`.
4. A compact golden fixture under `fixtures/golden-prompts/`.

## Pull requests

- One logical change per PR.
- Update the README task-type table, `task-types.json`, the worked example, and the golden fixture if you add or change a task type.
- Update `.codex-plugin/plugin.json` and `CHANGELOG.md` when public plugin packaging changes.
- CI must be green (skill, plugin, registry, fixture, and link validation).

By contributing, you agree your code contributions are licensed under MIT and skill, example, and fixture content is licensed under CC BY 4.0, matching the repository.
