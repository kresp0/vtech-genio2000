# readysetgo: "READY, SET, GO!" demo for the VTech Genio 2000 (Z80 at about 6.13 MHz)

A 16 KiB cartridge (at 0x8000, autostart `55 AA 59 45`; it uses 15,379 bytes) that starts like the machine's BASIC: a `READY` prompt with a blinking cursor, where somebody types `run`. Then giant letters spell **READY**, the fleet charges up behind a giant **SET**, the demo waits for you to press a key, and a giant **GO!** launches three ships out of a mothership and into hyperspace, while the names of the 4x20 machines it is written for scroll along the bottom row. It ends with the credits and the `READY` prompt again. 1-bit music and the caps-lock LED follow everything. Only documented Z80 opcodes are used.

## The show (about 64 s plus the waits)
| Segment | Length | Screen | Sound / LED |
|---|---|---|---|
| basic | 3.1 s | `READY`, blinking block cursor, `run` typed in lower case (as the BASIC editor shows it) | one click per key |
| ready | 3.3 s | READY in 3 x 8 "half-cell" letters (four glyphs: full, top, bottom, empty) dropping in one per 8th note, then a scan line runs through them and they flash inverted | a thunk per letter, an A minor chord stab; LED on the thunks |
| set | 6.7 s | SET, letters dotted and filling from the bottom while a 32-pixel POWER gauge rises to 100 %, then T-3, T-2, T-1, SET! | bass pulse and a rising whine, countdown beeps |
| prompt | 3.3 s, up to 4 times | `ALL SHIPS ARE SET!`, `PRESS ANY KEY TO GO!` (GO! blinks), `PRESS OFF TO QUIT`, a pixel-smooth dot running along a rail | heartbeat and a sonar ping; LED beats with the heart |
| go | 1.7 s | GO! strobing inverted, then the letters fly off the top | noise burst and a falling launch sweep |
| launch | 13.3 s | the mothership's bay door opens (pixel by pixel), three ships fly out pixel-smoothly and accelerate, the mothership scrolls away, the three come back in formation; parallax stars. From 7.7 s the bottom row scrolls `RUNS ON:  Genio 2000 · Genius 4000 · Genius LEADER 4000 Quadro · Genius LEADER 4004 Quadro L · PreComputer Power Pad`, about 7 characters per second | the groove: kick, snare, bass and arpeggio, 8 bars |
| warp | 13.3 s | hyperspace: four glyphs tile the top three rows, every pixel row scrolls at its own speed; a flash for the jump, then faster; the formation bobs and leaves; the names keep scrolling below until the last one has gone | the theme: melody against the chord root, 8 bars |
| credits | 15 s | four pages typed with a cursor: the title, the numbers (3 ships, 8 glyphs, 1 speaker bit...), how to switch off, thanks; then `BREAK IN 10` | the groove again and a coda that ends on A |
| end | 3.3 s, up to 15 times | `READY`, cursor, `KEY:AGAIN  OFF:BYE` | silence |
| bye | 1 s | `SEE YOU LATER!` / `POWERING OFF...`, then the unit switches itself off (OFF is ignored here, so it always plays to the end) | descending jingle |

Any key at the prompt starts GO! (after 4 loops, about 13 s, it launches by itself). At the end, a key plays everything again from the giant READY; after 15 loops (about 50 s) it says goodbye and switches off. **A press of OFF anywhere** (seen down in 15 frames in a row, 42 ms) plays the goodbye and switches off; there is no need to hold it.

The machines named on screen: Genio 2000, Genius 4000, Genius LEADER 4000 Quadro, Genius LEADER 4004 Quadro L, PreComputer Power Pad. Only the Genio 2000 has been emulated (see Status).

