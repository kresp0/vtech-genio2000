# UNRESOLVED_QUESTIONS (prioritised)

## Software / analysis
| ID | Question | What is missing |
|---|---|---|
| Q1 | Banks 1 and 4: **format solved** (T-D1a) and content classified by topic (DATA_FORMATS). Pending (T-D1b): which activity/key uses each group (in the 51 MAME traces selector 03 never took the values 1 or 2: the bank 1 questions and bank 2 were not exercised). Bank 2 and bank 3: own format, not deciphered; bank 6 = code | Compare with MAME screens per activity (SYNONYMS, ANTONYMS, PLURALS...); locate the readers of banks 2/3/6 with `exec_trace.lua` (`OUT (03)` = 02/03/06) |
| Q2 | Complete map of the BASIC RAM variables (D0xx-D3xx) and of the activity ones (DBxx/DDxx) | access-driven analysis; compare with MAME RAM dumps in different states |
| Q3 | Dispatch table of numeric functions (`B7:5608`/`58A5`) and handlers of `SGN...MID$`, operators | trace the evaluation of each function in MAME (`PRINT SGN(...)`, etc.) to fix the token->address map |
| Q4 | Representation of tokenised lines, variables, strings, arrays; memory and precision limits | RAM dumps with example programs; read `B7:5B49 (NEW)`, `5BF6...`, `6BC6 (DELETE)` |
| Q5 | `LOAD/SAVE/DIR/ERASE/FORMAT/LPRINT`: which device they use. **CLUE (PROBABLE, code reading)**: a cartridge with RAM; `7:79BA` requires the signature `55 AA EE` at `8000` (+`BB 46` at `8006`), writes and reads back `8000-8002`, directory at `8050` (16-byte entries, up to 112) and data at `8800`/`9000` with `OUT (03),80/81`. Still to be confirmed in MAME/HW | analyse 7:79BA, 7B28, 7827... and the I/O accesses they cause (no IN/OUT other than those seen: RAM?) |
| Q6 | Control codes of `lcd_putc` (`3572/351D/3528/34E8`) and scrolling | disassemble and EMU tests with CHR$ |
| Q7 | `0098` (123D, 62 calls): sound?; `004D` (106 calls) and `004A`: key reading? | disassemble and trace |
| Q8 | Keyboard debounce/repeat/combinations (`DB04-DB06`, `02DA...03xx`) | analysis of 0x0211-0x03AC |
| Q9 | Bank 5 dispatcher (`DB23` -> activity) against the 39+ keys; activities without a key? | `CP/JP` table at `5:4000-40xx` and comparison |
| Q10 | Anomaly row 1 col 0 of the DDRAM map (`A8`) | test in MAME with `LCD` and, if possible, on HW (existing test ROM for the LCD) |
| Q11 | String length: two conventions? | cross-check the callers of each print routine |
| Q12 | Regions of code not reached (about 50 % of the "expectable" code in 5/6/7) | more MAME scenarios (all activities with all answers; full calculator; editor; printing) |
| Q13 | First key lost when entering BASIC (EMU) | read the BASIC entry routine at 7:6EDF... and compare with HW |
| Q14 | Identical tails between banks in unit 1 (2=5: 1,095 B; 0=1: 401 B): **absent in unit 2**, so padding of that production run (PROBABLE) | close after decoding banks 2/3 of both units |
| Q15 | Which of the two revisions is the later one? What changes in banks 2 and 3? | chip labels/dates; decode 2 and 3 |

## Hardware (experiments on the real unit)
**Partly executed on 2026-11-10 (HW_RESULTS_20261110): E2 and E6-clock done, E4 partial, E1 partial (no `/WR` signal on the EEPROM); IRQ (E6) measured: 46.76 Hz (batch 2); `HALT` switches the unit off. E3/GA, F (matrix) and the photographs of G pending.** Originally prepared: `tools/hwtest/`, a cartridge + receiver that cover E2, E3 (GA variant), E4 partial, E1 partial (does /WR arrive? stage K), E6 and the LCD/keyboard/port 03 questions below; see `tools/hwtest/README.md`. E1, full E4, E5 and E7 remain outside.

| ID | Experiment | Reason |
|---|---|---|
| E1 | Cartridge with RAM at 8000-BFFF: write and read back | decides whether a cartridge with RAM/own latch is feasible (`/WR`). **Partial**: the stage K probe saw no write cycle on the EEPROM (not conclusive); BASIC seems to use a cartridge with RAM |
| E2 | Read port 0x00 (`IN` only) and 0x02-0x06 (read only) | confirm they are not readable / what is there. **DONE (HW 2026-11-10)**: 00-09 give FF; 0x11/0x12 repeat every 0x20. |
| E3 | Cartridge with signature `47 41` and `11` in the menu | confirm the two modes of CARTUCHOS ADICIONALES. GA image prepared (`hwtest`), **not run** |
| E4 | Pages 2-7 of a cartridge (128 KiB ROM with a mark per page) | confirm 3 page bits and maximum capacity. **Partial**: with 32 KiB only bit 1 moves A14; a larger ROM is missing |
| E5 | Self-starting cartridge without `CALL 05CF` | confirm that the LCD stays uninitialised on HW as in EMU |
| E6 | CPU and IRQ frequency (T7) | **DONE (HW 2026-11-10)**: CPU about 6.10-6.13 MHz, IRQ 46.76 Hz |
| E7 | RX through the printer port (read 0x10/0x11) | **DONE (HW 2026-11-13)**: BUSY (0x11 bit 5, inverted) receives a soft UART from a USB-serial adapter at 2400-76800 baud reliably and 115200-128000 with a recording receiver (`examples/pc-link`, `docs/hardware/PRINTER_PORT.md`). Open: the electrical side of BUSY and the other status lines |
| E8 | Press key combinations at start-up ("service mode" style) after the Q8/Q9 analysis | hidden functions |
