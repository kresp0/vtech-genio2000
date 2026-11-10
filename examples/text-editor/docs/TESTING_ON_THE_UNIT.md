# What to check on a real Genio (concrete list)

This is the checklist for testing the editor on a real unit. The author has tested the program on a real Genio 2000; the individual results are not recorded here. A complete pass with the **diagnostic** (menu 2) confirms the key table (see `docs/hardware/KEYBOARD.md`).

Preparation: burn the image, connect **only** DATA0 -> RXD and ground, and on the PC:
`python3 -I receiver/ge_rx.py --port /dev/ttyUSB0 --outdir <folder>` (at every step, `key_events.jsonl` must match the screen).

## A. Start-up and screen
| # | Action | Expected |
|---|---|---|
| A1 | power on with the cartridge | title screen "EDITOR GENIO 2000", `RAM doc 6144 OK` (about 1 s) and an empty screen with an underline cursor; the speaker is not heard |
| A2 | type `ÁÍÓÚ` (SHIFT+ALT+A, I, O, U) | the 4 glyphs with a thin 2 px accent (`01 02`), row 7 empty; Á comes out in the first cell (code 0x00 raw) |
| A3 | type `ñ Ñ ü Ü ¿ ¡ É` | correct native CGROM glyphs |
| A4 | the PC receives a HELLO at start-up (`ram_ok = 6144`) | `receiver` counts it as a frame (no protocol error) |

## B. Modifiers
| # | Action | Expected |
|---|---|---|
| B1 | `a`, SHIFT+`a`, ALT+`a`, SHIFT+ALT+`a` (and E, I, O, U) | `a A á Á` (`e E é É`, ...) |
| B2 | CAPS LOCK: `a`, SHIFT+`a`, ALT+`a`, SHIFT+ALT+`a` | `A a Á á`; **the LED turns on** when activated and off when deactivated |
| B3 | digits and signs with CAPS LOCK | do not change; with SHIFT they do |
| B4 | left **and** right MAYÚSCULAS separately | both give capitals; in the diagnostic `SL1 SR1` (same intersection: do both give the same scan `0x36`?) |
| B5 | hold SHIFT or ALT or BLOQ for several seconds | nothing is written or repeated |
| B6 | SHIFT+ALT+`'` (rectangle with SPACE) | nothing is written; in the diagnostic `G` (ghost) appears for `'` and SPACE; release ALT and it is accepted |
| B7 | ALT+`q`, ALT+`s`, ALT+`d`, ALT+`f`, ALT+`g` | `√ + - × ÷` |
| B7b | ALT+CAPS LOCK and then `a` (with ALT still held or already released) | `π`; the LED does **not** change; the next `a` is normal |

## C. Symbols of the photograph (SHIFT = left red, ALT = right red)
| # | Action | Expected |
|---|---|---|
| C1 | SHIFT+`1 2 3 4 5 6 7 8 9 0` | `¡ ¿ # $ % / & * ( )` |
| C2 | ALT+`1 2 3 4 5 6 7 8` | `\ @ - _ + [ ] =` (ALT+9 and ALT+0: nothing) |
| C3 | SHIFT+`, . ; '` | `? ! : "` |
| C4 | SHIFT+RETROCESO, SHIFT+AVANCE | `<` `>` |
| C5 | PAUSA (no SHIFT) | `^` |
| C6 | **position of `;` and `'`**: press both | `;` and `'` (they were swapped in `keyboard_es.h`; the firmware says `;` = scan 0x26, `'` = 0x2E) |
| C7 | ALT+W R T Y H J K L Z X C V B N M | write nothing |

## D. Editing and navigation
| # | Action | Expected |
|---|---|---|
| D1 | type more than 20 characters | continues on the next row; with more than 4 rows it scrolls without losing anything |
| D2 | RETROCESO/AVANCE; ALT+Ü / ALT+; | cursor left, right, up, down (the wanted column is kept on short lines) |
| D3 | ALT+RETROCESO / ALT+AVANCE; SHIFT+ALT+Ü / `;` | start / end of line; page up, down |
| D4 | INS | underline cursor <-> blinking block; in overwrite mode typing replaces |
| D5 | REPETIR/BORRAR, DEL | delete previous / next; held they repeat (about 0.5 s + about 0.1 s) |
| D6 | SHIFT+BORRAR (REPETIR), SHIFT+AYUDA (TAB) | repeats the last character; indent to a multiple of 4 |
| D7 | hold a letter until the document is full (6144) | `MEMORIA LLENA` on the last row; no text is lost; deleting frees space |
| D8 | AYUDA (left/right turn the 5 pages), SHIFT+PAUSA, RESPUESTA (menu 1-6) | correct screens and, on leaving, the text intact |
| D9 | menu 5 "Redibujar" | accents and text stay the same |
| D10 | ALT+Ñ and menu 4 | ask for confirmation; INTRO clears, another key cancels |

## E. Diagnostic (menu 2): check **every key** of the photograph
| # | Action | Expected |
|---|---|---|
| E1 | press every key of the keyboard | `v` + hex id, `C`olumn, `R`ow, `M1`, legend; release `^`; matches the key table (col/row/scan) |
| E2 | the panel keys (matrix 2) | `M2` with its name; **note whether the inferred names match** (only OFF is confirmed) |
| E3 | positions without a key (col 0 rows 2-7, col 7 rows 0, 1, 7) | must give no event; if they do, note the key |
| E4 | SHIFT, ALT, BLOQ, ALT+BLOQ (SYM) | `SL SR AL CP SY` change; BLOQ also generates an LED frame (`port12 = 0x20` / `0x00`) |
| E5 | SHIFT+ALT+vowel | `CGRAM slot n` for Á Í Ó Ú; `CGROM 90` for É |
| E6 | ALT+Q, ALT+F, ALT+G and ALT+BLOQ->A | `CGROM BE B7 B8 ED` |
| E7 | hold a key | a single press event and one release event (the port is not flooded) |
| E8 | short RESPUESTA, then **hold about 1.5 s** | the short tap is recorded; holding it leaves to the editor with the text intact |
| E9 | IMPRIMIR TEXTO inside the diagnostic | only recorded (it does not export) |

## F. Export (IMPRIMIR TEXTO or menu 1)
| # | Action | Expected |
|---|---|---|
| F1 | a document with `ñ Ñ ü ¿ ¡ ÁÉÍÓÚ áéíóú π√×÷` and several lines | `export_001.txt` identical UTF-8 (compare with what was typed), SHA256 saved, 0 protocol errors |
| F2 | an empty document | a valid empty `export_00N.txt` |
| F3 | a long document (about 1000 characters) | several frames, correct CRC |
| F4 | unplug RXD halfway | the receiver rejects the document (no `export_*.txt`) |

## G. OFF
| # | Action | Expected |
|---|---|---|
| G1 | hold OFF about 1.5 s in editor / help / menu / diagnostic / during export | it switches off; ON restarts |
| G2 | a short tap of OFF | does not switch off |
| G3 | power on with OFF pressed | ignored until released once |
| G4 | toggle CAPS LOCK 20 times | the unit does **not** switch off or make a sound |

## H. Timing (adjustable in `src/genio_text_editor_gl4000.c`)
`GE_TICK_ITERS`, `GE_REP_DELAY`, `GE_REP_RATE`, `GE_EXIT_HOLD`, `GE_FLASH_TICKS`: nominal values computed with a clock of about 6.16 MHz deduced from T642; **measure**: initial repeat about 0.5 s, then about every 0.1 s, leaving the diagnostic about 1.5 s.
