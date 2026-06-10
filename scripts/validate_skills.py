#!/usr/bin/env python3
"""Validate skills, plugin metadata, and prompt content fixtures.

Pure standard library – no third-party deps, so CI stays trivial.

Checks:
  - SKILL.md exists in each skills/<dir>/ directory
  - frontmatter block is present and well-formed (opens and closes with '---')
  - `name` is present, kebab-case, and equals the directory name
  - `description` is present and 20..1024 characters
  - `metadata.version` is present and valid semver (MAJOR.MINOR.PATCH)
  - optional agents/openai.yaml has required UI metadata and invokes the right skill
  - task-types.json points at existing examples and golden prompt fixtures
  - codex-prompt registry entries match the skill body and prompt templates
  - golden prompts contain the universal spine plus task-specific blocks
  - relative Markdown links point at files or directories that exist

Exit code 0 if all skills pass, 1 otherwise.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
PLUGIN_JSON = ROOT / ".codex-plugin" / "plugin.json"
MARKETPLACE_JSON = ROOT / ".agents" / "plugins" / "marketplace.json"
TASK_TYPES_JSON = ROOT / "task-types.json"
README_MD = ROOT / "README.md"
CHANGELOG_MD = ROOT / "CHANGELOG.md"
CODEX_PROMPT_SKILL = SKILLS_DIR / "codex-prompt" / "SKILL.md"
PROMPT_TEMPLATES = SKILLS_DIR / "codex-prompt" / "references" / "prompt-templates.md"

DESC_MIN, DESC_MAX = 20, 1024
SHORT_DESC_MIN, SHORT_DESC_MAX = 25, 64
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
SECRET_PATTERNS = [
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
    re.compile(r"gh[opsu]_[A-Za-z0-9_]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{32,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
TEXT_SUFFIXES = {
    ".json",
    ".md",
    ".py",
    ".txt",
    ".yml",
    ".yaml",
}


@dataclass(frozen=True)
class RegistryDocs:
    readme: str
    skill: str
    templates: str


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


def validate_release_metadata() -> list[str]:
    errors: list[str] = []
    if not PLUGIN_JSON.exists() or not CHANGELOG_MD.exists():
        return errors

    try:
        plugin = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f".codex-plugin/plugin.json: invalid JSON while checking release metadata: {exc}"]

    version = plugin.get("version", "")
    if not isinstance(version, str) or not SEMVER.match(version):
        return errors

    changelog = CHANGELOG_MD.read_text(encoding="utf-8")
    if f"## {version} - " not in changelog:
        errors.append(f"CHANGELOG.md: missing release heading for plugin version {version}")

    release_headings = re.findall(r"^##\s+(\d+\.\d+\.\d+)\s+-\s+", changelog, flags=re.MULTILINE)
    if release_headings and release_headings[0] != version:
        errors.append(
            f"CHANGELOG.md: latest release heading {release_headings[0]} does not match plugin version {version}"
        )

    return errors


def _read_required(path: Path, errors: list[str], label: str) -> str:
    if not path.exists():
        errors.append(f"{label}: missing at {path.relative_to(ROOT).as_posix()}")
        return ""
    return path.read_text(encoding="utf-8")


def _repo_relative_path(raw_path: str, prefix: str, errors: list[str]) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path:
        errors.append(f"{prefix}: path must be a non-empty string")
        return None
    path = Path(raw_path)
    if path.is_absolute():
        errors.append(f"{prefix}: path must be relative to the repo root")
        return None

    target = (ROOT / path).resolve()
    try:
        target.relative_to(ROOT.resolve())
    except ValueError:
        errors.append(f"{prefix}: path must stay inside the repo root")
        return None
    return target


def _require_substrings(text: str, required: list[str], prefix: str) -> list[str]:
    return [f"{prefix}: missing required block `{block}`" for block in required if block not in text]


def validate_task_type_registry() -> list[str]:
    errors: list[str] = []
    if not TASK_TYPES_JSON.exists():
        return ["task-types.json: missing task-type registry"]

    try:
        data = json.loads(TASK_TYPES_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"task-types.json: invalid JSON: {exc}"]

    if data.get("schemaVersion") != 1:
        errors.append("task-types.json: `schemaVersion` must be 1")
    if data.get("skill") != "codex-prompt":
        errors.append("task-types.json: `skill` must be codex-prompt")

    global_blocks = data.get("globalRequiredBlocks", [])
    if not isinstance(global_blocks, list) or not all(isinstance(block, str) and block for block in global_blocks):
        errors.append("task-types.json: `globalRequiredBlocks` must be a list of non-empty strings")
        global_blocks = []

    task_types = data.get("taskTypes", [])
    if not isinstance(task_types, list) or not task_types:
        errors.append("task-types.json: `taskTypes` must be a non-empty list")
        return errors

    docs = RegistryDocs(
        readme=_read_required(README_MD, errors, "README.md"),
        skill=_read_required(CODEX_PROMPT_SKILL, errors, "skills/codex-prompt/SKILL.md"),
        templates=_read_required(PROMPT_TEMPLATES, errors, "skills/codex-prompt/references/prompt-templates.md"),
    )

    seen_ids: set[str] = set()
    seen_golden_paths: set[Path] = set()
    display_names: list[str] = []

    for index, task in enumerate(task_types, start=1):
        prefix = f"task-types.json taskTypes[{index}]"
        if not isinstance(task, dict):
            errors.append(f"{prefix}: entry must be an object")
            continue

        task_id = task.get("id", "")
        display_name = task.get("displayName", "")
        skill_section = task.get("skillSection", "")
        template_sections = task.get("templateSections", [])
        required_blocks = task.get("requiredBlocks", [])

        if not isinstance(task_id, str) or not KEBAB.match(task_id):
            errors.append(f"{prefix}: `id` must be kebab-case")
        elif task_id in seen_ids:
            errors.append(f"{prefix}: duplicate id `{task_id}`")
        else:
            seen_ids.add(task_id)

        if not isinstance(display_name, str) or not display_name:
            errors.append(f"{prefix}: `displayName` must be a non-empty string")
        else:
            display_names.append(display_name)

        if not isinstance(skill_section, str) or not skill_section.startswith("### "):
            errors.append(f"{prefix}: `skillSection` must be a level-3 Markdown heading")
        elif docs.skill and skill_section not in docs.skill:
            errors.append(f"{prefix}: skill section `{skill_section}` not found in codex-prompt SKILL.md")

        if not isinstance(template_sections, list) or not template_sections:
            errors.append(f"{prefix}: `templateSections` must be a non-empty list")
        else:
            for heading in template_sections:
                if not isinstance(heading, str) or not heading.startswith("## "):
                    errors.append(f"{prefix}: template heading `{heading}` must be a level-2 Markdown heading")
                elif docs.templates and heading not in docs.templates:
                    errors.append(f"{prefix}: template heading `{heading}` not found in prompt-templates.md")

        if not isinstance(required_blocks, list) or not all(
            isinstance(block, str) and block for block in required_blocks
        ):
            errors.append(f"{prefix}: `requiredBlocks` must be a list of non-empty strings")
            required_blocks = []

        example_path = _repo_relative_path(task.get("examplePath", ""), f"{prefix} examplePath", errors)
        if example_path is not None:
            if not example_path.exists():
                errors.append(f"{prefix}: examplePath `{task.get('examplePath')}` does not exist")
            else:
                example_text = example_path.read_text(encoding="utf-8")
                if "## The generated prompt" not in example_text:
                    errors.append(
                        f"{prefix}: example `{task.get('examplePath')}` must include `## The generated prompt`"
                    )

        golden_path = _repo_relative_path(task.get("goldenPath", ""), f"{prefix} goldenPath", errors)
        if golden_path is not None:
            if not golden_path.exists():
                errors.append(f"{prefix}: goldenPath `{task.get('goldenPath')}` does not exist")
            else:
                seen_golden_paths.add(golden_path)
                golden_text = golden_path.read_text(encoding="utf-8")
                errors.extend(_require_substrings(golden_text, global_blocks, f"{prefix} goldenPath"))
                errors.extend(_require_substrings(golden_text, required_blocks, f"{prefix} goldenPath"))

    if docs.readme and display_names:
        table_row = "| " + " | ".join(display_names) + " |"
        if table_row not in docs.readme:
            errors.append("README.md: codex-prompt task-type table is out of sync with task-types.json")

    golden_dir = ROOT / "fixtures" / "golden-prompts"
    if not golden_dir.is_dir():
        errors.append("fixtures/golden-prompts: missing golden prompt fixture directory")
    else:
        for path in sorted(golden_dir.glob("*.md")):
            if path.resolve() not in seen_golden_paths:
                errors.append(
                    f"fixtures/golden-prompts/{path.name}: fixture is not referenced by task-types.json"
                )

    return errors


def _markdown_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if ".git" not in path.parts and path.is_file()
    )


def _extract_link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")]
    return target.split()[0] if target else ""


def _github_anchor_slug(heading: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", heading)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]+", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "-", text)
    return text.strip("-")


def _markdown_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = HEADING_RE.match(line)
        if not match:
            continue
        slug = _github_anchor_slug(match.group(2))
        if not slug:
            continue
        duplicate_count = counts.get(slug, 0)
        counts[slug] = duplicate_count + 1
        anchors.add(slug if duplicate_count == 0 else f"{slug}-{duplicate_count}")
    return anchors


def validate_markdown_links() -> list[str]:
    errors: list[str] = []
    anchor_cache: dict[Path, set[str]] = {}
    for md_file in _markdown_files():
        text = md_file.read_text(encoding="utf-8")
        rel_file = md_file.relative_to(ROOT).as_posix()
        for match in LINK_RE.finditer(text):
            target = _extract_link_target(match.group(1))
            if not target:
                continue
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue

            path_part = target.split("#", 1)[0].split("?", 1)[0]
            fragment = target.split("#", 1)[1].split("?", 1)[0] if "#" in target else ""

            path_part = unquote(path_part)
            if not path_part:
                candidate = md_file
            elif path_part.startswith("/"):
                candidate = ROOT / path_part.lstrip("/")
            else:
                candidate = md_file.parent / path_part

            if not candidate.exists():
                errors.append(f"{rel_file}: broken relative link `{target}`")
                continue

            if fragment and candidate.suffix.lower() == ".md":
                fragment = unquote(fragment).lower()
                anchors = anchor_cache.setdefault(candidate, _markdown_anchors(candidate))
                if fragment not in anchors:
                    errors.append(f"{rel_file}: broken heading anchor `{target}`")

    return errors


def validate_no_secrets() -> list[str]:
    errors: list[str] = []
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"{path.relative_to(ROOT).as_posix()}: possible secret pattern committed")
                break
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

    release_errors = validate_release_metadata()
    print(f"[{'FAIL' if release_errors else 'PASS'}] release metadata")
    all_errors.extend(release_errors)

    registry_errors = validate_task_type_registry()
    print(f"[{'FAIL' if registry_errors else 'PASS'}] task type registry")
    all_errors.extend(registry_errors)

    markdown_link_errors = validate_markdown_links()
    print(f"[{'FAIL' if markdown_link_errors else 'PASS'}] markdown links and anchors")
    all_errors.extend(markdown_link_errors)

    secret_errors = validate_no_secrets()
    print(f"[{'FAIL' if secret_errors else 'PASS'}] secret scan")
    all_errors.extend(secret_errors)

    if all_errors:
        print(f"\n{len(all_errors)} problem(s) found:\n", file=sys.stderr)
        for e in all_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"\nAll {len(skill_dirs)} skill(s), plugin metadata, registry, links, and safety checks valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
