# ROM_MAP: map of the 128 KiB ROM

Offsets = offset inside the bank; "addr" = logical address in its usual window. Data from the analysis tools (identification, coverage and listing statistics).

| Bank | Usual window | Entropy (bits/B) | Decoded code | Role | Evidence |
|---|---|---|---|---|---|
| 0 | 0000 (fixed) | 7.11 | 80.6 % | Core: vectors, API, ISR, keyboard, LCD, start-up, cartridges, sound, utilities | CONFIRMED (code) + EMU |
| 1 | 8000 (data) | 7.82 | 0 % | Header `55 AA 04 00 FF 7F FF 1F` + tables: **1,066 general-knowledge questions** with 3 answers | CONFIRMED (extractor with real code) |
| 2 | 8000 (data) | 7.96 | 0 % | High-entropy data (compressed/encoded) | no header; format UNKNOWN |
| 3 | 8000 (data) | 7.78 | 0 % | Data (accessed with `OUT (03),03` in activities, EMU) | EMU + PROBABLE |
| 4 | 8000 (data) | 7.60 | 0 % | Header `55 AA 01 00 FF 3F FF 0F` + tables: **2,601 words** in 14 groups x 4 subgroups; `OUT (03),04` heavily used (8,607 writes in the traces) | CONFIRMED (extractor with real code); group semantics pending |
| 5 | 4000 | 6.89 | 85.4 % | Dispatcher of activities and school games (`4000: LD A,(DB23)...` CP/JP table) | CONFIRMED + EMU |
| 6 | 8000 (and 4000 for the start) | - | 57.8 % | Editor/word processor, calculator, printing; `4000` = trampoline that puts bank 7 in window 1 | CONFIRMED + EMU |
| 7 | 4000 (window 1 with `DFF1`=7 in EMU) | - | 63.2 % | RST 10h-28h (4010...), **BASIC interpreter**, error messages, tables | CONFIRMED + EMU |

## Bank 0 (selection of verified regions)
| Region | Contents | Evidence |
|---|---|---|
| 0000-0037 | Vectors: reset `DI;IM 1;JP 0FAA`, RST 08->`JP D000` (RAM), RST 10/18/20/28->`JP 4010/4018/4020/4028`, RST 30->`JP 11E6`, IM1 0038->`JP 0119` | CONFIRMED |
| 0066 | **There is no NMI handler**: 0x0066 falls in the middle of `JP 34F9` of the API table (`F9 34 C3...`). If the NMI line were connected it would execute garbage, so it is inferred to be unused | CONFIRMED (bytes) / PROBABLE (inference) |
| 003B-0118 | Table of 74 `JP` = public API | CONFIRMED |
| 0119-0199 | ISR | CONFIRMED |
| 01A8-03xx | Keyboard scan, decoding | CONFIRMED |
| 03AD, 0415, 047D, 04E5, 054D | Character tables: SHIFT, normal, CAPS+SHIFT, CAPS, ALT (documented in `docs/hardware/KEYBOARD.md`) | CONFIRMED |
| 05CF-07F0 | LCD driver (init, refresh, CGRAM, character translation, DDRAM table at 07EE) | CONFIRMED |
| 08E8-09xx | Data block reader / nibble engine (not executed by the activities in EMU). The databases of banks 1/4 are read by `0C13` (+ `0E5A`, `0EB4`, `0CAF`) | PROBABLE (08E8-09xx) / CONFIRMED (0C13) |
| 0FAA-10E9 | Cold start | CONFIRMED |
| 118E-11E5 | Cartridge probe from the menu + "Sin cartucho" + RST 30h | CONFIRMED |
| 11E6-1216 | Soft restart (RST 30h) | CONFIRMED |
| 1364-138E | Tone routine (port 0x12 bit 5/3, see note) | PROBABLE |
| 13F4-14xx | Title screen, length-prefixed strings | CONFIRMED |
| 3xxx | Stack of high-level LCD routines (3509-36xx) and I/O utilities of the API | CONFIRMED |

## Bank 7 (BASIC)
| Region | Contents | Evidence |
|---|---|---|
| 4000-4050 | `DI;JP 6EB8` (BASIC start), RST 10h-28h stubs (`JP D003...; PUSH BC; LD B,n; JR 4046`) | CONFIRMED |
| 3651-3810 (addr 7:3651) | Error messages (1st letter with bit 7) | CONFIRMED |
| 5590-5610 | Floating point constants (pi/2 = `DB 0F 49 81`, pi = `DB 0F 49 83`, coefficients) | CONFIRMED |
| 5608-564F | Table of 36 words (dispatch of operators/functions, see BASIC_INTERNALS) | PROBABLE |
| 5650-581F | Keyword table | CONFIRMED |
| 5822-5899 | Statement dispatch table (60 words) | CONFIRMED + EMU |
| 58A5-58C7 | Function dispatch table (probable) | PROBABLE |
| 58CA-58F9 | 2-letter error codes (`NF SN RG OD FC OV OM UL BS DD /0 ID TM OS LS ST CN NR RW UE MO FD`) | CONFIRMED |
| 5920-5935 | `" ERROR"`, `" IN "`, `"READY"`, `"BREAK"` | CONFIRMED |
| 6EB8 | BASIC cold initialisation | CONFIRMED |

## Regions not interpreted
Banks 2-3 entirely, and most of 1 and 4 (data); about 20-40 % of 5/6/7 that neither static tracing nor the MAME traces reach (listing `.db` rows). **It is not claimed that they are data**: they may be code that was not reached.
