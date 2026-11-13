# Notes for AI agents working in this repository

* Start with `docs/DEVELOPING.md` (writing and testing cartridge programs) and `docs/README.md` (what is known about the machine and where the evidence is).
* **Never publish or add the firmware ROM** (`27-5575-00`, 128 KiB) or anything derived from it (disassembly listings, string tables, decoded data banks, RAM dumps). It is VTech's work; the repository publishes only checksums.
* Respect the evidence labels in the documents: HW (measured on a unit), FW (read from the firmware), EMU (only seen in MAME), PROBABLE / HYPOTHESIS / UNKNOWN. Do not present emulated behaviour as hardware behaviour, and say which of the two known units a measurement comes from.
* Rules for code that will run on the real unit (they cost an unexpected power-off or worse): no `HALT`; never write bit 0 of port 0x12; do not write ports 0x00, 0x01, 0x02, 0x04, 0x05, 0x06; nothing in this repository writes to a chip, so keep it that way.
* Running MAME: use headless mode with no display (`unset DISPLAY`, `SDL_VIDEODRIVER=dummy`, `-video none -sound none`), and never launch a windowed MAME on someone else's desktop without asking.
* Comments in code should say only what the code does not already say, in plain English; longer reasoning belongs in a commit message or a document.
* Licences: `examples/` is GPL-3.0-or-later (built against VGLDK); the rest of the code is 0BSD; documentation, photographs and the character table are CC0 1.0. Keep third-party code out unless its licence allows it, with its notice.
