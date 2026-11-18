---
name: testing
description: Test a Tiny Tapeout design with cocotb - run the RTL testbench in test/ and read its results correctly, and run the same test on the hardened gate-level netlist, where reset and X problems that RTL simulation hides show up. Use it whenever a Tiny Tapeout project (a tt_um_* module) needs tests, a test fails locally or in the GitHub `test` or `gl_test` job, someone asks how to simulate or debug their design, or before submitting a design to a shuttle.
---

# Test a Tiny Tapeout design

The template's cocotb test in `test/` runs twice: on the Verilog (RTL) on every push, and on the
gate-level netlist after hardening. A green gate-level test is the best evidence before tapeout
that the chip will behave like the simulation, so write tests that can run in both.

## Run

```bash
cd test
make -B
python -m cocotb_tools.check_results results.xml
```

`make` exits with success even when a test fails, so check `results.xml` as the last line does
(the template's CI does the same).

## Write tests that also run at gate level

- Test only through the top-level ports (`ui_in`, `uo_out`, `uio_*`). Internal signal names do
  not survive synthesis, so a test that reads them cannot run at gate level.
- Check the outputs right after reset too: a register without reset starts as X at gate level.
- `uio_oe` says which bidirectional pins the design drives; check it when the design uses them.
- For VGA output, render frames instead of asserting on pins (see the `vga-output` skill).
- An analog top has no gate-level netlist to test; test its digital blocks on their own and
  simulate the rest with ngspice (see the `mixed-signal` skill).

## Gate-level test

After hardening (see the `hardening` skill), run the test on the netlist. The `gl_test` job of
the `gds` workflow does this on every push; locally, with `PDK_ROOT` and `PDK` set as for
hardening (the path in the template's `test/README.md` is out of date):

```bash
cd test
TOP_MODULE=$(cd .. && ./tt/tt_tool.py --pdk $PDK --print-top-module)
cp ../runs/wokwi/final/pnl/$TOP_MODULE.pnl.v gate_level_netlist.v   # IHP: final/nl/$TOP_MODULE.nl.v
make -B GATES=yes
python -m cocotb_tools.check_results results.xml
```

A test that passes at RTL but fails at gate level almost always means a register without reset
(it starts as X), logic that relied on an `initial` value, or a test that reads internal signals.
If `make` cannot find the PDK's `primitives.v`, run `ciel ls` and `ciel enable <hash>` to enable
the installed PDK version.
