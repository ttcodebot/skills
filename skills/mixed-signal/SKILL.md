---
name: mixed-signal
description: Combine digital logic with hand-drawn analog in one Tiny Tapeout analog project - harden a digital block with LibreLane as a macro and place it next to custom analog layout, or place standard cells by hand in magic, with the right LibreLane settings (top metal, no power rings, pin side, unbuffered outputs), well taps, supply domains and level shifting, LVS that mixes gate-level Verilog with xschem netlists, and ngspice + Verilator co-simulation of the whole thing. Use it whenever a Tiny Tapeout project with ua[] analog pins also needs counters, state machines, shift registers, DAC or ADC control, clock dividers or any other digital logic, when someone wants to drive an analog block from ui_in / uio_in, or when LVS of such a project fails.
---

# Mixed-signal Tiny Tapeout projects

A mixed-signal project is an analog project (see the `analog` skill): you commit one GDS and LEF
built in the analog frame, and the precheck checks them. The digital part lives inside that
layout. No template hardens a `tt_um_*` Verilog top with analog pins for you: the analog
templates' `gds` workflow only packages the GDS you commit.

The reverse, a LibreLane-hardened top on the analog frame with the analog part placed as a macro
(`MACROS` in `config.json`), has been done
([ttgf0p3-tinyQV](https://github.com/MichaelBell/ttgf0p3-tinyQV), whose R-2R DAC drives `ua[0]`),
with a hand-built hardening and submission flow. Treat it as expert territory, and the precheck
still applies in full.

## Pick how to build the digital part

| Digital part                     | Build it as                                                                         |
| -------------------------------- | ----------------------------------------------------------------------------------- |
| A handful of gates or flip-flops | Standard cells placed and wired by hand in magic (or placed from Python with gdstk) |
| Counters, FSMs, registers, a CPU | A LibreLane macro, instanced in the analog top cell                                 |

Reference: [gf-r2r-dac](https://github.com/mattvenn/gf-r2r-dac) (gf180mcuD) hardens a sine and
divider block with LibreLane and drives a hand-drawn R-2R ladder; its `openlane/`, `mag/`,
`verilog/` and `sim/` folders cover every step below.

## Harden the digital block as a macro

Write the block as its own module with explicit supply ports (`VDD` / `VSS` or similar), test it
with cocotb like any design (see the `testing` skill), and harden it with the LibreLane version
the shuttle uses (see the `hardening` skill for installing it). Use a `config.json`; Tcl configs
are deprecated in LibreLane. Settings that matter for a block inside an analog layout:

| Setting                                           | Why                                                                                                       |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `FP_SIZING: "absolute"`, `DIE_AREA: [0, 0, w, h]` | Leave the rest of the frame free for analog                                                               |
| `RT_MAX_LAYER`                                    | The project's top metal: `met4` (sky130A), `Metal4` (gf180mcuD, ihp-sg13cmos5l), `TopMetal1` (ihp-sg13g2) |
| `PDN_MULTILAYER: false`                           | No core ring and no straps on the top layers; you connect the rails yourself                              |
| `IO_PIN_ORDER_CFG`                                | Put the outputs on the edge that faces the analog block                                                   |
| `DESIGN_REPAIR_BUFFER_OUTPUT_PORTS: 0`            | No buffers on outputs that drive analog nodes                                                             |
| `CLOCK_PORT`, `CLOCK_PERIOD`                      | As for any design                                                                                         |

Older configs use the names `DESIGN_IS_CORE`, `FP_PIN_ORDER_CFG` and
`PL_RESIZER_BUFFER_OUTPUT_PORTS` for the same settings. When copying a config from another
project, remove every cell name and library path from another PDK (sky130 `DECAP_CELL` lists are
the usual leftovers).

On gf180mcuD LibreLane defaults to the 5 V characterisation, but the chip's core supply is 3.3 V.
Copy the 3.3 V settings Tiny Tapeout uses (`VDD_PIN_VOLTAGE`, `LIB_SYNTH`, `LIB_FASTEST`,
`LIB_SLOWEST`, `DEFAULT_CORNER`, `STA_CORNERS`) from the `gf180mcuD` class in
[tt-support-tools' `tech.py`](https://github.com/TinyTapeout/tt-support-tools/blob/main/tech.py),
or the timing results describe the wrong chip.

From the run's `final/` folder, commit the GDS and the gate-level netlist (`final/pnl/`; IHP
writes `final/nl/`). Read the GDS into magic (`gds read`), save it as a cell and `use` it in the
top cell next to the analog cells.

## Place standard cells by hand

- Place cells on the library's placement grid, unscaled, in rows; mirror every other row so the
  rails abut.
- Wells need taps. sky130: a tap cell (for example `sky130_fd_sc_hd__tapvpwrvgnd_1`) within 15 um
  of every transistor. gf180mcuD: `filltie` in each row and `endcap` at row ends (see the
  `analog` skill's [gf180mcuD notes](../analog/references/gf180mcuD.md)).
- Connect each row's power rails to the supply stripes at several points along the row.
- Tie constant inputs and otherwise floating pins with the library's tie cells (`conb` on sky130,
  `tiel` / `tieh` on gf180mcuD) or straight to VGND.

The Tiny Tapeout guide [Laying out standard cells with magic](https://tinytapeout.com/guides/laying-standard-cells-with-magic/)
walks through this for sky130.

## Supplies and domains

- Digital logic runs from VDPWR. Analog that needs more headroom runs from VAPWR where the PDK
  has it (see the `analog` skill); VGND is common.
- Never drive a gate in the VAPWR domain directly from a VDPWR logic signal. Insert a level
  shifter, and check the extracted netlist for any net that crosses domains without one.
- Express the domain split in `src/project.v`: one child instance per block, each with the supply
  pins it really uses. That file is the precheck's stub and the top of your LVS netlist.

## LVS the whole layout

netgen compares the extracted layout with a source assembled from several netlists, all read into
one netlist object:

```tcl
set layout [readnet spice tt_um_yourname_project.lvs.spice]
set source [readnet spice /dev/null]
readnet spice $::env(PDK_ROOT)/$::env(PDK)/libs.ref/<std_cell_lib>/spice/<std_cell_lib>.spice $source
readnet verilog ../src/project.v $source                  ;# structural top
readnet verilog ../verilog/gl/<block>.pnl.v $source       ;# LibreLane netlist of the block
readnet spice ../xschem/simulation/<analog_cell>.spice $source
lvs "$layout tt_um_yourname_project" "$source tt_um_yourname_project" \
    $::env(PDK_ROOT)/$::env(PDK)/libs.tech/netgen/$::env(PDK)_setup.tcl lvs.report -blackbox
```

Then check `lvs.report` for `Circuits match uniquely`, and for property, pin or port errors. The
supply names in `project.v`, the block's power pins and the analog cells' subcircuit ports must
agree, or LVS reports shorts and opens on the supplies.

## Simulate digital and analog together

ngspice can run the RTL as a digital device through Verilator (`d_cosim`), driving the extracted
or schematic analog netlist:

```bash
ngspice vlnggen ../verilog/rtl/*.v      # compiles the Verilog into <top>.so
ngspice mixed.cir
```

From the R-2R project's `sim/mixed.cir`: the digital inputs and outputs are listed in brackets,
and the analog netlist is an ordinary subcircuit.

```spice
adut [ clk n_rst ext_data d7 d6 d5 d4 d3 d2 d1 d0 load_divider ] [b7 b6 b5 b4 b3 b2 b1 b0] null dut
.model dut d_cosim simulation="./r2r_dac_control.so"
.include "../xschem/simulation/r2r.spice"
xr2r b0 b1 b2 b3 b4 b5 b6 b7 out 0 r2r
* simulate tt output path
R1 out pin_out 500
C1 out 0 5p
```

Model the path to the pin as in the `analog` skill, and set the supply voltages to the PDK's (the
example's 1.8 V `vcc` is a sky130 leftover in a gf180mcuD project).

## Before submitting

Everything in the `analog` skill applies unchanged, above all the precheck, which must pass with
the template's workflows untouched. Also run the block's gate-level test (see the `testing` skill)
on the netlist you placed.

When a block's ports change, update `src/project.v`, the LVS source and any simulation stubs of
the analog cells in the same commit: a stale stub passes every analog check and breaks the
Verilog ones.
