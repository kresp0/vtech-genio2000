#!/usr/bin/env python3
# Prints the size of every function in the SDCC listing (largest first): python3 sizes.py [out/calc_gl2000.lst]
# Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
import re
import sys
res, cur, start, area = {}, None, 0, None
for l in open(sys.argv[1] if len(sys.argv) > 1 else "out/calc_gl2000.lst"):
    m = re.match(r"\s+([0-9A-F]{8})\s+\d+\s+(_\w+):", l)
    if m:
        a = int(m.group(1), 16)
        if cur: res[cur] = a - start
        cur, start = m.group(2), a
    m = re.match(r"\s+([0-9A-F]{8})\s", l)
    if m: endaddr = int(m.group(1), 16)
    if ".area" in l and cur:
        res[cur] = endaddr - start; cur = None
for k, v in sorted(res.items(), key=lambda x: -x[1]): print(v, k)
print("total", sum(res.values()))
