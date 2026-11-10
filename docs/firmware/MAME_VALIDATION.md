# MAME_VALIDATION

Binary used: MAME with the `genio2000` driver, private ROM 27-5575-00, reconstructed CGROM (BAD_DUMP). Everything marked EMU comes from there.

| Topic | MAME/EMU | ROM / HW | Result |
|---|---|---|---|
| Bank map | `OUT 01h` -> `&0x1F`, entries >= 8 mirror (`n&7`) | HW: selector&7 up to 0x1F | matches |
| Port 0x03 | `bit7 ? d&0x8F : d&0x1F` | firmware only writes 00,01,03,04,06,80,81 (EMU: 00,03,04,06,80) | no conflict; the connector only exposes A14-A16 (3 page bits) -> bit 3 of `&0x8F` probably not wired (HYPOTHESIS) |
| Port 0x00 | write only | the firmware never touches it | no conflict |
| Ports 0x02/04/05/06 | not modelled (0x06 warns of an unmapped write) | written only at reset (CONFIRMED) | the model is not needed to boot |
| ISR | *invented* 50 Hz timer (configurable IRQ in the development branch) | real source unknown | not validated |
| LCD | HD44780 4x20 with its own map | the ROM's DDRAM table (07EE) matches the map used (project tests); anomaly row1/col0=`A8` | **still to check** that MAME reproduces `A8` and what is seen on HW |
| Cartridge | `-cart` at 8000-BFFF | `YE` start verified in EMU with `hello_api.s` | OK in EMU; without LCD init the LCD stays half-initialised (consistent with real HW? **not measured**) |
| Keyboard | tables verified against the firmware (earlier project) | - | OK |

Possible improvements suggested by these findings (not implemented): (1) document that the normal start-up initialises the LCD *after* the cartridge probe; (2) do not model 0x06 without evidence; (3) perhaps limit the cartridge page to 3 bits if the wiring is confirmed.

## Comparison with HW (2026-11-10, `hwtest`)
* CPU clock 6.10 MHz measured, about the 6.13179 MHz of the driver (consistent).
* **IRQ: 46.76 Hz on HW versus the 50 Hz timer of the driver** (7 % difference; about clock/2^17). The automatic switch-off (`0xBA54` ticks) goes from 15.9 min to about 17 min.
* `HALT` switches the real unit off; MAME treats it as a CPU stop (`power_off()`), consistent.
* Port 03 sees the same 8 banks as port 01 on HW (`sel & 7`).
* The HW RAM does **not** start at zero (pattern `70 C1 07 1C`); MAME sets it to zero (`power_on()` and start-up): a simplification of the model.
* `IN 0x11` at rest = `5F` on HW versus `1F` in MAME (bit 6).
* RAM mirrored at E000-FFFF on HW (read); MAME does not model it.
* MAME's cartridge page mask (`&0x8F`): with the 32 KiB EEPROM of the RevD board only bit 1 changes the content; not conclusive (depends on the wiring of A14).
