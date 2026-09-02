#!/usr/bin/env python3
"""Build strails-api.skill from the strails-api/ source tree.

The .skill file is a zip of the skill directory. Source of truth is the
unpacked tree; this script only packages it, after checking the bundle is
well-formed.

Usage: python3 build.py [--check]
  --check   validate only, don't write the bundle
"""
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "skills" / "strails-api"
OUT = ROOT / "strails-api.skill"


def validate() -> list[str]:
    errors = []
    skill_md = SRC / "SKILL.md"
    if not skill_md.is_file():
        return [f"missing {skill_md}"]

    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        errors.append("SKILL.md has no YAML frontmatter")
        return errors

    frontmatter = text.split("---", 2)[1]
    name = re.search(r"^name:\s*(\S+)", frontmatter, re.M)
    description = re.search(r"^description:\s*(.+)", frontmatter, re.M)

    if not name:
        errors.append("frontmatter is missing `name`")
    elif name.group(1) != SRC.name:
        errors.append(f"frontmatter name '{name.group(1)}' != directory '{SRC.name}'")
    if not description:
        errors.append("frontmatter is missing `description`")

    # Every referenced reference file must exist, and vice versa.
    referenced = set(re.findall(r"references/([A-Za-z0-9._-]+\.md)", text))
    present = {p.name for p in (SRC / "references").glob("*.md")}
    for missing in sorted(referenced - present):
        errors.append(f"SKILL.md references references/{missing}, which does not exist")
    for orphan in sorted(present - referenced):
        errors.append(f"references/{orphan} is never referenced from SKILL.md")

    # Plugin + marketplace manifests must exist, be valid JSON, and agree.
    plugin_manifest = ROOT / ".claude-plugin" / "plugin.json"
    marketplace_manifest = ROOT / ".claude-plugin" / "marketplace.json"
    plugin = marketplace = None
    for manifest in (plugin_manifest, marketplace_manifest):
        if not manifest.is_file():
            errors.append(f"missing {manifest.relative_to(ROOT)}")
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{manifest.relative_to(ROOT)} is not valid JSON: {exc}")
            continue
        if manifest is plugin_manifest:
            plugin = data
        else:
            marketplace = data

    if plugin is not None:
        if plugin.get("name") != SRC.name:
            errors.append(
                f"plugin.json name '{plugin.get('name')}' != skill directory '{SRC.name}'"
            )
        if not plugin.get("version"):
            errors.append("plugin.json is missing `version`")
    if plugin is not None and marketplace is not None:
        entries = {p.get("name"): p for p in marketplace.get("plugins", [])}
        entry = entries.get(plugin.get("name"))
        if entry is None:
            errors.append(
                f"marketplace.json has no entry for plugin '{plugin.get('name')}'"
            )
        elif entry.get("description") != plugin.get("description"):
            errors.append(
                "plugin.json and marketplace.json descriptions differ - "
                "`claude plugin tag` requires them to agree"
            )

    # Every API URL must carry the /v1 prefix.
    hosts = r"(?:api\.strails\.io|beta\.stablesrail\.io|sandbox\.stablesrail\.io)"
    for path in sorted(SRC.rglob("*.md")):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in re.finditer(rf"https://{hosts}/(?!v1(?:/|\b))([A-Za-z])", line):
                rel = path.relative_to(ROOT)
                errors.append(f"{rel}:{line_no} API URL missing /v1 prefix")
    return errors


def build() -> None:
    """Package the skill as a .skill bundle for claude.ai uploads.

    The bundle is rooted at the skill directory itself, so paths inside the
    zip stay `strails-api/...` even though the source now lives under
    `skills/` for the plugin layout.
    """
    files = sorted(p for p in SRC.rglob("*") if p.is_file())
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            arcname = (Path(SRC.name) / path.relative_to(SRC)).as_posix()
            bundle.write(path, arcname)
    size_kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT.name} ({len(files)} files, {size_kb:.1f} KB)")


if __name__ == "__main__":
    problems = validate()
    for problem in problems:
        print(f"error: {problem}", file=sys.stderr)
    if problems:
        sys.exit(1)
    print("validation passed")
    if "--check" not in sys.argv:
        build()
