#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from collections import Counter
from pathlib import Path

REG = Path(__file__).resolve().parent

def read(p):
    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return p.read_text(encoding="utf-8", errors="replace")

b = read(REG / "СообщенияЗагрузкиВыписок_0906_было.txt")
s = read(REG / "СообщенияЗагрузкиВыписок_0906_стало.txt")

print("files byte-equal:", b == s)
print("lines:", len(b.splitlines()), len(s.splitlines()))

# normalize lines multiset
def norm_lines(t):
    return Counter(x.strip() for x in t.splitlines() if x.strip())

cb, cs = norm_lines(b), norm_lines(s)
diff = (cb - cs) + (cs - cb)
print("unique lines bylo/stalo:", len(cb), len(cs))
print("line multiset diff types:", len(diff))
if diff:
    for k, v in diff.most_common(10):
        side = "only_bylo" if (cb - cs).get(k) else "only_stalo"
        print(f"  {side} x{v}: {k[:120]}")

# load logs
lb = read(REG / "ЛогЗагрузкиВыписок_0906_было.txt")
ls = read(REG / "ЛогЗагрузкиВыписок_0906_стало.txt")
print("load log byte-equal:", lb == ls)
clb, cls = norm_lines(lb), norm_lines(ls)
d2 = (clb - cls) + (cls - clb)
print("load log line diff types:", len(d2))

DOC = re.compile(r'Перезаписан документ "(.+?)" № ([\w\-]+) от (\d{2}\.\d{2}\.\d{4})')
print("doc literal bylo:", b.count("Перезаписан документ"))
print("doc regex full:", len(DOC.findall(b)))

# categorize line diffs
timing = [k for k in diff if "время выполнения" in k]
rules_diff = [k for k in diff if k.startswith("Сработало Правило")]
other = [k for k in diff if k not in timing and not k.startswith("Сработало Правило")]
print("diff timing lines:", len(timing), "sum", sum(diff[k] for k in timing))
print("diff rule lines:", len(rules_diff), "sum", sum(diff[k] for k in rules_diff))
print("diff other lines:", len(other), "sum", sum(diff[k] for k in other))
for k in other[:15]:
    print("  other:", diff[k], k[:100])

# load log vypiska order
VYP = re.compile(r"Выписка:\s*(\d{2}\.\d{2}\.\d{4}).*ДУ\s+(\d+)")
def du_order(t):
    return [m.group(2) for m in VYP.finditer(t)]
ob, os_ = du_order(lb), du_order(ls)
print("load log vypiski count:", len(ob), len(os_))
print("same DU multiset:", Counter(ob) == Counter(os_))
print("same order:", ob == os_)
if ob != os_:
    first_diff = next(i for i, (a, c) in enumerate(zip(ob, os_)) if a != c)
    print("first order diff at index", first_diff, "bylo", ob[first_diff], "stalo", os_[first_diff])
