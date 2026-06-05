#!/usr/bin/env python3
"""Validate the frontmatter of every SKILL.md under skills/.

Pure standard library – no third-party deps, so CI stays trivial.

Checks per skill:
  - SKILL.md exists in each skills/<dir>/ directory
  - frontmatter block is present and well-formed (opens and closes with '---')
  - `name` is present, kebab-case, and equals the directory name
  - `description` is present and 20..1024 characters
  - `metadata.version` is present and valid semver (MAJOR.MINOR.PATCH)
  - optional agents/openai.yaml has required UI metadata and invokes the right skill

Exit code 0 if all skills pass, 1 otherwise.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"

DESC_MIN, DESC_MAX = 20, 1024
SHORT_DESC_MIN, SHORT_DESC_MAX = 25, 64


def _clean(value: str) -> str:
    """Strip an inline comment, surrounding whitespace, and quotes from a value."""
    if "#" in value:
        value = value.split("#", 1)[0]
    return value.strip().strip('"').strip("'")


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Minimal YAML-frontmatter parser.

    Returns None if no well-formed frontmatter block is found. Captures
    top-level `key: value` pairs, plus one level of nesting under `metadata:`
    exposed as `metadata.<key>` (enough to validate `metadata.version`).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None

    out: dict[str, str] = {}
    in_metadata = False
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indented = line[0] in (" ", "\t")
        if not indented:
            in_metadata = False
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = _clean(value)
            out[key] = value
            if key == "metadata" and value == "":
                in_metadata = True
        elif in_metadata and ":" in line:
            key, _, value = line.partition(":")
            out[f"metadata.{key.strip()}"] = _clean(value)
    return out


def validate_skill(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    name_expected = skill_dir.name
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.is_file():
        return [f"{name_expected}: missing SKILL.md"]

    fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    if fm is None:
        return [f"{name_expected}: missing or malformed frontmatter block (must open and close with '---')"]

    name = fm.get("name", "")
    desc = fm.get("description", "")
    version = fm.get("metadata.version", "")

    if not name:
        errors.append(f"{name_expected}: frontmatter missing `name`")
    else:
        if not KEBAB.match(name):
            errors.append(f"{name_expected}: `name` ('{name}') is not kebab-case")
        if name != name_expected:
            errors.append(f"{name_expected}: `name` ('{name}') does not match directory name")

    if not desc:
        errors.append(f"{name_expected}: frontmatter missing `description`")
    elif not (DESC_MIN <= len(desc) <= DESC_MAX):
        errors.append(
            f"{name_expected}: `description` length {len(desc)} outside [{DESC_MIN}, {DESC_MAX}]"
        )

    if not version:
        errors.append(f"{name_expected}: frontmatter missing `metadata.version`")
    elif not SEMVER.match(version):
        errors.append(
            f"{name_expected}: `metadata.version` ('{version}') is not semver MAJOR.MINOR.PATCH"
        )

    errors.extend(validate_openai_yaml(skill_dir))
    return errors


def parse_openai_yaml(text: str) -> dict[str, str]:
    """Parse the small agents/openai.yaml subset this repo uses."""
    out: dict[str, str] = {}
    section = ""
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indented = raw[0] in (" ", "\t")
        if not indented:
            key, sep, value = raw.partition(":")
            if not sep:
                continue
            section = key.strip()
            if value.strip():
                out[section] = _clean(value)
        elif section and ":" in raw:
            key, _, value = raw.partition(":")
            out[f"{section}.{key.strip()}"] = _clean(value)
    return out


def validate_openai_yaml(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    metadata_file = skill_dir / "agents" / "openai.yaml"
    if not metadata_file.exists():
        return errors

    data = parse_openai_yaml(metadata_file.read_text(encoding="utf-8"))
    prefix = f"{skill_dir.name}/agents/openai.yaml"

    display_name = data.get("interface.display_name", "")
    short_description = data.get("interface.short_description", "")
    default_prompt = data.get("interface.default_prompt", "")
    brand_color = data.get("interface.brand_color", "")
    implicit = data.get("policy.allow_implicit_invocation", "")

    if not display_name:
        errors.append(f"{prefix}: missing `interface.display_name`")

    if not short_description:
        errors.append(f"{prefix}: missing `interface.short_description`")
    elif not (SHORT_DESC_MIN <= len(short_description) <= SHORT_DESC_MAX):
        errors.append(
            f"{prefix}: `interface.short_description` length {len(short_description)} "
            f"outside [{SHORT_DESC_MIN}, {SHORT_DESC_MAX}]"
        )

    if not default_prompt:
        errors.append(f"{prefix}: missing `interface.default_prompt`")
    elif f"${skill_dir.name}" not in default_prompt:
        errors.append(f"{prefix}: `interface.default_prompt` must mention `${skill_dir.name}`")

    if brand_color and not re.match(r"^#[0-9A-Fa-f]{6}$", brand_color):
        errors.append(f"{prefix}: `interface.brand_color` must be a 6-digit hex color")

    if implicit and implicit not in {"true", "false"}:
        errors.append(f"{prefix}: `policy.allow_implicit_invocation` must be true or false")

    return errors


def main() -> int:
    if not SKILLS_DIR.is_dir():
        print(f"error: skills directory not found at {SKILLS_DIR}", file=sys.stderr)
        return 1

    skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())
    if not skill_dirs:
        print("error: no skills found under skills/", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    for skill_dir in skill_dirs:
        errs = validate_skill(skill_dir)
        status = "FAIL" if errs else "PASS"
        print(f"[{status}] {skill_dir.name}")
        all_errors.extend(errs)

    if all_errors:
        print(f"\n{len(all_errors)} problem(s) found:\n", file=sys.stderr)
        for e in all_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"\nAll {len(skill_dirs)} skill(s) valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
