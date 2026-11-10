# Tools

## The ROM dumper lives in its own repository
[kresp0/vtech-genio2000-rom-dumper](https://github.com/kresp0/vtech-genio2000-rom-dumper) has the dumper cartridge, the receivers and verifiers, the hardware modification guide and its own tests. It is not duplicated here. `hwtest/` uses `gframe.py`, `z80core.py` and the VGLDK headers from it: clone it as `tools/dumper/` (or set `GENIO_DUMPER_DIR`):
```bash
git clone https://github.com/kresp0/vtech-genio2000-rom-dumper tools/dumper
```

| Directory | What it is | Needs |
|---|---|---|
| `hwtest/` | Test cartridge that measures the real unit (clock, IRQ rate, ports, LCD, RAM, port 03) and its receiver; `results/` holds two real runs | a clone of the dumper repository (below), SDCC 4.5, Python 3 + pyserial |
| `analysis/` | Z80 disassembler, tracing, extractors for the BASIC tables and the data banks, MAME Lua probes | your own ROM dump (`GENIO_ROM`), `unidasm` from MAME, Python 3 |
| `analysis-tests/` | Tests that pin the findings of the firmware documents | your own ROM dump |
| `example-cartridge/` | A minimal machine-code cartridge that prints a message through the firmware API | SDCC |
| `mame/` | Helpers used while preparing the MAME driver: keyboard-port generator, timing and sound scripts, layout checks | a MAME working tree (`GENIO_MAME_DIR`) |
| `mame-tests/` | Automated tests of the MAME driver (they need the private ROMs, which are never published) | a MAME build with the `genio2000` driver |

## What has been run in this layout
* `hwtest/tests`: 9 tests pass.
* `analysis-tests/test_findings.py`: 12 tests pass with the author's ROM dumps.
These runs were done in a working copy that also held the build outputs and the ROM images, so they will not pass here until you build the images and provide your own ROM. Nothing in `mame/` or `mame-tests/` has been re-run for this repository.

## Environment variables
`GENIO_ROM` (ROM image to analyse), `GENIO_TAG` (suffix for the output of a second image), `GENIO_MAME_DIR` (MAME working tree), `GENIO_FW_DIR` (directory with verified `bank_N.bin`), `GENIO_CGROM` (character table), `GENIO_SCENARIO_LUA` (path of the MAME scenario helper in `mame-tests/lua/`).

## Safety
The cartridge sources write only to port 0x01 (dumper) or follow the documented stage list (`hwtest`), and they never write to a chip. Read `docs/firmware/CARTRIDGE_DEVELOPMENT.md`, `tools/dumper/docs/BANKS_AND_PRECAUTIONS.md` and the `hwtest` README before burning anything: on the real unit `HALT` switches it off.
