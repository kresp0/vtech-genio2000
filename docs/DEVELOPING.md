# Developing software for the Genio 2000

How to write, build, test and burn a cartridge program for the Spanish VTech Genio 2000. Everything here is backed by the other documents; each section says where. Things that were not verified are marked **(unverified)**; the programs in `examples/` were all tested by the author on a real unit.

## 1. What you need

| | |
|---|---|
| Toolchain | [SDCC](https://sdcc.sourceforge.net/) 4.5 (`sdcc`, `sdasz80`, `makebin`), Python 3 |
| C library layer | [VGLDK](https://github.com/hotkeymuc/vgldk) commit `6fbd389ace4c7bf156cb2c3fafafb1acf4a2a857` (GPL-3.0, not included), plus [`examples/vgldk-genio`](../examples/vgldk-genio/README.md) for the Spanish keyboard and the native character set |
| Emulator | MAME with the `genio2000` driver (section 4) and **your own** ROM dump (the firmware is not in this repository); the reconstructed character table is in [`cgrom/`](../cgrom/README.md) |
| Hardware (optional) | a Genio 2000, an AT28C256 EEPROM in a modified cartridge, a programmer, a USB-serial adapter for output and input. The cartridge modification is described in [vtech-genio2000-rom-dumper](https://github.com/kresp0/vtech-genio2000-rom-dumper) |

## 2. The machine in one page

* **CPU** Z84C0006 (Z80), about 6.13 MHz (measured; `docs/hardware/CLOCK_AND_SOUND.md`). Interrupt mode 1 at **46.76 Hz**.
* **Memory map**: `0000-3FFF` ROM bank 0 (fixed), `4000-7FFF` ROM window 1 (port 0x01), `8000-BFFF` window 2: internal ROM or **cartridge** (port 0x03), `C000-DFFF` **8 KiB RAM** (also seen at `E000-FFFF`). See `docs/hardware/MEMORY_MAP.md`.
* **Ports**: `0x01`/`0x03` bank select, `0x0A`/`0x0B` LCD command/data, `0x10`/`0x11` keyboard (also printer lines: DATA0 = `0x10` bit 0 out, BUSY = `0x11` bit 5 in, both inverted; `docs/hardware/PRINTER_PORT.md`), `0x12` system: **bit 0 = power off**, bit 2 printer strobe, bit 3 speaker, bit 5 caps-lock LED. See `docs/firmware/IO_REGISTERS.md`.
* **LCD**: HD44780, 4 x 20 characters, with the physical character set documented in `docs/hardware/CGROM.md` and 8 user glyphs (CGRAM). The firmware's interrupt routine normally refreshes the LCD from a RAM buffer and scans the keyboard (`docs/firmware/LCD_INTERNALS.md`, `KEYBOARD_INTERNALS.md`).
* **Sound**: no sound chip; one bit (port 0x12 bit 3) toggled by software.

## 3. Cartridge programs

A cartridge is a ROM visible at `8000-BFFF` (16 KiB window). On power-on the firmware looks at `8000-8003`:

* `55 AA 59 45` ("YE"): jumps to `8004` **without menu or title screen**. The LCD is **not** initialised yet and interrupts are disabled (`docs/firmware/BOOT_SEQUENCE.md`, `CARTRIDGE_INTERFACE.md`).
* From the CARTUCHOS ADICIONALES key the menu accepts `55 AA 47 41` ("GA", machine code) or `55 AA 11` (data). Only the first is useful to you, and it was **not tested on hardware**.

Rules learned on the real unit:

1. **Do not execute `HALT`**: the unit switches off. To wait, use a loop (`jr $`), with `EI` if you need the interrupt routine.
2. **Never write bit 0 of port 0x12** unless you want to power off. Writes to that port must be read-modify-write with bit 0 forced to 0 (`examples/text-editor/docs/LED_AND_POWEROFF.md`).
3. Do not write ports 0x00, 0x01, 0x02, 0x04, 0x05, 0x06 (unknown or bank selects of the internal ROM). Port 0x03 selects cartridge pages (`0x80`+); only pages 80/81 are known to work.
4. Return to the firmware menu with `JP 0030` (RST 30h).
5. The stack starts at `DFF0`. The firmware interrupt routine uses RAM from `DB00` up; if you keep interrupts enabled with the firmware ISR, keep your data below `DB00` (VGLDK puts variables at `C000`).
6. Use the stable API of the firmware only where it is documented (`docs/firmware/FIRMWARE_API.md`); about 25 of its 74 entries are identified, and key reading and sound are **not**. VGLDK does not use the firmware API: it drives the LCD, keyboard and speaker ports directly, which is why it is the recommended route.

### Text, CGRAM and the OFF key in practice (what the text editor does)
* **Text**: the LCD's own character ROM already has n-tilde, the accented lower-case vowels, inverted ? and !, and the other Spanish characters, at the codes listed in `docs/hardware/CGROM.md`. With `-DGENIO_NATIVE_CGROM`, `genio_native_puts("¡Hola, año!")` takes a UTF-8 string and writes the right LCD codes; characters without a glyph print `?`. VGLDK's `printf` takes one Latin-1 byte per character, so do not feed it UTF-8.
* **CGRAM**: nothing is written to CGRAM at boot. Only the four accented capitals (Á Í Ó Ú) are missing from the character ROM; `genio_native_install_accents(0, 0)` loads them into CGRAM slots 0-3 (a thin 2-pixel accent), after which the same text functions print them. CGRAM is read live, so redefining a slot changes every cell showing it, and there are only 8 slots. Code 0x00 (slot 0, where Á lives) must be written raw (`genio_lcd_putraw`): `lcd_putchar` swallows it, and turns 0x08, 0x0A and 0x0D into cursor commands.
* **Cursor**: `genio_lcd_putraw` repositions the hardware cursor after every character. The editor sets `lcd_cursor = 0` and manages the cursor itself, writing only the cells that changed.
* **OFF key**: it is a separate contact on the activity panel (matrix 2), read through ports 0x10/0x11. `keyboard_inkey()` and `keyboard_getchar()` of the Spanish layer poll it first and call `poweroff()` after about 1.4 s of continuous press, ignoring an OFF held since power-on until it has been released once. If your loop does not call them, call `genio_off_poll()` yourself and `poweroff()` when it returns 1 (the editor does this on every iteration, during waits and while exporting). The routine is the one verified on the real unit and ends in `HALT`, which is the only place `HALT` is acceptable.

## 4. Build and test

### Build a C cartridge with VGLDK
```bash
git clone https://github.com/hotkeymuc/vgldk && git -C vgldk checkout 6fbd389
cp -r examples/vgldk-genio/include vgldk/ && (cd vgldk && patch -p1 < ../examples/vgldk-genio/vgldk-genio.patch)
cd examples/text-editor && make VGLDK=../../vgldk
```
**`examples/text-editor` is the reference program**: it is the one validated on the real unit and it shows every technique this guide describes (native-CGROM text, CGRAM accents, the Spanish keyboard layer with a key-state matrix, OFF handling, a serial transmitter, a RAM self-test). Start from it and delete what you do not need; its `src/ge_*.h` modules are independent of each other. `examples/kepler-demo` shows tight timing, sound, LCD animation and the LED, and has the reusable 1-bit audio loop. **Use `VGLDK_SERIES=4000` with `-DGENIO_ES -DGENIO_NATIVE_CGROM`** (the text editor). That profile gives the 4-row LCD map, text through the LCD's native character ROM, the Spanish keyboard layout, and an OFF key that works: `keyboard_inkey()` / `keyboard_getchar()` poll OFF and switch the unit off after about 1.4 s. VGLDK's stock `VGLDK_SERIES=2000` assumes a 2-row LCD and has no OFF handling, so a program built that way can only be switched off by removing the cartridge or the batteries; the Kepler demo uses it with its own LCD map because it never needs the key while it plays.

Ready-made images of the examples are in [`release/`](../release/RELEASE_NOTES.md). The images are 16 KiB (or 8 KiB) of code **repeated** to 32 KiB for an AT28C256: on the unit, with a 32 KiB EEPROM, only bit 1 of the page selector changes the content, so a mirrored image works wherever the firmware looks (`docs/firmware/HW_RESULTS_20261110.md` #3).

### Pure assembly
`tools/example-cartridge/hello_api.s` is a cartridge in sdas Z80 assembly that calls the firmware API. Because the LCD is not initialised at autostart, it calls `0x05CF` first.

### Run it in MAME
Until the driver is merged into MAME, use the `genio2000-complete` branch of the author's fork:
```bash
git clone https://github.com/kresp0/mame && cd mame && git switch genio2000-complete
make SUBTARGET=genio SOURCES=src/mame/vtech/pc2000.cpp REGENIE=1 -j"$(nproc)"     # a plain `make` builds all of MAME
mkdir -p roms/genio2000      # put your own 27-5575-00 and cgrom/genio2000_cgrom_reconstructed.bin here (or in genio2000.zip)
./genio genio2000 -rompath roms -cart kepler_gl2000_mirrored_AT28C256_32K.bin
```
MAME models the clock (6.13179 MHz), the 46.76 Hz interrupt, the Spanish keyboard, the LCD, the 1-bit speaker and the cartridge slot, and it has a built-in photographic layout in `genio2000-complete`. For automated tests run it headless, `-video none -sound none -seconds_to_run N -snapshot_directory DIR`, and compare snapshots or Lua-script output (`tools/mame-tests/`, `tools/analysis/run_cart.sh`). Without a display, `unset DISPLAY` and set `SDL_VIDEODRIVER=dummy`.

What MAME does **not** reproduce: the LCD's persistence and contrast, the real RAM power-up state (it is zeroed; the unit's is not), `IN 0x11` bit 6, and anything electrical. Treat emulation as necessary, not sufficient.

### Test on the unit
Output you can capture without a debugger: serial over the printer port (DATA0 -> a USB-serial RXD, 9600 8N1 or faster; `examples/text-editor/src` has the transmitter and `tools/hwtest` a complete example with a receiver). Input from a PC goes the other way on the same cable: the adapter's TXD on BUSY (DB25 pin 11); `examples/pc-link` is a complete example (receiver routines with counted T-states, a packet protocol, a PC script, and a Lua bridge that tests it in MAME, which has no printer port). Burning and swapping EEPROMs is yours to do; nothing in this repository writes to a chip.

## 5. Capabilities and limits

| | |
|---|---|
| RAM | 8 KiB in total (`C000-DFFF`), shared with the stack and, if you use the firmware ISR, its variables. No known non-volatile storage for programs |
| Code | 16 KiB visible per cartridge page (the examples use 11 to 16 KiB). Pages 2-7 of a larger cartridge: **untested** |
| Screen | text only, 4 x 20, 8 user-defined 5 x 8 glyphs (CGRAM, read live: changing one changes every cell that uses it). `examples/kepler-demo` animates the whole screen by rewriting CGRAM about 337 times a second (tested on the unit) |
| LCD timing | the firmware does not read the busy flag; leave at least about 40 us between writes |
| Sound | 1 bit. Pitch and tempo come from CPU timing, so with interrupts enabled the 46.76 Hz ISR steals cycles from a tone loop; the examples disable interrupts while playing |
| Keyboard | 8 x 13 matrix, no diodes: ghosting is possible. Only one key per scan is decoded by the firmware. Layout and legends: `docs/hardware/KEYBOARD.md` |
| Printer port | a two-way serial link to a PC: transmit on DATA0, receive on BUSY, every packet good at 2400-76800 baud on the unit, 115200 and 128000 experimental (`examples/pc-link`, `docs/hardware/PRINTER_PORT.md`). No interrupt is tied to BUSY: the program must be polling when a byte arrives. Selecting keyboard column 0 drives DATA0 low |
| OFF key | not handled by the hardware or the cartridge ROM: your program must poll it (see section 3) |
| Interrupts | the firmware starts a cartridge with interrupts disabled. Enable them only if you want the firmware's keyboard/LCD service |
| Unknown | ports 0x02, 0x04-0x06 (written 0 at reset), the NMI, `/WR` to the cartridge (so RAM in the cartridge), the real capacity of the ROM |

## 6. Two firmware revisions
Banks 1, 2, 3 and 7 differ between the two units dumped. Cartridge programs do not depend on them, but anything that calls into the BASIC or the data banks might (`docs/firmware/ROM_REVISIONS.md`).

## 7. Checklist for a new program
1. Start from `examples/text-editor`; build with the VGLDK layer.
2. Run it in MAME headless and check a snapshot of the LCD.
3. Review the rules of section 3 against your code (no `HALT`, no write of bit 0 of port 0x12, no unknown ports).
4. Prepare a mirrored 32 KiB image and its SHA-256; burn it; first run with output on the serial port.
5. Record what you saw on the unit, and mark in your own notes what was only emulated.
