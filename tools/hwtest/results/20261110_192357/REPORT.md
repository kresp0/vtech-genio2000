# HWTEST results (HW, measured on the unit; none of this is MAME)

Captured: 2026-11-10 21:48:52. Rejected frames: 1, line errors: 0. End of program received: yes.

## Stages
- A (entry state + RAM copy): done
- B (IN ports 00..FF): done
- C (CPU clock bursts): done
- D (IRQ rate): SKIPPED
- E (LCD + LED questions): done
- F (keyboard matrix log): SKIPPED
- G (charset pages (photos)): done
- H (port 03 <- 00..07): done
- I (port 03 <- 80..8F): done
- J (port 03 <- 08..1F): done
- K (cartridge /WR probe): done
- L (port 03 <- 20 40 90 A0 C0): done

## A. Entry state
- cartridge `YE (autostart)`  SP=DFEE  build 0100  session 008C
- `LD A,I`: F=40 (bit 2 = IFF2 -> interrupts disabled) I=00
- DFF0..DFF7 = 14 00 00 80 14 33 00 00  (DFF1/DFF3 = shadows of ports 01/03, DFF4/DFF5 = bank and hook of the ISR)
- copy of C000-FFFF: 128/128 blocks received (`mem_C000_FFFF.bin`)
- E000-FFFF: 61/64 blocks identical to their pair at C000-DFFF (mirror), 0 all FF, 0 all 00

## B. Port reads (3 reads per port; 0A/0B deliberately not read)

| port | reads |
|---|---|
| 00 | FF FF FF |
| 01 | FF FF FF |
| 02 | FF FF FF |
| 03 | FF FF FF |
| 04 | FF FF 7F |
| 05 | FF FF FF |
| 06 | FF FF FF |
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
| 14 | 7F 7F 7F |
| 15 | F7 F7 F7 |
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
| 24 | 7F 7F 3F |
| 26 | 7E 7E 7E |
| 2C | 2F 2F 2F |
| 2D | ED ED ED |
| 2E | 2E 2E 2E |
| 2F | EF EF EF |
| 31 | 5F 5F 5F |
| 32 | 16 16 16 |
| 33 | FB FB FB |
| 34 | 37 37 37 |
| 35 | F5 F5 F5 |
| 36 | 36 36 36 |
| 37 | F7 F7 F7 |
| 38 | 3F 3F 3F |
| 39 | 7B 7B 7B |
| 3A | 3A 3A 3A |
| 3B | FB FB FB |
| 3C | 3E 3F 3F |
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
| 58 | 5F 7F 7F |
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
| 65 | 7F 7F 7F |
| 66 | 7E 7E 7E |
| 67 | 7F 7F 7F |
| 6C | 6E 6E 6E |
| 6D | 6D 6D 6D |
| 6E | 6E 6E 6E |
| 6F | 6F 6F 6F |
| 71 | 5F 5F 5F |
| 72 | 16 16 16 |
| 73 | 7B 7B 7B |
| 74 | 76 76 76 |
| 75 | 75 75 75 |
| 76 | 76 76 76 |
| 77 | 77 77 77 |
| 78 | 7A 7A 7A |
| 79 | 7B 7B 7B |
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
| 93 | FB FF FB |
| 94 | F7 F7 F7 |
| 95 | F5 F5 F5 |
| 96 | B6 B6 B6 |
| 97 | F7 F7 F7 |
| 98 | FF BF BF |
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
| A5 | BF BD BD |
| A6 | BE BE BE |
| A7 | BF BF BF |
| AC | AF AF AF |
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
| B8 | BF BF BF |
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
| CE | FE FE FE |
| CF | DF DF DF |
| D1 | 5F 5F 5F |
| D2 | 16 16 16 |
| D3 | DB DB DB |
| D4 | D7 D7 D7 |
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
- period per byte (s): [0.001096562708656565, 0.002199466982224038]
- **estimated CPU clock: 6.101 MHz** (T per byte in burst 1: 6690)

## E. LCD/LED questions

| # | question | answer | expected (MAME/datasheet) |
|---|---|---|---|
| 1 | all cells = code 00 show a solid block | S | S |
| 2 | rewriting CGRAM 0 changes ALL cells at once (live read) | S | S |
| 3 | codes 0-7 show 8 different shapes | S | S |
| 4 | rewriting CGRAM changes everything at once | S | S |
| 5 | codes 08-0F look the same as 00-07 (mirror) | S | S |
| 6 | a LED blinked 3 times (port 0x12 bit 5) | N | S |

## K. /WR probe of the cartridge (one write of the same value at 9BF0 from RAM)
- original value 00; 16 immediate reads: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00; read after 70 ms: 00; final read from the code: 00
- no write-cycle signals: /WR does **not** seem to reach the EEPROM (or there is no effective write); it does NOT prove that the connector has no /WR
- content intact

