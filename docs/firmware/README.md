# Firmware reverse engineering of the VTech Genio 2000 (Spanish version)

These documents describe the firmware of the Spanish Genio 2000 (`27-5575-00`, 128 KiB, 8 banks of 16 KiB) as understood from the ROM itself, from emulation in MAME and from measurements on real units. The ROM is **not** included in this repository (see the top-level README); the analysis tools in `tools/analysis/` expect you to provide your own dump through the `GENIO_ROM` environment variable.

## Levels of evidence (used in every document)
| Label | Meaning |
|---|---|
| **CONFIRMED** | Read directly from the ROM bytes (with offset) and covered by an automatic test in `tools/analysis-tests/test_findings.py`, or measured on the real unit (`HW`). |
| **EMU** | Observed while running the ROM in MAME (driver `genio2000`). It is evidence from **emulation**, not from hardware. |
| **PROBABLE** | Inferred from code plus consistent data, without a dynamic or hardware proof. |
| **HYPOTHESIS** | Plausible, still to be verified. |
| **UNKNOWN** | Not enough evidence. |

Address conventions: `B<k>@<window>:<logical address>` (for example `B7@4000:5650`) or `k:offset` (offset inside the 16 KiB bank). The window 0x0000-0x3FFF is always bank 0.

## Contents
| Document | Contents |
|---|---|
| FIRMWARE_OVERVIEW | Summary: what the ROM is, architecture, main findings |
| FINAL_REPORT | Answers to the eleven original questions of the analysis |
| ROM_MAP | Map by bank and region |
| DISASSEMBLY | How the disassembly is generated, coverage and limits |
| FUNCTION_CATALOG | Identified functions (with confidence) |
| MEMORY_MAP_DETAILED / IO_REGISTERS / BANK_SWITCHING | The hardware as seen from the firmware |
| BOOT_SEQUENCE / INTERRUPTS | Start-up and interrupt service routine |
| BASIC_INTERNALS / BASIC_TOKENS / BASIC_REFERENCE | The BASIC interpreter |
| LCD_INTERNALS / KEYBOARD_INTERNALS | Display and keyboard |
| CARTRIDGE_INTERFACE / CARTRIDGE_DEVELOPMENT | Cartridges and expansion |
| FIRMWARE_API | Reusable routines |
| DATA_FORMATS / HIDDEN_FEATURES / MAME_VALIDATION | Resources, hidden features, comparison with MAME |
| HW_RESULTS_20261110 | First measurements of the `hwtest` cartridge on a real unit (clock, port 03, RAM, ports, LCD) |
| ROM_REVISIONS | Two units = two firmware revisions (banks 1, 2, 3, 7 differ) |
| UNRESOLVED_QUESTIONS / RESEARCH_LOG / CONTINUITY | Open points, log, state for resuming the work |
| `../../tools/hwtest/README.md` | Test cartridge for the real unit and its receiver |

## Reproducing the analysis
You need your own dump of the ROM; the dumper has its own repository: https://github.com/kresp0/vtech-genio2000-rom-dumper .
```bash
export GENIO_ROM=/path/to/genio2000_es_128k.bin
cd tools/analysis
python3 -I romid.py                 # identification
python3 -I check_dis.py             # checks the disassembler against MAME unidasm
python3 -I dyn_batch.py ...         # dynamic traces (MAME), see RESEARCH_LOG
python3 -I build_db.py              # static + dynamic tracing -> instructions, functions, cross-references
python3 -I gen_listing.py           # per-bank listings
python3 -I extract_strings.py; python3 -I api_table.py
python3 -I basic_tokens.py; python3 -I basic_dispatch.py
python3 -I extract_data_banks.py 1 4   # decoded data banks
python3 -I ../analysis-tests/test_findings.py   # tests that pin the conclusions
```
The generated listings and tables are not published because they are derived from the firmware.
