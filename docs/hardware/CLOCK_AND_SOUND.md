# CPU clock and sound – what is known, measured and unknown

**What is known about the CPU clock of the Genio 2000 (corrected in the PR 1-3 review)**

| Item | Status |
|---|---|
| Frequency actually measured | **6.13179 MHz** (HW), read with the hardware frequency counter of an oscilloscope (Rigol DS1052E), §5.9. The scope's automatic reading on the same pin wandered between 6.098 and 6.173 MHz. |
| Where it was measured | **Pin 6 (CLK) of the Zilog Z84C0006PEC**, i.e. at the CPU, not at an oscillator or crystal. |
| Physical oscillator | **Not identified.** No crystal or resonator is visible on the component side. The value is 0.2 % from 6.144 MHz, so a plain 6.144 MHz crystal is unlikely (HYP). |
| Uncertainty and stability | **Not determined**: one unit, one session, one instrument; no calibration, no repeat with another supply (batteries / adapter), no warm-up or temperature study. |
| In MAME | `genio2000` uses `set_clock(6'131'790)`: a plain number, deliberately not an `XTAL()`, because no physical oscillator is identified. |

The `gl4000` driver uses 4 MHz ("probably not accurate"). The recordings and videos of the real unit (§5.1-5.3) are an indirect check: 4 MHz / 50 Hz does not reproduce its timings and about 6 MHz of effective speed does. The earlier wording of this file ("not confirmed by any electrical measurement") predates §5.9 and is superseded; the hypotheses of §5.5 were written before that measurement and are kept for the record.

**Sound in PR 1-3 versus PR 7.** PR 1-3 still use the generic `beep` device inherited from `gl4000` (a fixed 3250 Hz carrier gated by bit 3 of port 0x12), so the audible pitch of the emulated melody is *not* faithful in those PRs. The pitch and onset comparison of §5.1 and §5.9 was made with the 1-bit speaker model of PR 7 (the audio captures come from the `genio2000-dev` build). What does not depend on the audio model, and therefore also holds for PR 1-3, are the CPU-bound timings derived from the port 0x12 writes and from the boot events (title pause, melody span, farewell sound), which depend on the CPU clock only.

## 1. Separate quantities
| Quantity | Status |
|---|---|
| CPU clock | **HW: 6.13179 MHz measured on pin 6 (CLK) of the CPU** (§5.9; hardware counter, one session). The CPU is a **Zilog Z84C0006PEC, rated 6 MHz** (a rating, not the clock) |
| Physical oscillator | **UNK**: no crystal is visible on the component side; it may be built from the custom chip plus discrete parts. Stability and uncertainty of the measurement are not determined |
| Interrupt rate (IM 1) | **46.76 Hz measured on the unit** (HW, 2026-11-10, see §5.10); the PR series uses it from PR 3, the rest of the `gl4000` family keeps 50 Hz |
| Sound generator | **There is no sound chip in the model**: the firmware toggles bit 3 of port 0x12 itself (FW + EMU trace). Pitch is made by software timing loops, so *pitch, note length and tempo all come from CPU speed and interrupt load*, not from a separate oscillator. Emulation: PR 1-3 use the generic gated 3250 Hz beeper (pitch not faithful); the 1-bit speaker arrives in PR 7 |
| Firmware timing | note length = number of loop passes (software); other timeouts unexamined |
| Global emulation speed (`-speed`) | scales *everything* (including the 50 Hz interrupt) uniformly; not a substitute for the clock option |
| Rhythm vs pitch | in this firmware they are tied: both are `loop cycles / clock` |

## 2. Firmware facts (static + traced)
* Tone routine at bank 0 `0x1364` (`tools/dis.sh 0 1364 40`): inputs `DE` = number of periods, `HL` = half-period delay count. Each period writes port 0x12 twice (`0x08/0x28` then `0x00/0x20`; bit 5 keeps the caps LED) and calls the delay loop `0x138F` (`dec hl / ld a,h / or l / jr nz` = 26 T-states per count).
  Counted from the Z80 timings, one period is `256 + 52·HL` T-states, so the nominal frequency is `clock / (256 + 52·HL)`.
* Eight note stubs at `0x12F8…0x1337` set `HL = 218, 194, 172, 162, 144, 128, 114, 107` and `DE = 0x153…0x1A7`, with `DE x HL` ~constant (all notes last the same): a major scale (ratios 1.12, 1.27, 1.35, 1.51, 1.70, 1.91). At 4 MHz nominal 345, 387, 435, 461, 517, 579, 647 Hz.
* Boot melody in MAME (4 MHz): 5 notes 305.5, 387.1, 460.2, 407.2, 387.1 Hz, ~0.27 s each (`tests/lua/port12_log.lua` + `tools/analyze_p12.py`).
* Interrupts are enabled (`IFF1 = 1`) while notes play: the 50 Hz ISR runs inside the tone loop.

