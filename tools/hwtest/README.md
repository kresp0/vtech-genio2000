# hwtest: test cartridge for the real Genio 2000

A single cartridge (AT28C256 EEPROM) that runs several tests on the unit and sends the results over the same cable as the [dumper](https://github.com/kresp0/vtech-genio2000-rom-dumper) (printer port -> CP2102, 9600 8N1, Genio -> PC only). A receiver on the PC (`tools/hwtest_rx.py`) receives them and writes `results/<date>/REPORT.md`. **MAME was not used**; the program and the receiver were validated in a Z80 interpreter with a model of the unit (`tests/`), which proves **nothing** about the real unit.

## What to burn
Build the images with `./build.sh all` (SDCC); it needs a clone of the [dumper repository](https://github.com/kresp0/vtech-genio2000-rom-dumper) in `tools/dumper/` (or `GENIO_DUMPER_DIR`) for `gframe.py`, `z80core.py` and the VGLDK headers. The ready-made images are in `../../release/`.
| File (`../../release/`) | Header | When |
|---|---|---|
| `hwtest_YE_autostart_AT28C256_32K.bin` | `55 AA 59 45` | main: starts at power-on |
| `hwtest_GA_menu_AT28C256_32K.bin` | `55 AA 47 41` | test E3: launched from the CARTUCHOS ADICIONALES menu (also checks how the unit gets to that point: interrupts, RAM) |

Same format as the validated dumper: 4 copies of 8 KiB; they are identical **except for 32 bytes at `0x1BE0`** of each quarter (mark `4D 51 q ~q ...`), which tell which cartridge address lines reach the EEPROM.

## How to run it
```bash
cd tools/hwtest
python3 -I tools/hwtest_rx.py --port /dev/ttyUSB0
```
Wiring as always (DB25 pin 2 -> RXD of the CP2102, common GND, TXD unconnected). Power on the Genio with the cartridge. Each stage is launched with **ENTER**; **S** skips it; you can power off between stages (the report is rewritten after each stage). The important output is `REPORT.md`.

| Stage | What it does | Your part | Duration |
|---|---|---|---|
| A | State on entry (IFF, shadows DFF0-7) and a copy of C000-FFFF; **no writes** | ENTER | about 25 s |
| B | `IN` of ports 00-FF x3 (0A/0B are not read); **no OUT at all** | ENTER | 1 s |
| C | CPU clock: two bursts of 1200 bytes with a known delay (measured by the PC) | ENTER; do not touch the cable | 4 s |
| D | Interrupt rate, **v2 without HALT**: EI + busy wait while the firmware ISR calls a RAM hook (`DFF5`) that counts; marks at 1, 5, 20 and 100 interrupts and then 1000 timed by the PC | ENTER; **do not press keys**. v1 (EI + HALT) switched the unit off (2026-11-10); if v2 also switches it off, the marks say how many interrupts it survived | about 20 s |
| E | LCD/LED questions (5 about CGRAM, 1 about the LED) | S (yes) / N (no) for each | 1 min |
| F | Raw keyboard matrix log | ENTER; press ALT, SHIFT, CAPS, activity panel keys...; ENTER ends (not ON: it restarts the unit, see below) | free |
| G | Pages of the character set 00-FF (4 screens) | **take a photograph** of each; ENTER to move on | 1 min |
| H | Port 03 <- 00..07 (+ 80 as control) and restores | ENTER | about 15 s |
| I | Port 03 <- 80..8F (cartridge pages) | ENTER | about 20 s |
| J | Port 03 <- 08..1F | ENTER | about 30 s |
| K | `/WR` probe of the cartridge: **one** write at `9BF0` of the same byte that is already there, from RAM, and 16 probe reads + a 70 ms wait | ENTER (optional; S to skip) | about 2 s |
| L | Port 03 <- 20, 40, 90, A0, C0 (never tried) | ENTER (**the riskiest: leave it for last**) | about 8 s |

**ON** (checked on HW by the user, 2026-11-10): it is separate from the matrix; pressing it restarts the unit and the cartridge starts again at stage A.

## What each stage answers (questions of `docs/firmware/UNRESOLVED_QUESTIONS.md`)
| Stage | Question |
|---|---|
| A | IFF/RAM state when a cartridge starts (YE vs GA); is there RAM or a mirror at E000-FFFF?; are the DFF1/DFF3 shadows valid? |
| B | **E2**: what does each port return?; are 0x00/0x02/0x04-0x06 readable?; values of 0x10/0x11/0x12 at rest |
| C | **E6**: real CPU frequency (from 642 T per TX bit, already validated at 9600) |
| D | **E6**: frequency of the IM 1 interrupt |
| E | Whether the LCD reads the CGRAM "live" (only 8 distinct glyphs at a time), whether 08-0F mirrors 00-07 and whether the LED is bit 5 of 0x12 |
| F | Position of ON, ALT/SHIFT/CAPS and the activity panel in the matrix; ghosts; Q8/Q9 |
| G | Real character set of **this** LCD (against MAME's reconstructed CGROM) |
| K | **E1 partial**: does `/WR` reach the cartridge connector? If the EEPROM answers "busy" (DQ6/DQ7), yes |
| H-J, L | **Port 03 on HW**: which internal bank appears with each selector (until now EMU only), whether 08-1F repeats 00-07, how many pages the cartridge tells apart (**E4 partial**: the 32 KiB EEPROM only shows A13/A14) |

## What it does NOT prove (and why)
* **Full E1** (RAM at 8000-BFFF) and **full E4** (pages 2-7 with 128 KiB): they need another cartridge. The only write outside the internal RAM is the one of stage K: the same byte that is already at `9BF0` (if `/WR` reached the EEPROM it would rewrite the same value: no change of content), executed from RAM, with a wait > 10 ms. The receiver warns if the byte changed.
* **E5** (autostart without `CALL 05CF`) and **E7** (RX through the printer port): they require wiring or a different cartridge.
* Nothing is written to ports 00, 01, 02, 04, 05, 06 or to bit 0 of 0x12 (switch-off), and 0x0A/0x0B are not read (a badly decoded `IN` could put garbage into the HD44780). Sound is not tested either (bits 2/3 of 0x12 are not assigned with certainty).
* Port 03 receives values never tried on HW (stages H-K); the program runs from RAM meanwhile and restores `0x80` after each copy; if the cartridge stops being visible, it stops with a message.

## How it is built / validated
* `src/hwtest.c` + `src/bank_common.h` (copy of the validated TX/LCD/keyboard/frame code of the dumper repository; bit-by-bit CRC-16 instead of a table for size). `./build.sh all` compiles with SDCC and checks the memory discipline (`tools/mk_image.py`).
* `tests/test_hwtest.py` (9 tests): runs the real image in the Z80 interpreter with different unit models (clock, IRQ, E000 mirror, cartridge address lines) and checks that the receiver recovers the model, that there are no writes outside RAM, no forbidden ports, and no switch-off bit.
* Evidence: **everything that comes out of the unit is HW**; what is said here about the simulation is only verification of the program.
