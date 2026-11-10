# layout PR (proof of concept; would now be a 9th PR): the photographic, clickable front panel as a built-in layout

Status 2026-11-09: **proof of concept only; nothing committed or published**. It was done on top of PR 3 (before PRs 4-8 existed) and the series branches were not touched; with PRs 4-8 now in place, the ON button, the contrast switch and the caps LED also work through this layout (only the output `lcd_dark`, which colours the LCD glass margin, exists just on `genio2000-dev`). The scratch branch used for the experiment was removed after saving what is needed (`patches/pr4-layout-poc/`, `tools/embed_layout.py`).
Goal asked for: `mame genio2000` shows by default the same photographic representation that the experimental build shows (LCD working, interactive keys), with no external artwork files, keeping the appearance exactly, without redrawing it as a vector layout.

## 1. What the current artwork really is (`artwork/genio2000/`)
`default.lay` (47 KB, one view "Photo (clickable)", 349 `<element>` lines) + five images, all PNG:
| File | Size | Role |
|---|---|---|
| `lid.png` | 1867 x 1338 RGB, 2.5 MB | top half: the lid photograph (frame, printed panel, LCD window, LED, contrast switch) |
| `base.png` | 1845 x 1242 RGB, 3.7 MB | bottom half: the keyboard and activity-panel photograph |
| `lcdgrid.png` | 960 x 320 RGBA, 69 KB | faint dot-matrix grid drawn over the emulated screen |
| `led_on.png` | 32 x 32 RGBA, 2.8 KB | the lit caps LED, shown when output `led_caps` is 1 |
| `slider_right.png` | 142 x 60 RGB, 14 KB | the contrast switch in its right-hand position, shown when input `CONTRAST` is on |
How they combine, in this order (layout units = pixels of the lid image, 1867 x 2580 in total): `lid` at (0,0); a flat "glass" rectangle (two colours, switched by output `lcd_dark`) behind the LCD; the emulated `<screen index="0">` in the LCD window; the grid on top of the screen; the lit LED (output `led_caps`); the contrast switch image (input `CONTRAST`); `base` under the lid; then **336 invisible click areas** (`hit` element = yellow 45 % rectangle only while pressed): 56 key rectangles + 40 activity buttons x 7 strips each (the oval approximation, see `ARTWORK.md`), each bound with `inputtag`/`inputmask` to the input ports of the driver. Only the images, the `glass` colours, the input tags and the two outputs are specific to this machine.

## 2. Can raster images go into the binary with the current build system? **Yes, no build-system change is needed**
Verified on current `origin/master` (c7541016):
* `makefile` builds **every** `src/mame/layout/*.lay` into `$(GENDIR)/mame/layout/*.lh` with `scripts/build/complay.py` (`LAYOUTS = rwildcard`); a driver only has to `#include "name.lh"` and call `config.set_default_layout(layout_name)`. The same file already does this for `gl3000s.lay` (`#include "gl3000s.lh"`, `set_default_layout(layout_gl3000s)`), so the pattern is the one used in `pc2000.cpp`.
* The layout `image` component accepts, instead of `file="..."`, a `<data>` child. `src/emu/rendlay.cpp` (`load_image_data()`) **decodes Base64 in place and then checks whether the bytes are a bitmap (PNG, JPEG, DIB) before trying SVG**. The documentation (`layout_files.rst`) only mentions SVG for `<data>` (it says it is "useful for supplying simple, human-readable SVG graphics"), so embedded bitmaps work but are **not documented**: a reviewer may point that out.
* `complay.py` accepts the file (it checks `file` xor `<data>`), minifies the XML, zlib-compresses it and writes a C array.
* So the proof of concept is: `tools/embed_layout.py artwork/genio2000 src/mame/layout/genio2000.lay --optimize` (each `<image file="x.png" .../>` -> `<image ...><data>base64(x.png)</data></image>`, everything else unchanged; `--optimize` recompresses the PNGs with `optipng`, checked pixel-identical), plus the two lines in `pc2000.cpp` (`patches/pr4-layout-poc/pc2000_cpp_layout_hook.diff`: the include and `config.set_default_layout(layout_genio2000);` inside `gl4004_state::genio2000()`).

## 3. Results of the proof of concept (series binary, no external artwork)
| Check | Result |
|---|---|
| `complay.py` on the layout | OK (17 s for the 6.7 MB file) |
| build of the `genio` subset | OK, 26 s incremental, 0 warnings; generated `.lh` is 25.6 MB of C source (not in git) |
| `-validate` | OK |
| binary size | +5.09 MB (74,772,816 vs 69,681,392 bytes for the subset build; the compressed layout is 5.09 MB) |
| source size in git | `genio2000.lay` 6.7 MB of text (base64 of 4.97 MB of PNG after lossless optimisation; the raw PNGs were 6.3 MB) |
| appearance | window capture of the embedded layout (`-artpath` pointing to an empty directory) vs the external artwork with the same driver: **0 of 700,000 pixels differ** (`logs/artwork/pr4_poc/`) |
| default view | the photographic view is the first, hence the default; MAME still appends its automatic screen-only views |
| mouse | clicking the BASIC button with the real mouse in the embedded layout opens the BASIC prompt (`embedded_layout_click_BASIC.png`; script `tools/layout_click_check.py`, which accounts for the letterboxing of the view) |
| items bound to things the tested build did not have (`POWER`, `CONTRAST`, outputs `led_caps`/`lcd_dark`; the build was PR 3) | no warning at load; they stayed inert. With PRs 4-8 the first three exist; `lcd_dark` only on `genio2000-dev` (without it the glass margin keeps the lit-LCD colour) |
Lossless PNG optimisation (`optipng -o3 -strip all`): lid 2.55 -> 2.00 MB, base 3.67 -> 2.94 MB, grid 69 KB -> 0.3 KB (converted to a palette image; pixels identical when converted back to RGBA).

