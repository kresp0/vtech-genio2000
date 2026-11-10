# DATA_FORMATS

| Resource | Location | Format | Conf. |
|---|---|---|---|
| System strings (title, menus, messages) | `B0:13F4-14xx`, `B0:~2000-3600`, `B5:*`, `B6:*` | Strings with a **length byte** in front, no terminator. In the routines `00AD..00B6`/`007A` the prefix also counts its own byte (`prefix-1` characters are copied: `06 'VTECH'`, `11 'ELECTRONICS LTD.'`). Other strings of the same block (`05 'elige'`, `03 'una'`, `09 'actividad'`) seem to use the exact length, so **two conventions or different routines** (to be clarified) | CONFIRMED (partial) |
| Text codes | same | ASCII + `AD ¡ A8 ¿ A4 ñ A5 Ñ A7 º` (translated at `B0:07A8`) | CONFIRMED |
| BASIC strings (keywords, errors) | `B7:5650-581F`, `B7:3651-3810` | 1st letter with bit 7 | CONFIRMED |
| 2-letter error codes | `B7:58CA` | `NF SN RG OD FC OV OM UL BS DD /0 ID TM OS LS ST CN NR RW UE MO FD` | CONFIRMED |
| Storage messages | `B7:3F90-3FEF` | `DATOS`, `FORMATEAR DISKETTE? (S/N)`, `N. FICHERO`, `MEMORIA LLENA`, `ERROR DE DISKETTE`, `DISKETTE LLENO` (separated by `0D`) | CONFIRMED; function HYPOTHESIS (see HIDDEN_FEATURES) |
| Keyboard tables | `B0:03AD,0415,047D,04E5,054D` | 5 tables x (8 col x 13), reversed column order | CONFIRMED (earlier documents) |
| DDRAM table | `B0:07EE` | 80 bytes, 4x20 | CONFIRMED |
| Predefined CGRAM | `B0:07CA`, `07D2`, `07DA`, `07E4` | 8 bytes per character (5x8) | CONFIRMED (data), use PROBABLE |
| Numeric constants | `B7:5590-5610` | 32-bit float: 3 mantissa bytes (LSB first) + exponent (excess-128); pi/2 = `DB 0F 49 81` | CONFIRMED |
| "Cartridge" data header | `B1:0000`, `B4:0000` | `55 AA`, word (4/1), word (`7FFF`/`3FFF`), word (`1FFF`/`0FFF`), table of words at `80xx`; in the commercial one `55 AA 11` | PROBABLE |
| Compressed text engine `B0:0845-0B56` (cartridge format `55 AA 11`) | B0 | **Correction T-D1 (2026-11-10)**: this engine was **not executed in any of the 49 MAME scenarios** (`0845`, `08E8`, `0964`, `09DF`, `0A1A`), so the internal activities do not use it in EMU; PROBABLE that it serves cartridges with an `11` header. Structure read from the code (PROBABLE): a stream of word indices (`<E0`: length table at `(8008)`; `>=E0`: 11-bit index through `(8014)`); each word is bytes with nibbles: nibble `<0E` indexes T0 (14 characters), `0E`/`0F` are escapes to T1/T2 (tables at `D800/D802/D804`, at +0/+14/+44 from a header pointer); output with a length prefix. | PROBABLE; not verified |
| **Word/question databases** (bank 4 = words for SYNONYMS/ANTONYMS/PLURALS/DERIVATIVES..., bank 1 = general-knowledge questions) | B4, B1 (window 8000) | **SOLVED (T-D1a, 2026-11-10)**: header `55 AA` + words (`+8` -> count table P, `+A..+1A` pointers to code tables). P[0]=number of groups, P[1..n]=subgroups per group, then 1 count byte per (group,subgroup). Each entry is obtained with the routine `B0:0C13(A=group, D=subgroup, E=index)` -> string at `D401..` (length in `D400`) with **bit**-based decoding tables (bit field `B0:0E5A`, canonical-Huffman-style decoder `B0:0EB4`, recursive `B0:0CAF`), CP850-style character codes (`A0`=á, `82`=é, `A1`=í, `A2`=ó, `A4`=ñ). Verified: the Z80 harness with the real ROM reproduces what MAME shows (' abrasar quemar'). **Extractor**: `tools/analysis/extract_data_banks.py` -> bank 4 (2,601 entries, 14 groups x 4 subgroups) and bank 1 (1,066 questions; fields separated by `\`: question + 3 to 6 answer fragments; see "Classification" below). Banks 2, 3 and 6 do **not** use this format (empty output) | CONFIRMED (reproduction with real code); semantics of the groups: to be classified (T-D1b) |
| Sound/melodies | `B0:1364` (routine) + unknown data | 1-bit tone | PROBABLE (see `docs/hardware/CLOCK_AND_SOUND.md`) |
| Comparison with other variants | - | No ROM of another model with a clear licence is available (only MAME's private German `gl4000`, not used here) | UNKNOWN |

Existing extractors (in `tools/analysis/`): `extract_strings.py` (268 strings with bank, offset and % in decoded code), `basic_tokens.py`, `api_table.py`. Extractor of banks 1 and 4: `extract_data_banks.py` (T-D1a; needs the Z80 interpreter `z80core.py`). Missing: group classification (T-D1b) and the formats of banks 2, 3 and 6.

## Classification of the data of banks 1 and 4 (additional report 2026-11-10, **verified here against the extracted tables**; labels = inference from content)
**Bank 4** (2,601 rows; each group has subgroups 0-3). The association group <-> activity/key is **not** proven (T-D1b is still open).
| Group | Rows | Examples | Proposed label | Confidence |
|---|---:|---|---|---|
| 0 | 136 | `abajo arriba`, `abierto cerrado` | antonyms | high |
| 1 | 133 | `abajo debajo`, `abrasar quemar` | synonyms | high |
| 2 | 414 | `abajo igual`, `aboné decir` | lexical pairs, purpose not established | unknown |
| 3 | 213 | `abajo bajo`, `andar anda` | verb forms | high |
| 4 | 133 | `abierto abiertos`, `alta altas` | singular/plural | high |
| 5 | 135 | `actuación actuar` | derivation noun->verb | high |
| 6 | 136 | `abrasar abrasaba abrasé` | verb tenses | high |
| 7-10 | 102 / 282 / 126 / 31 | lists of 4 words | word lists, function unknown | medium |
| 11 | 200 | `la gabardina tiene 4 botones . gavardina 2 votones 5` | spelling-error identification (numeric format not deciphered) | high/low |
| 12 | 400 | `Si es mágica tiene un genio dentro . \abe` | riddles with an encoded answer | high/low |
| 13 | 160 | `lampara\\h\adios` | sequences segmented with `\`, use pending | low |

**Bank 1** (1,066 records in 5 groups of 213, 219, 220, 200 and 214; apparent topics: film/popular culture, general knowledge, history and geography, mathematics, natural sciences). **Correction:** they are not always "3 answers": fields per record (including the question) = 4 -> 785, 5 -> 253, 6 -> 25, 7 -> 3. The fragments are PROBABLY accepted variants of the answer (for example `GILITO \ TIO GILITO \ EL TIO GILITO`); the ROM's comparator still has to be verified. Pinned in `tools/analysis-tests/test_findings.py`.

## Regions repeated between banks (static, verified here)
Banks 2 and 5: identical tail of **1,095 B** from `0x3BB9`; banks 0 and 1: identical tail of **401 B** from `0x3E6F`; bank 3: **967 null bytes** at `0x1439-0x17FF`. The tails are neither decoded as code nor executed in any trace. **Update:** these tails **do not exist in the dump of the second unit** (ROM_REVISIONS), so they are padding of that production run and not a hardware feature. Original cause UNKNOWN (common padding, mask-ROM layout or a read artefact are different hypotheses; the dump was verified with two independent sessions, so it is not transmission corruption).
