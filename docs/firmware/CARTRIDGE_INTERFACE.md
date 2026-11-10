# CARTRIDGE_INTERFACE

## Detection and start (all CONFIRMED in ROM bytes, `B0`)
| Situation | Code | Condition | Action |
|---|---|---|---|
| **Power-on** | `1010-1030` | `OUT (03),80` ; `(8000)=55, (8001)=AA, (8002)=59 'Y', (8003)=45 'E'` | `POP AF; JP 8004` (the cartridge takes control, **without going through the menu or the title screen**) |
| Power-on, no signature | `1033-1038` | any other byte | restores the previous `OUT (03)` (`DFF3`) and continues with the normal start-up |
| **CARTUCHOS ADICIONALES key** | `118E-11E3` | `OUT (03),80`; `(8000)=55, (8001)=AA` and `(8002)` ... | `(8002)=11` -> `DB2A=1; JP 27BD` (**data/educational** cartridge handled by the internal engine); `(8002)=47 'G'` and `(8003)=41 'A'` -> `DB2A=1; JP 8004` (**machine-code program**); otherwise -> message "Sin cartucho" (string `B0:144B`), `CALL 0098` (sound), `JP 10DC` (back to the menu) |
| No cartridge (EMU) | - | `OUT (03),80` reads whatever MAME returns | **Not verified**: two attempts to press CARTUCHOS ADICIONALES (14 s and 30 s emulated) coincided with the welcome screen still being typed ("¡Hol...") and never showed "Sin cartucho"; the welcome typing is slow and the key is not served until it ends (EMU) |

* The start-up and menu signatures **are different**: a VGLDK cartridge (`55 AA 59 45`) starts on its own at power-on but, if CARTUCHOS ADICIONALES is pressed, it is **rejected** (the menu asks for `11` or `'G','A'`). CONFIRMED in the bytes; not tested on hardware for that case.
* The menu routine sets `DB2A=1`: it tells the data readers (`B0:08E8...`) that the database is the cartridge (pages `0x80`+) instead of the internal ROM (entry 1+). CONFIRMED.
* The internal ROM banks 1 and 4 have a `55 AA` + `04 00`/`01 00` header (not `11`/`GA`/`YE`): they are a **data-cartridge format** housed inside the internal ROM (PROBABLE). Header: `+2` word (4 or 1), `+4` word (`7FFF`/`3FFF`), `+6` word (`1FFF`/`0FFF`), `+8...` table of words pointing to `80xx` (pointers within the data ROM itself). Meaning of the fields: UNKNOWN.

## Cartridge memory
* Window 8000-BFFF (16 KiB visible at a time). Page selection: `OUT (03h)` with bit 7 = 1; the firmware only uses pages `80`/`81` (and `DFF3+1` when crossing 0xC000 while reading data, so it can chain more pages).
* Connector (36 contacts; pinout and netlist of a HotKey Rev D board plus 7 measurements): lines **A0-A16** (contact 12 = A16, 17 = A14, 19 = A15), D0-D7, `/RD` (33), `/WR` (5), +5 V (34), GND (18, 32), X1-X4, X36, "/RST" (35); **there is no A17+**. Since the CPU window 8000-BFFF has A15=1, A14=0 fixed, to see more than 16 KiB the system must **drive A14/A15/A16 as page bits** (PROBABLE; bits 0-2 of `P_BANK2`). Hence **direct maximum about 128 KiB (8 pages)** (matches the commercial ROM 27-5585-00 of 131,072 B according to MAME; HYPOTHESIS about the real wiring).
* `/WR` is on the connector: a cartridge can register writes (RAM, own bank latch). Does the system generate `/WR` towards the cartridge for writes to 8000-BFFF? **UNKNOWN** (experiment E1 in UNRESOLVED_QUESTIONS).

## HW measurements (2026-11-10, `hwtest` with a 32 KiB AT28C256 EEPROM; HW_RESULTS_20261110)
* The `YE` start works: `IFF2=0` on entry, `DFF3=80`, `DFF4=14`, `DFF5/6=0033`. The `GA` (menu) and `11` variants have **not** been tested on HW.
* Port 03 selector with bit 7 = 1: with that EEPROM **only bit 1 changes the content** (A14 of that board; A13 arrives correctly); bits 0, 2, 3, 4, 5, 6 produce no visible change. It cannot be used to say anything about the machine's page decoding without the schematic of the RevD board; the hypothesis "bits 0-2 = A14-A16" above is **not** confirmed (bit 0 does not move A14 on that board).
* An idempotent write to 8000-BFFF (same byte, from RAM) did **not** cause a write cycle in the EEPROM (stage K): it does not prove that `/WR` does not reach the connector (the `/WE` of that board may not be connected). The BASIC `LOAD/SAVE` code writes and reads back `8000-8002` (a cartridge with RAM, see HIDDEN_FEATURES), so the system does generate writes towards that window (PROBABLE, code reading).
* **Do not use `HALT`** in a cartridge: it switches the unit off (INTERRUPTS).
* ON restarts the unit and the cartridge starts again from zero.

## Leaving a cartridge to the menu
`JP 0030` (RST 30h) -> `11E6`: soft restart (CONFIRMED in the bytes; not tested in EMU with a cartridge). A `GA`/`YE` cartridge has no documented "clean" return other than that jump or restarting.