## 4. What the layout PR would contain
1. `src/mame/layout/genio2000.lay` (new, ~6.7 MB, generated by `tools/embed_layout.py`; header with license and copyright holder).
2. `src/mame/vtech/pc2000.cpp`: the `#include` and one `set_default_layout` line (3 lines).
3. Nothing in `makefile`, `scripts/` or `complay.py`.
4. PR text: what the layout shows, that it is the owner's photographs, size impact, AI disclosure (as in `PR_DRAFT.md`).
It only needs the `genio2000` machine of PR 1 (the keys need PR 2); ON, the contrast switch and the LED work through it once PRs 5, 6 and 8 are in. The glass-margin colour follows the contrast switch only with the output `lcd_dark`; a PR could add that one-line output (or the layout could drop the margin element).

## 5. Risks and open questions (what I could not settle)
* **No precedent found.** The largest internal layout in the tree is about 317 KB (`sc4ppclb.lay`) and none embeds bitmaps (129 layouts use `<data>`, all SVG in the ones inspected; no base64 PNG/JPEG). This layout is ~21 times larger, adds 5 MB to the executable and 5-7 MB to the repository history for one machine. I found no policy text about bitmap artwork in the source tree (the clone of the repository here is shallow, 8 commits, so I could not search history for accepted PRs). Debian and the artwork FAQs show artwork normally shipped separately, which is not proof of a rule. **Ask the maintainers first** (an issue/discussion or a draft PR) before preparing the full one.
* **Rights.** The layout is photographs of a VTech product including its printed graphics (logo, panel legends). The copyright holder of the photographs (the owner) can license them, but not VTech's graphics; the maintainers may refuse bitmaps of copyrighted printed artwork or ask for a redraw. The header uses `license:CC0-1.0` like the neighbouring `gl3000s.lay` as a placeholder: **the owner must choose the license** (BSD-3-Clause is the other usual one).
* **Undocumented feature**: base64 bitmaps in `<data>` (see section 2). If the maintainers do not want to rely on it, the images would have to be external, which is what the current artwork already is.
* **Size alternatives** (all change the appearance slightly, so not done): JPEG for lid/base would cut the size to about a fifth; fewer pixels; dropping the second image. Lossless options are already used.
* **Build impact**: +20 s on the first build of this one driver (complay and compiling a 25 MB array); a full MAME build is dominated by other things.
* The layout is stored as one file, so every change of the artwork re-adds ~5 MB to the history; the generator keeps it reproducible.

## 6. Alternatives if the PR is not accepted
Keep distributing it as external artwork (`artwork/genio2000/` or a zip named `genio2000.zip` in the artwork path, which is how it already works with `tools/run_genio.sh`), or a much smaller built-in layout (SVG or flat colours) for the keyboard only. The owner asked not to redraw it, so the first is the fallback.

## 7. To reproduce the proof of concept
```bash
git -C mame checkout -b scratch genio2000-pr3-cgrom
python3 tools/embed_layout.py artwork/genio2000 mame/src/mame/layout/genio2000.lay --optimize
git -C mame apply ../patches/pr4-layout-poc/pc2000_cpp_layout_hook.diff     # or add the two lines by hand
cd mame && make SUBTARGET=genio SOURCES=src/mame/vtech/pc2000.cpp USE_QTDEBUG=0 NOWERROR=1 TOOLS=0 -j12
python3 ../tools/layout_click_check.py <workdir> mame/genio <empty-artpath> BASIC out.png   # real-mouse check on an X display
```

## 8. Status 2026-11-09 (later): built on the consolidated series, branch prepared locally, held back
Branch `genio2000-photographic-layout` (one commit on `genio2000-lcd-contrast`; clone `work/review/mame-rev`). Layout generated by `tools/embed_layout.py ... --optimize` (the licence and copyright-holder lines are written as `PENDING-OWNER-DECISION`: **no licence attributed, branch not pushed until the owner decides**), plus three lines in `pc2000.cpp` (`#include "genio2000.lh"`, `config.set_default_layout(layout_genio2000)` in `genio2000_state::genio2000()`). Binary +5.09 MB (74,800,312 vs 69,712,976 bytes, driver-only build). Checks (private virtual X display, `-artpath` empty): capture of the built-in layout = capture of PR 8 + external artwork, 0 of 1,408,000 pixels differ; real clicks: OFF blanks the LCD, ON restarts, BASIC opens READY, the contrast switch darkens the LCD (mean luminance 141.3 -> 130.1) and back, BLOQ. MAYUSCULAS lights the LED (`logs`: `work/review/pr9check/click/`). The control names changed in the PR 2 review do not matter to the layout: it binds input tags and masks, not `PORT_NAME`s. The suite passes 38 / 13 skipped, identical to PR 8, once the tests pass `-snapview native` (with a built-in default layout the snapshot is of the whole photographic view). `lcd_dark` still does not exist in the series, so the glass margin keeps its lit-LCD colour.
