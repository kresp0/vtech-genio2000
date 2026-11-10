# Keyboard – Spanish Genio 2000

## Five levels that are never mixed
| Level | What it is | Where it is defined |
|---|---|---|
| A | physical key of the Genio (legend printed on the key, photo `genio2000_keyboard.jpg`) | `PORT_NAME` of each MAME field = the legend |
| B | matrix contact: `col_out` (bit written to port 0x10) x `row_in` (bit read back). Matrix 1 = rows 0-7 on port 0x10, matrix 2 = rows 8-12 on port 0x11 (activity panel) | `data/teclado_es_source.csv` |
| C | value read at the I/O ports (active low in MAME's model: `INn` = column *n*, bit = row) | `INPUT_PORTS_START(genio2000)` |
| D | key of the PC keyboard that triggers it in MAME (`PORT_CODE`) – a convenience mapping | same block; remap with *Tab > Input (this Machine)* |
| E | what the firmware does with it (character code from its four tables, activity, power-off) | firmware bank 0: normal `0x0415`, SHIFT `0x03AD`, CAPS `0x04E5`, CAPS+SHIFT `0x047D`, ALT `0x054D` |

## Provenance and verification
* The matrix positions come from an earlier keyboard table (`teclado_es.csv`, not included), itself derived from the firmware tables and the photograph; it is copied unchanged into `data/teclado_es_source.csv`.
* `tools/gen_keyboard_ports.py` regenerates the MAME block **and re-checks it against the firmware dump**: for all 55 matrix-1 keys the firmware normal-table code at (col,row) equals the CSV output, and the 39 activity keys carry codes 0x01-0x1F, 0xB0-0xB7 in panel order (OFF = 0xB4, ON = no code). The firmware tables are stored in reverse column order (slice *s* serves `col_out = 7 - s`); this was derived from the already hardware-confirmed positions (PAUSA, OFF) and is consistent with the German driver: `KP6` = `INC` bit 2 = matrix-2 column 4, row 10 = **ALGEBRA**, which is what the user observed on `gl4000`.
* Emulation tests (`tests/test_genio2000.py`): pressing the named field of 12 activity keys and OFF opens the activity with the same name on the LCD (EMU, not hardware).
* SHIFT: the firmware reads a single matrix position (col 6, row 6): the two MAYUSCULAS keys are the same contact. In MAME both `LSHIFT` and `RSHIFT` drive it.
* ON is not readable by the firmware; the position is left `IPT_UNUSED`.

## Findings that differ from the German driver
Column 0 contained DIP-like inputs and German labels in `pc2000`; for the Spanish unit column 0 = AYUDA (row 0), PAUSA (row 1). Activity keys: 5 per column (40 positions), not 4. Labels such as "Calculator"/"Letter Hunt" must not appear: test `test_keyboard_labels_match_firmware_verified_table`.

## Matrix 1 (main keyboard)
| Genio key (A) | matrix col_out,row_in (B) | MAME field (C/D) | PC key (D) | firmware code normal / SHIFT (E) |
|---|---|---|---|---|
| PAUSA | 0,1 | `IN0` bit 1 "PAUSA" | PAUSE | 5E / F7 |
| 1 | 1,1 | `IN1` bit 1 "1" | 1 | 31 / AD |
| 2 | 2,0 | `IN2` bit 0 "2" | 2 | 32 / A8 |
| 3 | 2,1 | `IN2` bit 1 "3" | 3 | 33 / 23 |
| 4 | 3,0 | `IN3` bit 0 "4" | 4 | 34 / 24 |
| 5 | 3,1 | `IN3` bit 1 "5" | 5 | 35 / 25 |
| 6 | 4,0 | `IN4` bit 0 "6" | 6 | 36 / 2F |
| 7 | 4,1 | `IN4` bit 1 "7" | 7 | 37 / 26 |
| 8 | 5,0 | `IN5` bit 0 "8" | 8 | 38 / 2A |
| 9 | 5,1 | `IN5` bit 1 "9" | 9 | 39 / 28 |
| 0 | 6,0 | `IN6` bit 0 "0" | 0 | 30 / 29 |
| RETROCESO | 7,2 | `IN7` bit 2 "RETROCESO" | LEFT | F1 / 3C |
| AVANCE | 7,3 | `IN7` bit 3 "AVANCE" | RIGHT | F0 / 3E |
| AYUDA | 0,0 | `IN0` bit 0 "AYUDA" | TAB | FD / D0 |
| Q | 1,2 | `IN1` bit 2 "Q" | Q | 71 / 51 |
| W | 2,7 | `IN2` bit 7 "W" | W | 77 / 57 |
| E | 2,2 | `IN2` bit 2 "E" | E | 65 / 45 |
| R | 3,7 | `IN3` bit 7 "R" | R | 72 / 52 |
| T | 3,2 | `IN3` bit 2 "T" | T | 74 / 54 |
| Y | 4,7 | `IN4` bit 7 "Y" | Y | 79 / 59 |
| U | 4,2 | `IN4` bit 2 "U" | U | 75 / 55 |
| I | 5,7 | `IN5` bit 7 "I" | I | 69 / 49 |
| O | 5,2 | `IN5` bit 2 "O" | O | 6F / 4F |
| P | 6,7 | `IN6` bit 7 "P" | P | 70 / 50 |
| Ü | 6,2 | `IN6` bit 2 "Ü" | OPENBRACE | 81 / 9A |
| REPETIR/BORRAR | 6,1 | `IN6` bit 1 "REPETIR / BORRAR" | BACKSPACE | F5 / FB |
| BLOQ. MAYUSCULAS | 1,0 | `IN1` bit 0 "BLOQ. MAYUSCULAS" | CAPSLOCK | FF / FF |
| A | 1,3 | `IN1` bit 3 "A" | A | 61 / 41 |
| S | 2,3 | `IN2` bit 3 "S" | S | 73 / 53 |
| D | 2,4 | `IN2` bit 4 "D" | D | 64 / 44 |
| F | 3,3 | `IN3` bit 3 "F" | F | 66 / 46 |
| G | 3,4 | `IN3` bit 4 "G" | G | 67 / 47 |
| H | 4,3 | `IN4` bit 3 "H" | H | 68 / 48 |
| J | 4,4 | `IN4` bit 4 "J" | J | 6A / 4A |
| K | 5,3 | `IN5` bit 3 "K" | K | 6B / 4B |
| L | 5,4 | `IN5` bit 4 "L" | L | 6C / 4C |
| Ñ | 6,3 | `IN6` bit 3 "Ñ" | COLON | A4 / A5 |
| ; | 6,4 | `IN6` bit 4 ";" | QUOTE | 3B / 3A |
| INTRO | 7,4 | `IN7` bit 4 "INTRO" | ENTER | F9 / F9 |
| MAYUSCULAS (izq.) | 6,6 | `IN6` bit 6 "MAYUSCULAS" | LSHIFT+RSHIFT | FF / FF |
| Z | 1,4 | `IN1` bit 4 "Z" | Z | 7A / 5A |
| X | 2,5 | `IN2` bit 5 "X" | X | 78 / 58 |
| C | 2,6 | `IN2` bit 6 "C" | C | 63 / 43 |
| V | 3,5 | `IN3` bit 5 "V" | V | 76 / 56 |
| B | 3,6 | `IN3` bit 6 "B" | B | 62 / 42 |
| N | 4,5 | `IN4` bit 5 "N" | N | 6E / 4E |
| M | 4,6 | `IN4` bit 6 "M" | M | 6D / 4D |
| , | 5,5 | `IN5` bit 5 "," | COMMA | 2C / 3F |
| . | 5,6 | `IN5` bit 6 "." | STOP | 2E / 21 |
| ' | 6,5 | `IN6` bit 5 "'" | SLASH | 27 / 22 |
| MAYUSCULAS (der.) | 6,6 | (same field as the other SHIFT key) | RSHIFT | – |
| JUGADOR IZQUIERDA / INS | 1,7 | `IN1` bit 7 "JUGADOR IZQUIERDA / INS" | INSERT | F8 / F8 |
| ALT | 1,5 | `IN1` bit 5 "ALT" | LALT | FF / FF |
| ESPACIO | 1,6 | `IN1` bit 6 "ESPACIO" | SPACE | 20 / 20 |
| RESPUESTA | 7,6 | `IN7` bit 6 "RESPUESTA" | ESC | FA / FA |
| JUGADOR DERECHA / DEL | 7,5 | `IN7` bit 5 "JUGADOR DERECHA / DEL" | DEL | FC / FC |

## Matrix 2 (activity panel; names follow the panel photo, order = firmware code order; **all 39 positions were measured on the real unit by T4 on 2026-11-09 and equal this table**; ON is a separate contact, not readable)
| Panel key (A) | matrix col_out,row (B) | MAME field | PC key (D) | firmware code (E) | opens in MAME |
|---|---|---|---|---|---|
| BUSCA LA LETRA | 0,8 | `IN8` bit 0 | F1 | 01 | – |
| RECUERDA LA PALABRA | 0,9 | `IN8` bit 1 | F2 | 02 | – |
| PLURALES | 0,10 | `IN8` bit 2 | F3 | 03 | verified (see tests) |
| VERBOS | 0,11 | `IN8` bit 3 | F4 | 04 | – |
| REVOLTIJO DE LETRAS | 0,12 | `IN8` bit 4 | F5 | 05 | – |
| LA PALABRA MISTERIOSA | 1,8 | `IN9` bit 0 | F6 | 06 | – |
| DERIVADOS | 1,9 | `IN9` bit 1 | F7 | 07 | – |
| SINONIMOS | 1,10 | `IN9` bit 2 | F8 | 08 | verified (see tests) |
| ANTONIMOS | 1,11 | `IN9` bit 3 | F9 | 09 | – |
| LA LETRA LOCA | 1,12 | `IN9` bit 4 | F10 | 0A | – |
| LA NUEVA PALABRA | 2,8 | `INA` bit 0 | F11 | 0B | – |
| TRUEQUE DE LETRAS | 2,9 | `INA` bit 1 | F12 | 0C | – |
| ALFAPUZZLE | 2,10 | `INA` bit 2 | 0_PAD | 0D | – |
| REVOLTIJO | 2,11 | `INA` bit 3 | 1_PAD | 0E | – |
| ACERTIJO GRAMATICAL | 2,12 | `INA` bit 4 | 2_PAD | 0F | – |
| SUMA | 3,8 | `INB` bit 0 | 3_PAD | 10 | verified (see tests) |
| RESTA | 3,9 | `INB` bit 1 | 4_PAD | 11 | verified (see tests) |
| MULTIPLICACION | 3,10 | `INB` bit 2 | 5_PAD | 12 | verified (see tests) |
| DIVISION | 3,11 | `INB` bit 3 | 6_PAD | 13 | verified (see tests) |
| FRACCIONES / DECIMALES | 3,12 | `INB` bit 4 | 7_PAD | 14 | – |
| FRACCIONES / PORCENTAJES | 4,8 | `INC` bit 0 | 8_PAD | 15 | – |
| RATIOS | 4,9 | `INC` bit 1 | 9_PAD | 16 | verified (see tests) |
| ALGEBRA | 4,10 | `INC` bit 2 | HOME | 17 | verified (see tests) |
| REPASO A LAS MATEMATICAS | 4,11 | `INC` bit 3 | END | 18 | – |
| EL SIGNO PERDIDO | 4,12 | `INC` bit 4 | PGUP | 19 | – |
| CIENCIAS | 5,8 | `IND` bit 0 | PGDN | 1A | verified (see tests) |
| CINE Y TELEVISION | 5,9 | `IND` bit 1 | SLASH_PAD | 1B | – |
| HISTORIA Y GEOGRAFIA | 5,10 | `IND` bit 2 | ASTERISK | 1C | – |
| GENERAL | 5,11 | `IND` bit 3 | MINUS_PAD | 1D | – |
| ¿QUE SOY? | 5,12 | `IND` bit 4 | PLUS_PAD | 1E | – |
| EL NUMERO RELAMPAGO | 6,8 | `INE` bit 0 | DEL_PAD | 1F | – |
| BASIC | 6,9 | `INE` bit 1 | ENTER_PAD | B0 | verified (see tests) |
| IMPRIMIR TEXTO | 6,10 | `INE` bit 2 | (none, map in UI) | B1 | verified (see tests) |
| CALCULADORA | 6,11 | `INE` bit 3 | (none, map in UI) | B2 | verified (see tests) |
| CARTUCHOS ADICIONALES | 6,12 | `INE` bit 4 | (none, map in UI) | B3 | – |
| OFF | 7,9 | `INF` bit 1 | (none, map in UI) | B4 | verified (see tests) |
| NIVEL | 7,10 | `INF` bit 2 | (none, map in UI) | B5 | – |
| 1 JUGADOR | 7,11 | `INF` bit 3 | (none, map in UI) | B6 | – |
| 2 JUGADORES | 7,12 | `INF` bit 4 | (none, map in UI) | B7 | – |

## Hardware measurements, T4 (2026-11-09, one unit; **HW**)
A helper cartridge (`t4-keymap/`) asked for each key in turn, read the raw matrix and sent it over the software serial port; capture, CSV, JSON and report are preserved in `logs/hardware/T4_keymap/`.
* **Activity panel: 39 of 39 keys measured exactly at the expected (column, row)**, first attempt each. The "inferred" caveat for the 26 keys is gone; `data/teclado_es_source.csv` now says "confirmado" for them (ON is not readable, still pending by construction).
* **Main keys: 55 of 56 positions measured as expected**; the printed key, the matrix position and the firmware table agree. Ñ was skipped during the session (it was already confirmed by earlier diagnostics). MAYUSCULAS (izq.) and (der.) both read 6,6: **one contact serves both shift keys (HW)**.
* **Combinations (MAYUS+A, ALT+A, MAYUS+ALT+A) gave no usable measurement**: the program reported only the modifier (6,6 / 1,5 / 6,6) and the raw columns show no sign of A (column 1 reads DF for ALT+A, not D7 as ALT+A together would). The program takes its sample at the first stable reading, so A was most probably not yet down; this is **not** evidence of ghosting or of a matrix limitation. Repeat with the letter pressed first if it matters.
* One 1-byte frame was rejected at start-up (line noise while the unit powered the port); the other 101 frames were valid and all 98 key records arrived.

## Pending (needs the physical unit)
* ALT / SHIFT / CAPS character tables are not exposed as MAME characters (natural keyboard is not implemented): typing relies on the PC SHIFT/ALT/CAPS keys mapped to the matrix keys.
* The 7 activity keys without a default PC key (the last of the list) have to be mapped from the UI, clicked on the photo artwork, or addressed by Lua field name.
* Optional: the same special keys inside an activity, SHIFT+ALT, a clean key-combination measurement.

## Hardware observations, T5 (2026-11-09, one unit, BASIC editor; **HW**)
Tested by the owner in BASIC (READY prompt): SHIFT, CAPS, ALT+vowel (á é í ó ú), SHIFT+1 (¡), SHIFT+2 (¿), PAUSA, RETROCESO, AVANCE, INS and DEL behave as expected by the table in `teclado_es_source.csv`. Exceptions / notes:

| Key / combination | Real unit (BASIC editor) | Firmware table (E) | MAME (same firmware, EMU) |
|---|---|---|---|
| SHIFT+PAUSA | line break | SHIFT code `PAUSA` | line break (matches) |
| REPETIR/BORRAR (plain and SHIFT) | no visible effect | BORRAR / REPETIR codes | no visible effect (matches) |
| ALT+Ü, ALT+; | no visible effect | ALT table gives the up / down codes | no visible effect (matches) |
| RESPUESTA, AYUDA | no visible effect | MENÚ / AYUDA codes | no visible effect (matches) |

* The key press produces a code that the BASIC editor ignores; presumably those codes are used inside the activities. Trying them inside an activity is optional and assumed to match MAME.
* "Up/down" for ALT+Ü / ALT+; therefore remain *table-derived* labels: no cursor movement was seen in BASIC. Page up/down (SHIFT+ALT) was not tried.
* The behaviour is covered by `test_basic_editor_special_keys_match_hardware_observation`; this agreement of the emulated firmware with the unit is evidence for the matrix map, but it is one session of one unit and it only compares visible effects.


## Photo check of the legends (2026-11-09, `logs/hardware/photos_2026-11-09/B_C_keyboard_and_activity_panel_topdown.jpg`)
* Activity panel: the 40 printed labels (5 rows x 8 columns) read from the photo equal the names of the table above (plus ON). Reading each physical column top to bottom gives exactly consecutive firmware codes (01-05, 06-0A, 0B-0F, 10-14, 15-19, 1A-1E, 1F B0-B3, [ON] B4-B7), which is the layout the table assumes. This checks the labels and the column layout; it does not prove the firmware code of each of the remaining 26 keys (that needs T4, pressing each key); the 13 keys exercised by tests are spread over columns 1, 2, 4, 5, 6, 7 and 8 and are consistent with it.
* Main keys: the red legends of the number row and punctuation keys read from the photo agree with the CSV (¡ \, ¿ @, # -, $ _, % +, / [, & ], * =, ( , ), ? , ! . and " '). On key 4 the printed mark is a long dash, longer than the short hyphen of key 3, and the firmware ALT table gives `_` (0x5F) for ALT+4 and `-` (0x2D) for ALT+3: consistent, but ALT+symbol output was not tried on the real unit.
