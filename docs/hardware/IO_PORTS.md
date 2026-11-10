# I/O ports (Z80 port space, 8-bit decoding in MAME)

Evidence column: HW / EMU / FW / HYP / UNK as defined in `HARDWARE.md`. "Observed in emulation" = `tools/io_survey.py` (16 scenarios x 36 s, boot, 14
activities, BASIC, OFF) and `tests/lua/io_inventory.lua`; the numbers are specific to those scenarios.

| Port | Dir | Function | Class | Evidence |
|---|---|---|---|---|
| 0x00 | W | ROM window 0x0000. **Never written** in any scenario or by static analysis; banks 7 contains `IN A,(00)` / `OUT (00),A` stubs with no known caller | FW (unused) / UNK (really bidirectional?) | earlier static-analysis report (not included) §4.2; EMU survey: no access |
| 0x01 | W | ROM window 0x4000. boot `0`; activities `5`, BASIC/editor `7` | **HW** (selectors 0x00-0x1F), EMU | sessions 010C/0113; survey: values 00, 05, 07 |
| 0x02 | W | reset value 0 only | FW | `XOR A; OUT 01..05` at 0x0FB5 / 0x11E9; function UNK |
| 0x03 | W | window 0x8000: 0x80 = cartridge probe, 00/03/04/06 internal entries, 80/81 cartridge pages | FW + EMU | survey values 00 03 04 06 80 |
| 0x04, 0x05 | W | reset value 0 only; function UNK | FW | as 0x02 |
| 0x06 | W | `0x40` written once at reset (PC 0x0FE9, bank 0). No read in any emulated scenario (the static analysis lists `IN`s: unreached in EMU). **Function UNKNOWN**; not modelled (MAME reports unmapped writes) | FW + EMU / UNK | survey |
| 0x0A | R/W | HD44780 instruction register | EMU (works), HYP (same chip family as gl4000) | boots, text & CGRAM exact |
| 0x0B | R/W | HD44780 data register | idem | LCD data log: the welcome string sends `A9` before `Hola!` |
| 0x10 | W | keyboard column select (bit n = column n), also printer data D0-D7 | HW (keyboard), FW | `KEYBOARD.md` |
| 0x10 | R | keyboard rows, matrix 1 (active low in MAME) | HW (positions), EMU | |
| 0x11 | R | keyboard rows, matrix 2 (activity panel); printer BUSY (bit 5) | FW | VGLDK `printer.h`; the firmware polls it |
| 0x11 | W | MAME maps this to the **same** latch as 0x10. The firmware writes 0x11 once at boot (`OUT 11,FF` per VGLDK/BIOS4000 01a6). Real function (latch / printer) UNK | UNK | |
| 0x12 | R/W | bit 0 = power-off request, bit 2 = printer STROBE, bit 3 = speaker, bit 5 = caps LED (the LED follows caps-lock on the real unit: HW photos; bit 5 as its driver is FW); the firmware reads it back (read-modify-write) | FW (all), HW (power-off, strobe via dump protocol) | `genio_text_editor/docs/LED_Y_APAGADO.md`; reset value `0xDE` (PC 0x0FB5) |
| 0x13-0xFF | – | no access seen | | |

No hardware function in this table was added to fill gaps: ports 0x02, 0x04, 0x05, 0x06 are deliberately left unmapped.
Open questions are listed in `KNOWN_LIMITATIONS.md`.
