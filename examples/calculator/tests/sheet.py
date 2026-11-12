#!/usr/bin/env python3
# Joins the native LCD snapshots of a run (tests/shots.txt) into one picture: tests/sheet.py <dir> <out.png>
# Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
import glob
import sys

from PIL import Image

fs = sorted(glob.glob(sys.argv[1] + "/genio2000/*.png"))
sheet = Image.new("RGB", (2 * 490, (len(fs) + 1) // 2 * 170), "white")
for i, f in enumerate(fs):
    sheet.paste(Image.open(f).convert("RGB").resize((480, 160), Image.NEAREST), ((i % 2) * 490, (i // 2) * 170))
sheet.save(sys.argv[2])
