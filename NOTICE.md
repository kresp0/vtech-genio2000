# Licensing and what is not in this repository

## Licences
* **Code and tools** (everything under `tools/` that is the author's own work): BSD 3-Clause, see `LICENSE`.
* **Examples** (`examples/`): GPL-3.0-or-later, because they are built against VGLDK (GPL-3.0), which is not included; see `examples/README.md`.
* **Documentation** (`docs/`), **photographs** (`photos/`) and the **reconstructed character table** of the LCD with its photographs (`cgrom/`): Creative Commons Attribution 4.0 International (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/ . Copyright (c) 2026 Santiago Crespo. The photographs are the author's own.
* The glyph designs of the character table are those of the LCD controller's maker; the file is a reconstruction from photographs of the unit's display, not a read of the chip.
* The VTech name, logos, product design and printed artwork that appear in the photographs and in the documents belong to their owners and are **not** covered by these licences.

## Tools and their layout
The scripts were written for a working tree in which they sit next to a `rom/` directory with the user's own dump and an `out/` directory for results. They have **not** been re-run after being moved into this repository layout, except the test suites listed in `tools/README.md`. Paths that were absolute in the original tree have been replaced by environment variables (`GENIO_ROM`, `GENIO_MAME_DIR`, `GENIO_FW_DIR`, `GENIO_CGROM`).

## AI assistance
Much of the analysis code, the test scripts and the text of these documents were written with AI assistance: Claude Sonnet 5.5 (`claude-sonnet-5-5`) through Claude Code, and ChatGPT (GPT-6) for research and review. The hardware work (opening the units, building and burning the cartridges, the dumps, the photographs and every measurement) is the author's, and the author is responsible for the content.
