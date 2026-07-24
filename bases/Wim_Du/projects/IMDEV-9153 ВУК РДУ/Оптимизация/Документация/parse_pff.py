#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse 1C .pff performance measurement and rank hotspots."""

import re
from pathlib import Path
from collections import defaultdict

p = Path(r"C:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-9153 ВУК РДУ\замерУдаления.pff")
text = p.read_text(encoding="utf-8-sig")

# Entry fragment: },"Module",line,"code",count,t1,t2,
pat = re.compile(
    r'\},"([^"]+)",(\d+),"((?:\\.|[^"\\])*)",(\d+),([0-9.eE+-]+),([0-9.eE+-]+),',
)

rows = []
for m in pat.finditer(text):
    module, line, code, cnt, t1, t2 = m.groups()
    code = code.replace('\\"', '"').replace("\\n", " ")
    rows.append(
        {
            "module": module,
            "line": int(line),
            "code": code[:160],
            "count": int(cnt),
            "t1": float(t1),
            "t2": float(t2),
        }
    )

print("parsed_rows", len(rows))

by_mod = defaultdict(lambda: {"count": 0, "t1": 0.0, "t2": 0.0})
for r in rows:
    b = by_mod[r["module"]]
    b["count"] += r["count"]
    b["t1"] += r["t1"]
    b["t2"] += r["t2"]

print("\n=== TOP modules by sum t2 (often wall/cumulative) ===")
for mod, b in sorted(by_mod.items(), key=lambda x: -x[1]["t2"])[:30]:
    print(f"{b['t2']:12.3f}s  cnt={b['count']:8d}  {mod}")

print("\n=== TOP modules by sum t1 (often pure) ===")
for mod, b in sorted(by_mod.items(), key=lambda x: -x[1]["t1"])[:30]:
    print(f"{b['t1']:12.3f}s  cnt={b['count']:8d}  {mod}")

print("\n=== TOP individual lines by t2 ===")
for r in sorted(rows, key=lambda x: -x["t2"])[:50]:
    mod = r["module"][-70:]
    print(f"{r['t2']:12.4f}s x{r['count']:6d} L{r['line']:4d} {mod} | {r['code'][:90]}")

# Keywords for our processing
print("\n=== Lines mentioning delete/register/write in our processing ===")
kw = ("удалить", "обязател", "операци", "записать", "прочитать", "наборзапис", "регистратор")
rel = []
for r in rows:
    blob = (r["module"] + " " + r["code"]).lower()
    if any(k in blob for k in kw) or "внешняяобработка" in blob or "objectmodule" in blob.lower():
        rel.append(r)

seen = set()
uniq = []
for r in sorted(rel, key=lambda x: -x["t2"]):
    key = (r["module"], r["line"], r["code"][:50])
    if key in seen:
        continue
    seen.add(key)
    uniq.append(r)

for r in uniq[:60]:
    mod = r["module"][-70:]
    print(f"{r['t2']:12.4f}s x{r['count']:6d} L{r['line']:4d} {mod} | {r['code'][:90]}")

# Aggregate by code snippet (normalized)
print("\n=== TOP by code text (sum t2) ===")
by_code = defaultdict(lambda: {"count": 0, "t2": 0.0, "t1": 0.0, "mod": ""})
for r in rows:
    c = re.sub(r"\s+", " ", r["code"]).strip()[:100]
    b = by_code[c]
    b["count"] += r["count"]
    b["t2"] += r["t2"]
    b["t1"] += r["t1"]
    b["mod"] = r["module"][-50:]

for code, b in sorted(by_code.items(), key=lambda x: -x[1]["t2"])[:40]:
    print(f"{b['t2']:12.3f}s x{b['count']:6d} {b['mod']} | {code}")
