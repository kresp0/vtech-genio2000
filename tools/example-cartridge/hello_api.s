; hello_api.s -- smallest cartridge that uses the firmware API (bank-0 jump table). Boots at power-on via 55 AA 59 45.
; Build: see build.sh. Verified in MAME only (EMU), NOT on hardware.
        .area   _HEADER (ABS)
        .org    0x8000
        .db     0x55, 0xAA, 0x59, 0x45
        jp      start
start:
        ld      sp, #0xDFF0
        call    0x05CF          ; LCD init (0x38 x4, clear, home, display on, entry mode, CGRAM chars) - NOT yet done at autostart
        call    0x009B          ; lcd_clear
        ld      hl, #msg1
        call    0x00AD          ; lcd_puts_centered_row0
        ld      hl, #msg2
        call    0x00B0          ; lcd_puts_centered_row1
        ei                      ; the ISR refreshes the LCD from the RAM buffer
loop:
        jr      loop            ; NOT halt: on the real unit HALT powers it off (hwtest, 2026-11-10)
msg1:   .db     6, 'H','O','L','A','!'          ; length byte = chars + 1
msg2:   .db     13, 'G','E','N','I','O',' ','2','0','0','0','!','!'
