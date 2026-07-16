#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check taxonomy labels for problematic OKATO members."""

import zipfile
import re
from pathlib import Path

needles = [
    "OKATO74000HersonskayaObl",
    "OKATO21000DoneczkayaNarodnResp",
    "OKATO43000LuganskayaNarodnResp",
    "OKATO23000ZaporozhObl",
    "OKATO70000TulskayaOblast",  # control: should exist
]

tax = Path(r"C:\Users\Acer\AppData\Local\XBRLConverter\Taxonomies\20251230.zip")
if not tax.exists():
    print("taxonomy zip not found:", tax)
    raise SystemExit(1)

z = zipfile.ZipFile(tax)
labs = [n for n in z.namelist() if "mem-int" in n.lower() and "label" in n.lower() and n.endswith(".xml")]
print("mem-int label files:", len(labs))
for lab in labs:
    print(" ", lab)

text_all = "".join(z.read(lab).decode("utf-8", errors="replace") for lab in labs)

for n in needles:
    print("\n===", n, "===")
    if n not in text_all:
        print(" NOT found in mem-int-label XML")
        continue
    print(" found in mem-int-label")
    # locator label ids
    locs = re.findall(
        r'xlink:href="[^"]*' + re.escape(n) + r'[^"]*"[^>]*xlink:label="([^"]+)"',
        text_all,
    )
    locs += re.findall(
        r'xlink:label="([^"]+)"[^>]*xlink:href="[^"]*' + re.escape(n),
        text_all,
    )
    locs = list(dict.fromkeys(locs))
    print(" locator labels:", locs[:5])
    for loc in locs[:3]:
        arcs = re.findall(
            r'xlink:from="' + re.escape(loc) + r'"[^>]*xlink:to="([^"]+)"',
            text_all,
        )
        print(" arcs to:", arcs[:8])
        for res in arcs[:8]:
            m = re.search(
                r'xlink:label="' + re.escape(res) + r'"[^>]*>([^<]+)<',
                text_all,
            )
            if m:
                print("  LABEL:", m.group(1)[:120])

# Also search dictionary-label / any label for Hersonskaya
print("\n=== broader search in all label xml ===")
all_label = [n for n in z.namelist() if "label" in n.lower() and n.endswith(".xml")]
hits = {n: 0 for n in needles}
for lab in all_label:
    t = z.read(lab).decode("utf-8", errors="replace")
    for n in needles:
        if n in t:
            hits[n] += 1
for n, c in hits.items():
    print(f" {n}: in {c} label files")
