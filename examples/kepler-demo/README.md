# kepler-demo: a Kepler 2000 demo that squeezes the Z80 (about 6.13 MHz)

A 16 KiB cartridge (at 0x8000, autostart `55 AA 59 45`; it uses 14.2 KiB). It plays the Kepler 2000 music (about 34 s) **while** animating the LCD's CGRAM and the caps-lock LED, with interrupts disabled and 100 % of the T-states spread over one single loop.

## What the loop does (256 T-states = 41.7 us per iteration; `gen_demo.py` generates it with the exact count)
* **Audio**: 2 samples per iteration (16-bit phase accumulator -> square wave on bit 3 of port 0x12), fs about 47.9 kHz. Measured in MAME: every sample comes out exactly 128 T-states after the previous one.
* **CGRAM**: 1 write to the LCD per iteration (>= 37 us between writes, as the HD44780 requires). Each frame (71 iterations, 2.96 ms, about 337 frames/s) rewrites the 64 bytes of CGRAM (8 characters). The 4 x 20 screen is 80 cells that use only those 8 characters (`(col + 2*row) & 7`), so the picture is a periodic ring of 40 x 8 pixels; the loop computes in real time 8 pixel strips with fractional (8.8) shifting, a sine ripple per row and tables of 5-pixel windows. Each frame updates one row (5 iterations of computation).
* **LED** (caps, port 0x12 bit 5): mixed into every audio sample (`or a,ixl` / `or a,ixh`, undocumented opcodes `DD B5` / `DD B4`) -> 3 brightness levels by 24 kHz PWM. It pulses with the bass (kick/bass line); in the warp jump and the lasers it grows with the pitch.
* **Synchrony**: in the warp jump and the final alert the speed of the stripes follows the pitch of the sweep (`fetch_note`).

## Scenes
warp jump (accelerating stripes) - scan (a breathing sine wave) - contact x2 (the words "KEPLER" and "GENIO" as a waving flag) - alert (diagonal stripes with lasers) - finale ("2000" and fading pings). When the section changes the tables are rebuilt (about 8 ms, hidden in the 14 ms of silence that ends each section).

## Use
```bash
make VGLDK=/path/to/vgldk      # -> kepler_demo_gl2000_mirrored_AT28C256_32K.bin (32 KiB, for MAME's -cart or an AT28C256)
```
`gen_demo.py` (music, scenes, loop) and `gen_helpers.py` (helper routines) generate `song.h`, `scenes.h`, `loop.h` and `helpers.h`. Needs `sdcc`, `makebin`, `python3`.

## Status
* It uses VGLDK's stock gl2000 profile with its own LCD map and never polls the OFF key while it runs (interrupts are disabled and every T-state is used); it waits for a key at the end of each pass. To switch the unit off during playback, remove the cartridge.
* Tested on a real Genio 2000 by the author, as well as in MAME. It relies on the LCD accepting one write every 41.7 us (at 6.13 MHz) and on the clock being the measured 6.13179 MHz.
* It uses `ld ixl/ixh` and `or ixl/ixh` (undocumented): they work on Zilog's Z80 (the unit's Z84C0006), not on every clone.
* MAME does not model the LCD's persistence nor the PWM brightness of the LED (in MAME the LED looks on or off depending on the instant of the capture); on a real STN display the animation looks different from MAME.

Licence: GPL-3.0-or-later (it is built against VGLDK, see `../README.md`).
