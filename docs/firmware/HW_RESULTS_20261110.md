# HW_RESULTS_20261110: first measurements of the `hwtest` cartridge on the real unit

Unit: the one of the reference ROM (the CRC-32 of internal banks 1, 2, 3 and 7 match **unit 1**, not unit 2; see ROM_REVISIONS). Capture: two boots in the same capture: the first did A, B and C and switched off in D; the second skipped A-D and did F. Evidence: **HW** unless stated otherwise. Earlier captures of the same day only have a partial stage A; the folders before them are empty (cable problem).

| # | Result | Detail | Status |
|---|---|---|---|
| 1 | **CPU clock about 6.10 MHz** | 6.101 MHz measured with bursts (precision about 1 %), against 6.13179 MHz of the oscilloscope counter (`docs/hardware/CLOCK_AND_SOUND.md`): -0.5 %, compatible | HW |
| 2 | **Port 03, internal entries** | selectors `00..1F` -> bank = `sel & 7` (bits 3 and 4 ignored); `20` and `40` -> bank 0 (bits 5 and 6 ignored). The CRCs of the 8 banks match the reference ROM: **port 03 sees the same 8 banks as 01** (until now EMU only) | HW (CONFIRMED) |
| 3 | **Port 03, cartridge pages** (`80..8F`, `90`, `A0`, `C0`) | with the 32 KiB EEPROM only **bit 1** of the selector changes the content (quarters 0/1 <-> 2/3: A14 of the EEPROM); bits 0, 2, 3, 4, 5 and 6 do **not** produce a change. A13 reaches the EEPROM (the two 8 KiB of the window differ). **Caution:** it depends on which line of the connector feeds A14 on **this** board (RevD); it does not prove by itself the machine's decoding nor that MAME (`&0x8F`, 16 KiB pages by bit 0) is wrong | HW (data) / HYPOTHESIS (interpretation) |
| 4 | **RAM mirrored at E000-FFFF** | 61/64 blocks identical to their pair at C000-DFFF (the other 3 contain variables that changed during the copy). Read only; nothing was written | HW |
| 5 | **State on cartridge entry (YE)** | `LD A,I` -> IFF2 = 0 (interrupts **disabled**); `DFF0..DFF7 = 14 00 00 80 14 33 00 00`: port 03 shadow = `80` ok, port 01 shadow = `00`, `DFF4 = 14`, **ISR hook `DFF5/6 = 0033` = `RET` at `B0:0033`** (default hook with no effect) | HW |
| 6 | **RAM is not zero when a cartridge starts** | 72 % of the 4-byte words of C000-DFFF are `70 C1 07 1C`; `DCA0` holds the title text (which the flow draws *after* the cartridge probe): PROBABLE leftover from an earlier start (RAM survives a restart/short power-off). A cold start only initialises specific variables (`B0:0FAA...`). MAME sets the RAM to zero | HW (data) / UNKNOWN (origin of the pattern). Nuance for the `power_on()` comment in MAME: "clears the RAM" is a simplification of the model |
| 7 | **`IN` ports** | `0x11` at rest = `5F` (MAME: `1F`; bit 6 is 1, function unknown) and `0x12` = `16`; `0x10` = `FF`. Ports `0x11` and `0x12` repeat identically at `+0x20*k` (**A5-A7 are not decoded**). The other ports have no device: they return the last byte on the bus (often the port number itself, with bits set), 0x00-0x09 give `FF`. `0x0A/0x0B` were not read | HW |
| 8 | **LCD: CGRAM is read "live"** | answers 1-5 = S (yes): rewriting the CGRAM changes **all** cells; there are only 8 distinct glyphs at a time; `08-0F` mirror `00-07` | HW (human observation) |
| 9 | **LED = bit 5 of `0x12`** | the LED blinked 3 times (the user confirms it; the answer was recorded as `N` by mistake (it was actually yes)) | HW (human observation) |
| 10 | **`/WR` probe (K)** | no write-cycle signals on the EEPROM; content intact. Says nothing about the connector | HW |
| 11 | **Stage D v1 (EI + HALT): the unit switched off** | see batch 2 (#14): the cause is `HALT` | HW |
| 13 | **ON is separate and restarts** | the user checks it physically: pressing ON restarts the unit and the cartridge starts again at stage A | HW (human observation) |
| 12 | Banks 1/2/3/7 | the unit tested is unit 1 | HW |

## Batch 2 (2026-11-10 20:05): stage D v2, E, L
| # | Result | Detail | Status |
|---|---|---|---|
| 14 | **IRQ frequency about 46.76 Hz** | 1,000 interrupts in 21.39 s with the firmware ISR running and an own hook at `DFF5` that counts (no `HALT`). The firmware's own counter **`DB28/29` matches exactly** the hook (1, 5, 20, 100, 1100): every IRQ was counted. 46.76 Hz = 6.13179 MHz / 2^17 (46.78 Hz) within 0.05 %: **the IRQ appears to come from the CPU clock divided by 131,072** | HW (measured) / HYPOTHESIS (divisor) |
| 15 | **`HALT` switches the unit off** | the ISR ran 1,100 times without switching it off; v1 only differed in `HALT` (and in not counting). The only `HALT` of the firmware: the farewell (`B0:018B`, after `OUT (12),01`). Examples and own cartridges **must not use `HALT`** (the project's `hello_api` and the FIRMWARE_API example used it; fixed) | HW (by difference between v1 and v2) |
| 16 | `DB28/29` = ISR tick counter; during the test `DB00 = D0` and `DB01 = F9` (at rest `C0`/`B4`); `DB26/27` stays at 0 (with `DB00 = D0` the ISR clears it on every IRQ) | HW |
| 17 | Stage E repeated: answers 1-6 all **S (yes)** (LED included) | HW |
| 18 | Stage L repeated: `20 = 40 =` bank 0; `90 = A0 = C0 =` cartridge page 0 | HW |
| 19 | Stage C repeated: 6.101 MHz again (same bias of the method: the IRQ and the oscilloscope give 6.13 MHz) | HW |

## Pending from this batch
F (keyboard matrix and position of ON) was not captured; the photographs of G (4 screens of the character set) are not in the folder; E3 (GA variant) and the run on unit 2 have not been done.
