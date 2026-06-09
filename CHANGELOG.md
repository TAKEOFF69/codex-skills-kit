# Changelog

## 0.2.0 - 2026-06-09

- Added `task-types.json` as the source-of-truth registry for `codex-prompt` task scaffolds.
- Added golden prompt fixtures for every supported task type.
- Extended validation to check registry drift, golden fixture required blocks, and relative Markdown links.
- Updated contributor docs and PR checklist for task-type and fixture changes.

## 0.1.1 - 2026-06-08

- Added Codex app metadata for bundled skills.
- Added PR and issue templates for skill changes.
- Extended validation to check `agents/openai.yaml` drift.
- Added Codex plugin packaging and a repo marketplace catalog.
- Clarified plugin and direct-skill install paths in the README.

## 0.1.0 - 2026-06-05

- Initial release of `codex-prompt` and `retro-distill`.
- Added worked examples for the supported task types.
- Added standard-library skill validation script and CI workflow.
