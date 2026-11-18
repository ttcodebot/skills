---
name: pinout
description: Standard pin assignments for Tiny Tapeout projects - which ui_in / uo_out / uio pin carries which signal for the Tiny VGA, Audio, Gamepad, QSPI flash/RAM, 7-segment and Rotary encoder Pmods, the demoboard's own 7-segment display and DIP switches, and UART / SPI. Use it whenever a Tiny Tapeout design (a tt_um_* module) gets its pins assigned or changed, when filling the `pinout:` section of info.yaml or setting uio_oe, and when a design must talk to a Pmod, a VGA monitor, a speaker, a game controller, external memory or a serial console - even if the user never says "pinout".
---

# Tiny Tapeout pinouts

Tiny Tapeout is a shared chip: other people will run your design on their own demoboard, with the
Pmods they already own. A design that follows the common pinouts works on that hardware with no
rewiring, and in tools such as the VGA Playground. Use these pinouts unless the design cannot fit
them, and say so in the project docs when you deviate.

## The 24 project pins

| Verilog port                       | Direction                        | Demoboard Pmod header |
| ---------------------------------- | -------------------------------- | --------------------- |
| `ui_in[7:0]`                       | input to the chip                | INPUT                  |
| `uo_out[7:0]`                      | output from the chip             | OUTPUT                 |
| `uio_in` / `uio_out` / `uio_oe`    | per pin; `uio_oe` bit 1 = output | BIDIR                  |

On each header, Pmod pins IO1..IO4 (top row) are bits 0..3 and IO5..IO8 (bottom row) are bits 4..7.
Logic levels are 3.3 V. `clk` and `rst_n` are not on any Pmod header. A Pmod's header follows from
its signal directions, so a peripheral cannot simply be moved to another header. The tables and
`info.yaml` write bit n of `ui_in`, `uo_out` and `uio_*` as `ui[n]`, `uo[n]` and `uio[n]`.

## Pin tables

Two peripherals can share a design when they do not use the same row.

<!-- pinouts:begin (generated from pinouts.yaml, do not edit) -->

**`ui_in` - INPUT header**

| Pin | Gamepad Pmod | Rotary encoder Pmod | UART | UART (alternative) |
| --- | --- | --- | --- | --- |
| `ui[0]` |  | A |  |  |
| `ui[1]` |  | B |  | RX |
| `ui[2]` |  | SW |  |  |
| `ui[3]` |  |  | RX |  |
| `ui[4]` | LATCH |  |  |  |
| `ui[5]` | CLK |  |  |  |
| `ui[6]` | DATA |  |  |  |
| `ui[7]` |  |  |  |  |

**`uo_out` - OUTPUT header**

| Pin | Tiny VGA Pmod | 7-segment display (on the demoboard) | Dual 7-segment Pmod | Audio Pmod (on uo) | UART | UART (alternative) |
| --- | --- | --- | --- | --- | --- | --- |
| `uo[0]` | R1 | A | A |  |  | TX |
| `uo[1]` | G1 | B | B |  |  |  |
| `uo[2]` | B1 | C | C |  |  |  |
| `uo[3]` | VSYNC | D | D |  |  |  |
| `uo[4]` | R0 | E | E |  | TX |  |
| `uo[5]` | G0 | F | F |  |  |  |
| `uo[6]` | B0 | G | G |  |  |  |
| `uo[7]` | HSYNC | DP | SEL | AUDIO |  |  |

**`uio` - BIDIR header**

| Pin | QSPI Pmod (flash + 2 PSRAM) | SPI, chip as controller | Audio Pmod | UART (on uio) |
| --- | --- | --- | --- | --- |
| `uio[0]` | CS0 flash (out) | CS (out) |  |  |
| `uio[1]` | SD0 / MOSI (inout) | MOSI (out) |  | RX (in) |
| `uio[2]` | SD1 / MISO (inout) | MISO (in) |  | TX (out) |
| `uio[3]` | SCK (out) | SCK (out) |  |  |
| `uio[4]` | SD2 (inout) |  |  |  |
| `uio[5]` | SD3 (inout) |  |  |  |
| `uio[6]` | CS1 RAM A (out) |  |  |  |
| `uio[7]` | CS2 RAM B (out) |  | AUDIO (out) |  |

