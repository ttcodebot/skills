---
name: hardening
description: Turn a Tiny Tapeout design into a chip layout (GDS) and get it to pass - harden locally with LibreLane through tt-support-tools, read utilisation, timing and warnings, fix placement, routing and timing failures, and diagnose a failing `gds`, `precheck` or `viewer` job. Use it whenever a Tiny Tapeout project (a tt_um_* module) must be hardened, the `gds` workflow fails or takes very long, someone asks whether a design fits its tiles or meets its clock, or before submitting to a shuttle.
---

# Harden a Tiny Tapeout design

The project's `gds` workflow hardens on every push; doing it locally gives answers in minutes and
full logs.

## Harden locally

Following [tinytapeout.com/guides/local-hardening](https://tinytapeout.com/guides/local-hardening/),
in the project folder, with Python 3.11 or newer and Docker running:

```bash
git clone https://github.com/TinyTapeout/tt-support-tools tt
python3 -m venv ~/ttsetup/venv && source ~/ttsetup/venv/bin/activate
pip install -r tt/requirements.txt
export PDK_ROOT=~/ttsetup/pdk PDK=sky130A LIBRELANE_TAG=3.0.14
pip install librelane==$LIBRELANE_TAG
./tt/tt_tool.py --pdk $PDK --create-user-config
./tt/tt_tool.py --pdk $PDK --harden
```

- `PDK` is the project's PDK: `sky130A`, `gf180mcuD`, `ihp-sg13g2` or `ihp-sg13cmos5l`. An old
  tt-support-tools clone has no `--pdk` flag: `git -C tt pull`.
- `LIBRELANE_TAG` must match what the shuttle's tt-gds-action uses: see the `librelane-version`
  logic in [tt-gds-action's action.yml](https://github.com/TinyTapeout/tt-gds-action/blob/main/action.yml)
  (`ihp-sg13cmos5l` needs a 3.1 release).
- Run `--create-user-config` again after changing `info.yaml` (tiles, sources, top module).

**No Docker?** `./tt/tt_tool.py --pdk $PDK --harden --no-docker` runs a LibreLane installed with
its tools on the machine instead, for example through Nix (see the
[LibreLane installation docs](https://librelane.readthedocs.io/)). If neither works, push and let
the `gds` workflow harden; say so rather than claiming the design fits.

## Read the result

Everything lands in `runs/wokwi/`; the layout and netlists are in `runs/wokwi/final/`.

```bash
./tt/tt_tool.py --pdk $PDK --print-stats          # utilisation and wire length
./tt/tt_tool.py --pdk $PDK --print-warnings       # synthesis warnings: read every one
./tt/tt_tool.py --pdk $PDK --print-cell-summary   # cells used, by kind
```

`runs/wokwi/final/metrics.json` has the sign-off numbers. All of these should be 0 for a design
that can be submitted: `timing__setup_vio__count`, `timing__hold_vio__count`,
`route__drc_errors`, `magic__drc_error__count`, `design__lvs_error__count`. Worst slack
(`timing__setup__ws`, `timing__hold__ws`) should be positive; the per-corner keys show which
corner fails. Synthesis warnings about multiple drivers, undriven outputs or combinational loops
are bugs even when the flow passes.

## Fix common failures

| Symptom                                                        | Fix                                                                                                                                         |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `GPL-0302` (global placement: design too dense)                | The knob in `src/config.json` its comments name, or more tiles                                                                             |
| Detailed placement or routing fails, or the run takes 20+ min  | The design does not fit: more tiles in `info.yaml`, or a smaller design                                                                    |
| Setup violations                                               | Shorten the logic between registers (pipeline), or run slower: raise `CLOCK_PERIOD` (ns) in `src/config.json` and lower `clock_hz` to match |
| Hold violations                                                | The hold margins in `src/config.json`                                                                                                       |
| Linter errors (`01-verilator-lint`)                            | Fix the Verilog                                                                                                                             |
| Far fewer cells than expected                                  | Logic that reaches no output was removed: check that results drive `uo_out` / `uio_out`                                                    |

Tile sizes per PDK are in `tech/<pdk>/tile_sizes.yaml` in tt-support-tools. More tiles cost money
at app.tinytapeout.com, but the `gds` workflow accepts any size in `info.yaml`, so try first, buy
after.

## A failing GitHub job

The run's summary page has the linter output, synthesis warnings, routing stats and cell usage.

- **`viewer` or pages fails:** set Settings, Pages, Source to "GitHub Actions". If the GDS was
  built before that, push a new commit or re-run the whole workflow; re-running only the `viewer`
  job fails with "Multiple artifacts named github-pages".
- **`precheck` fails:** the layout breaks a manufacturing rule; the job log names the check. For
  a plain Verilog project this is rare and usually means `src/config.json` or the workflow was
  edited.
- **`gl_test` fails:** see the gate-level section of the `testing` skill.
- **Submission asks to re-harden for another PDK:** the project was built for a different PDK
  than the shuttle (see the `project-setup` skill).

Still stuck? Ask in the `#questions` channel of the [Tiny Tapeout Discord](https://tinytapeout.com/discord)
with a link to the repository and the error message.
