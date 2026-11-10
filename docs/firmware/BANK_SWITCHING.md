# BANK_SWITCHING

## Registers and shadows (CONFIRMED)
| Window | Port | RAM shadow | Values seen in the code |
|---|---|---|---|
| 0000-3FFF | (0x00, unused) | - | always bank 0 |
| 4000-7FFF | 0x01 | `DFF1` | immediates 0, 5, 6, 7; `DFF4` (0 by default; 7 when the BASIC hook is installed) |
| 8000-BFFF | 0x03 | `DFF3` | immediates 0, 1, 4, 6, 0x80, 0x81; computed (`ADD A,B`, `INC A`) |

Reset: `0FB5-0FC6` writes 0 to ports 1-5 and to `DFF1/2/3`. Note: on the real unit the firmware starts with 0x4000 = bank 0 (identical to window 0, HW).

## Switching patterns
1. **Far jump to window 1** (for example 0x1161): `LD A,7; LD (DFF1),A; OUT (01),A; JP 4000` (bank 7 = BASIC); `LD A,5; ... JP 4000` (activities, 1184).
2. **Window 2 to an internal bank**: `LD A,6; OUT (03),A; LD (DFF3),A; JP 9600` (1166) / `JP 8000` (1175): editor/calculator in bank 6.
3. **ISR** (0x0119): saves `DFF1`, forces `DFF4` in window 1 (`0191`: `LD A,(DFF4); OUT (01),A`), calls `(DFF5)`, restores. The hook code must live in bank `DFF4`, in RAM or in bank 0.
4. **Paged data reading** (0x08E8-0x0935, cartridge `11` engine, not executed in EMU; and `0x0F1F` far_read_byte, which is executed): a pointer from `0x8000` walks data ROM; on reaching 0xC000 it does `DFF3+1` -> next page and returns to 0x8000. With `DB2A`=0 the base is internal entry 1 (+`D80A`); with `DB2A`=1 the base is the cartridge (`0x80`+).
5. **RST 10h-28h** (bank 0) always jump to 0x4010-0x4028: they only work if window 1 holds bank 7 (stubs at B7:4010...).

## What is not known
* Effect of bits 5-7 of the port 1 selector and of bits 4-6 of port 3 (never written).
* Physical capacity of the chip and real decoding (MAME uses `&0x1F`).

## Port 03 measured on HW (2026-11-10)
Internal entries: `sel & 7` for `00..1F` and also `20`, `40` (HW, CRCs identical to banks 0-7). Cartridge (`80..8F`, `90`, `A0`, `C0`): with a 32 KiB EEPROM only bit 1 changes the content (A14 of that board). Details and caveats in HW_RESULTS_20261110.
