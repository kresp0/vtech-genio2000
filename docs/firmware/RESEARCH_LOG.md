# RESEARCH_LOG (chronological; reproducible commands)

Working date: 2026-11-10. Environment: Python 3.13, SDCC 4.5 (sdasz80/sdldz80/makebin), MAME `unidasm` 0.276, MAME with the `genio2000` driver.

| # | Action | Result |
|---|---|---|
| 1 | Project inventory (dumper README, documents, project notes) | verified dump of 8 banks; MAME `genio2000` with a private ROM; earlier static report |
| 2 | Read-only copy of the ROM; `cmp` with `bank_0..7.bin` and with the MAME set file `27-5575-00` | identical; SHA-256 `f66f4d51...` |
| 3 | `romid.py` | entropy per bank, `55 AA` headers in banks 1 and 4 |
| 4 | `z80dis.py` + `check_dis.py` | 87,995 instructions compared with `unidasm`: 10 differences (undocumented forms) |
| 5 | `trace.py`: bank 0 from vectors and the API table | 67.4 % of B0 bytes reached with vectors+API only |
| 6 | `exec_trace.lua` (+ fix: use `CURPC` for the start of the instruction; the first attempt counted every operand byte) | traces per bank context |
| 7 | `dyn_batch.py`: 43+ scenarios (idle, BASIC, CALCULATOR, PRINT TEXT, CARTRIDGES, OFF, 37 activity keys) | dynamic coverage |
| 8 | `build_db.py`, `gen_listing.py` | instruction, function and cross-reference tables, per-bank listings |
| 9 | Manual study: start-up (B0:0FAA), ISR (0119), keyboard (01A8), LCD (05CF-07F0), cartridges (1012, 118E), API (003B) | see the documents |
| 10 | BASIC keyword table (`basic_tokens.py`), statement dispatch (`basic_dispatch.py`), RAM dump (`ram_dump.lua`) | 123 entries, 68 names, 55 blanked; stubs -> SYNTAX ERROR |
| 11 | BASIC sessions in MAME with `kb.py` | PRINT/FOR/LET/IF/GOTO/STOP/LIST observed; first key lost (EMU) |
| 12 | Example cartridge `hello_api.s` in MAME (`run_cart.sh`) | **fails** without `CALL 05CF` (LCD not initialised), **works** with it |
| 13 | `test_findings.py` | 8 tests pass |

Method errors corrected during the work (so they are not repeated): (a) `unidasm -skip 0` prints the help; (b) MAME's read tap fires on every operand byte, not only on the opcode; (c) `.area _CODE (ABS)` is not accepted with `.org` in sdasz80 (use `_HEADER (ABS)`); (d) the first key press in BASIC is lost, a key has to be pressed to "warm up".

| # | Action | Result |
|---|---|---|
| 14 | T-D1a: `exec_trace.lua` with `GENIO_PCS` records registers at given points; `0F1F` read by `0E5A` (bit field) and `0EB4`; high-level entry `0C13(A,D,E)`; Z80 harness with the real ROM | extractor `extract_data_banks.py`: bank 4 = 2,601 word entries, bank 1 = 1,066 questions; banks 2/3/6 are not this format |
| 15 | hwtest: HW test cartridge (ports, clock, IRQ, LCD/LED, keyboard, charset, port 03) + receiver `hwtest_rx.py` + simulation with a model | `tools/hwtest/`; 7 tests pass in the Z80 interpreter |
| 16 | external additional report (audit of the ZIP): its bank 4/1 figures, repeated tails and bank selectors were checked against the tables/ROM/`.io` traces; local `z80core.py` incorporated; `hwtest` + stage K (`/WR` probe) | 3 new tests in `test_findings.py`; its description of `hwtest` ("limited to extraction") does not correspond to this work |
| 17 | second Genio 2000 dumped (2 verified sessions): per-bank diff, extraction of bank 1, disassembly of the only different byte of bank 7; clue of a RAM cartridge for LOAD/SAVE | `ROM_REVISIONS.md` |
| 18 | hwtest run on HW (2 batches, 2026-11-10): clock, IRQ 46.76 Hz, port 03, RAM mirror, `HALT` switches off, LCD/LED, ON restarts; review of all the documents | `HW_RESULTS_20261110.md` |
