# BASIC_REFERENCE: statements and functions **present in the ROM**

Syntax: *no syntax has been verified except where stated*. "EMU test" = behaviour observed in MAME (`tools/analysis/kb.py`).

| Token | Word | Handler | Executed (EMU) | Notes |
|---|---|---|---|---|
| 0x80 | END | 0x5DAE | yes |  |
| 0x81 | FORMAT | 0x424C | no |  |
| 0x82 | FOR | 0x5CA1 | yes | `10 FOR I=1 TO 3 / 20 PRINT I / 30 NEXT I / RUN` prints " 1" and waits (EMU) |
| 0x84 | CLS | 0x41C9 | yes | clears the screen (executed) |
| 0x87 | NEXT | 0x62B6 | no |  |
| 0x88 | DATA | 0x5F05 | yes | executed |
| 0x89 | INPUT | 0x619A | no |  |
| 0x8A | DIM | 0x6608 | yes |  |
| 0x8B | READ | 0x61EF | yes | executed |
| 0x8C | LET | 0x5F21 | yes | `LET A=5` executed |
| 0x8D | GOTO | 0x5EC2 | yes |  |
| 0x8E | RUN | 0x5EA3 | yes | Runs; see FOR |
| 0x8F | IF | 0x6039 | yes | `15 IF A=5 THEN 20` accepted |
| 0x90 | RESTORE | 0x5D91 | yes |  |
| 0x91 | GOSUB | 0x5EB1 | no |  |
| 0x92 | RETURN | 0x5EDE | no |  |
| 0x93 | REM | 0x5F07 | yes |  |
| 0x94 | STOP | 0x5DA9 | yes | "BREAK IN 70" (EMU) |
| 0x95 | ELSE | 0x5F07 | yes |  |
| 0x96 | LOAD | 0x7827 | no |  |
| 0x97 | ERASE | 0x7B9E | no |  |
| 0x99 | SAVE | 0x786B | no |  |
| 0x9A | DIR | 0x7BCE | no |  |
| 0x9E | EDIT | 0x7534 | no |  |
| 0xAF | LPRINT | 0x6067 | no |  |
| 0xB2 | PRINT | 0x606F | yes | Seen: `PRINT 1+2` -> " 12" with a sign space. Test: `print 12` |
| 0xB3 | CONT | 0x5DE4 | no |  |
| 0xB4 | LIST | 0x6E93 | yes | Shows lines one by one (4x20 screen) |
| 0xB5 | LLIST | 0x6B29 | no |  |
| 0xB6 | DELETE | 0x6BC6 | no |  |
| 0xB7 | AUTO | 0x6008 | no |  |
| 0xB8 | CLEAR | 0x5E7A | no |  |
| 0xBB | NEW | 0x5B49 | no | typed in test C; effect not verified |

## Functions and operators (tokens 0xBC-0xFA)
`TAB(` `TO` `USING` `THEN` `NOT` `STEP` `+ - * / ^` `AND` `OR` `> = <` `SGN` `INT` `ABS` `SQR` `RND` `LOG` `EXP` `COS` `SIN` `TAN` `ATN` `LEN` `STR$` `VAL` `ASC` `CHR$` `LEFT$` `RIGHT$` `MID$`.

Function handlers: table not yet resolved (see BASIC_INTERNALS).

## Test programs
Reproducible with `python3 -I dyn_batch.py` (see RESEARCH_LOG). Example without special symbols:
```basic
10 FOR I=1 TO 3
20 PRINT I
30 NEXT I
RUN
```
