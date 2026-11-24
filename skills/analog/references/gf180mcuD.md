# gf180mcuD analog notes

Read this for a GlobalFoundries 180 nm (`ttgf`) analog or custom-GDS project, before drawing
the first device and again when the `precheck` job fails.

## Sign-off is the KLayout deck, not magic

On gf180mcuD the precheck does not run magic DRC. It runs the PDK's full KLayout deck
(`gf180mcu.drc`: FEOL, BEOL and connectivity rules) without the density rules, then the antenna
rules as a separate check. A layout with zero magic DRC errors can still have thousands of
KLayout violations, typically off-grid vertices, wrong cut sizes and metal slotting. Use magic DRC
while drawing; judge the layout by the deck.

Run the deck the way the precheck does, from the project folder, with `PDK_ROOT` set and the
`klayout` binary on `PATH` (the `klayout` Python module alone cannot run the deck):

```bash
TOP=tt_um_yourname_project
klayout -b -r $PDK_ROOT/gf180mcuD/libs.tech/klayout/tech/drc/gf180mcu.drc \
  -rd input=$PWD/gds/$TOP.gds -rd topcell=$TOP -rd variant=gf180mcuD -rd run_mode=deep \
  -rd threads=1 -rd decks=all,-density,-antenna -rd report=$PWD/drc.lyrdb
klayout -b -r $PDK_ROOT/gf180mcuD/libs.tech/klayout/tech/drc/gf180mcu.drc \
  -rd input=$PWD/gds/$TOP.gds -rd topcell=$TOP -rd variant=gf180mcuD -rd run_mode=deep \
  -rd threads=1 -rd decks=antenna -rd report=$PWD/antenna.lyrdb
klayout gds/$TOP.gds -m drc.lyrdb      # browse the markers
```

`klayout -b -r .../gf180mcu.drc -rd help=true` lists the other options. Density hits (`PL.8`,
`M1.4` to `M5.4`, `MT.3`) are expected in a single macro and are not checked: fill is added after
precheck. Every other rule counts.

## Rules that bite

| Rule                     | Value                                                                                     |
| ------------------------ | ----------------------------------------------------------------------------------------- |
| Manufacturing grid       | 5 nm: every vertex, on every layer (`*_OFFGRID`)                                          |
| Contact (`CO.1`)         | exactly 0.22 x 0.22 um                                                                    |
| Via1 to Via3 (`V1.1`...) | exactly 0.26 x 0.26 um                                                                    |
| Wide metal (`MSLOT.1`)   | solid metal wider than 30 um in both directions needs slots; one slot direction is enough |
| Routing metals           | Metal1 to Metal4. Metal5 is forbidden; power stripes and pins are on Metal4               |
| Power stripe width       | at least 0.8 um (precheck); the init script draws 2 um                                    |
| Pin labels               | `Metal4_Label` (46/10) over the Metal4 pin shape, in the top cell                         |
| Boundary                 | a `PR_bndry` rectangle covering exactly the frame's die area                              |

Cuts are fixed-size, not minimum-size: never scale a cut. A design scaled from a 130 nm PDK
(for example by 1.45) lands vertices on a 1 nm grid and turns contacts into 0.232 um squares.
After scaling, snap every vertex to 5 nm and replace each cut with an exact square centred on the
grid. Write the GDS with a 1 nm database unit and the geometry on the 5 nm grid; a 5 nm database
unit has made magic fail to recognise PDK standard cells and flatten them, which breaks LVS.

## Devices and supplies

- VDPWR is 3.3 V. VAPWR goes through a 5 V-rated power gate and analog switch on this PDK, so it
  can carry more than VDPWR _(inferred from the multiplexer's `tt_pg_5v0` / `tt_asw_5v0`; check
  the shuttle's datasheet for the voltage actually supplied)_.
- 3.3 V devices: `nfet_03v3` / `pfet_03v3`. Do not draw the `Dualgate` layer (55/0) over them: it
  turns them into 6 V devices with a much longer minimum gate. Devices on VAPWR: `nfet_06v0` /
  `pfet_06v0` (or `*_05v0`), drawn with the MV layers in magic.
- Never drive a gate in the VAPWR domain straight from 3.3 V logic: put a level shifter between
  them (a 3.3 V inverter driving a cross-coupled latch on VAPWR).
- No MIM capacitors: the precheck runs MIM option B on five metal layers, whose top plate is
  Metal5, and Metal5 is forbidden. Build large capacitors from MOS gates, small ones from metal
  fingers (MOM).
- Poly resistor `ppolyf_u_1k`: 1 kOhm per square nominal in the models. Build ratios from one unit
  resistor in series and parallel, not from differently sized ones.
- Models for ngspice: `.include $PDK_ROOT/gf180mcuD/libs.tech/ngspice/design.ngspice` and
  `.lib $PDK_ROOT/gf180mcuD/libs.tech/ngspice/sm141064.ngspice typical`, plus `res_typical`,
  `moscap_typical` or `mimcap_typical` for those devices; `ss` / `ff` for the corners.
- Substrate and well taps are yours to draw: nothing in the frame provides them. After extraction
  every nfet body must reach VGND and every pfet body its own supply, with no `VSUBS` node and no
  floating well left.

## Standard cells inside an analog layout

TT uses `gf180mcu_fd_sc_mcu7t5v0` (7-track) characterised at 3.3 V. Its cells have no well taps:
put a `gf180mcu_fd_sc_mcu7t5v0__filltie` cell in each row and an `__endcap` at each row end, then
connect the row rails to VDPWR and VGND. Without them the wells float, which extraction shows.
Place cells unscaled and on grid. The flip-flops have only a `Q` output (`dffq`, `dffrnq`, ...):
make a toggle stage with an `inv` cell from `Q` to `D`. Use `tiel` / `tieh` for constant levels.
For LVS, add `$PDK_ROOT/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/spice/gf180mcu_fd_sc_mcu7t5v0.spice`
to the netgen source side.

## Reference designs

Working gf180mcuD analog projects with their full flow committed:

| Project                                                                         | Shows                                                                      |
| ------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| [tt_tnt_gf_555](https://github.com/smunaut/tt_tnt_gf_555)                       | magic + xschem harness (`mag/Makefile`, `mag/tcl/`): DRC, LVS, PEX, export |
| [ttgf_analog_factory_test](https://github.com/smunaut/ttgf_analog_factory_test) | VAPWR design, level shifter, rail sense lines                              |
| [gf-r2r-dac](https://github.com/mattvenn/gf-r2r-dac)                            | LibreLane digital block + hand-drawn R-2R (see the `mixed-signal` skill)   |
| [ttgf0p3-momcap](https://github.com/htfab/ttgf0p3-momcap)                       | metal-only MOM capacitor generated from Python                             |
| [ttgf0p3-submission](https://github.com/christoph-weiser/ttgf0p3-submission)    | OTA test buffer with a specification table in `docs/info.md`               |
