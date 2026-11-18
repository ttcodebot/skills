# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
# SPDX-FileCopyrightText: (c) 2026 Tiny Tapeout B.V.
# SPDX-License-Identifier: Apache-2.0
"""Check every skills/*/SKILL.md header against the Agent Skills format, and that files are ASCII.

Usage: uv run scripts/check_skills.py
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
# Limits from https://agentskills.io/specification
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME, MAX_DESCRIPTION = 64, 1024


def skill_errors(skill_md: Path) -> list[str]:
    text = skill_md.read_text()
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return ["no YAML header between --- lines"]
    header = yaml.safe_load(match[1])
    name, description = header.get("name", ""), header.get("description", "")
    errors = []
    if name != skill_md.parent.name:
        errors.append(f"name {name!r} differs from the folder name")
    if not NAME_RE.match(name) or len(name) > MAX_NAME:
        errors.append(f"name {name!r} must be lowercase words joined by '-', at most {MAX_NAME} characters")
    if not description or len(description) > MAX_DESCRIPTION:
        errors.append(f"description must be 1 to {MAX_DESCRIPTION} characters, not {len(description)}")
    return errors


def main() -> None:
    failed = False
    for skill_md in sorted(ROOT.glob("skills/*/SKILL.md")):
        for error in skill_errors(skill_md):
            print(f"{skill_md.relative_to(ROOT)}: {error}")
            failed = True
    tracked = [
        *ROOT.glob("*.md"),
        *ROOT.glob("skills/**/*"),
        *ROOT.glob("scripts/*.py"),
        *ROOT.glob(".claude-plugin/*.json"),
        *ROOT.glob(".github/**/*"),
    ]
    for path in sorted(p for p in tracked if p.is_file()):
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if not line.isascii():
                print(f"{path.relative_to(ROOT)}:{number}: non-ASCII character, write - -> ... instead")
                failed = True
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