## The loop (`gen_engine.py` writes it, `engine.h`)
One iteration = **256 T-states (41.7 us)**: `[audio sample][W1][audio sample][W2][note check][tail]`. The two samples are exactly 128 T apart (fs = 47.9 kHz; 16-bit phase accumulator, bit 15 -> bit 3 of port 0x12, LED bit 5 OR-ed in with `or a,(ix+0/1)` from a two-byte RAM pair, so 3 LED levels by PWM). W1 ends with the LCD write when the iteration has one, so all LCD writes sit at the same place in their iteration: never closer than 252 T (41.1 us). The generator pads every slot with instructions that touch no live register and **asserts that every iteration adds up to exactly 256 T**; a slot it cannot pad stops the build.

A **frame** is 68 iterations (2.84 ms, 352 per second): the CGRAM address command, the 64 CGRAM bytes (glyphs 0-3 from one pointer, 4-7 from another), a countdown to the next event and a 16-bit countdown to the next marquee step. Twelve of the 64 data iterations also scan one key column (port 0x10/0x10, rotating, like the text editor), the OFF key (column 0x80, port 0x11 bit 1, like the firmware routine), and check for the exits (OFF counts in steps of 17 and switches off at 255; a mask byte, `offm`, hides it during the goodbye). When the event countdown reaches 0 a **record** fires: `[runs][count, DDRAM address, characters]...[glyphs 0-3 index][glyphs 4-7 index][frames to wait]`. A wait of 0 is a jump (the hold at the end of every stream). The record costs 7 + 2 per run + 1 per character iterations. When the marquee countdown ends, 25 more iterations rewrite the bottom row (three DDRAM address commands, 20 characters) straight from the text in ROM, starting at the marquee pointer, and move the pointer one character on: the scrolling names cost no event data at all. The encoder simulates the frames one by one, marquee steps included, to place every step on time (at most 3.3 ms late), and the stream never writes the bottom row while the marquee owns it.

The **music** is one voice of 3-byte entries (14-bit phase step, LED level, duration in units of 32 iterations), plus three ops that `fetch_note` interprets between notes: call a pattern, return, and repeat the last K entries R times. Fast alternation of two notes (18 + 9 units) makes the melody-plus-bass parts. Reading a new note delays the next sample by 130-540 T (a small jitter at note boundaries, measured in MAME).

## The pictures (`gen_scenes.py`, `scenes.h`)
Each scene is a Python function that returns full screens: 80 cells, each a ROM character or a 5 x 8 bitmap with a key. The encoder gives each key one of the four glyphs of its half and keeps it there while its picture changes (so a flash or a moving sprite changes only CGRAM, not the screen), deduplicates the 32-byte glyph halves (82 of them, 2,624 bytes), and writes only the DDRAM cells that changed, as runs. Sprites are drawn on a 100 x 32 dot screen and cut into cells; ships of one formation share the same sub-cell position, so three ships need only two glyphs.

Budget: music 2,361 bytes, event streams 7,247, glyph halves 2,624, marquee text 159, code and tables the rest (15,379 of 16,384).

## Build
```bash
make VGLDK=/path/to/vgldk      # -> readysetgo_gl2000_mirrored_AT28C256_32K.bin (32 KiB: the 16 KiB twice, for MAME's -cart or an AT28C256)
```
Needs `sdcc` 4.5, `makebin`, `python3` and an **unmodified** VGLDK at commit 6fbd389 (see `../../docs/DEVELOPING.md`). It uses VGLDK's gl2000 start-up and LCD routines only (`__KEYBOARD_H`, `__VGL_SOUND_H` and `LCD_MINIMAL` keep the rest out; VGLDK's `vgl_sound_off` is disabled because it writes port 0x12 without masking bit 0) and carries its own power-off routine. The build is reproducible: clean builds give the image in `../../release/` byte for byte (`../../release/SHA256SUMS`). `gen_demo.py` prints the length and size of every segment.

