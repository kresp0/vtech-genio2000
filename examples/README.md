# Examples

| | Program | What it is |
|---|---|---|
| <img src="kepler-demo/screen.png" width="360" alt="kepler-demo"> | [`kepler-demo/`](kepler-demo/) | A music and animation demo |
| <img src="calculator/screen.png" width="360" alt="calculator"> | [`calculator/`](calculator/) | A scientific calculator |
| <img src="diagnostics/screen.png" width="360" alt="diagnostics"> | [`diagnostics/`](diagnostics/) | A diagnostic cartridge: CPU, RAM, ROM, interrupt, LCD, keyboard, sound, LED |
| <img src="pc-link/screen.png" width="360" alt="pc-link"> | [`pc-link/`](pc-link/) | A serial link from a PC through the printer port |
| <img src="readysetgo/screen.png" width="360" alt="readysetgo"> | [`readysetgo/`](readysetgo/) | READY, SET, GO!, a demo with sprites and music |
| <img src="text-editor/screen.png" width="360" alt="text-editor"> | [`text-editor/`](text-editor/) | A text editor with serial export |
| | [`vgldk-genio/`](vgldk-genio/) | The Genio 2000 layer for VGLDK that the text editor needs |

Every program has been tested on a real Genio 2000; its README says how, and shows more MAME snapshots.

All of them are built with [VGLDK](https://github.com/hotkeymuc/vgldk), which is **not** included: use an unmodified clone at commit `6fbd389ace4c7bf156cb2c3fafafb1acf4a2a857`. See [`../docs/DEVELOPING.md`](../docs/DEVELOPING.md).

## Licence
VGLDK is GPL-3.0 and these programs are built against its headers, so the programs in `examples/` are released under **GPL-3.0-or-later** (copyright (c) 2026 Santiago Crespo; VGLDK headers belong to their authors). Their README files and screenshots are documentation, CC0 1.0 like the rest (`../LICENSE-CC0`). The rest of the repository's code is 0BSD (`../LICENSE`).

Built images are in [`../release/`](../release/RELEASE_NOTES.md) with their checksums; you can also build them yourself. Burn them to your own EEPROM.