## 3. Measurements in MAME with the experimental `CLOCK` option (EMU)
Note of 104 periods (HL = 194), speed relative to 4 MHz (`CLOCK` index 9), `tests/test_genio2000.py::test_clock_switch_follows_effective_clock_model`:

| clock (MHz) | 3.0 | 3.5795 | 4.1943 | 4.9152 | 5.0 | 6.0 | 6.144 | 8.0 |
|---|---|---|---|---|---|---|---|---|
| measured speed | 0.714 | 0.880 | 1.058 | 1.261 | 1.283 | 1.567 | 1.590 | 2.127 |
| clock / 4 MHz | 0.750 | 0.895 | 1.049 | 1.229 | 1.250 | 1.500 | 1.536 | 2.000 |

Pitch and duration move together (one number). The data are linear in *(clock − S)* with **S ≈ 0.476·10^6 cycles/s** (~9.5 k T-states per 50 Hz interrupt): *effective clock = clock − irq_rate x ISR_cycles*. Consequences (model fitted to the emulator, interpretation HYP):
* A recording of the real unit measures only the **effective** clock; it cannot separate crystal frequency from interrupt rate. Both must be established independently (oscillator photo/measurement, and a measurement of the interrupt-driven behaviour such as the LED/key-scan period).
* `-speed 1.5` multiplies the interrupt rate too, so it is not equivalent to a 6 MHz CPU (6 MHz gives 1.567, -speed 1.5 gives 1.5 with all timing scaled).
* 4 -> 6 MHz is a ratio of 1.5 = 701.96 cents, 1.96 cents from an equal-tempered fifth: the *musical* intervals of the boot tune and any 12-TET grid cannot discriminate 4 from 6 MHz (nor 3 from 4.5). Only absolute duration/pitch against a recording can.

## 4. How to repeat the comparisons (experimental branch, no recompilation)
```bash
tools/timing_matrix.sh logs/timing/emulation          # boot + power-off at 4/6/6.144/6.13179 MHz and IRQ 40/50/60 Hz, same firmware/CGROM/scenarios
tools/timing_run.sh boot 9 0 work/timing_x            # one run: <boot|off> <CLOCK idx> <IRQ idx> <outdir>   (CLOCK 0 = 6.13179 MHz driver default, 9 = 4.0, 6 = 6.0, 7 = 6.144 MHz; IRQ 0=50 1=40 4=60 Hz)
tools/set_cfg.py <cfg_dir> CLOCK=9 IRQ=0               # options for a hand-made run; indices: CLOCK 0=6.13179 (default) 1=3.0 2=3.579545 3=4.194304 4=4.9152 5=5.0 6=6.0 7=6.144 8=8.0 9=4.0 MHz
tools/record_sound.sh out.wav CLOCK=9                  # emulator capture (the speaker is always the 1-bit model since PR 7); tools/record_t1.sh records the real unit with the default microphone
tools/wav_compare.py emulator.wav recording.wav        # note onsets, time scale and spectral-peak ratios
```
Numbering note: until 2026-11-09 the CLOCK index 0 was 4 MHz and 9 was 6.13179 MHz; after the series was rebased on the new driver (whose default is the measured clock) they were swapped. File names under `logs/timing/` carry the frequency, not the index.
The same options are in the MAME UI of the `genio2000-dev` build (Scroll Lock toggles UI mode, then Tab > Machine Configuration). The speaker is the 1-bit model that follows port 0x12 bit 3 (PR 7); the old gated 3250 Hz beeper is no longer audible on this machine. Raw logs, scripts and commands of the 2026-11-09 comparison: `logs/timing/README.md`.

## 5. Measurements on the real unit (2026-11-09) – T1, T2, T8

Everything in this section is **HW** (phone recordings and videos of one physical unit) compared with **EMU** (MAME) numbers; raw material, scripts, commands and hashes are in
`logs/timing/` (start with `logs/timing/README.md`). The HW and EMU numbers share one machine, one firmware image and one measuring method; the three recordings and the two videos are
**not** independent measurements of the clock, and no statistical independence is claimed. Nothing in this section is an electrical measurement of the crystal or of /INT (the electrical reading of the CLK pin is §5.9).

