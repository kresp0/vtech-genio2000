# Known limitations and unverified assumptions

Evidence classes as in `HARDWARE.md` (HW / EMU / FW / HYP / UNK).

## Emulation status
* The PR series (`UPSTREAM_PLAN.md`) flags the machine `MACHINE_NOT_WORKING` in PR 1 and 2 (German inputs / generic character set), `MACHINE_NODEVICE_PRINTER | MACHINE_IMPERFECT_SOUND` in PR 3-6 and `MACHINE_NODEVICE_PRINTER` from PR 7 (speaker); `MACHINE_IMPERFECT_TIMING` was dropped on 2026-11-10 after the interrupt rate was measured; staying on `MACHINE_NOT_WORKING` is the conservative alternative. The experimental branch (`genio2000-dev`) adds only the CLOCK/IRQ selectors and the `lcd_dark` output.

## Clock, interrupt and sound (`CLOCK_AND_SOUND.md` §5, evidence in `logs/timing/`)
* **CPU clock measured on the CPU CLK pin with an oscilloscope: 6.13179 MHz (hardware counter; `CLOCK_AND_SOUND.md` §5.9)**; the PR series uses it as the CPU clock of `genio2000` and with it the CPU-bound timings of MAME agree with the unit within 3-4 % and, with the 1-bit speaker of PR 7 (not with the generic beeper of PR 1-6), the recorded melody onsets and pitch; stability over time and with the supply not yet established; the interrupt rate is still not measured. The CPU is a Zilog Z84C0006 (6 MHz-rated) and no crystal was found on the board (2026-11-09 photos); the oscillator is not identified and the stability and uncertainty of the 6.13179 MHz reading are not determined (one unit, one session). `gl4000` keeps its inherited 4 MHz ("not accurate").
* Measured on one real unit (recordings and videos compared with MAME): 4 MHz / 50 Hz does **not** reproduce the real timings (boot melody, title pause and farewell sound ~1.5-1.6x too slow). With the emulated CPU at 6 MHz the CPU-bound timings agree within ~1-6 %. This is evidence for roughly 6 MHz **effective speed**, not proof of a 6 MHz CPU. The candidate therefore runs music and animations too slowly.
* The interrupt rate was measured on the unit: 46.76 Hz (`CLOCK_AND_SOUND.md` §5.10); this explains the welcome-text typing (5.45 s on the unit vs 5.12 s in MAME at 50 Hz). The divider that produces it (CPU clock / 2^17) is a hypothesis.
* Limits of the timing evidence: 60 fps video, LCD fade latency not measured, one unit/phone/camera, uncalibrated microphone, shared machine/firmware/method (not independent), key press instant not visible. T3 (right/wrong sounds) is recorded but not analysed.
* `-speed` is not equivalent to a faster CPU (it also scales the interrupt rate).
* The speaker is a 1-bit model following port 0x12 bit 3 (PR 7), which reproduces the recorded start-up melody; the speaker's own response is not modelled. T3 (right/wrong sounds) is recorded but not analysed.

## Not modelled in the PR series (PRs 1-8)
* Ports 0x06 (written 0x40 at reset) and 0x02/0x04/0x05 (written 0 at reset): function UNKNOWN, left unmapped on purpose. Port 0x00 behaviour (stubs in bank 7), cartridge bank decoding beyond the 2-page cartridges, bits 5-7 of the port 0x01 selector.
* Printer (DB25: data 0x10, busy 0x11 bit 5, strobe 0x12 bit 2). MAME maps port 0x11 writes onto the keyboard latch (inherited, probably inexact).
* The speaker's own frequency response; the LCD's contrast model (the switch only scales the palette by amounts from one pair of photographs); the exact dot colours (by eye).
* Natural keyboard / typing from the PC layout; only matrix keys are emulated.
* OFF/ON: the unit is switched off only in the sense that the CPU halts and the LCD goes blank; ON is emulated in place (RAM cleared although the unit does not zero it, most words read `70 C1 07 1C`; latches and LCD controller reset, RESET pulsed), not as a hard reset of the machine. Whether ON is a CPU reset line or the power-up of the whole board is unknown.

## Experimental branch only (`genio2000-dev`)
* `CLOCK` and `IRQ` options (clock and interrupt-rate selectors) and the output `lcd_dark`. Not hardware; not for upstream.
* The photo artwork (`ARTWORK.md`): rectangles placed from photographs, a mouse click holds one key at a time (SHIFT/ALT combinations need the PC keyboard); not part of the series (`PR9_LAYOUT.md` explores a 9th PR).

## CGROM
* Optical reconstruction, `BAD_DUMP`. After manual review all pixels are *verified* by the owner's confirmations, but 45 glyphs were LOW confidence before review. Codes 0x10-0x1F are blank by observation, not by dump. Rows 8-15 (5x10 mode) are zero. Ordinary letters with descenders do not use the eighth row; the cursor and ten symbol codes do (`CGROM.md`).
* It is unproven that the Genio's LCD controller is an HD44780 clone; the commands used so far behave like one.

## Keyboard
* All 39 activity-panel positions and 55 of 56 main-key positions were measured on the real unit (T4) and equal the table; ON is a separate contact (not readable). SHIFT-left/right are one contact (HW). Key combinations were not measured usefully. PC key choices are conventions.
* BASIC-editor behaviour of the special keys was observed on hardware (T5) and matches MAME; the same keys inside activities, SHIFT+ALT and ALT+symbols were not tried.
* The firmware column of `KEYBOARD.md` uses the 0x0415/0x03AD tables extracted by earlier sessions; the CAPS, CAPS+SHIFT and ALT tables were not re-verified.

## Firmware
* The dump is 128 KiB with 8 distinct banks; the physical capacity of the chip is a hypothesis (content coherent); banks 2 and 3 are unexplained high-entropy data (compressed?).
* The ROM region is 512 KiB (32 x 16 KiB) because the shared banking code configures 32 entries; the capacity of the real chip is not confirmed (the dump is 128 KiB). Mirroring reproduces what was measured for selectors 0x00-0x1F of port 0x01 only.
* The regression baseline in the tests is an earlier MAME commit of the same driver; no software list for Genio cartridges exists (`gl2000`/`misterx` lists are inherited from `gl4000`).

## Process
* The automated tests contain no hardware comparison. The hardware-vs-emulator evidence is in `logs/timing/` and `logs/hardware/` (one unit, analysed by scripts). Statements marked EMU are consistency checks of the emulated firmware, not proofs about the unit.