## H-K. Port 03: window 8000-BFFF per selector

| sel | CRC-32 16 KiB | stable | content | 8K quarter low/high (mark) |
|---|---|---|---|---|
| 00 | D49DECF0 | yes | internal bank 0 | None / None |
| 01 | 67EBAB51 | yes | internal bank 1 | None / None |
| 02 | 35C99AC6 | yes | internal bank 2 | None / None |
| 03 | 021A7E5B | yes | internal bank 3 | None / None |
| 04 | 8A1F0214 | yes | internal bank 4 | None / None |
| 05 | 63924486 | yes | internal bank 5 | None / None |
| 06 | 8F71AB6E | yes | internal bank 6 | None / None |
| 07 | F28A4E52 | yes | internal bank 7 | None / None |
| 08 | D49DECF0 | yes | internal bank 0 | None / None |
| 09 | 67EBAB51 | yes | internal bank 1 | None / None |
| 0A | 35C99AC6 | yes | internal bank 2 | None / None |
| 0B | 021A7E5B | yes | internal bank 3 | None / None |
| 0C | 8A1F0214 | yes | internal bank 4 | None / None |
| 0D | 63924486 | yes | internal bank 5 | None / None |
| 0E | 8F71AB6E | yes | internal bank 6 | None / None |
| 0F | F28A4E52 | yes | internal bank 7 | None / None |
| 10 | D49DECF0 | yes | internal bank 0 | None / None |
| 11 | 67EBAB51 | yes | internal bank 1 | None / None |
| 12 | 35C99AC6 | yes | internal bank 2 | None / None |
| 13 | 021A7E5B | yes | internal bank 3 | None / None |
| 14 | 8A1F0214 | yes | internal bank 4 | None / None |
| 15 | 63924486 | yes | internal bank 5 | None / None |
| 16 | 8F71AB6E | yes | internal bank 6 | None / None |
| 17 | F28A4E52 | yes | internal bank 7 | None / None |
| 18 | D49DECF0 | yes | internal bank 0 | None / None |
| 19 | 67EBAB51 | yes | internal bank 1 | None / None |
| 1A | 35C99AC6 | yes | internal bank 2 | None / None |
| 1B | 021A7E5B | yes | internal bank 3 | None / None |
| 1C | 8A1F0214 | yes | internal bank 4 | None / None |
| 1D | 63924486 | yes | internal bank 5 | None / None |
| 1E | 8F71AB6E | yes | internal bank 6 | None / None |
| 1F | F28A4E52 | yes | internal bank 7 | None / None |
| 20 | D49DECF0 | yes | internal bank 0 | None / None |
| 40 | D49DECF0 | yes | internal bank 0 | None / None |
| 80 | B849702B | yes | cartridge/other | 0 / 1 |
| 81 | B849702B | yes | cartridge/other | 0 / 1 |
| 82 | 2C078205 | yes | cartridge/other | 2 / 3 |
| 83 | 2C078205 | yes | cartridge/other | 2 / 3 |
| 84 | B849702B | yes | cartridge/other | 0 / 1 |
| 85 | B849702B | yes | cartridge/other | 0 / 1 |
| 86 | 2C078205 | yes | cartridge/other | 2 / 3 |
| 87 | 2C078205 | yes | cartridge/other | 2 / 3 |
| 88 | B849702B | yes | cartridge/other | 0 / 1 |
| 89 | B849702B | yes | cartridge/other | 0 / 1 |
| 8A | 2C078205 | yes | cartridge/other | 2 / 3 |
| 8B | 2C078205 | yes | cartridge/other | 2 / 3 |
| 8C | B849702B | yes | cartridge/other | 0 / 1 |
| 8D | B849702B | yes | cartridge/other | 0 / 1 |
| 8E | 2C078205 | yes | cartridge/other | 2 / 3 |
| 8F | 2C078205 | yes | cartridge/other | 2 / 3 |
| 90 | B849702B | yes | cartridge/other | 0 / 1 |
| A0 | B849702B | yes | cartridge/other | 0 / 1 |
| C0 | B849702B | yes | cartridge/other | 0 / 1 |

Selectors that give the same content (mirrors): 00 = 08 = 10 = 18 = 20 = 40; 01 = 09 = 11 = 19; 02 = 0A = 12 = 1A; 03 = 0B = 13 = 1B; 04 = 0C = 14 = 1C; 05 = 0D = 15 = 1D; 06 = 0E = 16 = 1E; 07 = 0F = 17 = 1F; 80 = 81 = 84 = 85 = 88 = 89 = 8C = 8D = 90 = A0 = C0; 82 = 83 = 86 = 87 = 8A = 8B = 8E = 8F

---
Generated by tools/hwtest_rx.py. The quarter marks (0..3) come from the 32 bytes at 0x1BE0 of each 8 KiB of the EEPROM image.
