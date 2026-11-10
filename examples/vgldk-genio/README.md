# vgldk-genio: a Genio 2000 layer for VGLDK

The examples in this repository are built with [VGLDK](https://github.com/hotkeymuc/vgldk) (the VTech Genius LEADER Development Kit by Bernhard "HotKey" Slawik, GPL-3.0). VGLDK is not included. Use an unmodified clone at commit `6fbd389ace4c7bf156cb2c3fafafb1acf4a2a857`.

This directory adds what the Spanish Genio 2000 needs on top of VGLDK's `gl4000` target. It is only compiled in when `GENIO_ES` is defined; the stock `gl4000` target is untouched otherwise.

| File | What it provides |
|---|---|
| `genio.h` | ties the layers together |
| `genio_hw.h` | power-off (`poweroff()`), OFF key polling (verified on the real unit) |
| `keyboard_es.h` | the Spanish keyboard distribution (derived from the firmware's own key tables) |
| `cgrom_profile_vtech_gl4000_v1.h` | which glyph the physical character ROM has at every code (Latin-1 -> LCD code) |
| `cgram_accents.h` | a library of CGRAM glyphs (accented capitals A, I, O, U) |
| `genio_native.h` | the native-CGROM profile (`GENIO_NATIVE_CGROM`): no CGRAM at boot, raw-safe output |
| `genio_legacy_cgram_es.h` | the older approach that loaded Spanish glyphs into CGRAM at boot |
| `genio_compat_gl2000.h` | compatibility shims |
| `vgldk-genio.patch` | two small patches to VGLDK itself: `arch/gl4000/system.h` (include the layer when `GENIO_ES` is set) and `tools/Makefile.mk` (an extra `VGLDK_CFLAGS` variable) |

## Applying it
```bash
git clone https://github.com/hotkeymuc/vgldk && git -C vgldk checkout 6fbd389
cp -r examples/vgldk-genio/include vgldk/          # adds the new headers
(cd vgldk && patch -p1 < ../examples/vgldk-genio/vgldk-genio.patch)
```
Then build an example with `make VGLDK=/path/to/vgldk` (for a Genio program with the Spanish keyboard use `VGLDK_SERIES=4000 VGLDK_CFLAGS="-DGENIO_ES -DGENIO_NATIVE_CGROM"`, as `../text-editor/Makefile` does).

Licence: GPL-3.0-or-later (these files extend VGLDK headers).
