# ROM_REVISIONS: two units, two revisions of the Spanish firmware

Second dump (2026-11-10), **another Genio 2000** (capture `capture_20261110_182327.bin`, sessions `06A1` and `0CCF`: 8/8 banks `COMPLETE_VERIFIED_BY_ROM_CRC`, 0 rejected frames, the two sessions identical byte for byte). The reference ROM remains the one from unit 1 (SHA-256 `f66f4d51...ea48`); unit 2 has SHA-256 `5e41fdab...cc771`. Neither has been modified. The ROM files are not part of this repository.

## Differences (CONFIRMED: byte-by-byte comparison of two verified dumps)
| Bank | Unit 1 CRC-32 | Unit 2 CRC-32 | Different bytes | What it is |
|---|---|---|---:|---|
| 0 | D49DECF0 | D49DECF0 | 0 | identical |
| 4, 5, 6 | 8A1F0214, 63924486, 8F71AB6E | same | 0 | identical (words, activities, editor/calculator) |
| 7 | F28A4E52 | 0468223B | **1** | `7:39AC` (logical `79AC`): `9C` -> `99` |
| 1 | 67EBAB51 | 14879354 | 15,865 | question bank: **14 questions corrected/changed** (the bit stream shifts after the first one, hence so many bytes) |
| 2 | 35C99AC6 | 13B41C7F | 16,331 | data of a still unknown format; it changes from offset 0 |
| 3 | 021A7E5B | 992915F8 | 5,176 | offsets `0000-1449` change; from `144A` it is identical |

### Bank 7: a single byte, in the BASIC file code
`79AB: 38 xx  jr c,...` (xx = 9C -> `79AD+9C-100 = 7949`; xx = 99 -> `7946`). `7949` = `xor a ; ret`; `7946` = `pop bc ; pop hl ; pop af ; xor a ; ret`. In unit 1 the "does not fit" branch leaves **without undoing the `push`es** of the routine; unit 2 pops them before returning. Reading (PROBABLE, from code; not executed): **a stack imbalance fix** in the file-space allocation routine (`7:7994...`, uses the directory at `8050` and window 8000). It is the only code change between the units.

### Bank 1: 14 different questions (decoded with `extract_data_banks.py` and `GENIO_ROM`/`GENIO_TAG`)
It fixes typos of unit 1 (`R2C2`->`R2D2`, `FRANKESNSTEIN`->`FRANKENSTEIN`, `GINGE`->`GINGER`, `JAGER`->`JAGGER`, `KATMANDU ... LA INDIA \ INDIA`->`NEPAL`, a missing full stop) and **changes the wording** of others (Cinderella, the Little Mermaid, Kevin Costner, the Ebro "rises"->"flows into"); it introduces at least one new typo (`767` instead of `776` as the first answer). Bank 4 (words): 2,601 entries **identical**.

## What it implies
* There are **at least two revisions** of the Spanish firmware (PROBABLE that unit 2 is the later one: it fixes more than it breaks; the direction is **not** proven). Any conclusion about banks 1, 2, 3 and 7 must say which unit it comes from. Banks 0, 4, 5 and 6 (core, words, activities, editor) are common.
* The "identical tails" between banks of unit 1 (banks 2=5: 1,095 B; 0=1: 401 B; see DATA_FORMATS) **do not exist in unit 2** (common tail 0 B in both pairs) and the null run of bank 3 goes from 967 B (`1439`) to 950 B (`144A`, same end `17FF`). They are therefore properties of that particular production run (padding), not of the architecture.
* For MAME the two images would have to be told apart if both were to be included (another set of ROMs or a hash per revision); **the driver has not been touched**.
* `hwtest_rx.py` recognises the internal banks of both units by CRC (on HW it will show which unit it runs on).

## Pending
Run `bank_dump_verify.py` on the capture to get the official manifest/hash of unit 2; identify the label/date of the chip or board of each unit; decode banks 2 and 3 in both units to see which text changes.
