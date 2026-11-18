# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
# SPDX-FileCopyrightText: (c) 2026 Tiny Tapeout B.V.
# SPDX-License-Identifier: Apache-2.0
"""Render the pin tables in skills/pinout/SKILL.md from skills/pinout/pinouts.yaml.

Usage:
    uv run scripts/render_pinouts.py           # rewrite the tables
    uv run scripts/render_pinouts.py --check   # exit 1 if they are out of date
"""

import re
import sys
from pathlib import Path

import yaml

SKILLS = Path(__file__).resolve().parent.parent / "skills"
PINOUTS = SKILLS / "pinout/pinouts.yaml"
BEGIN = "<!-- pinouts:begin (generated from pinouts.yaml, do not edit) -->"
END = "<!-- pinouts:end -->"

# Project pin group -> (Verilog port, demoboard Pmod header)
GROUPS = {
    "ui": ("ui_in", "INPUT"),
    "uo": ("uo_out", "OUTPUT"),
    "uio": ("uio", "BIDIR"),
}
PIN_RE = re.compile(r"^(ui|uo|uio)\[([0-7])\]$")


def load_peripherals() -> list[dict]:
    peripherals = yaml.safe_load(PINOUTS.read_text())["peripherals"]
    for peripheral in peripherals:
        name = peripheral["name"]
        directions = peripheral.get("dir", {})
        for pin in peripheral["pins"]:
            match = PIN_RE.match(pin)
            if not match:
                sys.exit(f"{name}: bad pin name {pin!r}")
            # A uio pin needs a direction, because it decides uio_oe.
            if (match[1] == "uio") != (pin in directions):
                sys.exit(f"{name}: {pin} needs a 'dir' entry if and only if it is a uio pin")
        for pin, direction in directions.items():
            if pin not in peripheral["pins"] or direction not in ("in", "out", "inout"):
                sys.exit(f"{name}: bad 'dir' entry {pin}: {direction}")
    return peripherals


def signal(peripheral: dict, pin: str) -> str:
    """The signal a peripheral puts on a pin, with the direction for uio pins."""
    name = peripheral["pins"].get(pin, "")
    if pin in peripheral.get("dir", {}):
        name += f" ({peripheral['dir'][pin]})"
    return name


def render_by_header(peripherals: list[dict]) -> str:
    """One table per Pmod header, one column per peripheral: shows conflicts."""
    tables = []
    for group, (port, header) in GROUPS.items():
        columns = [p for p in peripherals if any(pin.startswith(f"{group}[") for pin in p["pins"])]
        lines = [
            f"**`{port}` - {header} header**",
            "",
            "| Pin | " + " | ".join(p["name"] for p in columns) + " |",
            "| --- | " + " | ".join("---" for _ in columns) + " |",
        ]
        for bit in range(8):
            pin = f"{group}[{bit}]"
            cells = " | ".join(signal(p, pin) for p in columns)
            lines.append(f"| `{pin}` | {cells} |")
        tables.append("\n".join(lines))
    return "\n\n".join(tables)


TARGETS = {SKILLS / "pinout/SKILL.md": render_by_header}


def main() -> None:
    peripherals = load_peripherals()
    for path, render in TARGETS.items():
        text = path.read_text()
        if BEGIN not in text or END not in text:
            sys.exit(f"{path}: pinout markers not found")
        head, rest = text.split(BEGIN, 1)
        tail = rest.split(END, 1)[1]
        rendered = f"{head}{BEGIN}\n\n{render(peripherals)}\n\n{END}{tail}"
        if "--check" in sys.argv:
            if rendered != text:
                sys.exit(f"{path} is out of date: run scripts/render_pinouts.py")
        else:
            path.write_text(rendered)


if __name__ == "__main__":
    main()
