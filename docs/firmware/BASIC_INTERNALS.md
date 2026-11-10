# BASIC_INTERNALS

Bank 7, window 0x4000 (plus auxiliary code in bank 6 @8000: editor/input). Entry from the menu: `1161: LD A,7; LD (DFF1),A; OUT (01),A; JP 4000` -> `4000: DI; JP 6EB8` (BASIC start) (CONFIRMED, EMU).

## Lineage of the interpreter (reasoned HYPOTHESIS)
Typical structure of an 8 KiB Microsoft BASIC / BASIC-80 ported to the Z80: keyword table with bit 7 on the 1st letter, 32-bit numbers with excess-128 exponent (pi/2 = `DB 0F 49 81` at `B7:558C`), 2-letter error codes (`B7:58CA`), "READY", RSTs 08/10/18 as `SYNCHR`/`CHRGET`/`COMPAR`-like through RAM hooks (`D000...`). There is **no** third-party copyright signature in the ROM, so the attribution is only structural.

## Confirmed facts
| Topic | Fact | Evidence |
|---|---|---|
| Keywords | 123 entries (tokens 0x80-0xFA), 68 with a name, 55 blanked | `tools/analysis/basic_tokens.py`, `tools/analysis-tests/test_findings.py` |
| Statement dispatch | `B7:5D60-5D75`: `SUB $80; JP C,5F21 (LET); CP $3C; JP NC,6AE7; RLCA; LD HL,$5822; ADD HL,BC; ...; PUSH BC` -> handler = word number (token-0x80) of `B7:5822` | code + EMU (FOR, PRINT, LET, GOTO, RUN, IF, DIM, READ, DATA, RESTORE, STOP, REM, CLS, LIST, END executed) |
| Removed statements | The handlers of the blanked tokens point to `D1xx` (RAM) which holds `JP 412D`; `412D: LD E,2; JP 59A2` = error 2 (`SN`, "SYNTAX ERROR") | EMU (RAM dump) + code |
| Error | `B7:59A2...`: prints `?` + text from the table `B7:3651` (1st letter bit 7): "`?SYNTAX ERROR`" seen on screen | EMU |
| Messages | `READY` (B7:592A), `BREAK` (B7:5932; "BREAK IN 70" seen), ` IN ` (B7:5925) | EMU |
| Numbers | Output with a leading space for positives (` 12` seen on screen) | EMU |
| Program | Program text from `C006`; CPU stack `SP=DF00` in BASIC (6EC0) | CONFIRMED (code) |
| Input | Keys are shown in lower case while typing and the line is listed in UPPER CASE/tokenised ("15 IF A=5 THEN 20" after typing in lower case) | EMU |
| BASIC keyboard | The first key after entering BASIC is lost (EMU, repeatable, `tools/analysis/kb.py`) | EMU, effect not explained |
| Paging | `LIST` and `PRINT` on the 4-line screen show one line and wait (solid `?` cursor) | EMU (HYPOTHESIS: waits for a key) |

## What does NOT exist (CONFIRMED in the keyword table)
`PEEK`, `POKE`, `CALL`, `USR`, `OUT`, `INP`, `WAIT`, `DEF`, `FRE`, `POS`, `ON`, `FN`, `SPC(`, `INKEY$`, `INSTR` **are not in the table** (68 names present, see BASIC_TOKENS). Neither are `AT`/`LOCATE`/`SOUND`/`BEEP`. The 55 blanked entries cannot be typed; their handlers are error stubs. Hence there is **no documented route from BASIC to machine code**; the only writable surface is the hook RAM (`D000-D0xx`, `D152-D1A0`), reachable only from machine code that is already running (for example from a cartridge).

## Pending (see UNRESOLVED_QUESTIONS)
Exact format of a tokenised line and of variables/arrays/strings (HYPOTHESIS: MBASIC style), memory limits (C006-...), precision (HYPOTHESIS: 24-bit mantissa, about 6-7 digits), function table (`B7:5608`/`58A5`), `LPRINT` and the handlers of `LOAD/SAVE/DIR/FORMAT/ERASE` (there are texts "FICHERO", "DISKETTE", "MEMORIA LLENA" at `B7:3FB9-3FEF`; HYPOTHESIS of support for an external drive that is not present; see HIDDEN_FEATURES for the later reading as a cartridge with RAM), `EDIT`.
