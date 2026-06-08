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

Run the validator locally before opening a PR:

```bash
python scripts/validate_skills.py
```

## Adding a worked example

Drop a Markdown file in `examples/` named `<task-type>-example.md`. It must:

1. State which skill and task type it demonstrates.
2. Show the full, copy-paste-ready generated prompt following that skill's real skeleton.
3. Close with a short "why it's shaped this way" section tying choices back to the methodology.

## Pull requests

- One logical change per PR.
- Update the README task-type table if you add a task type.
- Update `.codex-plugin/plugin.json` and `CHANGELOG.md` when public plugin packaging changes.
- CI must be green (frontmatter validation).

By contributing, you agree your contributions are licensed under MIT (code) and CC BY 4.0 (content), matching the repository.
