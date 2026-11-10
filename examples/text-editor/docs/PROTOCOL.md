# Genio -> PC protocol (version 1)

One-way link through the DB25: `DATA0 (pin 2) -> RXD` of the CP2102, 9600 baud 8N1, **T642** timing (110 + 16*30 + 13*4 = 642 T-states per bit; `tx_send` is a literal copy of the serial test cartridge, validated on the unit). BUSY is never read.

## Frame (same framing as the firmware dumper)
`END(0xC0)  stuff( 'G' 'E' ver type seq16 len16 payload[len] crc16 )  END`, all little-endian.
* SLIP stuffing: `0xC0 -> DB DC`, `0xDB -> DB DD`; `0xC0` only appears as a delimiter. An invalid escape invalidates the frame.
* `ver = 1`. `seq16`: frame counter since start-up (the receiver detects gaps). `len16`: payload bytes.
* `crc16` = **CRC-16/CCITT-FALSE** (poly 0x1021, init 0xFFFF, no reflection) over `'G'...last payload byte`, low byte first. `CRC("123456789") = 0x29B1`. The firmware computes it bit by bit (no table).
* The document content and the diagnostic events travel in **different types**.

## Types
| Type | Name | Payload |
|---|---|---|
| `0x01` | HELLO | `ver u8, hc u8 (30), f u8 (4), 0 u8, ram_ok u16 (document characters verified), doc_max u16`. At start-up and when entering the diagnostic. |
| `0x10` | DOC_BEGIN | `utf8_len u16, n_characters u16, n_lines u16` |
| `0x11` | DOC_DATA | `offset u16` + up to 48 UTF-8 bytes (the offset is into the UTF-8 stream) |
| `0x12` | DOC_END | `utf8_len u16, crc16 u16` (CRC-16 of **all** the UTF-8 bytes of the document) |
| `0x20` | KEY | `ev u16, tick u16, type u8 (0 release, 1 press, 2 ghost discarded), scancode u8, col_out u8, row_in u8 (0-7 matrix 1, 8-12 matrix 2), mods u8, class u8 (0 nothing, 1 character, 2 function, 3 modifier), value u16 (Unicode or function id), lcd_type u8 (0 none, 1 CGROM, 2 CGRAM), lcd u8` |
| `0x22` | LED | `ev u16, tick u16, state u8, port_0x12_value u8` |
| `0x30` | STATUS | `ev u16, tick u16, code u8 (1 enters diag, 2 leaves, 3 events lost, 4 ghost), arg u16` |

`mods`: bit0 SHIFT (shared intersection), bit1 right SHIFT (copy of SL), bit2 ALT, bit3 BLOQ, bit4 SYM, bit5 insert. `tick` is about 5 ms nominal per iteration (approximate). `ev` grows with every diagnostic event.

## Exported document
Standard UTF-8: every LCD code is converted to its Unicode (`ge_lcd_to_uni`): ASCII as is, Latin-1 and CGROM symbols, Á Í Ó Ú from CGRAM slots 0-3, `0x0A` -> `\n`. **Raw LCD codes are never sent.** A code with no BMP equivalent is exported as U+FFFD. The receiver accepts the document only if length, CRC-16 and UTF-8 are valid and there are no sequence/offset gaps; otherwise it rejects it and records it in `protocol_errors.jsonl` (with `--keep-partial` it saves it as `...PARTIAL_UNVERIFIED.txt`).

## Pace
A byte takes about 1.04 ms; an event frame about 30-35 ms. One event is transmitted per stable change of a key (there are no repeats), the queue holds 15 events (if it fills up this is counted and reported with STATUS 3), and the editor transmits nothing except when exporting. While transmitting, the keyboard is not scanned (a complete event lasts less than any human key press).
