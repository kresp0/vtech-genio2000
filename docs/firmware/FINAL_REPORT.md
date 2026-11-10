# FINAL_REPORT (partial, honest): answers to the 11 questions

1. **Internal operation**: Z80 + 8 banks of 16 KiB ROM (bank 0 fixed; windows 4000 and 8000 switched through ports 01/03) + 8 KiB RAM; HD44780 4x20 LCD refreshed by the ISR from a RAM buffer; 8x(8+5) matrix keyboard scanned by the ISR; cartridges in the 8000 window. See FIRMWARE_OVERVIEW. *Partial*: clock about 6.1 MHz and IRQ 46.76 Hz measured on HW (HW_RESULTS_20261110); the physical source of the IRQ and the function of ports 02/04/05/06 are still unknown (`IN` returns the floating bus).
2. **What each region does**: ROM_MAP (banks 0, 5, 6, 7 with a clear role; 1 and 4 = question and word databases already extracted; 2 and 3 not deciphered). 36 % of the ROM is disassembled and verified.
3. **Start-up and execution**: BOOT_SEQUENCE (complete up to the key wait). Program execution: bank 5 dispatcher, bank 6 editor/calculator, bank 7 BASIC.
4. **Display, keyboard, cartridges**: LCD_INTERNALS, KEYBOARD_INTERNALS, CARTRIDGE_INTERFACE (signatures `YE`, `GA`, `11` shown in the bytes; `YE` tested in EMU and on HW with `hwtest`; `GA` and `11` not tested on HW).
5. **BASIC**: BASIC_INTERNALS/TOKENS (tables resolved; no PEEK/POKE/CALL/USR; 55 words removed). *Missing*: data format and functions.
6. **Reusable routines**: FIRMWARE_API (74 entry points; about 25 identified; example verified in EMU). Key reading and sound are still to be documented.
7. **Maximum demonstrable expansion**: 128 KiB of cartridge ROM (A0-A16 of the connector) = **PROBABLE** (from the pinout only); on HW with a 32 KiB EEPROM only bit 1 of selector 03 moves A14 (HW_RESULTS_20261110): to be tested with a larger ROM (E4). RAM in the cartridge: BASIC seems to use it (HIDDEN_FEATURES); `/WR` was not seen on the EEPROM (E1 open).
8. **Cartridge with Wi-Fi**: CARTRIDGE_DEVELOPMENT; the path with the most evidence is loader ROM + 8 KiB internal RAM + link through the printer port (E); dual-port SRAM (D) is feasible but needs E1.
9. **Undocumented functions** (and now two ROM revisions: ROM_REVISIONS; BASIC storage points to a cartridge with RAM): HIDDEN_FEATURES (`GA` signature, RST 30h, RAM hooks, non-volatile storage support). No factory mode found (not explored in depth).
10. **Improvements for MAME**: MAME_VALIDATION (3 minor points; no urgent fix).
11. **Missing / experiments**: UNRESOLVED_QUESTIONS (15 software questions, 8 hardware experiments: E2 and E6 done, E1 and E4 partial; Q1 partially solved).
