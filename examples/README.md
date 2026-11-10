# Examples

| Directory | What it is | Verified |
|---|---|---|
| [`kepler-demo/`](kepler-demo/) | The same music while animating the CGRAM and the LED with a single 256 T-state loop | builds; tested on a real unit by the author |
| [`text-editor/`](text-editor/) | A 4 x 20 text editor with the Spanish keyboard layer, a diagnostic and serial export | builds; its first 16 KiB are byte-identical to the original build; tested on a real unit by the author |
| [`vgldk-genio/`](vgldk-genio/) | The Genio 2000 layer for VGLDK (headers and a small patch) that the text editor needs | applies cleanly to VGLDK 6fbd389 |

All of them are built with [VGLDK](https://github.com/hotkeymuc/vgldk), which is **not** included: use an unmodified clone at commit `6fbd389ace4c7bf156cb2c3fafafb1acf4a2a857`. See [`../docs/DEVELOPING.md`](../docs/DEVELOPING.md).

## Licence
VGLDK is GPL-3.0 and these programs are built against its headers, so everything in `examples/` is released under **GPL-3.0-or-later** (copyright (c) 2026 Santiago Crespo; VGLDK headers belong to their authors). The BSD-3-Clause licence of the top-level `LICENSE` covers the rest of the repository's code.

Built images are in [`../release/`](../release/RELEASE_NOTES.md) with their checksums; you can also build them yourself. Burn them to your own EEPROM.
