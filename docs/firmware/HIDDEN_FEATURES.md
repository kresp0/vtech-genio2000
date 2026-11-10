# HIDDEN_FEATURES: candidates (none activated or verified on hardware)

| Candidate | Evidence | Status |
|---|---|---|
| Support for **"GA" machine-code cartridges** from the menu (besides `YE` at start-up) | `B0:11B6-11C6` | CONFIRMED in the bytes; the known commercial cartridge uses `55 AA 11`. Possible "unannounced" feature |
| **RST 30h = restart to the menu** | `B0:0030` | CONFIRMED |
| **RAM for RST/statement hooks** (D000.., D152..) and the ISR hook pointer (`DFF5`) | `B0:0FF5`, `B7:6F32` | CONFIRMED; allows extending BASIC *from machine code* |
| **BASIC with removed statements**: 55 keywords blanked (no PEEK/POKE/CALL/USR/OUT/INP/DEF/ON/...); their handlers go to `SYNTAX ERROR` | `B7:5650..`, `B7:5822..` | CONFIRMED: **there is no route to machine code from BASIC**. The 5 commands `FORMAT LOAD SAVE DIR ERASE` and `LPRINT` do exist |
| **Storage (BASIC `LOAD/SAVE/DIR/ERASE/FORMAT`)**: messages `FORMATEAR? (S/N)`, `ERROR DE DATOS`, `MEMORIA LLENA`... | `B7:79BA-7A70`, `B7:7994`, `B7:794B`, `B7:3A86` | **PROBABLE (code reading, not executed)**: they use a **cartridge with RAM** in window 8000: they check `55 AA EE` at `8000-8002` and `BB 46` at `8006-8007`, **write and read back** that signature when formatting (`ld (hl),a ; cp (hl)`), directory at `8050` (16-byte entries, 0x70 at most), data at `8800` and `9000` selecting pages with `OUT (03),80/81`. This implies the connector accepts `/WR` towards the cartridge (which `hwtest` stage K probes on the EEPROM cartridge). It replaces the earlier hypothesis of an "external floppy". |
| Ports `0x02`, `0x04`, `0x05`, `0x06` written only at reset | `B0:0FB8-0FE7` | UNKNOWN (ASIC registers? for example 0x06=0x40). **HW (reads, 2026-11-10):** `IN` of 0x00-0x09 returns `FF` (3 reads; 0x04 sometimes `7F`); their function cannot be deduced from the reads |
| `IN A,(00)`/`OUT (00),A` in bank 7 (earlier reports) | do not appear in the decoded code | probably a false positive from data |
| Factory test modes / hidden key sequences | **not analysed**: requires walking the decision tree of `kbd` and the bank 5 dispatcher | UNKNOWN |
| Bank 5 dispatcher tokens/codes with no associated key | still to compare `DB23` (1..N) with the keys | UNKNOWN |
| **`HALT` = switch off** | only `HALT` in the firmware at `B0:018B` (farewell) | **HW (by difference, 2026-11-10):** executing `HALT` in a cartridge switches the unit off even if bit 0 of 0x12 is not written and the ISR is healthy. A "hidden function" in reverse: an instruction that cannot be used. PROBABLE |
| **ISR hooks** (`DFF4/DFF5`) | `B0:018E` | HW: `DFF5` can be replaced by an own routine in RAM (the firmware ISR still provides keyboard, LCD and the `DB28/29` counter); used by `hwtest` to measure the IRQ (46.76 Hz). CONFIRMED |

Rule applied: no "unreachable" code is declared a hidden function without a reference plus an activation condition.
