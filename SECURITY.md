# Security Policy

This repository ships **prompt content and a small validation script** – there is no runtime service and no network code. The realistic security surface is limited, but we still take reports seriously.

## Reporting a vulnerability

If you find a security-relevant issue – for example, a prompt template that could coax an agent into an unsafe action, or a problem in `scripts/validate_skills.py` – please report it privately:

- Use GitHub's **[Private vulnerability reporting](https://github.com/TAKEOFF69/codex-skills-kit/security/advisories/new)** (Security tab → Report a vulnerability), or
- Open a regular issue for non-sensitive concerns.

Please do **not** open a public issue for anything you believe is genuinely exploitable until it has been addressed.

## Scope notes

- The skills instruct agents to scope risk gates narrowly and to stop before destructive or privileged actions. If you find guidance that undermines that, it's a bug – report it.
- The included scripts use only the Python standard library and perform no network or filesystem mutation beyond reading `skills/*/SKILL.md`.

## Response

We aim to acknowledge reports within a few days and to address valid issues in a timely manner. Thank you for helping keep the ecosystem safe.
