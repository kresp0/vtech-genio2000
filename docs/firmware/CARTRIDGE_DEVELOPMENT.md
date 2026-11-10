# CARTRIDGE_DEVELOPMENT: what can be built

## Minimum demonstrable requirements (ROM + bus)
1. ROM visible at 8000-BFFF with `55 AA 59 45` at 8000-8003 and code from 8004 -> direct start at power-on (CONFIRMED in firmware; it matches VGLDK and the test cartridges already used on the unit, HW).
2. To appear in the menu: `55 AA 47 41` (machine code) or `55 AA 11` (data). A cartridge that wants both modes needs two signatures that are **incompatible in the 3rd position** (`59` != `47`): one has to be chosen, or the content of 8002-8003 switched depending on the moment (for example by reading with a latch/access counter): HYPOTHESIS.
3. Useful entry points when returning: `JP 0030` (menu), see FIRMWARE_API.

## Capabilities according to the evidence
| Capability | Status | Note |
|---|---|---|
| Up to 128 KiB of ROM through pages | PROBABLE | A14-A16 driven by the system; only 80/81 used by the firmware, pages 2-7 **untested** |
| More than 128 KiB with an own latch | HYPOTHESIS | requires writing a register in the cartridge; `/WR` present; not verified whether the system generates the write |
| RAM in the cartridge | HYPOTHESIS | same dependence on `/WR`; the internal RAM (8 KiB at C000-DFFF) stays free for the program |
| Keyboard/LCD reading through the firmware API | CONFIRMED (code) | requires `EI` and the ISR to stay alive; see INTERRUPTS |
| Communication with an ESP32 | HYPOTHESIS | options: (a) bit-bang through the printer port (0x10 data, 0x11 BUSY, 0x12 STROBE; tested as a soft-UART TX on HW during the dump: 9600 8N1), (b) a register mapped in the cartridge space (read yes; write depends on E1) |

## Proposed architectures (from lowest to highest risk)
**A. Simple ROM cartridge (28/32 pins).** Parallel flash/EEPROM (for example the AT28C256 already used in the project, 32 KiB mirrored 4x for 8 KiB at `8000`). Essential: ROM + VCC/GND + /CE decoding by /RD and page selection. Low risk; tested on HW by the project itself.

**B. Development cartridge with execution RAM (RAM + CPLD/GAL).** Small ROM with a loader + SRAM at 8000-BFFF if `/WR` reaches it; the loader receives the program through the printer port ("monitor" mode). Depends on E1 (are writes to the cartridge generated?). Alternative without /WR: the loader copies the program to the internal RAM C000-DFFF (8 KiB) and jumps there (CONFIRMED feasible: RAM is free and the dumper already worked without extra banks).

**C. ESP32 as a "virtual ROM" on the bus.** The ESP32 presents data on the cartridge bus (D0-D7 with addresses A0-A13 + page): **not shown** to be possible because of timing: the unit's Z80 runs at an **unknown** frequency (6 MHz chip rating; measurements point to about 6.13 MHz), and ROM access requires roughly less than 300 ns according to a 6 MHz Z80 cycle; an ESP32 cannot answer like that through GPIO directly. Real intermediate ROM/SRAM is needed (architecture B/D). Marked as **not recommended without tests**.

**D. Dual-use SRAM loaded over Wi-Fi (recommended for the goal "load over Wi-Fi").** SRAM (>= 32 KiB) in the 8000-BFFF window with page selection + a loader in minimal ROM (`55 AA 59 45` + code). The ESP32 writes the SRAM while the Z80 is in reset/wait (or through a mux/74xx244/245 buffers with /BUSRQ not available, so the Z80 must be **kept from accessing** the cartridge meanwhile), then "releases" the SRAM to the bus. Essential: SRAM, 2 bidirectional buffers/address mux, /CE logic by /RD and page, an ESP32 control line (GPIO) for the mux, 5 V supply (the ESP32 runs at 3.3 V: level conversion). Open dependencies: E1 (whether writing from the Z80 is needed), existence of the /RST on contact 35 (function not confirmed) to restart after loading.

**E. Hybrid through the printer port.** ROM in the cartridge (>= 8 KiB) with a loader that receives a binary from the ESP32 over the DATA/BUSY line and runs it from the 8 KiB internal RAM. Essential: only ROM + a 25-pin connector to the ESP32. It is the path with **the most evidence** (the soft-UART TX worked on HW; RX would be missing, which depends on reading 0x11 bit 5 BUSY or 0x10; RX has not been tested on HW). It limits the program to 8 KiB of RAM.

## Electrical
No voltages/currents are claimed: there are no verified electrical measurements beyond +5 V on contact 34. Bus contention: the cartridge must tri-state D0-D7 when /RD is not active and the page is not its own (HYPOTHESIS of good practice; there is no data on the ASIC).

> **HW warning (2026-11-10):** do not use `HALT` in a cartridge. On the real unit `HALT` switched the unit off even with the firmware ISR healthy; to wait, use a loop (`jr $`) with `EI` if you need the interrupt refresh. The IRQ is about 46.8 Hz.