### 5.1 Boot melody (audio, T1)
Real recordings vs the emulator capture of the same melody (note onsets aligned by least squares; per-note Welch spectral peak; `tools/wav_compare.py`, `logs/timing/audio/results/wav_compare.txt`):

| Recording (real) | Notes used | Time scale real/MAME 4 MHz | Speed ratio | vs MAME 6 MHz |
|---|---|---|---|---|
| batteries, take 1 | 10 | 0.648 | x1.54 | 0.994 (x1.006) |
| batteries, take 2 | 10 | 0.648 | x1.54 | 0.994 |
| mains adapter | 7 (fewer usable notes) | 0.634 | x1.58 | 0.970 |

* Pitch (spectral-peak ratio, median of matched notes): 1.52-1.53 vs 4 MHz, 1.02 vs 6 MHz. Pitch and tempo scale by a similar factor (about x1.53), as expected when only the execution speed of the software tone loop changes.
* The two battery takes give identical onsets because the firmware is deterministic: this shows repeatability of the measurement, not independent confirmation. The adapter take has fewer usable notes; its slightly larger ratio (x1.58) is within what that sample can resolve, and no battery-vs-adapter difference is claimed.
* The recordings named `t1_ok_*` / `t1_fail_*` are not boot-melody takes: they are the T3 right/wrong-answer sounds (SUMA / PLURALES), kept as `t3_ok_*` / `t3_fail_*` in `logs/timing/audio/real/`; they are not used above and are not analysed yet.
* Outlier notes in the spectral-peak lists (1.38-2.1) are octave/harmonic errors of the peak picker on microphone audio; only the median is quoted.

### 5.2 Boot sequence (video, T2)
Event times were read by eye from the 60 fps video (`logs/timing/video/events.csv`, frames in `logs/timing/video/frames/`); EMU values come from `logs/timing/emulation/*/summary.json`:

| Quantity | MAME 4 MHz / 50 Hz | MAME 6 MHz / 50 Hz | Real unit |
|---|---|---|---|
| title screen visible -> first character of "¡Hola!" | 4.38 s | 2.81 s | 2.68 s (+-0.05, see 5) |
| boot melody span | 4.15 s | 2.65 s | 2.67 s (audible run in the video) |
| welcome text typing ("¡" -> last "d" of "actividad") | 5.12 s | 5.12 s | 5.45 s (+-0.05, see 5) |

### 5.3 Power-off (video, T8)
Real: farewell sound from 2.02 s to 4.40 s of the video (2.38 s); "¡HASTA LUEGO!" visible from ~2.08 s, screen dark at ~4.58 s (message on screen ~2.5 s). The key press itself is not visible in the video.
MAME (OFF pressed at 20.0 s; span from the first port-0x12 write to `OUT (12h),01`): 3.78 s at 4 MHz, 2.52 s at 6 MHz, 2.46 s at 6.144 MHz. The EMU span and the audible run of the video are defined differently (the latter cuts the quiet ends), so a ~5 % difference is within what the definitions allow.

### 5.4 Two timing mechanisms
* **Delays tied to Z80 instruction execution** (the tone loop at 0x1364 and the pause between the title and the welcome text): in MAME they scale with the emulated CPU clock (title -> "¡" 4.38 s -> 2.81 s; farewell sound 3.78 s -> 2.52 s; melody 4.15 s -> 2.65 s).
* **Delays counted in periodic-interrupt ticks** (the welcome-text typing): in MAME the span is 256.1 ticks at every CPU clock (5.12 s at 50 Hz regardless of 4 or 6 MHz; 6.40 s at 40 Hz; 4.27 s at 60 Hz: span x rate = 256.1, `logs/timing/emulation/summary.csv`). The farewell sound is CPU-bound and does not depend on the interrupt rate in MAME (2.523 s at 40/50/60 Hz), while the boot melody depends on it slightly (2.61 / 2.66 / 2.72 s) because the interrupt service steals cycles from the tone loop.
These two mechanisms are what lets a video separate the two quantities that an audio recording alone cannot.

