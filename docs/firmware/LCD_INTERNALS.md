# LCD_INTERNALS

## Hardware as seen from the firmware (CONFIRMED in code)
* **HD44780**-type controller (port 0x0A = instruction, 0x0B = data). Initialisation (`B0:05CF-0607`): four times `0x38` (function set, 8 bit, 2 lines... according to the HD44780) with delay `068F` between them; then clear (`01`), home (`02`), `0C` (display on, no cursor), `06` (entry mode). It then loads 2 CGRAM characters (`07CA`, `07D2`) and 2 more (`078F`: data at 07DA/07E4).
* **Logical screen 4 x 20**. The firmware keeps a **shadow buffer** `DCA0-DCEF` (4 rows x 20, stride 0x14) and flags `DCF0-DCF3`. The ISR (`057E`) writes out the dirty rows: for each one it writes the DDRAM address `07EE+row*20` and 20 characters, passing each through `07A8` (translation).
* **DDRAM table** `B0:07EE` (80 bytes, CONFIRMED):
```
row0 80 81 82 83 88 89 8A 8B 8C 8D 8E 8F 98 99 9A 9B 9C 9D 9E 9F
row1 A8 C1 C2 C3 C8 C9 CA CB CC CD CE CF D8 D9 DA DB DC DD DE DF
row2 84 85 86 87 90 91 92 93 94 95 96 97 A0 A1 A2 A3 A4 A5 A6 A7
row3 C4 C5 C6 C7 D0 D1 D2 D3 D4 D5 D6 D7 E0 E1 E2 E3 E4 E5 E6 E7
```
  80 distinct addresses (test). **Observed anomaly**: the first character of row 1 is at `A8`, not at `C0`/`C8` (the pattern would be `C0`); it has not been explained (a design error absorbed by the hardware? the map of a 4-controller LCD module?). PROBABLE that it matches the "GL4" map tested on the real unit with the diagnostic ROMs; **not measured again here**.
* **Character translation** (`B0:07A8`, CONFIRMED): AD->A9 (¡), A8->9F (¿), A4->9B (ñ), A5->9C (Ñ), A7->9E (º); everything else passes unchanged. That is, the internal text uses CP437/850-style codes for those 5 symbols and the LCD's CGROM has them at other positions (the CGROM is **reconstructed from photographs**, not extracted; BAD_DUMP in MAME).
* Cursor: `DCF4`=column, `DCF5`=row (`006E` sets, `006B` reads); `DCF7`=0 hides the cursor (command `0C`), 1 shows it with a style according to `DCF6` (`0F` blinking / `0E` underline). `0062`/`0065` = cursor on/off. The position is sent to DDRAM at `062D` (address = `07EE[row*20+col]`).
* CGRAM: `0728` (A = character 0-7 -> address `0x40+8*A`, `HL` -> 8 bytes; interrupts with `DI`/`EI`). Fixed characters 0 and 1: `00 00 00 00 00 00 00 1F` (underline) and `1F x7,00` (block), (HYPOTHESIS: used as cursor/fill symbols; which routine uses them has not been verified).
* Delays: `0689` (about 0x120 iterations) after each write, `068F` (about 0x3F0) after long commands; no busy-flag reading (there is no `IN` of port 0x0A in the decoded code): CONFIRMED.

## Control codes (print routine `3572`, API `0x0077`)
Detailed analysis pending (`351D` decides whether the character is printable; carry = ignore). See FIRMWARE_API.

## Relation to the real hardware
* 4x20/GL4 map and visual behaviour: tested on the unit by earlier sessions (see `docs/hardware/HARDWARE.md`); not repeated here.

## HW (2026-11-10, `hwtest` stage E; human observation)
* The CGRAM is read **live**: rewriting it changes all the cells that use that code at once, so there are at most **8 distinct custom glyphs** at the same time. Codes `08-0F` show the same as `00-07`. Answers S/S/S/S/S (yes) in two runs.
* The CAPS LOCK LED is bit 5 of port `0x12` (it blinked 3 times when toggled; 2 runs).
* The photographs of the 4 screens of the character set (stage G) are pending.
