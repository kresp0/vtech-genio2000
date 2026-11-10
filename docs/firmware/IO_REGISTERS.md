# IO_REGISTERS: I/O ports seen by the firmware

Source: all `IN/OUT (n)` instructions in the decoded code (**there are no** `IN/OUT (C)`, `INI/OUTI/OTIR...` in the decoded code) + inventory of accesses in MAME (EMU) + earlier HW measurements. Columns: *Dir* R/W from the CPU.

| Port | Dir | Proposed name | Bits / values | Effect | Values seen | Evidence |
|---|---|---|---|---|---|---|
| 0x00 | - | `P_BANK0` | - | **Never written or read by decoded code**; bank 0 is fixed | - | CONFIRMED (static, on reached code). The `IN A,(00)`/`OUT (00),A` in bank 7 pointed out by an earlier static-analysis report do not appear in the decoded code: probably data (HYPOTHESIS) |
| 0x01 | W | `P_BANK1` | bits 0-4 effective (HW: selector & 7 up to 0x1F) | Selects the bank of window 4000-7FFF | 00, 05, 06, 07 (EMU); 0-0x1F (HW, dumper) | HW + CONFIRMED |
| 0x02 | W | `P_02` | - | Only 0 is written, at reset (0FB8, 11EC). Function unknown | 00 | CONFIRMED / UNKNOWN |
| 0x03 | W | `P_BANK2` | bit 7=1 -> cartridge, page = bits 0-3 (MAME: `&0x8F`); bit 7=0 -> internal entry (`&0x1F`) | Selects window 8000-BFFF. Shadow `DFF3`. **HW (2026-11-10):** internal: `sel & 7` (bits 3-6 ignored; 20 and 40 -> bank 0); cartridge (32 KiB EEPROM): only bit 1 changes the content on that board | 00, 01, 03, 04, 06, 80 (EMU); 80/81 (static); 00-1F, 20, 40, 80-8F, 90, A0, C0 (HW) | CONFIRMED (use) + HW |
| 0x04, 0x05 | W | `P_04`,`P_05` | - | Only 0 is written, at reset | 00 | CONFIRMED / UNKNOWN |
| 0x06 | W | `P_06` | - | `0x40` once at reset (0FE7, 1208). Function unknown | 40 | CONFIRMED / UNKNOWN |
| 0x0A | W | `P_LCD_CMD` | HD44780: instruction | init `38,38,38,38`, `01` clear, `02` home, `06` entry, `0C/0E/0F` display, `40+n` CGRAM addr, `80+n` DDRAM addr | see LCD_INTERNALS | CONFIRMED (code) / EMU |
| 0x0B | W | `P_LCD_DATA` | data | characters and CGRAM | - | same |
| 0x10 | W | `P_KEY_COL` | 1 active bit = column (0x80->0x01) | Keyboard column select (also printer data, according to earlier documents) | 00, 01...80 | CONFIRMED |
| 0x10 | R | `P_KEY_ROW_A` | rows 0-7 (active low in MAME) | Keyboard | FF idle | CONFIRMED |
| 0x11 | W | `P_11` | - | `0xFF` at reset (0FAF) and before scanning (01B0) | FF | CONFIRMED |
| 0x11 | R | `P_KEY_ROW_B` | rows 8-12 (activity panel) | Keyboard, matrix 2 | 1F idle | CONFIRMED |
| 0x12 | R/W | `P_SYS` | bit 0 = power-off request; bit 5 = CAPS LOCK LED (01F2-020C); bits 2, 3 used by printer/sound (earlier documents) | Read-modify-write | reset `DE`; `01` off | CONFIRMED (writes); function of bits 2/3/5 see earlier documents (partial HW) |
| 0x13-0xFF | - | - | - | No accesses in decoded code | - | CONFIRMED |

**HW (2026-11-10, `HW_RESULTS_20261110`)**: `0x11` at rest = `5F`, `0x12` = `16`, `0x10` = `FF`; `0x11`/`0x12` repeat at `+0x20*k` (A5-A7 not decoded); no device = last byte on the bus. Port 03: bits 3-6 ignored for internal entries (`sel & 7`).

Remarks:
* The registers in the table already match `docs/hardware/IO_PORTS.md`; **differences**: (1) that table gives 0x00 as "never written" and it is further confirmed here that there are no decoded reads; (2) the value `P_BANK2` = 0x03 is used both as internal entry 3 (EMU, 1,212 writes) and as 4 (EMU, 8,607).
* The first access to the cartridge ROM is made with `OUT (03),80`; with no cartridge the read returns whatever MAME provides (UNKNOWN on real hardware).
