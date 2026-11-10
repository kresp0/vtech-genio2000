# Test report

Date: 2026-11-09. Debian trixie, GCC 14.2.0, MAME `origin/master` c7541016 (2026-11-09). The PR series (`genio2000-pr1-system` ... `genio2000-pr8-contrast`, eight stacked branches) and `genio2000-dev` (PR 8 + the CLOCK/IRQ options).
Everything below was run **in MAME only**; hardware evidence is kept apart (`logs/timing/`, `logs/hardware/`).

## Build
* `make SUBTARGET=genio SOURCES=src/mame/vtech/pc2000.cpp USE_QTDEBUG=0 NOWERROR=1 TOOLS=0 -j12` (needs `SDL2_ttf` headers: `deps/` holds the extracted `libsdl2-ttf-dev` .deb; nothing installed system-wide). First build of the subset ~10 min, incremental ~10 s. A `DEBUG=1` build must use fewer jobs (`-j8`, `nice`): the first attempt with `-j20` hung the computer and left a corrupt `libsqlite3.a` and zero-size objects that had to be deleted.
* `tools/check_pr_series.sh` builds every branch of the series in turn and reports, for each: commits and files changed (only `pc2000.cpp` and `mame.lst`), warnings in `pc2000.cpp` (**0** for all eight), `-validate` (OK for all eight) and the ROM listing; for the last branch it also checks that the binary has no experimental option string and runs the tests below in candidate mode. Logs: `logs/build_genio2000-pr*.log`, `logs/check_pr_series_run.txt`.
* `DEBUG=1` build of PR 3 (`geniod`, `logs/build_pr3_debug2.log`): links, `-validate` OK, the boot and an activity run without assertion failures. The later branches were not built in debug.
* `-listroms genio2000`: `27-5575-00` CRC `7a9d7b8a` / SHA-1 `76e41bc3...`, `genio2000_cgrom_reconstructed.bin` `BAD_DUMP` `1f712c25` / `0ad6de16...`; `-verifyroms` with `submission/genio2000.zip`: firmware OK, character table "NEEDS REDUMP" (BAD_DUMP honoured).

## Suites (final run)
* `genio2000-dev` (`mame/genio`): `python3 -m pytest -v tests` - **51 passed, 0 failed** (51 s); `tools/check_all.sh` rc 0.
* PR 8 (the full series; binary `mame/genio_candidate`, `GENIO_MAME=... GENIO_CANDIDATE=1`): **38 passed, 13 skipped** (the 13 `dev_only` tests need the CLOCK/IRQ options). The series diff against `origin/master` touches only `pc2000.cpp` and `mame.lst`.
* `gl4000` is unchanged by the series (`test_gl4000_identical_to_baseline`: snapshots identical to an unpatched earlier build of the same driver; the 4x20 position table was only moved into a shared function).
* Intermediate branches (PR 1 ... 7) were built, validated and, for the LCD (PR 4), power (PR 5), LED (PR 6), speaker (PR 7) and contrast (PR 8) stages, exercised with a scripted check at the time; the full suite is run on the last branch only.
* All runners pass `-artpath work/noart` so the photo artwork never changes snapshots. The default clock is 6.13179 MHz, so the 4 MHz reference runs use `CLOCK` index 9. The screen readers (`tests/lcd_ocr.py`, `tests/render_lib.py`) understand both formats (gl4000 120x36 and genio2000 120x40).

