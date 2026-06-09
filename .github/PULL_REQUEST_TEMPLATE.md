## Summary

<!-- What changed and why? -->

## Validation

- [ ] `python scripts/validate_skills.py`
- [ ] README updated if install, task-type, or public positioning changed
- [ ] Examples updated if a task scaffold changed
- [ ] `task-types.json` updated if a task type, scaffold, or fixture changed
- [ ] Golden prompt fixtures updated if required blocks or task scaffolds changed
- [ ] `.codex-plugin/plugin.json` updated if plugin packaging changed
- [ ] `CHANGELOG.md` updated for user-visible changes

## Skill quality

- [ ] Skill descriptions still clearly describe when the skill should trigger
- [ ] `agents/openai.yaml` still matches each changed skill
- [ ] Plugin metadata still matches bundled skills
- [ ] New rules are project-neutral and do not mention private systems
- [ ] Added methodology prevents a real failure mode or clarifies a repeated workflow
