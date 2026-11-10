# MEMORY_MAP_DETAILED

## CPU space
| Range | Device | Control | Evidence |
|---|---|---|---|
| 0000-3FFF | ROM bank 0 | fixed: no code writes port 0x00 (all decoded `OUT`: 0x01-0x06, 0x0A, 0x0B, 0x10-0x12) | CONFIRMED (static) |
| 4000-7FFF | ROM, bank = `OUT (01h)`; RAM shadow `DFF1` | selectors 0-0x1F -> bank `n & 7` | HW (selectors), CONFIRMED (use) |
| 8000-BFFF | internal ROM (`OUT (03h)` = 1,3,4,6...) or cartridge (`OUT (03h)` = 0x80+); shadow `DFF3` | see BANK_SWITCHING | CONFIRMED/EMU |
| C000-DFFF | RAM 8 KiB (GM76C88AL-15, photograph of the board) | initial stack `SP=DFF0`. **HW (hwtest, 2026-11-10): not zeroed at start-up**: 72 % of the 4-byte words are `70 C1 07 1C` (start-up only initialises specific variables; origin of the pattern: UNKNOWN, may be leftover from earlier starts) | HW (photograph, content) + CONFIRMED |
| E000-FFFF | **Mirror of RAM C000-DFFF** (A13 not decoded): 61 of 64 blocks of 128 B identical to their pair; the other 3 changed during the copy. Only read was tested; not used by the firmware | HW (read) |

## RAM: identified variables (only those backed by code; proposed names)
| Address | Proposal | Function | Evidence |
|---|---|---|---|
| C000/C002/C004 | `bas_ptrs` | BASIC program pointers (start, top; `C006` = first byte of the program) | PROBABLE (7:6EED-6F14, 6BE5-6BF1) |
| D000-D035 | `bas_rst_hooks` | Table of `JP` to RST 08/10/18/20/28 handlers (zero in the menu; BASIC fills it) | CONFIRMED (RST code) + EMU (RAM dump) |
| D152-D1A0 | `bas_stubs` | `JP 412D` xN: handlers of blanked statements -> `LD E,2; JP 59A2` = SYNTAX ERROR | CONFIRMED + EMU |
| D800-DAFF | `txt_scratch` | Buffer for decompression/reading text from data ROM | PROBABLE |
| DB00 | `key_state` | Key buffer state: `0xC0` = no key (rest, EMU: value in the menu), `0xD0` = a decoded key is waiting to be consumed (start-up routine 10E4 and the key waits do `LD A,(DB00); CP D0`), other values (for example `0xB0` in BASIC, EMU). Writers: 02E6, 035F, 0370, 10E1, 1219... `01A8` does not rescan while it is `0xD0`. | CONFIRMED (code) / PROBABLE (fine semantics) |
| DB02/DB03 | `key_a/key_b` | Set to 0x19 and 0xFF when the scan starts ("no key") | PROBABLE |
| DB04/DB05/DB06 | key state / LED | `DB05` toggles bit 5 of port 0x12 (CAPS LOCK LED) | PROBABLE |
| DB07-DB16 | `kbd_matrix` | 8 columns x 2 bytes: (port 0x11, port 0x10) | CONFIRMED |
| DB17/DB18 | `kbd_col/kbd_row_idx` | detected column / row index while decoding | PROBABLE |
| DB21/DB22/DB23 | activity variables | `DB23` selects the activity in the bank 5 dispatcher (`4000`) | CONFIRMED (code) |
| DB26/DB28 | `idle_ticks` / `irq_ticks` | `DB26` (16 bits): inactivity, >= 0xBA54 -> switch off (set to 0 on every IRQ while `DB00==D0`). **`DB28/29`: free-running interrupt counter**, matches exactly an own counter over 1,100 IRQs (HW, 46.76 Hz -> 0xBA54 about 17 min) | CONFIRMED (code + HW) |
| DB2A | `cart_data_mode` | 1 = data taken from the cartridge (pages 0x80+) | CONFIRMED (08E2-091B) |
| DB44-DB46 | `ram_sig` | `55 AA 18`: valid-RAM mark (warm/cold start) | CONFIRMED (1039-10D4) |
| DCA0-DCEF | `lcd_buf` | 4 rows x 20 chars (stride 0x14) | CONFIRMED |
| DCF0-DCF3 | `lcd_dirty[4]` | row pending refresh | CONFIRMED |
| DCF4/DCF5 | `cur_col/cur_row` | cursor position | CONFIRMED |
| DCF6 | `cur_style` | 1 = blinking (LCD cmd 0x0F), other = underline (0x0E) | CONFIRMED |
| DCF7 | `cur_visible` | 0 = cursor hidden (cmd 0x0C) | CONFIRMED |
| DD01-DD05 | various | DD03 = 1 before beeps | UNKNOWN |
| DFF1 | `shadow_p1` | copy of the last value written to port 0x01 | CONFIRMED |
| DFF2 | `shadow_p2` | start-up sets it to 0 | PROBABLE |
| DFF3 | `shadow_p3` | copy of port 0x03 | CONFIRMED |
| DFF4 | `isr_bank` | bank the ISR puts in window 1 before calling `(DFF5)`; 0 at rest (EMU), 7 if BASIC installs its hook (7:6F2D-6F35). **HW when a cartridge is entered: `14`** (-> bank 4) | CONFIRMED (code) + EMU + HW |
| DFF5/DFF6 | `isr_hook` | pointer to the secondary ISR handler (default `0033`=`RET`, **HW confirmed when a cartridge is entered**; routine 7:6F15 sets `7036`). It can be replaced by an own hook in RAM that counts IRQs (used by `hwtest` stage D) | CONFIRMED (0FF5, 6F32) + HW |

HW state when a YE cartridge is entered (the RAM dump file is not published): `DB00=C0 DB01=B4 DB26/27=0000 DFF0..7 = 14 00 00 80 14 33 00 00`, `DCA0` = title screen text (leftover: see BOOT_SEQUENCE).

Notes: the complete "variable table" of BASIC (D0A4, D0E1, D3C2...) is not catalogued; it is pending (UNRESOLVED_QUESTIONS).