## Dev-branch tests, in the order of the log
* `test_firmware_hashes`
* `test_cgrom_binary_format`
* `test_cgrom_eighth_row_used_only_by_ten_symbol_glyphs`
* `test_validate_and_romdef`
* `test_bank_mirroring_matches_hardware_observation`
* `test_cgrom_region_is_the_reconstructed_file`
* `test_gl4000_keeps_device_default_cgrom`
* `test_boot_welcome_screen`
* `test_lcd_data_register_sends_a9_before_hola`
* `test_activity_key_opens_its_activity[ALGEBRA-ALGEBRA]`
* `test_activity_key_opens_its_activity[BASIC-BASIC]`
* `test_activity_key_opens_its_activity[SUMA-SUMA]`
* `test_activity_key_opens_its_activity[PLURALES-PLURAL]`
* `test_activity_key_opens_its_activity[SINONIMOS-SINONIMOS]`
* `test_activity_key_opens_its_activity[CALCULADORA-CALCULADORA]`
* `test_activity_key_opens_its_activity[RESTA-RESTA]`
* `test_activity_key_opens_its_activity[MULTIPLICACION-MULTIPLICACION]`
* `test_activity_key_opens_its_activity[DIVISION-DIVISION]`
* `test_activity_key_opens_its_activity[CIENCIAS-CIENCIAS]`
* `test_activity_key_opens_its_activity[RATIOS-RATIOS]`
* `test_off_key_says_goodbye`
* `test_keyboard_labels_match_firmware_verified_table`
* `test_bank_selects_boot_and_algebra`
* `test_demo_menu_boots`
* `test_three_cgrom_diagnostic_screens_match_binary[1-32]`
* `test_three_cgrom_diagnostic_screens_match_binary[2-112]`
* `test_three_cgrom_diagnostic_screens_match_binary[3-192]`
* `test_cgrom_differs_from_stock_a00`
* `test_gl4000_identical_to_baseline`
* `test_boot_melody_is_a_bit_banged_scale_at_4_mhz`
* `test_clock_switch_follows_effective_clock_model[1]`
* `test_clock_switch_follows_effective_clock_model[2]`
* `test_clock_switch_follows_effective_clock_model[3]`
* `test_clock_switch_follows_effective_clock_model[4]`
* `test_clock_switch_follows_effective_clock_model[5]`
* `test_clock_switch_follows_effective_clock_model[6]`
* `test_clock_switch_follows_effective_clock_model[7]`
* `test_clock_switch_follows_effective_clock_model[8]`
* `test_cgram_codes_and_aliases_render_like_the_hd44780`
* `test_timing_reference_runs_are_stable`
* `test_irq_switch_scales_welcome_typing_only[1-40]`
* `test_irq_switch_scales_welcome_typing_only[4-60]`
* `test_irq_switch_scales_welcome_typing_only[6-100]`
* `test_basic_editor_special_keys_match_hardware_observation`
* `test_artwork_clickable_items_exist_as_input_fields`
* `test_power_off_blanks_lcd_and_on_restarts_with_full_boot`
* `test_contrast_switch_darkens_the_lcd_by_the_photographed_ratio`
* `test_lcd_photographed_drawing_cell_layout`
* `test_on_button_resets_and_clears_ram_at_any_time`
* `test_speaker_plays_the_boot_melody_at_the_measured_clock`

## What each group proves
| Group | Real check |
|---|---|
| hashes / ROM def | file sizes and SHA-1/SHA-256/CRC32 of the dump and the CGROM; MAME's own ROM listing; BAD_DUMP flag |
| bank mirroring | a Lua script reads all 32 entries of the `:bios` region of the running machine and compares each 16 KiB with bank `n & 7` of the dump |
| boot / LCD | OCR of snapshots (exact glyph match against the CGROM binary) reads "¡Hola! Por favor elige una actividad"; LCD data log shows 0xA9 sent before "Hola!" |
| keyboard | 13 virtual key presses (12 activities + OFF) by the Spanish field names open the activity with the same name; field list equals the firmware-verified table; no German labels; the special keys of the BASIC editor behave as observed on hardware (T5) |
| bank events | I/O tap log: boot `OUT 01,00` first, ALGEBRA writes selector 5, port 0x00 never written, selectors <= 0x1F; port 0x06 only written (0x40), never read |
| CGROM pages | the three diagnostic screens of the original viewer (demo cartridge, option 4) are pixel-exact against the binary (3 x 80 cells); menu text too |
| CGRAM | 8 patterns + codes 0x00-0x0F + aliases + sample CGROM codes exact |
| regression | `gl4000` snapshots (demo cartridge + keypress) byte-identical between the new build and the unpatched baseline build of an earlier commit (`dev/mame-cgrom/mame-src-build/mame_baseline_genio`); `gl4000` still uses the device's default CGROM |
| timing | MAME boot/power-off timing at 4 and 6 MHz and the IRQ sweep reproduce `logs/timing/emulation` (EMU only; the real-unit numbers in `logs/timing/` are inputs, not tests) |
| sound/clock | bit-banged boot melody has the expected scale ratios; the experimental CLOCK switch reproduces the effective-clock model for 8 clocks; the IRQ option scales the interrupt-paced welcome typing (256.1 ticks) and not the CPU-bound farewell sound |
| LCD / controls (PRs 4-8) | the LCD drawing keeps rows 7 and 9 and column 5 unlit, shows the cursor underline in row 8 and faint unlit dots; OFF blanks the LCD and ON restarts to the start-up sequence (also from BASIC); the caps LED output follows port 0x12 bit 5; the contrast switch scales the three pens by 0.86 and toggles back; the speaker melody has nine notes and ends about 2.6 s after power-on |
| artwork | all clickable items of the photo layout map to existing input fields |

