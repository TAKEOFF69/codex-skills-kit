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

import json
import re
import sys
from pathlib import Path

KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
PLUGIN_JSON = ROOT / ".codex-plugin" / "plugin.json"
MARKETPLACE_JSON = ROOT / ".agents" / "plugins" / "marketplace.json"

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


def validate_plugin_manifest() -> list[str]:
    errors: list[str] = []
    if not PLUGIN_JSON.exists():
        return errors

    try:
        data = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f".codex-plugin/plugin.json: invalid JSON: {exc}"]

    name = data.get("name", "")
    version = data.get("version", "")
    skills_path = data.get("skills", "")
    interface = data.get("interface", {})
    author = data.get("author", {})

    if name != "codex-skills-kit":
        errors.append(".codex-plugin/plugin.json: `name` must be codex-skills-kit")
    if not SEMVER.match(version):
        errors.append(".codex-plugin/plugin.json: `version` must be semver MAJOR.MINOR.PATCH")
    if not data.get("description"):
        errors.append(".codex-plugin/plugin.json: missing `description`")
    if not author.get("name"):
        errors.append(".codex-plugin/plugin.json: missing `author.name`")
    if skills_path != "./skills/":
        errors.append(".codex-plugin/plugin.json: `skills` must be ./skills/")
    elif not (ROOT / "skills").is_dir():
        errors.append(".codex-plugin/plugin.json: `skills` path does not exist")

    required_interface = [
        "displayName",
        "shortDescription",
        "longDescription",
        "developerName",
        "category",
        "defaultPrompt",
        "brandColor",
    ]
    for key in required_interface:
        if key not in interface:
            errors.append(f".codex-plugin/plugin.json: missing `interface.{key}`")

    if interface.get("brandColor") and not re.match(r"^#[0-9A-Fa-f]{6}$", interface["brandColor"]):
        errors.append(".codex-plugin/plugin.json: `interface.brandColor` must be a 6-digit hex color")

    prompts = interface.get("defaultPrompt", [])
    if not isinstance(prompts, list) or not prompts:
        errors.append(".codex-plugin/plugin.json: `interface.defaultPrompt` must be a non-empty list")
    else:
        if len(prompts) > 3:
            errors.append(".codex-plugin/plugin.json: `interface.defaultPrompt` must contain at most 3 entries")
        for prompt in prompts:
            if not isinstance(prompt, str) or len(prompt) > 128:
                errors.append(
                    ".codex-plugin/plugin.json: each `interface.defaultPrompt` entry must be a string <= 128 chars"
                )

    for key in ("homepage", "repository"):
        value = data.get(key, "")
        if value and not value.startswith("https://"):
            errors.append(f".codex-plugin/plugin.json: `{key}` must be an https:// URL")

    return errors


def validate_marketplace() -> list[str]:
    errors: list[str] = []
    if not MARKETPLACE_JSON.exists():
        return errors

    try:
        data = json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f".agents/plugins/marketplace.json: invalid JSON: {exc}"]

    if data.get("name") != "codex-skills-kit":
        errors.append(".agents/plugins/marketplace.json: `name` must be codex-skills-kit")

    plugins = data.get("plugins", [])
    if not isinstance(plugins, list) or len(plugins) != 1:
        errors.append(".agents/plugins/marketplace.json: must contain exactly one plugin entry")
        return errors

    plugin = plugins[0]
    source = plugin.get("source", {})
    policy = plugin.get("policy", {})

    if plugin.get("name") != "codex-skills-kit":
        errors.append(".agents/plugins/marketplace.json: plugin `name` must be codex-skills-kit")
    if source.get("source") != "local":
        errors.append(".agents/plugins/marketplace.json: plugin `source.source` must be local")
    if source.get("path") != "./":
        errors.append(".agents/plugins/marketplace.json: plugin `source.path` must be ./")
    if policy.get("installation") != "AVAILABLE":
        errors.append(".agents/plugins/marketplace.json: plugin `policy.installation` must be AVAILABLE")
    if policy.get("authentication") != "ON_INSTALL":
        errors.append(".agents/plugins/marketplace.json: plugin `policy.authentication` must be ON_INSTALL")
    if plugin.get("category") != "Productivity":
        errors.append(".agents/plugins/marketplace.json: plugin `category` must be Productivity")
    if not PLUGIN_JSON.exists():
        errors.append(".agents/plugins/marketplace.json: source path points at repo root but plugin.json is missing")

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

    plugin_errors = validate_plugin_manifest()
    print(f"[{'FAIL' if plugin_errors else 'PASS'}] plugin manifest")
    all_errors.extend(plugin_errors)

    marketplace_errors = validate_marketplace()
    print(f"[{'FAIL' if marketplace_errors else 'PASS'}] marketplace")
    all_errors.extend(marketplace_errors)

    if all_errors:
        print(f"\n{len(all_errors)} problem(s) found:\n", file=sys.stderr)
        for e in all_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"\nAll {len(skill_dirs)} skill(s) and plugin metadata valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