## Tests in MAME (`mame/`)
* `run_test.sh <dir> <seconds> <scenario>` (after `make`; set `MAME` to the binary with the genio2000 driver and `ROMPATH` to your own ROMs, `docs/DEVELOPING.md` section 4) runs MAME headless (no display, no window; `-video none`, SDL dummy drivers, its own cfg/nvram folders) with `rsg_test.lua`, which presses keys, takes snapshots, logs where each segment ends, and watches every write to ports 0x0A/0x0B/0x12.
* `check_run.py` replays the event streams and the marquee of `scenes.h` from their bytes alone, with the engine's frame lengths, renders the LCD it predicts, and compares it dot by dot with each snapshot. The replay counts iterations but not the T-states `fetch_note` spends between notes (0.2-0.8 % in the busy sections), so it searches up to 1 % of the elapsed time back, allows the marquee one step either way, and prints what it used (at most 18 ms and one step). `check_snaps.py` does the same for single snapshots. Both draw the ROM characters from your own reconstructed CGROM: set `GENIO_CGROM` to `genio2000_cgrom_reconstructed.bin` (it is not in this repository).
* Example: `MAME=... ROMPATH=... mame/run_test.sh runA 80 "15:press:ESPACIO;20:snap;30:snap;31:quit" -snapview native && GENIO_CGROM=... python3 mame/check_run.py runA basic,ready,set,prompt,go,launch,warp`. Add `-sound sdl -wavwrite out.wav` (with the SDL dummy audio driver the script sets) to record the audio.

## Status
Verified **in MAME only** (genio2000 driver, 6.13179 MHz, the release image above):
* The whole show runs: 27 of 27 snapshots (BASIC, READY, SET, prompt, GO, launch with and without the marquee, warp, credits, end) equal, dot for dot, the screens predicted from the streams. The marquee runs through all the names and ends blank before the credits.
* LCD writes: the shortest gap is 252 T-states (41.1 us); port 0x12: the samples are 128 T apart except right after a note change; **bit 0 of port 0x12 is never written** until the power-off, and no other unknown bit is written; the only ports written are 0x0A, 0x0B, 0x10 and 0x12; the only `HALT` is the one of the power-off sequence.
* Pitch: the prompt's A5 measures 879.8 Hz and SET's E2 82.6 Hz in a WAV recorded with `-wavwrite`.
* SPACE at the prompt ends it within 16 ms; with no key it launches by itself after 4 loops. A 0.1 s tap of OFF during the warp and a 1.5 s hold give the same result: the segment ends 42 ms after the press, the whole goodbye plays (0.99 s) and `OUT (0x12),1` follows.

**Not tested on a real unit.** Risks, in the order I would look at them:
* **LCD timing.** One write every 41.1-41.7 us and the whole CGRAM rewritten 352 times per second. The tested Kepler demo does the same at 41.7 us, but this demo is 4 T-states tighter on some writes, and the controller is an unproven HD44780 clone. A failure would show as wrong glyphs or misplaced characters.
* **LCD persistence.** MAME shows each frame sharply; the real STN panel smears. The warp texture and the fast strobes (GO!, READY inverted) may look grey or blurred, and the dot of the prompt may leave a trail.
* **Keyboard scan.** It writes one column mask to port 0x10, reads the rows about 128 T later, and returns to 0, as the text editor does but slower; OFF is read like the firmware routine but with a longer settling time. Untested on the unit. A key held when the prompt starts counts at once.
* **OFF press.** 42 ms of debounce instead of the 1.4 s hold of the text editor and the firmware routine: a brush against the key switches the demo off. Contact bounce on the real key was not measured.
* **Dirty RAM.** The unit's RAM is not cleared at power-up; every variable the loop reads is assigned in `run()` or by the engine before use, but this was only checked in MAME, where RAM starts at zero.
* **The other machines.** Pitch, tempo and LCD spacing come from the CPU clock and the 4x20 DDRAM map of the gl4000 family. On a machine with a different clock the music is out of tune and, if the clock is faster, the LCD writes come closer than 41 us. None of the four other machines named on screen has been emulated or tested.
* The LED's three brightness levels are PWM at 24 kHz; MAME shows it only on or off.

Licence: GPL-3.0-or-later (it is built against VGLDK).
