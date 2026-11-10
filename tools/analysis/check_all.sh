#!/bin/bash
# Re-run the cheap, deterministic checks (no MAME needed except check_dis' unidasm).
set -e; cd "$(dirname "$0")/.."
python3 -I tools/romid.py >/dev/null && echo "romid ok"
python3 -I tools/check_dis.py | tail -1
python3 -I tests/test_findings.py | tail -1
