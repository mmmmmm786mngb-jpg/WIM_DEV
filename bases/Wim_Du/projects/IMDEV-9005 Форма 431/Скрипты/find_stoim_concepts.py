#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find Stoim* concept names in CBR taxonomy."""

import re
import zipfile
from pathlib import Path

TAX = Path(r"C:\Users\Acer\AppData\Local\XBRLConverter\Taxonomies\20251230.zip")


def main():
    if not TAX.exists():
        print("missing", TAX)
        return
    z = zipfile.ZipFile(TAX)
    print("--- xsd concepts with Stoim/Summ/Postup/Izyat/Dox/Vrem ---")
    keys = ("Stoim", "Summ", "Postup", "Izyat", "Dox", "VremGor", "AktStoim", "Ocen")
    found = set()
    for n in z.namelist():
        if not n.endswith(".xsd"):
            continue
        if "dic" not in n.lower() and "purcb" not in n.lower():
            continue
        t = z.read(n).decode("utf-8", errors="ignore")
        for m in re.finditer(r'name="([^"]+)"', t):
            name = m.group(1)
            if any(k.lower() in name.lower() for k in keys):
                found.add(name)
    for name in sorted(found):
        print(" ", name)

    print("\n--- labels containing 'Стоимостная оценка на' ---")
    cnt = 0
    for n in z.namelist():
        if not n.endswith("-lab.xml"):
            continue
        t = z.read(n).decode("utf-8", errors="ignore")
        if "Стоимостная оценка на" not in t:
            continue
        # xlink label id near
        for m in re.finditer(
            r'xlink:label="([^"]+)"[^>]*>Стоимостная оценка на[^<]*',
            t,
        ):
            print(n[-70:], "->", m.group(1), m.group(0)[-80:])
            cnt += 1
            if cnt >= 15:
                break
        if cnt >= 15:
            break
        # alternate without attr order
        if cnt == 0:
            for m in re.finditer(r"(Stoim[A-Za-z0-9_]*)", t):
                pass
            # find label text and previous label id in 500 chars
            for m in re.finditer(r"Стоимостная оценка на отчетную дату", t):
                frag = t[max(0, m.start() - 300) : m.end() + 20]
                ids = re.findall(r'xlink:label="([^"]+)"', frag)
                print(n[-70:], "ids", ids[-3:], "...")
                cnt += 1
                if cnt >= 10:
                    break
        if cnt >= 10:
            break


if __name__ == "__main__":
    main()
