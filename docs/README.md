# Documentation

| Folder | Contents |
|---|---|
| `hardware/` | The machine as measured: CPU, clock and interrupt rate, memory map, I/O ports, the printer port as a serial link, keyboard matrix and legends, character generator, known limitations |
| `firmware/` | Reverse engineering of the Spanish firmware: boot, ISR, BASIC, LCD, keyboard, cartridges, data formats, results of the hardware tests, the two known ROM revisions |
| `mame/` | Notes about the MAME driver: the plan for submitting it upstream, tests, the photographic layout |

Start with `hardware/HARDWARE.md`, then `firmware/README.md`. Every statement carries an evidence label (HW = measured on a unit, FW = read from the firmware, EMU = observed in MAME, PROBABLE / HYPOTHESIS / UNKNOWN), and the documents say which unit a measurement comes from.
