---
name: analog-simulation
description: Simulate and verify the analog part of a Tiny Tapeout project with xschem and ngspice - netlist schematics headless, set up the PDK's ngspice init file, run corners, Monte Carlo mismatch, supply, temperature and power-up sweeps, compare the extracted layout with the schematic, and catch the failures that ngspice reports quietly. Use it whenever a Tiny Tapeout analog or mixed-signal design (ua[] pins, transistor-level blocks) needs a testbench, a simulation gives a surprising or suspiciously good result, Monte Carlo samples look identical, a post-layout result differs from the schematic, or someone asks whether a design is verified well enough to tape out.
---

# Simulate and verify analog blocks

The precheck only checks the layout (see the `analog` skill). Whether the circuit works is decided
here, in simulation, before tapeout. A chip cannot be patched after it is made.

## Run ngspice the PDK's way

- Netlist xschem schematics headless: `xschem -n -s -q -o <out_dir> <file>.sch`. Check the netlist
  for missing symbols before simulating; the exit code does not tell you.
- Copy the PDK's ngspice init file, `$PDK_ROOT/$PDK/libs.tech/ngspice/spinit` on sky130A, to
  `.spiceinit` in the directory ngspice runs in. It sets the options the PDK models need. Lower
  its `num_threads` when several ngspice processes run at once, so their total stays within the
  machine's CPUs.
- That file selects the KLU solver (`option klu`), and ngspice refuses noise analysis with it
  (`Noise simulation is not (yet) supported with 'option KLU'`). Leave `option klu` out of the
  `.spiceinit` used for `.noise` runs.
- Load corners from the PDK library (on sky130A, `.lib $PDK_ROOT/$PDK/libs.tech/ngspice/sky130.lib.spice tt`).
  On sky130A the MOS corners (`tt`, `ss`, `ff`, `sf`, `fs`) leave resistors and capacitors typical;
  their corners are separate sections (`ll`, `hh`, `hl`, `lh`, and combinations such as `ss_ll`).
  Sections ending in `_mm` add device mismatch for Monte Carlo.
- Model the pad and board on every output (see the `analog` skill): a block that works into an
  ideal node can fail on the pin.

## Failures ngspice does not report as errors

- **A failed operating point becomes a "transient op".** ngspice prints `Transient op started` and
  carries on from an unsettled state. Grep every log for it; in extracted netlists the usual cause
  is a node with no DC path (an unconnected stub), which a 1 GOhm resistor to ground fixes.
- **Monte Carlo with a fixed seed repeats itself.** With `.options seed=N`, every `reset` draws the
  same sample again. Run one sample per process, each with its own seed, and check the results for
  duplicate rows.
- **A run can end early and still exit cleanly.** Judge each run by its output files and the end
  of its log, not by the exit code.

## What to sweep

Corners alone miss most real failures. Before tapeout, run at least:

| Check                                        | Catches                                                          |
| -------------------------------------------- | ---------------------------------------------------------------- |
| Monte Carlo mismatch                         | offsets and trim ranges: anything with a trim loop needs it      |
| each supply swept on its own, the others not | level shifters and bias that fail only with the rails apart      |
| temperature, including outside the spec      | where the cliff is                                               |
| power-up (fast and slow ramps), power-down   | start-up failures, output glitches, floating nodes when off      |
| each supply missing in turn                  | outputs pulled to the wrong rail                                 |
| interacting blocks simulated together        | loading between blocks: give each bench the real source and load |
| the extracted layout against the schematic   | parasitics, on what the block must do (gain, delay, offset)      |

- Put the operating point in the middle of the working range, not at a knee, and check that the
  Monte Carlo spread (mean plus and minus 4 sigma) stays inside any trim range on both sides.
- After any circuit change, rerun the system-level checks, not only the block's.
- Write down what simulation does not cover (package, board, latch-up, substrate coupling) in the
  project's docs.

## Prove the checks can fail

A check that cannot fail proves nothing. For every checker (a testbench assertion, an LVS run, a
pinout or bus check), plant a deliberate fault once and confirm it fails: swap two bus bits,
change a device size, disconnect a pin. Also confirm each testbench result moves when its
stimulus does: if no input and ten times the input give the same answer, the bench is broken.
Smoke-test every new testbench with a short run before starting a long one.

## Post-layout simulation

Extract the layout with parasitics (see the `analog` skill) and run the same testbench on the
extracted netlist in place of the schematic subcircuit, with the same port order. Drive only the
supplies and real inputs, so missing taps and floating wells show up. Extracted netlists run far
slower than schematics, especially long high-gain paths with noise: time a short run first, and
simulate a split system (fast part extracted, slow part behavioural) when the whole would take days.

## Further reading

Harald Pretl's open courses (JKU Linz) cover the design side:
[Analog Circuit Design](https://github.com/iic-jku/analog-circuit-design) (start with the appendix
on circuit designer's etiquette), [Design of Complex ICs](https://github.com/iic-jku/design-complex-ic)
(layout, matching, extraction) and
[Radio-Frequency Integrated Circuits](https://github.com/iic-jku/radio-frequency-integrated-circuits).
