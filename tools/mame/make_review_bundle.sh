#!/bin/bash
# make_review_bundle.sh – packs PRs 1-3 for an outside review (e.g. by ChatGPT) into review/genio2000_review_PR1-3.zip: the three patches, the PR texts,
# and background documents.  NO ROM data (the patches carry hashes only; this is checked), local paths are scrubbed.  The prompt to paste is review_prompt.txt.
set -e; H=$(cd "$(dirname "$0")/.." && pwd); cd "$H"
OUT=review; B=$OUT/bundle; rm -rf $B; mkdir -p $B/patches $B/context
cp patches/upstream-pr-series/000[123]-*.patch $B/patches/
# the descriptions of PR 1-3 from docs/PR_DRAFT.md (everything up to the heading of PR 4)
awk '/^## PR 4 /{exit} {print}' docs/PR_DRAFT.md > $B/PR_descriptions_1-3.md
for f in MAME_POLICY MEMORY_MAP CGROM KEYBOARD CLOCK_AND_SOUND HARDWARE KNOWN_LIMITATIONS; do cp docs/$f.md $B/context/; done
cat > $B/README_FOR_REVIEWER.txt <<'TXT'
Contents
  patches/            the three pull requests as `git format-patch` files (apply in order 0001, 0002, 0003 on top of mamedev/mame master c7541016)
  PR_descriptions_1-3.md   the draft descriptions to be posted with each PR (the AI disclosure is part of them)
  context/            background: MAME contribution policy summary, memory map, character set notes, keyboard notes (with the measurements done on the unit),
                      clock and sound notes, hardware facts, known limitations
No ROM data is included: the firmware (27-5575-00) and the reconstructed character table are submitted separately to MAMEdev; the patches contain only their hashes.
Only src/mame/vtech/pc2000.cpp and src/mame/mame.lst change. Later follow-up PRs (LCD drawing, OFF/ON, LED, speaker, contrast) are not part of this review.
TXT
# scrub local paths / user names
find $B -type f \( -name '*.md' -o -name '*.txt' -o -name '*.patch' \) -exec sed -i "s#$HOME[^ )\`'\"]*#<home>#g" {} +
# safety: no binary data and no ROM-like content
if grep -r -a -l -P '[\x80-\xff]{16}' $B/patches >/dev/null 2>&1; then echo "REFUSED: binary-looking data in a patch"; exit 1; fi
if grep -r -l -E "ROM_LOAD.*0x[0-9a-f]{40}" $B >/dev/null 2>&1; then echo "REFUSED: unexpected content"; exit 1; fi
(cd $OUT && rm -f genio2000_review_PR1-3.zip && cd bundle && zip -q -r ../genio2000_review_PR1-3.zip .)
cp review_prompt.txt $OUT/PROMPT.txt
echo "zip:    $H/$OUT/genio2000_review_PR1-3.zip ($(du -h $OUT/genio2000_review_PR1-3.zip | cut -f1))"; unzip -l $OUT/genio2000_review_PR1-3.zip | tail -n +4 | head -20
echo "prompt: $H/$OUT/PROMPT.txt (also review_prompt.txt)"
