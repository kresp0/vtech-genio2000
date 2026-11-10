# CGROM of the Spanish Genio 2000 in MAME

## What is integrated
* File: `genio2000_cgrom_reconstructed.bin`, 4096 bytes = 256 entries x 16 bytes, **MAME `hd44780` format** (bit 4 = leftmost pixel, rows 0-7 in bytes 0-7, bytes 8-15 zero because 5x10 mode was never observed, codes 0x00-0x1F zero).
* **Version used: "final reviewed" of 2026-11-09 01:30** – CRC32 `1F712C25`, SHA-1 `0AD6DE16DB67C014F44211DFD1328091BE389CC7`, SHA-256 `7E4FF917DFFD…745534`. Source: `dev/mame-cgrom/preservation/rom_archive/20261109_final/` (output of the manual review editor, `corrections_20261109_final.json`).
  Earlier version an earlier reconstruction (SHA-1 `EF026A8B…`, 1101 inferred + 192 unknown pixels) differs in 32 bytes and is **superseded**; the older `LIMITATIONS.md` numbers refer to it.
  A copy of the used file and its hashes are in `data/cgrom/`.
* Provenance: optical reconstruction from 4 photographs of the LCD of the real unit running the project's CGROM viewer (identities confirmed by the owner, 194 hardware events); in the final version all 8960 pixels are flagged *verified* after manual review (1305 pixels in 199 glyphs were hand-set, each with a log entry). It is **not a read of the silicon**, so the ROM entry stays **`BAD_DUMP`** (MAME then reports "NEEDS REDUMP"). Full evidence: `dev/mame-cgrom/EVIDENCE.md`, `preservation/PROVENANCE.md`, `editor/output/r_20261109_013018/` (uncertainty, correction log, per-glyph notes).

## Integration (smallest change)
`hd44780_device` already prefers a memory region named like the device (`m_cgrom_region(*this, DEVICE_SELF)`), the same mechanism `psion.cpp` uses. The driver therefore only adds
`ROM_REGION(0x1000, "hd44780", 0)` to `ROM_START(genio2000)`. `hd44780_a00.bin` and every other HD44780 user are untouched (tests: `test_gl4000_keeps_device_default_cgrom`, `test_gl4000_identical_to_baseline`).
The device's own A00 ROM is still listed by `-verifyroms` as a required (datasheet-derived BAD_DUMP) file; it is never read for this machine.

## Format check
`test_cgrom_binary_format`: size, hashes, zero rows 8-15, zero codes 0x00-0x1F, 5-bit glyphs, every printable ASCII glyph non-blank.
`test_cgrom_region_is_the_reconstructed_file`: the region in the running machine equals the file byte for byte.

## Rendering checks (all against the binary, EMU)
* `test_three_cgrom_diagnostic_screens_match_binary`: the three pages of the original CGROM viewer (demo cartridge, option 4: three pages starting at codes 0x20, 0x70 and 0xC0, covering all 224 codes 0x20–0xFF) are drawn pixel-exact: ASCII, Spanish accents, ñ Ñ ¿ ¡ (0x9B 0x9C 0x9F 0xA9), mathematical symbols (× ÷ √ 0xB7 0xB8 0xBE), Greek letters (0xE0-0xFF region, π = 0xED), inverted/solid glyphs.
* `test_cgram_codes_and_aliases_render_like_the_hd44780`: eight patterns written into CGRAM through ports 0x0A/0x0B appear for codes 0x00-0x07 and again for 0x08-0x0F; CGROM glyphs written in the same screen are exact.
* `test_boot_welcome_screen`: `¡Hola!` is drawn with CGROM 0xA9 ("¡"); the LCD data log shows the firmware sends **0xA9** (not 0xAD): the 0xAD seen in the ROM string is translated by the firmware before output (EMU). This closes the old "0xAD vs 0xA9" question for the emulator; a physical bus trace would be needed to call it HW.
* Which glyphs use the 8th row (checked on the binary, `test_cgrom_eighth_row_used_only_by_ten_symbol_glyphs`): normal letters with descenders (g j p q y , ;) stay within seven rows, so on the real unit the detached eighth row is visible only in the cursor underline and in ten codes of 0xE0-0xFC (0xE0 0xE1 0xE4 0xE5 0xEA 0xEC 0xEE 0xF2 0xF3 0xFC: Greek-like letters and the box 0xFC; the owner reports "some mathematics" symbols do reach the bottom line). Photographing them needs the CGROM viewer page that starts at code 0xC0.
* The 8th pixel row: the data is the eighth byte of each entry; MAME's `gl4000` layout draws character cells 6 x 9 pixels (eight rows + one blank), i.e. it does **not** reproduce the extra physical separation of the last row. Cosmetic limitation, see `KNOWN_LIMITATIONS.md`.

## Differences with the German `gl4000`
The `gl4000` driver uses the generic HD44780 **A00** table of the device (Japanese/European ROM). The Spanish unit has its own table: for example CP437-like order in 0x80-0xA9 (Ç ü é … ñ Ñ ¿ ¡ at 0x80, 0x81, 0x82, 0x9B, 0x9C, 0x9F, 0xA9), õ at 0xAD, × ÷ √ at 0xB7 0xB8 0xBE, Greek 0xE0-0xFF, and `\` `~` at 0x5C / 0x7E (A00 has ¥ and →). Test `test_cgrom_differs_from_stock_a00` only proves that the region replaces the stock table (here the stock table on disk is a stand-in, see `PRESERVATION_MANIFEST.md`); a comparison with the authentic A00 requires `hd44780.zip`.

## Remaining uncertainty
The editor reports expected wrong pixels 0.4 of 8960 after review, but that number rests on the owner's confirmations of ambiguous pixels; **45 glyphs were LOW before review**. Independent re-photography (straight-on, two exposures) and codes 0x10-0x1F (observed blank on hardware, never photographed) are listed in `PHOTOS_TODO.md` §I.
