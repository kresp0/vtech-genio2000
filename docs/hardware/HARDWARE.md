# Genio 2000 (Spain) – hardware summary

Evidence classes used in every document of this package: **HW** = verified on the physical unit (reproducible session on record) ·
**EMU** = verified only in MAME emulation · **FW** = inferred from the firmware (static analysis or traces) · **HYP** = hypothesis ·
**UNK** = unknown.

| Item | Statement | Class | Source |
|---|---|---|---|
| Model | VTech Genio 2000, Spanish variant; family of the Genius Leader / PreComputer (`gl4000` is the closest MAME machine) | HW | unit, keyboard photo `genio2000_keyboard.jpg` |
| CPU | **Zilog Z84C0006PEC** ("Z80 CPU", date code 9523 = 1995 week 23), 40-pin plastic DIP: a CMOS Z80 whose speed code **06 means a 6 MHz rating** (Zilog part-number convention; a rating is a maximum, not the clock in use). **CLK pin (pin 6) measured at 6.13179 MHz** with an oscilloscope hardware counter (one session; uncertainty and stability not determined); the physical clock source is **UNKNOWN** (no crystal seen); the timing of the real unit (recordings/videos) is consistent (`CLOCK_AND_SOUND.md` §5) | HW (marking, CLK pin reading) / UNK (oscillator) | `logs/hardware/internal_2026-11-09/cpu_Z84C0006PEC_IMG_4476.jpg` |
| Interrupt | IM 1 (`IM 1` at reset, handler `0038 -> 0119`). **Rate 46.76 Hz, measured on the unit** with the `hwtest` cartridge (1000 interrupts in 21.39 s; = 6.13179 MHz / 2^17 within 0.05 %, divider is a hypothesis); the PR series sets it in PR 3, the rest of the `gl4000` family keeps 50 Hz (`set_periodic_int`, "not accurate") | FW / UNK | traces |
| Firmware ROM | The dump is 128 KiB = 8 distinct banks of 16 KiB (the physical capacity of the chip is not confirmed, see next row). The ROM chip is a 28-pin DIP marked **`VTECH LH531H7H / 1995 27-5575-00 / (c) VTECH ELECTRONICS / 9532 D`** (a mask ROM; 27-5575-00 is the VTech part number, date code 1995 week 32) | HW (content) | two independent dumps, SHA-1 `76e41bc3…`, CRC32 `7A9D7B8A` |
| ROM capacity | 128 KiB is the best-supported hypothesis and the chip is a 28-pin DIP (consistent with a 1 Mbit mask ROM), but the capacity of an "LH531H7H" was not looked up in a datasheet: **not proven** | HYP | earlier static-analysis report (not included) §5 |
| Bank register | port 0x01 selects the 0x4000-0x7FFF window; selectors 0x00-0x1F give bank `selector & 7` | HW | sessions 010C, 0113 |
| Other bank registers | 0x00 (window 0x0000) and 0x03 (window 0x8000, bit 7 = cartridge) are **not** written by the dumps and 0x00 is never written by the firmware | FW | static analysis |
| RAM | ~8 KiB at 0xC000-0xDFFF (stack starts at 0xDFF0; firmware shadow variables at 0xDB00 / 0xDFxx). One **GoldStar GM76C88AL-15** (9513) 28-pin SRAM is fitted, which by its part number is an 8K x 8 CMOS SRAM (not checked against a datasheet) | FW + HW (marking) | traces; `logs/hardware/internal_2026-11-09/chips_SRAM_ROM_CPU_IMG_4477.jpg` |
| Other chips | A custom chip-on-board device (die under a clear coating, ~80 pads) next to a metal-bodied part with a green adjustable slug marked "COILS"; one National DM74LS244N octal buffer (9506); discrete transistors, diodes and resistors. **No crystal or ceramic resonator is visible on the component side.** The oscillator may be inside the custom chip with discrete external parts (HYP; the adjustable part is a candidate, not identified) | HW (photos) | `logs/hardware/internal_2026-11-09/` |
| Label / power | underside label: VTECH Video Technology, 32-0682-426, rating DC 6 V 0.6 W, 4 x 1.5 V AA, adaptor DC 9 V 300 mA; no date on the label | HW | `label_underside_IMG_4468.jpg` |
| LCD | 4 x 20 character LCD, HD44780-compatible command set, 5x8 characters; the eighth pixel row is physically separated from the other seven | HW | photos / unit; `logs/hardware/T6_led_lcd/` (READY prompt: the cursor underline is the detached eighth row) |
| LCD DDRAM layout | Same 4x20 interleaving as `gl4000` (`gl4000_pixel_update`) | EMU | OCR of the firmware screens is consistent |
| CGROM | Not a silicon dump. Reconstructed optically from photographs (4096 bytes, 224 glyphs 0x20-0xFF); `BAD_DUMP` | HW (photos) | `CGROM.md` |
| CGRAM | Codes 0x00-0x07, aliases 0x08-0x0F; 0x10-0x1F blank | HW | CGROM viewer sessions (3 sessions, notes not included) |
| Cartridge | Header `55 AA 59 45`, entry at 0x8004; shared with VGLDK cartridges | FW + HW | static analysis + VGLDK programs run on the unit |
| Keyboard | 8 columns x 13 rows (matrix 1, port 0x10: 8 rows; matrix 2, port 0x11: 5 rows = activity panel) | HW/FW | firmware tables + photo, `KEYBOARD.md` |
| Printer | DB25: data on port 0x10, BUSY on 0x11 bit 5, STROBE on 0x12 bit 2 | HW (dump transport) | VGLDK `printer.h`; the dump protocol used it |
| Speaker | Bit 3 of port 0x12, toggled by software (bit-banged). Transducer type UNKNOWN | FW | `0x1364` tone routine, EMU trace |
| LED | Caps-lock LED = bit 5 of port 0x12. **HW: the LED follows the caps-lock state** (photos 3 off / 4 on, owner-confirmed, `logs/hardware/T6_led_lcd/`); that bit 5 drives it is FW-inferred | FW + HW | firmware `0x01F2`; photos |
| ON button | Behaves as a restart (HW, owner): after OFF and the farewell, pressing ON briefly always shows the VTECH title screen, and pressing it while the unit is running restarts it the same way. The work RAM is not zeroed by it: most 4-byte words read `70 C1 07 1C` (HW, `hwtest`; the origin of the pattern is unknown). The emulation clears the RAM instead: filling it with that pattern made the boot write a bank selector of 0x70 from the interrupt routine and corrupted the restart screen (tests failed), so it was not adopted. Wiring (reset line or board power-up) unknown | HW | owner test 2026-11-09; `ARTWORK.md` |
| LCD contrast | Two-position slide switch (left / right), analog LCD bias; **HW** (owner + photos): the right position gives a visibly darker LCD (mean luminance of the LCD area ~14 % lower in a non-calibrated pair of photos). Emulated as a toggling input that scales the LCD colours by 0.86 and makes the unlit dots more visible (PR 8) | HW | `KNOWN_LIMITATIONS.md` |
| Power off | `OUT (12h),01h; HALT` | HW | tested by the project's own programs |
| Oscillator / crystal | **UNKNOWN**: the frequency at the CPU CLK pin is measured (6.13179 MHz), the component that generates it is not identified; see `PHOTOS_TODO.md` §H | UNK | – |

Cheap physical clock facts that can be established tomorrow are in `HARDWARE_TESTS_TODO.md`.
