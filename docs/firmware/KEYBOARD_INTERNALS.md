# KEYBOARD_INTERNALS

> **HW (user, 2026-11-10):** the **ON** key is separate from the matrix and restarts the unit: with the `hwtest` cartridge inserted, pressing it takes it back to stage A (the cartridge starts again). This is consistent with the firmware not reading it and with the `power_on()` comment in MAME.

The key-to-code maps are already documented and checked against the dump in `docs/hardware/KEYBOARD.md` (not duplicated here). This file covers the **mechanism** (CONFIRMED in code, bank 0).

## Scanning (in the ISR; `01A8-02DF`)
1. It leaves without scanning if `DB00 == D0` (previous key not consumed).
2. `OUT (11),FF`; sets the 16 bytes `DB07-DB16` to `FF`.
3. For `C = 80h, 40h ... 01h` (8 columns, `B=8`): `OUT (10),C; IN A,(11) -> (HL++); IN A,(10) -> (HL++); OUT (10),0`. That is **8 columns**, each read through **two ports** (0x11 rows 8-12 = activity panel; 0x10 rows 0-7 = main keyboard). Pairs at `DB07+2*col`.
4. If `DB14` bit 0 (column 7, port 0x11): branch that handles a panel contact (HYPOTHESIS: OFF key; not verified): `020F-0224`; the real switch-off is in the ISR (INTERRUPTS).
5. Decodes the first column with active bits (`AND 1F; CP 1F`): walks the rows with `CALL 0374` and computes the index in tables with stride 13 (`LD E,0D; CALL 1485` = 8x8 multiplication; `+ 03AD`, etc.).
6. Writes the result to `DB00` (=D0 when a key is present), `DB01/DB02/DB03` (codes); `0x19`/`0xFF` = "no key".

## Character tables
Normal `0415`, SHIFT `03AD`, CAPS+SHIFT `047D`, CAPS `04E5`, ALT `054D` (13 bytes per column x 8). The tables are stored in **reverse column order** (already recorded in the project notes). Special codes: `F0/F1` (AVANCE/RETROCESO), `F5` (BORRAR), `FD` (AYUDA), `FF` (BLOQ), `F7` (PAUSA) ...

## CAPS LOCK LED
`DB05` toggles; the code reads port 0x12 and writes `(v|0x20)&0xFB` (01F2-01F8, LED on) or `v&0xDB` (0204-0206, off). Bit 5 = LED (HW: the LED follows the lock, earlier documents); bit 2 is cleared in both cases (CONFIRMED in code; function of bit 2: see earlier documents, printer strobe).

## Simultaneous keys, repeat, debounce
Only **one key** is decoded per scan (first column with bits). Repeat/debounce: variables `DB04`, `DB06` (value `DD` marks "already handled"). **Detailed analysis pending.**

## HW (2026-11-10)
With no key pressed: `IN 0x10 = FF`, `IN 0x11 = 5F` (not `1F`: bit 6 is 1, function unknown; bits 7 and 5 are 0). The raw matrix log (stage F of `hwtest`) is pending.
