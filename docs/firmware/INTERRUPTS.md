# INTERRUPTS

## Mode and vectors (CONFIRMED)
* `IM 1` at reset (0002). Vector 0x0038 -> `JP 0119` (ISR). `EI` at 10D8 (start-up) and 1210 (RST 30h).
* **NMI (0x0066)**: there is no routine; that offset falls in the middle of `JP 34F9` (bytes `F9 34 C3`). It is inferred (PROBABLE) that the NMI line is unused or not connected. Not verified on HW.
* Frequency of the periodic interrupt: **46.76 Hz measured on HW** (hwtest stage D v2, 1,000 IRQs in 21.39 s; the firmware counter `DB28/29` agrees) = 6.13179 MHz / 2^17 (46.78 Hz) within 0.05 %: **the divisor 2^17 of the CPU clock is the hypothesis** (HYPOTHESIS; the physical source is still unidentified: no visible timer in the ports). MAME uses an *invented* 50 Hz timer: it does not match the hardware.

## Routine (0x0119-0x015B, 0x016A-0x018B)
```
push af,bc,de,hl,ix,iy
call 01A8        ; keyboard scan (if DB00 != D0)
ld a,(DFF1); push af
call 018E        ; A=(DFF4); OUT(01),A; DFF1=A; JP (DFF5)   -> secondary hook (default 0033 = RET)
pop af; OUT (01),A; (DFF1)=A    ; restores window 1
call 057E        ; LCD refresh (dirty rows, cursor)
; inactivity counter
if DB00 == D0 -> DB26=0 (015D) ; if DB01 == B4 ... else
else   DB26 += 1 ; DB28 += 1 ; if DB26 >= BA54 -> switch off (016A)
pop iy..af ; EI ; RETI
```
* **Automatic switch-off** (016A-018B): `call 0621; 0608` (cursor / screen), shows "¡HASTA LUEGO!" (string at 019A), `A=7; CALL 0098` (sound), `OUT (12),01; HALT; JR $`. The counter `DB26` is set to 0 when `DB00==D0` (key pending) and incremented on every interrupt otherwise: threshold `0xBA54` = 47,700 interrupts, about **17.0 min** at the 46.78 Hz measured on HW (not at 50 Hz). PROBABLE (function) / HW (frequency). Note: `HALT` itself switches the unit off (see HW below).
* The ISR does **not** save `AF'`, `BC'`.. (alternate registers): the calling code/hook must not use them (CONFIRMED: there is no `EXX`/`EX AF,AF'` in 0119-015B).
* The ISR temporarily changes window 1, so hooks cannot assume which bank was mapped.

## For your own software (cartridges)
* A cartridge that starts through `55 AA 59 45` receives control with `EI` **not** yet executed (`DI` since reset; `IFF2=0` observed on HW, see the dumper repository, https://github.com/kresp0/vtech-genio2000-rom-dumper). Without `EI` there is no keyboard and no LCD refresh through the ISR: the cartridge either enables `EI` (and then ISR+LCD keep working with the API) or handles everything directly.
* With `EI`, the cartridge must keep `SP` in RAM and not touch `DFF1/DFF3/DFF4/DFF5` unless it knows what it is doing.

## HW (2026-11-10, hwtest; details in HW_RESULTS_20261110)
* IFF2 = 0 when a YE cartridge is entered; `DFF4 = 14`, `DFF5/6 = 0033` (RET).
* **46.76 Hz** measured with the firmware ISR running 1,100 times (EI + busy wait, own hook at `DFF5` that counts); `DB28/29` counts the same ticks. During the test `DB00 = D0`, `DB01 = F9` and `DB26/27` stays at 0.
* **`HALT` switches the unit off** (PROBABLE by difference: the test with `EI`+`HALT` switched it off; the same ISR without `HALT` did not). The only `HALT` in the firmware is the farewell one (`B0:018B`). **A cartridge must not use `HALT`.**
