#!/bin/bash
# check_all.sh – reproducible acceptance run: hashes, driver validation, full pytest suite. Exit status 0 only if everything passes.
set -e; H=$(dirname "$0")/..; cd "$H"
echo "== hashes"; sha1sum roms_local/genio2000/27-5575-00 roms_local/genio2000/genio2000_cgrom_reconstructed.bin | tee work/hashes_now.txt
grep -q 76e41bc3b19f3f0c0ae4605257ba4ee9d812659f work/hashes_now.txt; grep -q 0ad6de16db67c014f44211dfd1328091be389cc7 work/hashes_now.txt
echo "== keyboard generator vs firmware"; python3 tools/gen_keyboard_ports.py --out /dev/null
echo "== validate"; mame/genio -validate; echo "validate rc=$?"
echo "== pytest"; python3 -m pytest -q tests -p no:cacheprovider
echo "== no commercial data in the patches"; ! grep -a -P '[\x80-\xff]{16}' patches/*/*.patch && echo clean