<!-- pinouts:end -->

## Notes per peripheral

- **Tiny VGA**: 2 bits per colour, R1/G1/B1 are the high bits. It takes the whole OUTPUT header,
  so a VGA design puts audio on `uio[7]` and a UART on `uio`.
- **Audio Pmod**: one-bit audio (PWM or sigma-delta) on `uio[7]`, or on `uo[7]` in designs that
  leave the OUTPUT header free. Keep the PWM frequency at 200 kHz or more, as the
  Pmod's filter cutoff is high. The Pmod passes the other seven pins through to a second Pmod and
  pulls that Pmod's IO8 high: with a QSPI Pmod stacked on it, the flash and RAM A stay usable and
  RAM B stays deselected. For stereo the convention is left on `uio[6]` and right on `uio[7]`, which
  also takes RAM A's chip select.
- **Gamepad Pmod**: the chip only listens; the Pmod sends the state of one or two SNES-style
  controllers on three inputs. Instantiate `gamepad_pmod_single` or `gamepad_pmod_dual` from
  [`gamepad_pmod.v`](https://github.com/TinyTapeout/vga-playground/blob/main/src/examples/common/gamepad_pmod.v)
  instead of writing the protocol again.
- **QSPI Pmod**: 16 MB flash and two 8 MB PSRAMs on one bus. Drive all three chip selects high when
  idle, including the ones the design does not use. The data arrives after a round trip through the
  chip's I/O multiplexer and pads, so designs that worked on silicon make the read latency
  adjustable (input pins or a calibration step) instead of fixing it in the RTL.
- **7-segment display on the demoboard**: wired straight to `uo_out`, active high, so it lights up
  with whatever the design drives there (harmless for VGA or UART designs).
- **Dual 7-segment Pmod**: same segment order; `SEL` high lights the right digit, low the left, so
  alternate the two digits fast enough to avoid flicker. It has no decimal point.
- **DIP switches on the demoboard**: switch N pulls `ui[N-1]` high. The demoboard firmware can
  drive the same pins, so do not assume a switch is the only source.
- **Rotary encoder Pmod**: quadrature A/B, idle high; `SW` is high while the knob is pressed. The
  signals are filtered on the Pmod but still asynchronous: pass them through two flip-flops.
- **UART**: the three pairs in the tables are the ones the demoboard's RP2350 can serve with its
  hardware UARTs, so the user gets a serial console with one line of MicroPython, for example
  `machine.UART(1, baudrate=115200, tx=tt.pins.ui_in3.raw_pin, rx=tt.pins.uo_out4.raw_pin)`
  (`UART(0, ...)` with `ui_in1` / `uo_out0` for the alternative, `UART(1, ...)` with `uio1` / `uio2`
  on `uio`). Any other pin pair needs a PIO UART on the demoboard. RX and TX are named from the
  chip's side.
- **SPI, chip as controller**: the same pins as the QSPI Pmod's flash in single-SPI mode.

There is no common pinout yet for I2C or for SPI with the chip as the peripheral: pick free pins and
document them.

## Write the pinout into the project

Put the signal names from the tables in the `pinout:` section of `info.yaml`, and set `uio_oe`
per pin from the `(out)` / `(in)` marks in the BIDIR table. Example for VGA with audio and a
gamepad:

```verilog
assign uo_out  = {hsync, b[0], g[0], r[0], vsync, b[1], g[1], r[1]};
assign uio_out = {audio, 7'b0};
assign uio_oe  = 8'b1000_0000;  // uio[7] drives the Audio Pmod, the rest stay inputs
wire gamepad_latch = ui_in[4], gamepad_clk = ui_in[5], gamepad_data = ui_in[6];
```

Then check the result against the tables for two signals on one pin, and for a `uio` pin whose
`uio_oe` bit disagrees with its direction.

More Pmods, including ones built for a single project:
https://github.com/TinyTapeout/awesome-tinytapeout-pmods
