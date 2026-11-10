# CONTINUITY: exact state for resuming (2026-11-10)

## What is done (summary)
Phases 1, 2 (partial), 3 (partial), 5 (partial), 6 (cartridge interface complete in code; HW experiments missing), 8 (Lua infrastructure + 50 scenarios), 9 (API catalogued, 1 example verified in EMU), 11 (documents). Phase 4 (BASIC): keyword tables and statement dispatch solved; functions, data formats and file I/O are **missing**. Phase 7: string extractor done; extractor of banks 1 and 4 done (T-D1a); the formats of banks 2, 3 and 6 are **missing**.
Coverage: 36 % of the ROM as code (47,021 B); banks 1 and 4 with a solved format (group semantics pending); 2, 3 and 6 (data) not interpreted. It is not declared complete.

## First hwtest run on HW (2026-11-10)
See `HW_RESULTS_20261110.md`. Done: A, B, C, E, G (photographs still to arrive), H, I, J, K, L. Missing: **F** (matrix; ON is already known: it restarts), D v2 done: 46.76 Hz, `HALT` switches the unit off (HW_RESULTS_20261110, batch 2), the G photographs, the GA variant, a run on unit 2. Answer 6 (LED) was actually `S` (yes).

## Second unit (2026-11-10)
A second Genio was dumped and verified (2 sessions): banks 0/4/5/6 identical; 1, 2, 3 and 7 differ (ROM_REVISIONS). The tools accept `GENIO_ROM=<image>` and `GENIO_TAG=<suffix>`.

## Additional report (2026-11-10)
Contributed and verified here: classification of the bank 4 groups, distribution of bank 1 fields, repeated tails between banks, bank 1/2 never selected in the traces, `z80core.py` now local (the extractors no longer depend on the dumper) and the `/WR` probe in `hwtest`. `test_findings.py` = 14 tests.

## Hardware tests
`tools/hwtest/` (own README): the YE autostart cartridge (+ a GA variant for the menu) and the receiver `hwtest_rx.py`, which writes a `REPORT.md` per run. Validated in the Z80 interpreter with a hardware model (`tools/hwtest/tests/test_hwtest.py`, stages A-L; D v2 without HALT). When a REPORT.md arrives: update IO_REGISTERS (port reads), BANK_SWITCHING (port 03 on HW), INTERRUPTS (IRQ frequency), KEYBOARD_INTERNALS (ON/matrix), LCD_INTERNALS (CGRAM/charset), MAME_VALIDATION and CARTRIDGE_INTERFACE (cartridge address lines, GA variant).

## Next concrete steps (in order)
1. **T-D1 DONE (session 3)**: see DATA_FORMATS; pending: classify the 14 groups of bank 4 and the groups of bank 1 by activity (compare with keys in MAME), and locate what data banks 2, 3 and 6 use (other formats).
2. **T-B1** BASIC function table: run `PRINT SGN(1)`, `INT`, `ABS`, `SQR`, ... with `kb.py` and `exec_trace.lua`; compare with `B7:5608/58A5`.
3. **T-B2** Program/variable format: dump RAM (`ram_dump.lua`) after known programs and read `C000-C006`, `D0A4...`.
4. **T-B3** I/O of `LOAD/SAVE/DIR/FORMAT`: follow `7:79BA`, `7:7B28`, `7:7D3D`.
5. **T-L1** Control codes of `lcd_putc` (`B0:3572`, `351D`, `3528`, `34E8`), scrolling and the 2nd string convention.
6. **T-K1** Keyboard: debounce, repeat, multiple keys (`B0:0211-03AC`); DB04-DB06.
7. **T-A1** More API examples (key reading: identify `004D`/`004A`; sound `0098`) and an example returning to the menu (`JP 0030`).
8. **T-C1** Test in MAME the `47 41` and `11` signatures from CARTUCHOS ADICIONALES (wait for the welcome to finish or press after 45 emulated seconds).
9. **T-M** Extend the MAME scenarios (all activities with answers, calculator, editor/printing) and run `build_db.py` + `gen_listing.py` again until coverage stops growing; review `unresolved_far`.
10. Prepare experiments E1-E8 (UNRESOLVED_QUESTIONS) as test ROMs with the flow already used in the project (AT28C256).

## Key commands (from `tools/analysis/`, with `GENIO_ROM` set)
```bash
./check_all.sh                                   # quick checks
python3 -I dyn_batch.py "name=SCENARIO@STOP"     # scenario .lua (see kb.py for typing)
python3 -I build_db.py && python3 -I gen_listing.py
python3 -I dis.py <bank> <addr_hex> <len> [window_hex]   # quick linear disassembly
./run_cart.sh ../example-cartridge/hello_api_16k.bin 8   # test cartridge in MAME (EMU)
```
## Known traps
* Pressing keys before the welcome typing ends (over 40 emulated seconds in some runs) has no effect.
* The first key in BASIC is lost; type a warm-up key.
* `unidasm` does not accept `-skip 0`.
* The bank context of `*.exec` is that of MAME's `:bank0/1/2` (entry n = bank n&7; 0x80 = cartridge).
