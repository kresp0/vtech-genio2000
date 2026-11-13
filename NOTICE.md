# Licensing and what is not in this repository

## Licences
* **Code and tools** (everything under `tools/` and the other code outside `examples/` that is the author's own work): **0BSD**, see `LICENSE`: use, copy, modify and distribute it for any purpose, with or without fee, without conditions. The `hwtest` images in `release/` are an exception: they are built against VGLDK (see the next item).
* **Examples** (`examples/`) and the images in `release/`: GPL-3.0-or-later, because they are built against VGLDK (GPL-3.0), which is not included; see `examples/README.md`.
* **Documentation** (`docs/` and the README files), **photographs** (`photos/`) and the **reconstructed character table** of the LCD with its photographs (`cgrom/`): dedicated to the public domain under **CC0 1.0 Universal**, see `LICENSE-CC0` (https://creativecommons.org/publicdomain/zero/1.0/). No attribution is required; a link back is welcome. The photographs are the author's own.
* Until 2026-11-13 the code outside `examples/` was released under BSD-3-Clause and the documentation, photographs and character table under CC BY 4.0; copies taken then may still be used under those terms.
* The glyph designs of the character table are those of the LCD controller's maker; the file is a reconstruction from photographs of the unit's display, not a read of the chip.
* The VTech name, logos, product design and printed artwork that appear in the photographs and in the documents belong to their owners and are **not** covered by these licences.

## Tools and their layout
The scripts were written for a working tree in which they sit next to a `rom/` directory with the user's own dump and an `out/` directory for results. They have **not** been re-run after being moved into this repository layout, except the test suites listed in `tools/README.md`. Paths that were absolute in the original tree have been replaced by environment variables (`GENIO_ROM`, `GENIO_MAME_DIR`, `GENIO_FW_DIR`, `GENIO_CGROM`).

## AI assistance
Much of the analysis code, the test scripts and the text of these documents were written with AI assistance: Claude Sonnet 5.5 (`claude-sonnet-5-5`) through Claude Code, and ChatGPT (GPT-6) for research and review. The hardware work (opening the units, building and burning the cartridges, the dumps, the photographs and every measurement) is the author's, and the author is responsible for the content.