### 5.4b Earlier hardware evidence found in the project: the software serial port (HW, previous sessions, not re-run here)
an earlier serial-test cartridge and the documentation of the dumper repository (https://github.com/kresp0/vtech-genio2000-rom-dumper) record that the project's soft-UART transmitter (printer port DATA0, one bit = `110 + 16*H + 13*F` T-states) worked on this unit only above a certain speed setting: with **T642** (6.16 MHz implied if the line is exactly 9600 baud) the firmware dump arrived as 256/256 verified blocks with 0 line errors, while **T603** (5.79 MHz implied) corrupted 0x00 bytes. A receiver tolerates only a few percent of baud error, so the unit's CPU runs at roughly **6.0-6.5 MHz** (the exact window depends on the tolerance of the CP2102 receiver, not measured). This is independent of the audio/video comparison (a different mechanism: instruction counts against a known baud rate) and supports it, but it is still an indirect measurement: the Z80 clock pin itself has not been measured.

### 5.5 What the data support, and what they do not
Supported by the measurements (HW vs EMU):
* The MAME configuration of the `gl4000` family (4 MHz CPU, 50 Hz interrupt) **does not reproduce** the timings of the real unit: its melody, title pause and farewell sound are ~1.5-1.6 times too slow.
* With the emulated CPU at 6 MHz (interrupt 50 Hz) the CPU-bound quantities agree with the real unit within about 1-6 % (speed ratios real/MAME-6 MHz: melody onsets 1.006, melody span 0.99, title pause 1.05, farewell sound 1.06).

Hypotheses (HYP, not confirmed by any electrical measurement):
* The real CPU is probably close to 6 MHz. The statement is about effective execution speed; a crystal and a divider that give a different CPU clock with other interrupt costs are not excluded. These audio/video measurements alone do not prove a 6 MHz CPU; the direct reading of the CLK pin (§5.9, 6.13179 MHz) was taken afterwards and is the value the driver uses.
* (Superseded by §5.10: the rate is 46.76 Hz.) The periodic interrupt is probably close to 50 Hz, but the typing span of 5.45 s corresponds to about 47 Hz if the firmware uses 256 ticks, i.e. ~6 % below 50 Hz (46-48 Hz for +-0.05 s per edge). This single measurement is not explained: LCD latency, a different tick count on the real unit or a real interrupt rate of 47 Hz are all possible.
* The ~1-6 % spread between the CPU-bound quantities is not explained either.

### 5.6 Uncertainties and resolution limits
* Frame step 1/60 s; the LCD fade-in/fade-out latency (~0.1-0.2 s) was not measured and is included in every "visible" time. Intervals between two "appears" events partly cancel it; intervals involving the audio track do not.
* The power key press and the real power-on instant are not visible; only intervals are used.
* Audio-run thresholds cut the quiet ends of notes; MAME spans are write-to-write; recorder gain/speed and microphone response are uncalibrated (only ratios are used).
* One unit, one phone, one camera, one room. Earlier chat messages of this project quoted ~3.05 s and ~5.0 s for the real pause and typing span; they came from a crop that hid the first LCD line and are superseded by 2.68 s and 5.45 s.

### 5.7 What would change or settle the conclusion
Photo of the crystal/oscillator and CPU markings (`PHOTOS_TODO.md`) and T7 (crystal and /INT with an instrument). After either, repeat: `tools/timing_matrix.sh`, `tools/wav_compare.py`, `tools/timing_derived.py` with the measured CPU clock and interrupt rate (add them to the `CLOCK`/`IRQ` option tables if they are not listed).

### 5.8 Measuring the clock with a multimeter (2026-11-09, owner's Fluke 79III)
Probing the Z84C0006 with the meter's Hz function gave 49.95 Hz for a few ms and then 0 on **both** pin 6 (CLK) and pin 16 (/INT): the same 49.95 Hz on two unrelated pins is **mains pickup** by the high-impedance input (no ground reference connected), not a signal; and the meter's counter tops out near 200 kHz, far below a 4-6 MHz clock, so a 0 on pin 6 is expected. The CPU clock cannot be read with this meter. A usable indirect method with the same meter: run the project's soft-UART cartridge sending 0x55 continuously (`dev/serial_test_gl2000`, `S` mode): DATA0 (DB25 pin 2, ground on pin 18-25) is then a square wave of frequency `f = clock / (2 x T_bit)` = clock / 1284 for H30 F4 (T642), i.e. ~4.7-4.8 kHz, well inside the meter's range, giving `clock = f x 1284` to 0.1 % if the loop is not disturbed by interrupts (the program disables them; the figure is the *instruction* clock, which is what matters for the firmware timing).

### 5.9 Oscilloscope measurement of the Z84C0006 pins (2026-11-09, owner's Rigol DS1052E; HW, first reading)
* **Pin 6 (CLK): 6.098 to 6.173 MHz** read off the scope's automatic measurement, fluctuating between those values (centre ~6.135 MHz, spread ~1.2 %). This is the first direct measurement of the CPU clock, taken at the CPU pin and not at an oscillator: it agrees with the 6 MHz rating of the part, with the soft-UART evidence (§5.4b, 6.0-6.5 MHz) and with the audio/video comparison (§5.1-5.3), and the emulator option `CLOCK` = 6.144 MHz (index 7) is within the observed range. The spread is too large for the clock of a quartz crystal, but the automatic reading of a scope fluctuates on its own: the stability has **not** been established yet (to do: the DS1052E hardware counter, longer record, batteries vs adapter).
* **Pin 6 with the scope's hardware frequency counter: 6.13179 MHz** (owner, same day). This is the figure to use. It is 0.2 % below 6.144 MHz (a standard crystal value), more than a crystal's tolerance would explain, so the oscillator is probably not a plain 6.144 MHz crystal (HYP; stability over time and with the supply still not recorded).
* **Emulator at the measured clock** (the driver default, `CLOCK` index 0 = 6.13179 MHz, IRQ 50 Hz, same scenarios; `logs/timing/emulation/{boot,off}_clk6.13179MHz_irq50Hz`, `logs/timing/audio/emulation/boot_6.13179MHz_irq50.wav`): boot melody onset time scale real/MAME = **1.000** for both battery recordings (0.994 adapter), spectral-peak ratio 1.00 (it was 1.52 at 4 MHz and 1.02 at 6.000 MHz); title pause 2.75 s (real 2.68), melody span 2.59 s (2.67), farewell sound 2.47 s (2.38), i.e. the CPU-bound timings agree with the video within 3-4 %, which is the resolution of the video readings (+-0.05-0.1 s). The interrupt-paced welcome typing is unchanged by the clock: 5.12 s in MAME vs 5.45 s on the unit (the /INT rate is still unmeasured).
* **Pin 16 (/INT): no oscillation seen** in the first look. Not conclusive: pulses of a few microseconds are missed at 5 ms/div unless Peak Detect is on, and the interrupt may only be active in some states (the firmware paces the welcome typing by interrupt ticks, so it must be active then). Open.

## 6. Experimental configuration for timing studies (branch `genio2000-dev` only)
Options `CLOCK` (3 ... 8 MHz, default 6.13179, 4.000 kept for comparisons), `IRQ` (periodic interrupt 40/45/50/55/60/75/100 Hz, default 50 = unchanged behaviour: the default boot log is byte-identical to the previous build) (the old `SOUND` and `LCD` options were removed: the 1-bit speaker and the photographed LCD drawing are now the machine's behaviour, PRs 7 and 4).
They are set per run with `tools/set_cfg.py` (see `tools/timing_run.sh`, `tools/timing_matrix.sh`) or in the MAME UI (Tab > Machine Configuration; Tab is only the UI key after Scroll Lock toggles to the UI mode). `-speed` is not used: it also scales the interrupt rate.
The PR series (`UPSTREAM_PLAN.md`) contains none of these options: PR 1 sets the CPU clock of `genio2000` to the measured 6.13179 MHz and PR 3 sets the measured 46.76 Hz interrupt; the options exist only on `genio2000-dev`, where index 0 is that same default and index 9 keeps 4.000 MHz for comparisons.

### 5.10 Measurements with the `hwtest` test cartridge (HW, 2026-11-10, unit 1)
Source: `docs/firmware/HW_RESULTS_20261110.md` (#1, #14, #19). The cartridge counts events and reports over the printer port, with the unit's own firmware running.
* **Interrupt rate: 46.76 Hz.** 1000 interrupts in 21.39 s with the firmware ISR running and a counting hook; the firmware's own tick counter (`DB28/29`) matches the hook exactly, so every interrupt was counted. 46.76 Hz is 6.13179 MHz / 2^17 (46.78 Hz) within 0.05 %: the interrupt appears to come from the CPU clock divided by 131 072 (HYPOTHESIS, the divider is not seen). The earlier video estimate (about 47 Hz from the welcome-text typing, 5.45 s) is consistent with it, so the 6 % discrepancy with the emulator's 50 Hz was the emulator's, not the video's. PR 3 sets 46.76 Hz and `MACHINE_IMPERFECT_TIMING` is dropped; the automatic switch-off (`0xBA54` ticks) goes from about 15.9 to about 17 minutes.
* **CPU clock by bursts: 6.101 MHz** (precision about 1 %), −0.5 % against the 6.13179 MHz of the oscilloscope counter. It is compatible, but the method has its own bias (the same run gives 6.10 MHz again), so it is a second measurement on the same unit, not an independent confirmation of the oscillator frequency; with the 46.76 Hz interrupt the two clock estimates agree within 0.5 %.
* **`HALT` switches the real unit off** (the firmware's only `HALT` is in its farewell); the emulation's `power_off()` stops the CPU, which is consistent.