## Not tested / limits of these tests
* The automated tests contain no hardware comparison. The only hardware-vs-emulator comparison is the timing evidence of `logs/timing/` (recordings/videos of one unit, analysed by scripts, not asserted by tests). The "verified in emulation" statements mean *the emulated firmware behaves coherently with the documented hardware evidence*.
* Only 12 of 39 activity keys and OFF are exercised by tests (the other 26 were measured on the unit by T4, `logs/hardware/T4_keymap/`); BASIC and the editor are exercised with single keys, no natural-keyboard typing.
* Printer port, cartridge pages above the demo cartridge, serial/CP-M use: untested.
* The sound tests use port-edge logs and the 1-bit WAV; the stock beeper model (gated 3250 Hz) is not validated.
* The `gl4000` regression baseline is an earlier MAME commit of the same driver code, not the rebased tree.
* The real-mouse behaviour of the artwork was checked by hand with `tools/artwork_click_test.py` (`logs/artwork/`), not by the suite.

## Review of PR 1-3 (2026-11-09, corrected state; isolated clone, original branches untouched)
Work copy `work/review/mame-rev` (uncommitted edits on top of each original tip: `edit_pc2000.py`), base c7541016. Each stage built with `make SUBTARGET=genio SOURCES=src/mame/vtech/pc2000.cpp USE_QTDEBUG=0 NOWERROR=1 TOOLS=0 -j16` (a subset, not full MAME):
| Stage | pc2000.cpp warnings | `-validate` | 20 s headless run | pytest (GENIO_CANDIDATE=1) |
|---|---|---|---|---|
| PR 1 | 0 | OK | exit 0 | `firmware_hashes`, `bank_mirroring` pass; `boot_welcome_screen`, `bank_selects_boot_and_algebra` fail as expected (German inputs, generic character set) |
| PR 2 | 0 | OK | exit 0 | `firmware_hashes`, `bank_mirroring`, `bank_selects`, `keyboard_labels` pass; the OCR-based tests (activity keys, BASIC editor) fail as expected (generic character set until PR 3) |
| PR 3 | 0 | OK | exit 0 | whole suite: 33 passed, 5 failed, 13 skipped; the 5 failures are the artwork, power/ON, contrast and LCD-drawing tests of later PRs |
Full builds, made only on the PR 3 state, in a copy under /dev/shm (the disk had 25 GB free): `make USE_QTDEBUG=0 TOOLS=0 -j20` (all drivers, `mame`) and `make DEBUG=1 USE_QTDEBUG=0 TOOLS=0 -j12` (`mamed`): both link, 0 warnings in `pc2000.cpp` (the full build prints 316 warnings in unrelated files), `-validate` OK with both, 20 s run of `genio2000` with `mamed`: exit 0, no assertion. The PR 3 pytest run on the full release binary gives the same 33 / 5 / 13. `-validate` was run for each binary; nothing was run on PR 1 and PR 2 beyond the subset builds listed above.
Local `hd44780_a00.bin` is a stand-in (documented in PRESERVATION_MANIFEST.md), hence the "WRONG CHECKSUMS" line at start-up.

## Consolidated series and PR 9 (2026-11-09; clone work/review/mame-rev)
* Branches `genio2000-r2-pr1..8` (base d077ea24), then public branches `genio2000-system` ... `genio2000-lcd-contrast`, `genio2000-photographic-layout` on master 5b02f514. Driver-only build (`REGENIE=1`, needed for the device list of PR 7 and the layout of PR 9), `-validate` OK and 0 warnings in `pc2000.cpp` for all of them. Suite results (`GENIO_CANDIDATE=1`): PR 1 9 pass / 29 fail, PR 2 11 / 27, PR 3 33 / 5, PR 4 34 / 4, PR 5 35 / 3, PR 6 36 / 2, PR 7 36 / 2 (the failures exercise features of later PRs or need the Spanish character set), PR 8 and PR 9 38 pass, 13 skipped, equal test by test to the original PR 8 (38 / 13) before the consolidation.
* Full MAME build (release) and full DEBUG=1 build of the state ending with PR 8 (d077ea24): 0 warnings in `pc2000.cpp`, `-validate` OK for `mame` and `mamed`, 20 s debug run without assertion.
* Test harness: `-snapview native` added to the invocations (needed from PR 9 on; harmless before).
