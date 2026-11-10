# CAPS LOCK LED and power-off (port 0x12)

**Status:** a hardware test with a dedicated test cartridge confirmed that bit 5 of port 0x12 drives the LED (see `docs/firmware/HW_RESULTS_20261110.md`), and the editor was tested on a real unit by the author. Power-off = a routine already validated on hardware, reused byte for byte.

## What each source says about port 0x12
| Source | Fact |
|---|---|
| VGLDK `include/arch/gl4000/led.h` | LED on bit 5 (`0x20`) of port 0x12; `led_on()` = `led_port \|= 0x20`, `led_off()` = `led_port &= ~0x20` (read-modify-write with `IN A,(0x12)`), protecting no other bit |
| **Original firmware** (verified dump) `0x01F2...0x020C` | when CAPS LOCK is pressed: `IN A,(12h); OR 20h; AND FBh; OUT (12h),A` (LED on, bit 2 to 0) and a 1 is stored in the firmware's RAM; on the next press: `IN A,(12h); AND DBh; OUT (12h),A` (bits 5 and 2 to 0). **It confirms that on the Genio 2000 the LED is bit 5 and that `IN A,(12h)` returns what was written** (the firmware depends on it) |
| Firmware `0x0183...0x018A` and `genio_hw.h` | power-off: `DI; LD A,1; OUT (12h),A; HALT; JR $` -> **bit 0 of port 0x12 at 1 is the power-off request** |
| VGLDK `sound.h` | bit 3 = speaker (`sound_off`: `IN; AND F7h; OUT`; `sound_tone` writes 0x08/0x00 **absolutely**: it would destroy the LED, which is why the editor does not use the speaker) |
| `softuart`/T642 transmitter | bit 2 = strobe (set and cleared on every bit with IN/OR/OUT/AND/OUT) |

## The risk in `led.h` and how it is avoided
`led_port |= 0x20` writes what it reads plus 0x20; if `IN A,(0x12)` ever returned bit 0 at 1, it would **switch the unit off**. `ge_led_set()` (`src/genio_text_editor_gl4000.c`):
```c
v = led_port;                 // IN A,(0x12)   (reads the other bits: they are kept)
v &= ~0x01;                   // bit 0 ALWAYS at 0: no LED write asks for power-off
v = on ? (v | 0x20) : (v & ~0x20);
led_port = v;                 // OUT (0x12),A
```
Checked in the original project's simulator: the LED follows CAPS LOCK; the other bits (strobe, speaker...) are kept (`0x14 -> 0x34 -> 0x14`); no write carries bit 0 even with a port that returns `0xFF`; the LED is off at start-up; it survives serial transmission (the transmitter's RMW keeps bit 5); `ALT+BLOQ` does not touch the LED; mutation tests detect removing the mask or the RMW.

Honest caveats: (1) VGLDK's start-up `sound_off()` and the T642 transmitter do RMW **without** the mask; they are those of the ROMs already validated and run before / only on export, so they were not modified; (2) in the simulator `IN A,(0x12)` returns the last value written (as the real firmware indicates).

## Power-off
`poweroff()` and `genio_off_poll()` are those of `genio_hw.h` (untouched): confirmation by holding (0xFFFF scans, about 1.4 s, `BC = 0xFFFF` of the verified ROM), it ignores OFF pressed from start-up until it has been seen released once, `DI; LD A,1; OUT (12h),A; HALT; JR $` (`F3 3E 01 D3 12 76 18 FD`, checked in the image). It is served on every iteration of the main loop, in all modes (editor, help, menu, diagnostic) and during waits and export. No other path of the program writes a value to 0x12 with bit 0 set. Note that on the real unit `HALT` itself switches the unit off (see `docs/firmware/INTERRUPTS.md`).
When switching off the document is lost (no known backup battery for the RAM): export first.
