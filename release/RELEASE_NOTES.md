# Cartridge images

Ready-to-burn images for an AT28C256 EEPROM (32 KiB) in a Genio 2000 cartridge, and for MAME's `-cart`. **None of them contains any part of the Genio's firmware** (checked: no 64-byte block of the ROM appears in any image). Check the SHA-256 sums in `SHA256SUMS` before burning. Nothing in this repository writes to a chip; burning is yours to do.

| Image | What it is | Source | Tested |
|---|---|---|---|
| `kepler_demo_gl2000_mirrored_AT28C256_32K.bin` | Kepler 2000 music with a CGRAM, ROM-text and LED animation, a scroll with the names of the 4 x 20 family, and a finale that switches the unit off | `examples/kepler-demo` | on a real unit by the author (a build with VGLDK's `poweroff()` patch; this image has the same code with the power-off routine inside the demo), and in MAME |
| `readysetgo_gl2000_mirrored_AT28C256_32K.bin` | READY, SET, GO!: a BASIC-like READY prompt, giant READY / SET / GO! letters, a key to launch three ships out of a mothership into hyperspace while the names of the 4 x 20 family scroll below, 1-bit music and the LED; a press of OFF plays a goodbye and switches the unit off | `examples/readysetgo` | in MAME only (snapshots compared dot by dot with the expected screens, port timing, keys and OFF); **not tested on a real unit** |
| `genio_text_editor_gl4000_AT28C256_32K.bin` | the 4 x 20 text editor with serial export | `examples/text-editor` | on a real unit by the author (this is the image that was tested) |
| `hwtest_YE_autostart_AT28C256_32K.bin` | the hardware test cartridge, autostart | `tools/hwtest` | on a real unit by the author (two runs in `tools/hwtest/results`) |
| `hwtest_GA_menu_AT28C256_32K.bin` | the same, started from the CARTUCHOS ADICIONALES menu | `tools/hwtest` | on a real unit by the author (results not itemised here) |

Read `tools/hwtest/README.md` before running `hwtest`: its last stage writes values never tried before to port 0x03, and `HALT` switches the unit off.

## How they were built
* SDCC 4.5.0, `makebin`, Python 3; VGLDK at commit `6fbd389ace4c7bf156cb2c3fafafb1acf4a2a857`, with `examples/vgldk-genio` applied for the text editor.
* The text editor image is byte-identical to the image that was tested on the unit, and the Kepler and READY, SET, GO! images are rebuilt exactly from the sources in this repository; the example sources rebuild them exactly (`make VGLDK=/path/to/vgldk` in each directory). `hwtest` is built with `tools/hwtest/build.sh`.
* Layout: the 16 KiB (or 8 KiB) of code repeated up to 32 KiB, so that it works whichever page selector the firmware uses (`docs/firmware/HW_RESULTS_20261110.md` #3).

## Licence
The images are built from GPL-3.0-or-later sources (they link VGLDK headers and the VGLDK start-up code), so they are distributed under **GPL-3.0-or-later**; their corresponding source is in this repository plus the unmodified VGLDK commit above. Copyright (c) 2026 Santiago Crespo; VGLDK is by Bernhard "HotKey" Slawik and others.
