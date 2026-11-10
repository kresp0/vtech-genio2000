# DISASSEMBLY

## How it is generated (reproducible)
1. `tools/analysis/z80dis.py`: own Z80 decoder (DD/FD/ED/CB prefixes, undocumented forms). Checked against MAME `unidasm` with `check_dis.py`: 87,995 instructions compared, 100 % agreement in length, 10 text differences only in undocumented forms (`NEG *`, `RETN`/`RETI` aliases, `SET n,(IY+d),r`).
2. `exec_trace.lua` + `dyn_batch.py`: runs in MAME (driver `genio2000`, private ROM, **EMU**) that record every executed instruction with the bank context (`:bank0/1/2` entries) and every I/O access.
3. `trace.py` + `build_db.py`: recursive descent over *images* (bank, window) seeded with vectors, the API table, stubs and every PC seen in MAME; cross-window references are only followed when MAME supplies the context (otherwise they are noted as `unresolved_far`: 48).
4. `gen_listing.py` produces one listing per bank (`*` = executed in MAME; `.db` rows = not decoded; labels `fn_XXXX`/`l_XXXX`; names from `names.json`).

## Coverage (bytes decoded as code / 16,384)
| Bank | % | Remark |
|---|---|---|
| 0 | 80.6 | the rest: tables (keyboard 03AD-05xx, DDRAM 07EE, messages) and code not reached |
| 5 | 85.4 | |
| 6 | 57.8 | window 8000 (editor/calculator) + 4000 (trampoline) |
| 7 | 63.2 | BASIC; the remaining 36.8 % includes tables (about 2 KiB), messages and code not reached (functions, file I/O) |
| 1-4 | 0 | data (to be confirmed; 1 and 4 with a cartridge header) |
Total about 36 % of the 128 KiB ROM (47,021 of 131,072 bytes) as code; the other areas are **not classified** as data. Decoding overlaps (contiguous instructions misaligned by data after a `CALL`) are resolved in the listing by giving priority to what MAME executed, but the instruction table keeps them.

## Limits
* Indirect jumps are not followed (`JP (HL)`: 9 detected, dispatch tables: BASIC 7:5822; the rest unresolved).
* The bank context of far calls is only exact where MAME went through them.
* The listings are not "the original source code": the names are proposals.
