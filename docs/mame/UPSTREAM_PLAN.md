# Plan for the MAME contribution (nothing has been published or opened)

The first candidate (one big commit, 4 MHz) is **superseded**: branch `genio2000-upstream-superseded`, patches in `patches/superseded/`. The new plan is a series of three small, stacked PRs on the current `origin/master` (c7541016, fetched 2026-11-09). Policy research: `MAME_POLICY.md`. Texts: `PR_DRAFT.md`. ROM e-mail: `../submission/`.

## The series (branches in `mame/`, patches in `patches/upstream-pr-series/`)
| # | Branch | What it changes | Flags | Depends on |
|---|---|---|---|---|
| 1 | `genio2000-pr1-system` | adds `genio2000` as a clone of `gl4000`: ROM `27-5575-00` (128 KiB dump mirrored over the 32 banks), CPU clock **6.13179 MHz**, `mame.lst`; still the gl4000 (German) inputs and the generic HD44780 table | `NOT_WORKING` | - |
| 2 | `genio2000-pr2-keyboard` | the Spanish input ports (56 main keys + 39 activity buttons, matrix measured on the unit) | `NOT_WORKING` | 1 |
| 3 | `genio2000-pr3-cgrom` | the Spanish character generator as a `BAD_DUMP` region named `hd44780`; flags relaxed; interrupt rate 46.76 Hz (measured) | `NODEVICE_PRINTER`, `IMPERFECT_SOUND` | 2 |
| 4 | `genio2000-pr4-lcd` | `genio2000_state`; the LCD drawn as on the unit (6x10 cells, detached eighth row, faint unlit dots, 120x40) | same | 3 |
| 5 | `genio2000-pr5-power` | OFF (port 0x12 bit 0: CPU stops, LCD blank) and the ON button (reset + RAM clear + power-on, in place) | same | 4 |
| 6 | `genio2000-pr6-led` | output `led_caps` (port 0x12 bit 5) | same | 5 |
| 7 | `genio2000-pr7-speaker` | 1-bit speaker following port 0x12 bit 3 instead of the generic beeper | `NODEVICE_PRINTER` | 6 |
| 8 | `genio2000-pr8-contrast` | the two-position contrast switch (toggling input; darker LCD, more visible unlit dots) | same | 7 |
PRs 1-3 are the machine itself; 4-8 are small follow-ups that can wait until 1-3 are merged (their texts: `PR_DRAFT.md`). Each branch builds with 0 warnings in `pc2000.cpp` and passes `-validate` (`tools/check_pr_series.sh`, which also runs, on the last branch, the 38 tests that do not need the experimental options; `genio2000-dev` passes 51). A `DEBUG=1` build of PR 3 linked, validated and ran a boot and an activity without assertion failures (`logs/build_pr3_debug2.log`); the later branches were built normally only.
Each PR is stacked on the previous one: open PR 2 and later ones as drafts, or after the one they need is merged.
The year is written `199?` in the driver (decision of the PR 1-3 review): no documentary evidence of the release year exists yet, and neither 1994 nor 1995 is claimed. Evidence to keep in mind: the chips on this unit carry 1995 date codes (SRAM 9513, CPU 9523, ROM 9532 and "1995" printed on the ROM), so this unit cannot have been made before 1995; that does not show the year the model was introduced (a 1994 catalogue entry would be an earlier revision). `199?` is the notation MAME already uses for an unknown year within a decade. The family years in the driver are 1993 (pc2000, gl2000) and 1994 (gl4000). Replace it once a catalogue (Biblioteca Nacional) gives a date.

## Before opening PR 1
1. Read `MAME_POLICY.md`; the owner must be able to explain every line (AI policy).
2. Fetch and rebase again if `origin/master` moved: `git -C mame fetch origin master && git -C mame rebase origin/master` per branch, rerun `tools/check_pr_series.sh`.
3. Done: credit "Santiago Crespo", ChatGPT named as OpenAI ChatGPT (GPT-6), `Co-Authored-By` trailers kept (decided by the owner); the commits are authored by the owner's git identity (`kresp0`).
4. Send the ROM zip first or together with PR 1 (`../submission/README.md`): MAME cannot run the set without it, and the PR can then point to the zip name.
5. Open PR 1 from your fork (GitHub account needed; not done here).

