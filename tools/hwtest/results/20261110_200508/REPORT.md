# HWTEST results (HW, measured on the unit; none of this is MAME)

Captured: 2026-11-10 21:48:52. Rejected frames: 0, line errors: 0. End of program received: yes.

## Stages
- A (entry state + RAM copy): done
- B (IN ports 00..FF): done
- C (CPU clock bursts): done
- D (IRQ rate): done
- E (LCD + LED questions): done
- F (keyboard matrix log): SKIPPED
- G (charset pages (photos)): SKIPPED
- H (port 03 <- 00..07): SKIPPED
- I (port 03 <- 80..8F): SKIPPED
- J (port 03 <- 08..1F): SKIPPED
- K (cartridge /WR probe): SKIPPED
- L (port 03 <- 20 40 90 A0 C0): done

## A. Entry state
- cartridge `YE (autostart)`  SP=DFEE  build 0100  session 041D
- `LD A,I`: F=40 (bit 2 = IFF2 -> interrupts disabled) I=00
- DFF0..DFF7 = 14 00 00 80 14 33 00 00  (DFF1/DFF3 = shadows of ports 01/03, DFF4/DFF5 = bank and hook of the ISR)
- copy of C000-FFFF: 128/128 blocks received (`mem_C000_FFFF.bin`)
- E000-FFFF: 61/64 blocks identical to their pair at C000-DFFF (mirror), 1 all FF, 0 all 00

## B. Port reads (3 reads per port; 0A/0B deliberately not read)

| port | reads |
|---|---|
| 00 | 7F FF FF |
| 01 | FF FF FF |
| 02 | FF FF FF |
| 03 | FF FF FF |
| 04 | 7F 7F 7F |
| 05 | FF FF FF |
| 06 | FF FF FE |
| 07 | FF FF FF |
| 08 | FF FF FF |
| 09 | FF FF FF |
| 0A | EE EE EE |
| 0B | EE EE EE |
| 0C | 7F 7F 7F |
| 0D | FF FF FF |
| 0E | FE FE FE |
| 0F | FF FF FF |
| 10 | FF FF FF |
| 11 | 5F 5F 5F |
| 12 | 16 16 16 |
| 13 | FF FF FF |
| 14 | 77 77 77 |
| 15 | F5 F5 F5 |
| 16 | F6 F6 F6 |
| 17 | F7 F7 F7 |
| 18 | 7F 7F 7F |
| 19 | FF FF FF |
| 1A | 7A 7A 7A |
| 1B | FB FB FB |
| 1C | 7F 7F 7F |
| 1D | FD FD FD |
| 1E | 7E 7E 7E |
| 1F | FF FF FF |
| 20 | 7F 7F 7F |
| 22 | 7E 7E 7E |
| 24 | 3F 3F 3F |
| 26 | 7E 7E 7E |
| 2C | 2F 2F 2F |
| 2D | ED ED ED |
| 2E | 2E 2E 2E |
| 2F | EF EF EF |
| 31 | 5F 5F 5F |
| 32 | 16 16 16 |
| 33 | FB FB FB |
| 34 | 37 37 37 |
| 35 | 75 F5 F5 |
| 36 | 36 36 36 |
| 37 | F7 F7 F7 |
| 38 | 3F 3F 3F |
| 39 | 7B 7B 7B |
| 3A | 3A 3A 3A |
| 3B | FB FB FB |
| 3C | 3E 3E 3E |
| 3D | 7D 7D 7D |
| 3E | 3E 3E 3E |
| 40 | 7F 7F 7F |
| 41 | 7F 7F 7F |
| 42 | 7E 7E 7E |
| 43 | 7F 7F 7F |
| 44 | 7F 7F 7F |
| 45 | 7F 7F 7F |
| 46 | 7E 7E 7E |
| 47 | 7F 7F 7F |
| 4C | 7F 7F 7F |
| 4D | 7F 7F 7F |
| 4E | 7E 7E 7E |
| 4F | 7F 7F 7F |
| 51 | 5F 5F 5F |
| 52 | 16 16 16 |
| 53 | 5B 5B 5B |
| 54 | 77 77 77 |
| 55 | 55 55 55 |
| 56 | 56 56 56 |
| 57 | 57 57 57 |
| 58 | 5F 5F 5F |
| 59 | 5B 5B 5B |
| 5A | 5A 5A 5A |
| 5B | 5B 5B 5B |
| 5C | 5F 5F 5F |
| 5D | 5D 5D 5D |
| 5E | 5E 5E 5E |
| 5F | 5F 5F 5F |
| 60 | 7F 7F 7F |
| 61 | 7F 7F 7F |
| 62 | 7E 7E 7E |
| 63 | 7F 7F 7F |
| 64 | 7F 7F 7F |
| 65 | 7D 7D 7D |
| 66 | 7E 7E 7E |
| 67 | 7F 7F 7F |
| 6C | 6E 6E 6E |
| 6D | 6D 6D 6D |
| 6E | 6E 6E 6E |
| 6F | 6F 6F 6F |
| 71 | 5F 5F 5F |
| 72 | 16 16 16 |
| 73 | 73 73 73 |
| 74 | 76 76 76 |
| 75 | 75 75 75 |
| 76 | 76 76 76 |
| 77 | 77 77 77 |
| 78 | 7A 7A 7A |
| 79 | 79 79 79 |
| 7A | 7A 7A 7A |
| 7B | 7B 7B 7B |
| 7C | 7C 7C 7C |
| 7D | 7D 7D 7D |
| 7E | 7E 7E 7E |
| 7F | 7F 7F 7F |
| 82 | FE FE FE |
| 86 | FE FE FE |
| 8E | FE FE FE |
| 91 | 5F 5F 5F |
| 92 | 16 16 16 |
| 93 | FB FB FB |
| 94 | B7 B7 B7 |
| 95 | F5 F5 F5 |
| 96 | B6 B6 B6 |
| 97 | F7 F7 F7 |
| 98 | BF BF BF |
| 99 | FB FB FB |
| 9A | BA BA BA |
| 9B | FB FB FB |
| 9C | BF BF BF |
| 9D | FD FD FD |
| 9E | BE BE BE |
| A0 | BF BF BF |
| A1 | BF BF BF |
| A2 | BE BE BE |
| A3 | BF BF BF |
| A4 | BF BF BF |
| A5 | BD BD BD |
| A6 | BE BE BE |
| A7 | BF BF BF |
| AC | AE AE AE |
| AD | AD AD AD |
| AE | AE AE AE |
| AF | AF AF AF |
| B1 | 5F 5F 5F |
| B2 | 16 16 16 |
| B3 | BB BB BB |
| B4 | B6 B6 B6 |
| B5 | B5 B5 B5 |
| B6 | B6 B6 B6 |
| B7 | B7 B7 B7 |
| B8 | BB BB BB |
| B9 | BB BB BB |
| BA | BA BA BA |
| BB | BB BB BB |
| BC | BC BC BC |
| BD | BD BD BD |
| BE | BE BE BE |
| BF | BF BF BF |
| C2 | FE FE FE |
| C6 | FE FE FE |
| CD | FD FD FD |
| CE | CE CE CE |
| CF | CF CF DF |
| D1 | 5F 5F 5F |
| D2 | 16 16 16 |
| D3 | DB DB DB |
| D4 | D6 D6 D6 |
| D5 | D5 D5 D5 |
| D6 | D6 D6 D6 |
| D7 | D7 D7 D7 |
| D8 | DF DF DF |
| D9 | DB DB DB |
| DA | DA DA DA |
| DB | DB DB DB |
| DC | DE DE DE |
| DD | DD DD DD |
| DE | DE DE DE |
| DF | DF DF DF |
| E2 | FE FE FE |
| E4 | FE FE FE |
| E5 | FD FD FD |
| E6 | FE FE FE |
| EC | EE EE EE |
| ED | ED ED ED |
| EE | EE EE EE |
| EF | EF EF EF |
| F1 | 5F 5F 5F |
| F2 | 16 16 16 |
| F3 | F3 F3 F3 |
| F4 | F6 F6 F6 |
| F5 | F5 F5 F5 |
| F6 | F6 F6 F6 |
| F7 | F7 F7 F7 |
| F8 | FA FA FA |
| F9 | F9 F9 F9 |
| FA | FA FA FA |
| FB | FB FB FB |
| FC | FC FC FC |
| FD | FD FD FD |
| FE | FE FE FE |

