# -*- coding: utf-8 -*-
"""Сравнение модулей BSL двух релизов по процедурам: новые, удаленные, измененные (число строк разницы).
python diff_procs.py <старый.bsl> <новый.bsl>"""
import difflib, re, sys
sys.stdout.reconfigure(encoding="utf-8")
HEAD = re.compile(r'^\s*(Процедура|Функция)\s+([\wА-Яа-яЁё]+)\s*\(', re.I)
END = re.compile(r'^\s*(КонецПроцедуры|КонецФункции)', re.I)

def procs(path):
    lines = open(path, encoding="utf-8-sig").read().splitlines()
    out, cur, buf = {}, None, []
    for l in lines:
        m = HEAD.match(l)
        if m:
            cur, buf = m.group(2), [l]
            continue
        if cur:
            buf.append(l)
            if END.match(l):
                out[cur] = [x.rstrip() for x in buf]
                cur = None
    return out

old, new = procs(sys.argv[1]), procs(sys.argv[2])
for name in sorted(set(old) | set(new), key=lambda n: (n not in new, n)):
    if name not in old:
        print(f"НОВАЯ     {name} ({len(new[name])} строк)")
    elif name not in new:
        print(f"УДАЛЕНА   {name} ({len(old[name])} строк)")
    else:
        d = [l for l in difflib.unified_diff(old[name], new[name], lineterm="", n=0) if l[:1] in "+-" and not l.startswith(("+++", "---"))]
        if d:
            print(f"ИЗМЕНЕНА  {name}: -{sum(1 for l in d if l[0]=='-')} +{sum(1 for l in d if l[0]=='+')}")
