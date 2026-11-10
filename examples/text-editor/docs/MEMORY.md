# Genio 2000 memory and the editor's layout

Generated from the real link (`build/genio_text_editor_gl4000.sym`) in the original project. It is not a measurement of the unit.

## Machine map (sources: MAME `pc2000.cpp`, VGLDK, the firmware dump, `docs/firmware/MEMORY_MAP_DETAILED.md`)

| Range | Contents | Use by the editor |
|---|---|---|
| `0x0000-0x7FFF` | internal ROM (16 KiB windows switched through ports 0x00/0x01) | read only; **no bank port is written** |
| `0x8000-0xBFFF` | 16 KiB cartridge window (first half of the AT28C256; the 32 KiB image repeats the window) | code and constants: **15826 bytes used, 558 free** |
| `0xC000-0xDFFF` | 8 KiB RAM (the mirror at 0xE000 is not used) | data and stack |

## RAM (0xC000-0xDFFF)

| Zone | Range | Size | Contents |
|---|---|---|---|
| Program data | `0xC000-0xD9F4` | 6645 B | VGLDK variables (80 B LCD buffer...), the editor's, and the **document buffer** |
| - document buffer (`doc`) | `0xC0EB-0xD8EA` | 6144 B | gap buffer, 1 byte per character (LCD code, 0x0A = line break) |
| - screen `want[80]`, `scr[80]` | see table | 160 B | wanted cell / cell on the LCD (only the differences are written) |
| Stack reserve | `0xD9F5-0xDFEF` | 1531 B | the stack starts at `0xDFF0` (`vgldk_init`) and grows downwards; the code is not recursive and uses few levels |
| Unused | `0xDFF0-0xDFFF` | 16 B | |

The original build script **rejected** the ROM if the data went beyond `0xDC00` (guaranteeing at least 1008 B of stack). Now: data up to `0xD9F5`, available stack **1531 B**.

Free RAM is not assumed: at start-up `ram_pass()` (asm, about 0.1 s) writes and verifies the document buffer with three patterns (l xor h of the address, its complement, 0). If it fails at address N, the capacity of the document is reduced to N characters (shown at start-up and in PAUSA). The original firmware uses 0xDB00-0xDFFF while it runs, but with the cartridge running (DI) it does not execute; the editor does use that zone **for its stack and its document**, so nothing is kept between starts (switching off and on starts empty).

## Document

* Capacity: **6144 characters** (another can be compiled with `-DGE_DOC_MAX=n`; the original tests used 96 to fill the buffer).
* Structure: *gap buffer* (`src/ge_buffer.h`). Inserting and deleting at the cursor is O(1); moving the cursor copies only the bytes the gap crosses. No dynamic memory.
* Limit: with the buffer full, inserting is rejected and `MEMORIA LLENA` is shown on the last row for about 0.75 s (it does not block the keyboard). Overwriting in a full document is still allowed (it does not grow).
* Line wrap by characters at 20 columns (no horizontal scrolling); a line of n characters takes n/20 + 1 rows (one of exactly 20*k characters shows an empty final row where the cursor falls).
* End-of-line searches with `CPIR`/`CPDR` (21 T per byte): a 3000-character line without breaks is redrawn with no noticeable delay.

## Largest variables

| Symbol | Address | Bytes |
|---|---|---|
| `_doc` | `0xC0EB` | 6144 |
| `_want` | `0xD8EB` | 80 |
| `_scr` | `0xD93B` | 80 |
| `_ex_buf` | `0xD9BA` | 52 |
| `_mx_evq` | `0xC099` | 32 |
| `_mx_prev` | `0xC078` | 16 |
| `_mx_stable` | `0xC088` | 16 |
| `_mx_gmark` | `0xC0BB` | 16 |
| `_ge_namebuf` | `0xC070` | 8 |
| `_ex_n` | `0xD9EE` | 7 |
| `_accent_slot` | `0xC065` | 4 |
| `_ge_val` | `0xC06E` | 2 |
| `_ge_ghosts` | `0xC0CC` | 2 |
| `_ed_buf` | `0xC0CE` | 2 |

## ROM budget

| | Bytes |
|---|---|
| Code + constants | 15826 |
| Cartridge window | 16384 |
| Free | 558 |

About 3 KiB of it is VGLDK/GENIO_ES code that `system.h` links in even though this program does not call it (the stock keyboard driver `keyboard_es.h`, `lcd_putchar`, `genio_native_putn`...): SDCC does not remove unused functions inside a compilation unit.