Ports that do not appear returned FF FF FF.

## C. CPU clock
- bursts found: 2  bytes: [1200, 1200]
- period per byte (s): [0.0010966570703974294, 0.0021996561297992286]
- **estimated CPU clock: 6.101 MHz** (T per byte in burst 1: 6690)

## D. Interrupts (firmware ISR + DFF5 hook that counts; no HALT)
- marks received: phase 0: 0 IRQ (DB26/27=0000 DB00=C0 DB01=B4), phase 2: 1 IRQ (DB26/27=0000 DB00=D0 DB01=F9), phase 2: 5 IRQ (DB26/27=0000 DB00=D0 DB01=F9), phase 2: 20 IRQ (DB26/27=0000 DB00=D0 DB01=F9), phase 2: 100 IRQ (DB26/27=0000 DB00=D0 DB01=F9), phase 3: 100 IRQ (DB26/27=0000 DB00=D0 DB01=F9), phase 1: 1100 IRQ (DB26/27=0000 DB00=D0 DB01=F9)
- measured window: 1000 interrupts in 21.39 s -> **46.76 Hz**

## E. LCD/LED questions

| # | question | answer | expected (MAME/datasheet) |
|---|---|---|---|
| 1 | all cells = code 00 show a solid block | S | S |
| 2 | rewriting CGRAM 0 changes ALL cells at once (live read) | S | S |
| 3 | codes 0-7 show 8 different shapes | S | S |
| 4 | rewriting CGRAM changes everything at once | S | S |
| 5 | codes 08-0F look the same as 00-07 (mirror) | S | S |
| 6 | a LED blinked 3 times (port 0x12 bit 5) | S | S |

## H-K. Port 03: window 8000-BFFF per selector

| sel | CRC-32 16 KiB | stable | content | 8K quarter low/high (mark) |
|---|---|---|---|---|
| 20 | D49DECF0 | yes | internal bank 0 | None / None |
| 40 | D49DECF0 | yes | internal bank 0 | None / None |
| 90 | 7ADC7C79 | yes | cartridge/other | 0 / 1 |
| A0 | 7ADC7C79 | yes | cartridge/other | 0 / 1 |
| C0 | 7ADC7C79 | yes | cartridge/other | 0 / 1 |

Selectors that give the same content (mirrors): 20 = 40; 90 = A0 = C0

---
Generated by tools/hwtest_rx.py. The quarter marks (0..3) come from the 32 bytes at 0x1BE0 of each 8 KiB of the EEPROM image.
