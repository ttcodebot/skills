# Tiny Tapeout agent skills

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) ![AI Assisted](https://www.aihonestybadge.com/badges/ai-assisted-small.svg)

Skills that teach AI coding agents (Claude Code, Cursor, Codex, Copilot and others) how to design
chips for [Tiny Tapeout](https://tinytapeout.com). One folder per skill, each a `SKILL.md` in the
open [Agent Skills](https://agentskills.io/specification) format, so the same files work in every
agent that reads skills.

Agents can already write Verilog. What they don't know is how a Tiny Tapeout project is laid out,
how its pins are wired to the outside world, and how to check that a design will work on a real
chip before it's made. These skills fill that in.

## Skills

| Skill                                            | Use it to                                                                                                                     |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| [`project-setup`](skills/project-setup/SKILL.md) | Start a project: the template for the shuttle's PDK, the `tt_um_*` module, `info.yaml`, and the rules that differ from FPGAs |
| [`pinout`](skills/pinout/SKILL.md)               | Assign pins the standard way: VGA, audio, gamepad, QSPI memory, 7-segment, rotary encoder, UART and SPI on the demoboard      |
| [`testing`](skills/testing/SKILL.md)             | Write and run the cocotb tests, read failures, and run the same test on the gate-level netlist                                |
| [`hardening`](skills/hardening/SKILL.md)         | Harden locally with LibreLane, read utilisation and timing, and fix a failing `gds` workflow                                  |
| [`vga-output`](skills/vga-output/SKILL.md)       | Draw to a VGA monitor, with habits that held up on silicon, and check the picture with [tt-vga-sim](https://github.com/TinyTapeout/tt-vga-sim) |
| [`analog`](skills/analog/SKILL.md)               | Analog and custom-layout projects: the frame, analog pins, xschem to GDS, and passing the precheck locally, with IIC-OSIC-TOOLS on any OS |
| [`mixed-signal`](skills/mixed-signal/SKILL.md)   | Digital logic inside an analog project: a LibreLane macro or hand-placed cells, LVS of the mix, and ngspice + Verilator co-simulation |

## Install

**Claude Code, as a plugin** (all skills, namespaced `/tinytapeout:<skill>`):

```text
/plugin marketplace add TinyTapeout/skills
/plugin install tinytapeout@tinytapeout-skills
```

**Claude Code, one project, no plugin:** copy `skills/<name>/` into the repo's `.claude/skills/`
(or `~/.claude/skills/` for every project).

**Any other agent:** copy the folder to wherever that agent loads skills from, or paste the
`SKILL.md` body into the instructions file it reads (`AGENTS.md`, `.cursorrules`,
`copilot-instructions.md`). The files are plain Markdown with a small YAML header.

## Contributing

The pin tables in `skills/pinout/SKILL.md` are generated from
[`skills/pinout/pinouts.yaml`](skills/pinout/pinouts.yaml). Edit the YAML, then run:

```bash
uv run scripts/render_pinouts.py
```

CI checks that the tables are up to date and that every skill's header follows the Agent Skills
format (`uv run scripts/check_skills.py`).

## License

Apache License 2.0, see [LICENSE](LICENSE).
