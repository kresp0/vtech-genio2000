# Examples

| Directory | What it is | Verified |
|---|---|---|
| [`kepler-demo/`](kepler-demo/) | Music while animating the CGRAM, ROM text and the LED with loops of 256 T-states, a scroll with the names of the 4 x 20 family, and a finale that switches the unit off | builds with an unmodified VGLDK; runs to the end in MAME; tested on a real unit |
| [`diagnostics/`](diagnostics/) | A diagnostic cartridge with a menu (in English; keys by their Spanish legends): all tests, the automatic ones, or one group or test. Automatic: CPU (registers, ALU against a model of the documented flags, jumps, block and indexed instructions, R and I), RAM (data bus, address lines, March C- over all 8 KiB), cartridge and internal ROM CRCs, keys at rest, interrupt rate and its exact period in T-states (IM 2), ports. Interactive: LCD (dots, checkerboard, cell order, character set, CGRAM, cursor), keyboard, sound, LED | builds with an unmodified VGLDK; every test run in MAME, with injected RAM, ROM and key faults detected; **not tested on a real unit** (the IRQ period test is the first use of IM 2 on this hardware) |
| [`readysetgo/`](readysetgo/) | READY, SET, GO!: a BASIC-like prompt, giant letters, a key to launch the ships, pixel-smooth sprites and hyperspace, a scroll with the names of the 4 x 20 family, 1-bit music and the LED, all in one data-driven loop of 256 T-states; OFF plays a goodbye and switches off | builds with an unmodified VGLDK; runs to the end in MAME (snapshots compared dot by dot); **not tested on a real unit** |
| [`text-editor/`](text-editor/) | A 4 x 20 text editor with the Spanish keyboard layer, a diagnostic and serial export | builds; its first 16 KiB are byte-identical to the original build; tested on a real unit |
| [`vgldk-genio/`](vgldk-genio/) | The Genio 2000 layer for VGLDK (headers and a small patch) that the text editor needs | applies cleanly to VGLDK 6fbd389 |

All of them are built with [VGLDK](https://github.com/hotkeymuc/vgldk), which is **not** included: use an unmodified clone at commit `6fbd389ace4c7bf156cb2c3fafafb1acf4a2a857`. See [`../docs/DEVELOPING.md`](../docs/DEVELOPING.md).

## Licence
VGLDK is GPL-3.0 and these programs are built against its headers, so everything in `examples/` is released under **GPL-3.0-or-later** (copyright (c) 2026 Santiago Crespo; VGLDK headers belong to their authors). The BSD-3-Clause licence of the top-level `LICENSE` covers the rest of the repository's code.

Built images are in [`../release/`](../release/RELEASE_NOTES.md) with their checksums; you can also build them yourself. Burn them to your own EEPROM.
