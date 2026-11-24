---
name: analog
description: Build an analog or custom-layout Tiny Tapeout project - pick the analog template for the shuttle's PDK, set analog_pins / uses_vapwr / tiles in info.yaml, start the layout from the tt-support-tools DEF frame, draw power stripes and analog pins the precheck accepts, draw or generate the layout (magic, KLayout, KLayout Python with the PDK pcells, gdstk), run DRC, LVS and antenna checks, export the committed GDS and LEF, and pass the Tiny Tapeout precheck without touching it. Use it whenever a Tiny Tapeout project uses the ua[] analog pins, VAPWR, magic, KLayout, netgen or a hand-drawn or generated GDS (op-amps, DACs, ADCs, oscillators, bandgaps, passives, silicon structures), whenever a precheck, DRC or LVS fails on such a project, and when someone needs the analog toolchain (including on macOS) - even if they only say "custom GDS" or "transistor-level".
---

# Analog and custom-layout Tiny Tapeout projects

In an analog project you draw the layout yourself and commit `gds/<top_module>.gds` and
`lef/<top_module>.lef`. The `gds` workflow does not harden anything: its `custom_gds` step only
packages those files, and the `precheck` job checks them. Everything about the layout is your
responsibility, so check it locally before pushing.

## Pick the template

| PDK                    | Template                                                                      | Notes                                                                   |
| ---------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| SkyWater 130 nm        | [ttsky-analog-template](https://github.com/TinyTapeout/ttsky-analog-template) |                                                                         |
| GlobalFoundries 180 nm | [ttgf-analog-template](https://github.com/TinyTapeout/ttgf-analog-template)   | Read [references/gf180mcuD.md](references/gf180mcuD.md)                 |
| IHP 130 nm             | [ttihp-analog-template](https://github.com/TinyTapeout/ttihp-analog-template) | Targets `ihp-sg13cmos5l`; its README says how to switch to `ihp-sg13g2` |

The workflows pin `TinyTapeout/tt-gds-action/...@<shuttle>` for the shuttle the template was last
updated for. The IHP template also serves custom-layout projects with no analog pins
(`analog_pins: 0`, `ua` port left commented out).

## Size, pins and supplies

- **Tiles:** an analog project is 1x2 or 2x2 tiles (one or two "analog slots"). Bigger is charged
  as several projects ([FAQ](https://tinytapeout.com/faq/#what-is-an-analog-slot)).
- **Analog pins:** `analog_pins` is how many `ua` pins are bonded to pads, and each one is paid
  for. Use them in order from `ua[0]`; only `ua[0]` to `ua[5]` exist. The precheck requires metal
  touching `ua[n]` exactly when `n < analog_pins`, and a description of that pin in `pinout`.
- **VAPWR:** a second supply, only with `uses_vapwr: true`, the `VAPWR` port uncommented in
  `src/project.v`, the frame variant that has it, and at least one analog pin. The VAPWR frames
  are narrower than the plain ones.
- **Unused digital outputs:** tie every `uo_out`, `uio_out` and `uio_oe` bit you do not drive to
  VGND in the layout. Floating outputs are not allowed.
- **Pad path:** between `ua[n]` and the pad sit an analog switch and routing. On sky130 it is
  under 500 Ohm and 5 pF, 4 mA max ([analog specs](https://tinytapeout.com/specs/analog/)).
  Simulate every output driving that load plus the pad, board and probe; an RLC pad model is
  `xschem/pad_model.sch` in [ttsky-oscillating-bones](https://github.com/urish/ttsky-oscillating-bones).
- **Never feed on-chip circuits from a `ua` net.** Drive the pad from its own buffer and take
  internal signals from the node before it. On a taped-out ring oscillator, the pad load pulled
  `ua[0]` down to a 100 mV ripple, below the trip point of the level shifter it also fed, so the
  digital outputs never toggled.

| PDK              | VDPWR | VAPWR               | Frame with VAPWR | Stripes and `ua` pins | Min stripe width | Forbidden layer |
| ---------------- | ----- | ------------------- | ---------------- | --------------------- | ---------------- | --------------- |
| `sky130A`        | 1.8 V | 3.3 V               | `*_3v3.def`      | met4                  | 1.2 um           | met5            |
| `gf180mcuD`      | 3.3 V | VAA, 5 V-rated path | `*_pgvaa.def`    | Metal4                | 0.8 um           | Metal5          |
| `ihp-sg13g2`     | 1.8 V | not available       | -                | TopMetal1             | 2.1 um           | TopMetal2       |
| `ihp-sg13cmos5l` | 1.8 V | 3.3 V               | `*_pgvaa.def`    | Metal4                | 2.1 um           | TopMetal1       |

PDK notes the precheck will not tell you:

- **gf180mcuD:** read [references/gf180mcuD.md](references/gf180mcuD.md) before drawing; its DRC
  deck is far stricter than magic's.
- **ihp-sg13g2:** digital pins are on Metal4, while stripes and `ua` pins are on TopMetal1 (magic
  calls it `met6`).
- **ihp-sg13cmos5l:** needs magic 8.3.657 or newer. TopMetal1 is the chip's power grid; route on
  Metal1 to Metal4 only.
- **IHP, both:** the boundary must be on `prBoundary.boundary` (189/4), not `prBoundary.drawing`.

## Start from the frame

Never start from a blank cell. The frame fixes the die size and every pin. Take it from
`tech/<pdk>/def/analog/` on the `main` branch of
[tt-support-tools](https://github.com/TinyTapeout/tt-support-tools) (the website still links an
old `tt10` copy for sky130): `tt_analog_<tiles>.def`, or the VAPWR variant from the table.
`magic_init_project.tcl` in the same folder reads the DEF, renames `tt_um_template` to your top
cell and draws labelled power stripes as ports. Edit `TOP_LEVEL_CELL`, `TEMPLATE_FILE` and the
`POWER_STRIPES` list (uncomment the VAPWR line for a VAPWR frame), then in magic, started with the
PDK's rc file (`magic -rcfile $PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc`): `source magic_init_project.tcl`.

What the precheck checks against the frame:

- The top cell is named exactly `top_module`, is the only top cell, has no cell names with `#`
  or `/`, and has a boundary rectangle (`prBoundary`, `PR_bndry` on gf180mcuD) equal to the die
  area. No shape may stick out.
- Every frame pin is in the LEF on the same layer with the same rectangle. Do not move, resize,
  merge or add pins. Pin shapes and labels must be in the top cell, not only in a subcell.
- Power stripes are vertical, on the stripe layer, at least the minimum width, start within 10 um
  of the bottom edge and end within 10 um of the top edge. Several stripes per net are fine; pins
  of different nets must not overlap or touch.
- Only layers the PDK allows; none of the forbidden layer.

## Write the Verilog stub

`src/project.v` is the black box that places your layout on the chip; rename `tt_um_example` to
your top module. The precheck parses it with Yosys, and on sky130A and gf180mcuD also checks that
`VGND` and `VDPWR` appear outside comments, and `VAPWR` exactly when `uses_vapwr` is set (the LEF
must match, with `USE POWER` / `USE GROUND` on those pins). Make it structural, instantiating your analog cells
with their supply pins and assigning the tied-off outputs to `VGND`, and it doubles as the
golden netlist for LVS of the top level.

## Design flow

1. **Schematic and simulation:** xschem and ngspice with the PDK's models, through corners,
   mismatch and supply sweeps (see the `analog-simulation` skill).
2. **Layout:** one layout cell per schematic cell, drawn or generated (see "Draw the layout"
   below). Keep the layout hierarchical; do not flatten the top before export. Draw the substrate
   and well taps yourself.
3. **DRC:** run the deck the precheck runs (see below). magic's DRC is quick while drawing but is
   not the sign-off on gf180mcuD or IHP.
4. **LVS:** extract with magic and compare with netgen and the PDK's setup file
   (`$PDK_ROOT/$PDK/libs.tech/netgen/${PDK}_setup.tcl`, `-blackbox`). Extract with
   `ext2spice lvs`, `ext2spice cthresh infinite` and `ext2spice short resistor`. Run LVS and
   post-layout extraction one at a time: they share magic's extraction files. netgen can print
   `Circuits match uniquely` and report property errors (device sizes that differ) in the same
   report: treat any property error as a failure.
5. **Antenna on sky130A:** the precheck runs an antenna check only on gf180mcuD, so on sky130A run
   one yourself (magic's `antennacheck` after extraction). Prove it works once with a deliberate
   violation: a long metal wire on one small gate.
6. **Post-layout simulation:** extract with parasitics (`extresist`) and simulate again (see the
   `analog-simulation` skill).
7. **Export:** `gds write gds/<top>.gds` and `lef write lef/<top>.lef -pinonly -hide`.

## Draw the layout

Any tool that writes a correct GDS will do: the precheck reads only the GDS, the LEF and the
Verilog stub.

| Method                                  | Devices from                                               | Good for                                    |
| --------------------------------------- | ---------------------------------------------------------- | ------------------------------------------- |
| magic, interactively                    | the PDK's device generators (magic's Devices menu, or Tcl) | most reference projects; DRC while drawing  |
| KLayout, interactively                  | the PDK's KLayout pcells, with the PDK's technology loaded | the IHP PDK, which is built around KLayout  |
| KLayout Python (`klayout -b -r gen.py`) | the same pcells, called from a script                      | generated blocks, arrays, sweeps and reruns |
| gdstk or another GDS library            | none: every shape is yours                                 | metal-only structures (MOM caps, passives)  |

- **PDK pcells:** sky130A ships a KLayout library named `skywater130` in
  `$PDK_ROOT/sky130A/libs.tech/klayout/python/cells`, which needs `gdsfactory` in the Python that
  KLayout uses. IHP ships `sg13g2_pycell_lib` with its KLayout tech files. The gf180mcu pcells are
  in [gf180mcu_fd_pr](https://github.com/fossi-foundation/globalfoundries-pdk-libs-gf180mcu_fd_pr)
  under `cells/klayout`.
- **Generators** pay off for anything that will be redrawn: give the generator the block's size
  and pin sides as inputs, so a floorplan change is a rerun. Pin the versions of KLayout and the
  pcell libraries, and after changing shared generator code, regenerate every block and XOR each
  GDS against the committed one.
- **Whatever draws it,** DRC and LVS still run through the PDK's decks and netgen, and magic
  writes the LEF (step 7). Use the PDK's devices rather than drawing transistors from plain
  shapes, so extraction recognises them.

Examples: [ook-asic-radio](https://github.com/mattvenn/ook-asic-radio) (sky130A: KLayout Python
generators with the PDK pcells, magic and netgen for the checks) and
[ttgf0p3-momcap](https://github.com/htfab/ttgf0p3-momcap) (gf180mcuD: metal only, from Python).

Commit the sources (`.mag`, `.sch`, `.sym`, generator scripts) with the GDS and LEF; leave
extraction output out of git. The `mag/Makefile` and `mag/tcl/` of
[tt_tnt_gf_555](https://github.com/smunaut/tt_tnt_gf_555) are a reusable harness for DRC, LVS,
extraction and export: change `PROJECT_NAME` and the netlists `lvs.tcl` reads.

Then fill `docs/info.md` for someone with a demoboard and lab instruments: which `ua` pin does
what, supplies and bias to apply, what to measure, and simulated numbers to compare against.

## Design for test

Decide these with the architecture: none can be added after tapeout.

- Give every block a defined off state, and simulate start-up and off.
- Bring key internal decisions (a comparator output, a block enable) out to digital pins, and let
  pins drive them too, so the bench can bypass the logic around them.
- To watch an internal analog node on a `ua` pin, go through a switch that is off by default,
  from a low-impedance node: pad leakage into a high-impedance node shifts it.
- A ring oscillator or another free-running block on a pin is a cheap check of the chip's speed
  against simulation.
- Keep noisy, high-current loads on their own supply where the PDK has two, and put decoupling
  capacitance next to the circuits that draw the current.

## The precheck is mandatory

The `precheck` job runs Tiny Tapeout's manufacturing checks on your GDS: the foundry DRC deck,
antenna (gf180mcuD), layers, frame, pins, power stripes and analog pins. Keep the template's
`.github/workflows/` exactly as shipped:

- Do not disable, skip or edit jobs: no deleted `precheck` job, no `if: false`, no
  `continue-on-error`, no extra steps that patch files before it runs.
- Do not change the `tt-gds-action` reference, and do not add `tools-repo` or `tools-ref`
  inputs that point the action at other checks.
- Do not edit, swap or trim DRC decks, precheck rules, DEF frames or tech files, in the PDK or in
  a tt-support-tools clone, to make a check pass.

A layout that passes only because a check was weakened fails again at submission, and if it got
onto the chip it could short a supply or damage the shared chip for every other project. DRC
fights on analog layouts are long, and weakening the check is never the way out. Instead:

- fix the layout, rule by rule, using the violation markers;
- run the same checks locally (below), so each iteration takes minutes, not a CI round trip;
- if a rule looks wrong or cannot be met, stop and ask in the
  [Tiny Tapeout Discord](https://tinytapeout.com/discord) with the repository and the report.
  Say so to the user rather than claiming the layout passes.

## Run the precheck locally

The precheck job uses tt-support-tools `main` and a PDK version pinned in
[tt-gds-action's `precheck/action.yml`](https://github.com/TinyTapeout/tt-gds-action/blob/main/precheck/action.yml).
It needs the `klayout` binary (and `magic` for sky130) on `PATH`; `nix-shell` in `tt/precheck`
gives the versions CI uses. From the project folder, with Python 3.11 or newer:

```bash
git clone https://github.com/TinyTapeout/tt-support-tools tt
pip install -r tt/precheck/requirements.txt
export PDK_ROOT=~/ttsetup/pdk PDK=gf180mcuD          # the project's PDK
ciel enable --pdk-root $PDK_ROOT --pdk-family gf180mcu <PDK_VERSION from precheck/action.yml>
TOP=tt_um_yourname_project
mkdir -p tt_submission
cp gds/$TOP.gds lef/$TOP.lef tt_submission/ && cp src/project.v tt_submission/$TOP.v
GDS=$PWD/tt_submission/$TOP.gds
(cd tt/precheck && python precheck.py --gds $GDS --tech $PDK)   # must run from tt/precheck
```

The ciel family is `sky130`, `gf180mcu` or `ihp-sg13g2` (which also holds `ihp-sg13cmos5l`). The
GDS, LEF and Verilog must sit side by side under the top module's name, as CI arranges them;
`tt_submission/` is already in the template's `.gitignore`, `tt/` is not.
Results land in `tt/precheck/reports/` (`results.md`, and DRC reports to open in KLayout's marker
browser). To iterate on DRC alone, run the deck the precheck names for your PDK; for gf180mcuD
the commands are in [references/gf180mcuD.md](references/gf180mcuD.md).

## Fix common precheck failures

| Message                                                        | Fix                                                                            |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `Analog pin ua[n] is connected to some metal but ...`          | Raise `analog_pins` / describe the pin, or remove metal and vias near `ua[n]`  |
| `Analog pin ua[n] is not connected to any adjacent metal`      | Wire the pin, or lower `analog_pins` and blank its description                 |
| (either of the two above, unexpectedly)                        | "Connected" means pin-layer metal 0.1 to 0.5 um around the pin, or a via on it |
| `Port ... has different dimensions` / `not found`              | Re-take the pins from the frame; regenerate the LEF with `-pinonly -hide`      |
| `Port V... is too far from bottom/top edge`                    | Stretch the stripe to within 10 um of both edges                               |
| `Missing top-level prBoundary` / `Shapes outside project area` | Keep the frame's boundary; clip geometry to the die                            |
| `Top macro name mismatch` / `GDS top level not unique`         | One top cell, named `top_module`; delete stray cells before `gds write`        |
| `Forbidden layer` / `Invalid layers in GDS`                    | Remove the top metal / non-PDK layers (often from imported art or generators)  |
| `Verilog contains VAPWR` or `doesn't contain ...`              | Match `src/project.v` and the LEF to `uses_vapwr`                              |
| `Klayout ... failed with N DRC violations`                     | Open the report in `tt/precheck/reports/` and fix each rule                    |

## Get the tools

You need xschem, ngspice, magic, netgen and KLayout, the PDK, and Python. The easy way on every
OS, and the recommended one on macOS, where native builds are hard, is
[IIC-OSIC-TOOLS](https://github.com/iic-jku/IIC-OSIC-TOOLS): one container (`hpretl/iic-osic-tools`,
about 4 GB, x86_64 and Apple Silicon) with all of these, LibreLane, ciel and the `sky130A`,
`gf180mcuD`, `ihp-sg13g2` and `ihp-sg13cmos5l` PDKs.

```bash
curl -fsSL https://osic.tools/install.sh | bash      # or install Docker yourself; adds XQuartz on macOS
git clone --depth=1 https://github.com/iic-jku/iic-osic-tools.git && cd iic-osic-tools
./start_vnc.sh      # a desktop in the browser
./start_x.sh        # or: the tools in local X11 windows (XQuartz on macOS)
```

With `start_vnc.sh`, open `http://localhost/?password=abc123` (port 8080, as
`http://localhost:8080/?password=abc123`, under rootless Podman).

`$HOME/eda/designs` on the host is `/foss/designs` in the container (change it with `DESIGNS=`),
so keep the project there. Inside, `sak-pdk gf180mcuD` (or another PDK name) switches PDK. On
macOS prefer `start_vnc.sh`: X11 to XQuartz goes over TCP and redraws slowly. Pin the image to a
release tag rather than `latest`, so tool versions, and with them simulation results, do not
change under the project. The PDK in the
container may differ from the version the precheck pins: judge DRC by the precheck. The README
covers Windows, Podman and dev containers.

Without containers: install the tools natively or through Nix, and the PDK with
[ciel](https://github.com/fossi-foundation/ciel) (not `volare`). A machine without native builds
can wrap each tool, for example `nix-portable nix shell --impure nixpkgs#klayout --command klayout "$@"`
in a `klayout` script on `PATH`.

## More

- Specs and pricing: [tinytapeout.com/specs/analog](https://tinytapeout.com/specs/analog/).
- Testbenches, corners, Monte Carlo and post-layout simulation: see the `analog-simulation` skill.
- Digital logic in the same project, a LibreLane block or standard cells next to analog: see the
  `mixed-signal` skill.
- Measuring a finished chip: [testing projects with the Analog Discovery](https://tinytapeout.com/guides/analog-discovery/).
