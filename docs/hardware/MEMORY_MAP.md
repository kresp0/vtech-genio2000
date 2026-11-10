# Memory map as implemented by `genio2000` (derived from `gl4000`)

| CPU address | Device | Notes | Class |
|---|---|---|---|
| 0x0000-0x3FFF | `bank0`, ROM entry selected by port 0x00 | MAME resets it to entry 0 and the firmware never writes port 0x00 → fixed bank 0 (core: reset, IM 1, keyboard, LCD helpers) | FW |
| 0x4000-0x7FFF | `bank1`, ROM entry selected by port 0x01 (`data & 0x1F`) | selectors 0-31 → bank `n & 7` | HW |
| 0x8000-0xBFFF | `bank2`, port 0x03: `data & 0x80` → cartridge page `data & 0x8F`, else internal entry `data & 0x1F` | values seen: 00 01 03 04 06 80 81 (decoding of bits 5-6 and 4 unproven) | FW / EMU |
| 0xC000-0xDFFF | RAM 8 KiB | not battery backed as far as known; mirrored at 0xE000-0xFFFF (HW read, not modelled); not zero after a restart: most words read `70 C1 07 1C` (HW); the emulation clears it | FW / HW |
| 0xE000-0xFFFF | unmapped (reads 0xFF, `unmap_value_high`) | | EMU |

## How the 128 KiB is represented (no commercial data in the source)
`ROM_REGION(0x80000, "bios")` has 32 entries of 16 KiB (what `gl4004_state::machine_start` configures for banks 0-0x1F).
`ROM_LOAD("27-5575-00", 0, 0x20000)` followed by three `ROM_RELOAD` makes entry *n* equal to bank *n & 7*, i.e. exactly the mirroring that
was measured on the unit for port 0x01. This region size is a **MAME internal requirement of the shared banking code**, not a statement about the chip:
what was obtained is a dump of 131072 bytes with 8 distinct 16 KiB banks, repeated in the address space (bank = selector & 7 for selectors 0x00-0x1F). This shows how much firmware is reachable with the extraction procedure, not the exact physical capacity of the LH531H7H, which is not confirmed. Test: `test_bank_mirroring_matches_hardware_observation` compares all 32 entries with the file.

## What is NOT known
* Behaviour of bits 5-7 of the port 0x01 selector (never written by firmware or dumps; the 0x00-0x1F measurement covers bits 0-4).
* Ports 0x00 and 0x03 on the real unit were never written by the dump programs; the model is MAME's inherited one (FW).
* Cartridge bank decoding for pages > 1; cartridges of 2 pages are the only ones inspected.
