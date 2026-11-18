---
name: project-setup
description: Start or restructure a Tiny Tapeout chip project - pick the right template for the shuttle's PDK, write the tt_um_* top module, fill info.yaml and docs/info.md, and follow the rules that differ from FPGA work (explicit reset, no initial values, flip-flops are expensive). Use it whenever someone creates a new Tiny Tapeout design, ports Verilog from an FPGA or another project into Tiny Tapeout, edits info.yaml or the top module, or asks how many tiles, which template or which clock to use - even if they only say "I want to make a chip".
---

# Set up a Tiny Tapeout project

A Tiny Tapeout project is a GitHub repository made from a template; its workflows test it, harden
it and build its datasheet page on every push.

## Pick the template

Each shuttle is made in one PDK. Start from the template for that PDK (GitHub: "Use this template"):

| PDK                    | Template                                                                        |
| ---------------------- | ------------------------------------------------------------------------------- |
| SkyWater 130 nm        | [ttsky-verilog-template](https://github.com/TinyTapeout/ttsky-verilog-template) |
| GlobalFoundries 180 nm | [ttgf-verilog-template](https://github.com/TinyTapeout/ttgf-verilog-template)   |
| IHP 130 nm             | [ttihp-verilog-template](https://github.com/TinyTapeout/ttihp-verilog-template) |

Each template's `.github/workflows/gds.yaml` pins `TinyTapeout/tt-gds-action@<shuttle>`; it must
name the shuttle the project goes to. Otherwise keep the template's workflows exactly as they are:
they run the mandatory precheck (see the `hardening` skill). A project made for one PDK has to be
hardened again for another: copy the sources into the other template rather than editing the
workflow by hand.
For gate-level designs drawn in the browser, the matching `*-wokwi-template` repositories exist.
For analog or hand-drawn layout, use the `*-analog-template` repositories (see the `analog` skill).

## The top module

Keep the template's port list exactly: do not add, remove or resize ports, even when porting a
design that had other ones. The module name must start with `tt_um_` and be unique across the
shuttle, so include the GitHub username: `tt_um_<username>_<project>`. Which signal goes on which
pin is in the `pinout` skill.

## Rules that differ from FPGA work

- **Reset everything that holds state.** Flip-flops on a chip power up random; `initial` blocks
  and `reg x = 0` are ignored by synthesis. Use `rst_n` (active low) for every register whose
  value matters. Missing resets are among the most common defects found on real chips.
- **One clock.** Clock all registers from `clk` and use enables for slower events. Registers
  clocked by other signals are not checked by timing analysis.
- **Flip-flops are expensive, logic is cheap.** A SkyWater 1x1 tile fits roughly 300 flip-flops
  with little room for logic; prefer deriving values from counters over storing them. Memory
  options (latches, DFF RAM, SRAM macros, external QSPI memory) are on
  [tinytapeout.com/specs/memory](https://tinytapeout.com/specs/memory/).

## info.yaml

- `tiles`: start at `1x1` and grow only when hardening says the design does not fit (see the
  `hardening` skill).
- `clock_hz`: the clock the design expects (0 if none); the demoboard sets the clock from it.
  Plan for 50 MHz or less: on SkyWater shuttles the I/O pads are rated for about 66 MHz in and
  33 MHz out ([tinytapeout.com/specs/gpio](https://tinytapeout.com/specs/gpio/)).

The comments in the template's `info.yaml` cover the other fields.

## docs/info.md

This becomes the project's page in the chip's datasheet. Write **How to test** for someone holding
a demoboard: which inputs to set, which clock, and what they should see.

## Check before pushing

With [tt-support-tools](https://github.com/TinyTapeout/tt-support-tools) cloned into `tt/` and its
`requirements.txt` installed (Python 3.11 or newer). It runs Yosys through `yowasp`, which cannot
read files under `/tmp`, so keep the project elsewhere:

```bash
./tt/tt_tool.py --pdk sky130A --create-user-config   # validates info.yaml; errors list every problem
./tt/tt_tool.py --pdk sky130A --check-docs           # checks the fields the datasheet needs
```

Use the project's PDK (see the `hardening` skill). Then run the tests (see the `testing` skill) and
harden (see the `hardening` skill).
