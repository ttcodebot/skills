---
name: vga-output
description: Generate VGA video (and sound) from a Tiny Tapeout design - the Tiny VGA pinout, 640x480 timing, a sync/colour skeleton, the design habits that held up on real silicon, and a loop that renders frames to PNG so the picture can be checked without a monitor. Use it whenever a Tiny Tapeout project (a tt_um_* module) draws to a screen - games, demos, demoscene entries, screensavers, anything with hsync / vsync or the VGA Playground - when a picture is blank, shifted, torn or flickering, and before hardening a VGA design, even if the user only asks to "show something on screen".
---

# VGA output from a Tiny Tapeout design

A tile holds a few hundred flip-flops and a 640x480 frame has 307,200 pixels, so there is no
frame buffer: the design "races the beam", computing each pixel's colour from the beam position
and a little state while the monitor scans. Every choice below follows from that.

## Pins and timing

The Tiny VGA Pmod takes the whole OUTPUT header; the bit order is in the skeleton below. Audio and
a gamepad have standard pins too (see the `pinout` skill).

Use 640x480 at 60 Hz, nothing custom: non-standard modes that looked fine on one screen have failed
on other monitors. Set `clock_hz: 25175000`. Take
[`hvsync_generator.v`](https://github.com/TinyTapeout/vga-playground/blob/main/src/examples/common/hvsync_generator.v)
from the VGA Playground instead of writing counters again, and take the current file: copies from
before February 2026 have active-high sync (`hsync <= (hpos>=...` without the `~`).

## Skeleton

```verilog
wire hsync, vsync, display_on;
wire [9:0] hpos, vpos;
hvsync_generator sync_gen (
    .clk(clk), .reset(~rst_n),
    .hsync(hsync), .vsync(vsync), .display_on(display_on), .hpos(hpos), .vpos(vpos)
);

wire [5:0] rgb = /* {r[1:0], g[1:0], b[1:0]} from hpos, vpos and state */;

reg [5:0] rgb_q;  // registered colour: no glitches, and lined up with the registered sync
always @(posedge clk) rgb_q <= display_on ? rgb : 6'b0;  // black outside the visible area

wire [1:0] r = rgb_q[5:4], g = rgb_q[3:2], b = rgb_q[1:0];
assign uo_out = {hsync, b[0], g[0], r[0], vsync, b[1], g[1], r[1]};

// One pulse per frame, at the start of vertical blanking: the place to move things.
wire frame_tick = (hpos == 0) && (vpos == 480);
reg [7:0] frame;
always @(posedge clk)
  if (~rst_n) frame <= 0;
  else if (frame_tick) frame <= frame + 1;
```

## Habits that held up on silicon

These come from taped-out designs and their test reports, in rough order of how often they bite.

- **Reset every piece of state, and use one clock** (see the `project-setup` skill). In taped-out
  VGA designs a missing reset is the most common defect: objects off screen or music out of step
  until a manual reset, or forever. Move things on `frame_tick`, not in `always @(posedge vsync)`.
- **Register the colour outputs**, as in the skeleton. Colour that comes straight from combinational
  logic glitches at the pins while the logic settles, more with every level of logic, and sits one
  clock ahead of the sync. Six flip-flops fix both.
- **Move things only during blanking.** State that changes while the beam is in the visible area
  tears the picture. Update per frame on `frame_tick`; prepare per-line values during the 160
  clocks of horizontal blanking.
- **Mind the 39.7 ns pixel.** When the colour logic gets deep, pipeline it and delay hsync, vsync
  and `display_on` by the same number of stages, or run at twice the pixel clock (50.35 MHz, just
  over the usual 50 MHz guideline) with a pixel enable. Leave margin: designs that only just met timing needed a slower clock on real
  chips, so read the slow-corner numbers after hardening.
- **Stream from external memory.** With a QSPI Pmod there is no time for a random read per pixel:
  send the command and address during blanking, then read sequentially into a small FIFO or line
  buffer, and keep the read latency adjustable (see the `pinout` skill).
- **Lock audio to video.** Generate the one-bit audio on `uio[7]` from the same counters, for
  example one sample per line (31.5 kHz) and one tempo tick per frame, so sound and picture cannot
  drift and both restart together.
- **Dither in space, not time.** For more than 64 colours use an ordered (Bayer) pattern on
  `hpos` / `vpos`; frame-to-frame dithering looks fuzzy on LCD monitors.

## Fast iteration

Do not wait for hardening or hardware to see the picture. Render frames with
[tt-vga-sim](https://github.com/TinyTapeout/tt-vga-sim) and look at them:

```bash
git clone https://github.com/TinyTapeout/tt-vga-sim ~/tt-vga-sim   # once
uv run ~/tt-vga-sim/vga_sim.py . -n 3 --check-reset                # in the project folder
```

It starts every flip-flop at a random value, as a real chip does, and writes
`frames/frame_0000.png` (the first picture after reset) and on. Read its text output before the
pictures: it reports the sync timing, colour outside the visible area and missing resets. A
`Note: frame 0 began before reset ended` means the sync counters do not start at the top of the
frame after reset. Render 60 frames (`-n 60`) to see a second of motion. Its README covers GIF and
MP4 output, inputs, and a workflow to add to the project's CI with `--compare` against reference
frames.

Rendering runs the Verilog cycle by cycle and does not model the chip's timing, so also run the
project's cocotb tests and the gate-level test. A project exported from the VGA Playground has a
`test/test.py` that compares frames 0 to 2 with `test/reference/frame0.png` to `frame2.png` at gate
level too; `--compare test/reference/` reads the same files, so one set of references serves both.

To let a person try the design live in a browser, push it to GitHub and give them
`https://vga-playground.com/?repo=https://github.com/<owner>/<repo>` (add `&ref=<branch>` for a
branch other than the default).
