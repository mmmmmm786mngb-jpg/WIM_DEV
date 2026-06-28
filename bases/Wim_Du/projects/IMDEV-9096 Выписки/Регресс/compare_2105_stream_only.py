#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
REG = SCRIPT_DIR / "Регресс2105"
sys.path.insert(0, str(SCRIPT_DIR))

from compare_2105_final import parse_pp_stream, find_pp_by_number, pp_core_key, PP_CORE, PP_LINK, extract_hash_cells
from compare_mxl import parse_rows
from compare_2105_robust import compare_vypiski, vypiski_alt_key
from collections import Counter

vb = extract_hash_cells(REG / "2105_2105_ПП_было.mxl")
vs = extract_hash_cells(REG / "2105_2105_ПП_стало.mxl")
sb, ss = parse_pp_stream(vb), parse_pp_stream(vs)

keys = set(sb) | set(ss)
only_b, only_s, core_diff, link_diff = [], [], [], []
for k in sorted(keys):
    rb = sb.get(k) or find_pp_by_number(vb, k[0], k[1])
    rs = ss.get(k) or find_pp_by_number(vs, k[0], k[1])
    if rb is None:
        only_s.append(k)
        continue
    if rs is None:
        only_b.append(k)
        continue
    if pp_core_key(rb) != pp_core_key(rs):
        core_diff.append(k)
    if rb.get(PP_LINK, "").strip() != rs.get(PP_LINK, "").strip():
        link_diff.append((k, rb.get(PP_LINK, "")[:60], rs.get(PP_LINK, "")[:60]))

print("STREAM ONLY: bylo", len(sb), "stalo", len(ss), "union", len(keys))
print("only BYLO", len(only_b), only_b[:5])
print("only STALO", len(only_s), only_s[:5])
print("core diffs", len(core_diff), core_diff[:5])
print("link diffs", len(link_diff))
for item in link_diff[:5]:
    print(" ", item)