## Machine flags: the options (`src/emu/gamedrv.h`)
`MACHINE_NOT_WORKING` (used in PR 1 and 2), `MACHINE_IMPERFECT_SOUND`, `MACHINE_IMPERFECT_TIMING`, `MACHINE_IMPERFECT_GRAPHICS` (could describe the 6x9 LCD cell that lacks the detached eighth row), `MACHINE_IMPERFECT_CONTROLS`, `MACHINE_NODEVICE_PRINTER` (the printer port exists and is not emulated), `MACHINE_NO_SOUND` (the system has sound and it is not emulated at all: not true), `MACHINE_NO_SOUND_HW`, `MACHINE_IMPERFECT_COLORS`/`WRONG_COLORS`, `MACHINE_UNEMULATED_PROTECTION`, `MACHINE_NODEVICE_MICROPHONE`/`LAN`, `MACHINE_NO_COCKTAIL`, `MACHINE_REQUIRES_ARTWORK`, `MACHINE_MECHANICAL`, `MACHINE_IS_INCOMPLETE`, `MACHINE_SUPPORTS_SAVE` (no flag = save states warn). The set proposed for PR 3 is the honest "works, with known gaps" one (and `MACHINE_IMPERFECT_SOUND` goes away in PR 7 when the speaker follows the bit); staying on `MACHINE_NOT_WORKING` is the conservative alternative and is the maintainers' call.

## Timing (`MACHINE_IMPERFECT_TIMING` dropped in PR 3)
Done 2026-11-10: the interrupt rate was measured on the unit with the `hwtest` cartridge, 46.76 Hz (1000 interrupts in 21.39 s, `HW_RESULTS_20261110.md` #14), and PR 3 sets it instead of the family's 50 Hz; it agrees to 0.05 % with the CPU clock divided by 2^17, and it explains the 5.45 s of the welcome-text typing (about 47 Hz). Still open:
1. The /INT pulse width and whether it is held until acknowledged (MAME uses `irq0_line_hold`).
2. **Clock stability** with the counter (batteries / adapter / cold / warm): if the oscillator is not a crystal the value may drift and the 6.13179 MHz is only one point.
3. How the interrupt is generated and released (pulse or held until acknowledged): MAME uses `irq0_line_hold`.
4. The two recorded T3 sounds and a second video of the boot, to confirm the tempo with a second activity.
5. The speaker is done (PR 7).
The owner decided on 2026-11-10 to drop `MACHINE_IMPERFECT_TIMING` after the measurement; it can be put back if the maintainers want it.

## Possible 9th PR: the photographic layout built in (proof of concept done, not committed)
`PR9_LAYOUT.md`: the five PNG images can be embedded in a built-in layout with no build-system change (Base64 `<data>` in `image`, decoded by `rendlay.cpp`); the result is pixel-identical to the external artwork, adds 5 MB to the binary and 6.7 MB to the repository, and has no precedent in the tree; licence and the maintainers' view on bitmap artwork are open. Ask them before opening it.

## Everything that stays out of the series
The experimental branch `genio2000-dev` (PR 8 + one commit): the `CLOCK` and `IRQ` options (clock and interrupt-rate selectors, not hardware) and the output `lcd_dark` used by the photo artwork; and the photo artwork (`ARTWORK.md`, possibly a 9th PR: see above). The OFF/ON, LED, speaker, contrast and LCD drawing that used to live there are now PRs 4-8.

## Open items that do not block PR 1
Ports 0x02/0x04/0x05/0x06 and the printer (unmapped on purpose), ROM capacity (T9), the unexplained 6 % in the welcome typing, the CGROM being a reconstruction (PR 3 may be refused or ask for a real dump).
