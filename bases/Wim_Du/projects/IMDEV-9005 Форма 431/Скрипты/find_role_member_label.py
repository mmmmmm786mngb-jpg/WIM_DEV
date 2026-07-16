#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find RU label for DepozOsushUchPravNaCZB in taxonomy."""

import re
import zipfile
from pathlib import Path

TAX = Path(r"C:\Users\Acer\AppData\Local\XBRLConverter\Taxonomies\20251230.zip")
NEEDLE = "DepozOsushUchPravNaCZB"


def main():
    z = zipfile.ZipFile(TAX)
    for n in z.namelist():
        if not n.endswith("-lab.xml"):
            continue
        t = z.read(n).decode("utf-8", errors="ignore")
        if NEEDLE not in t:
            continue
        print("FILE", n)
        # find label resources linked to this member
        # typical: label xlink:label="label_Depoz..." then arc from Depoz...
        for m in re.finditer(
            rf"<link:label[^>]*xlink:label=\"([^\"]+)\"[^>]*xml:lang=\"ru\"[^>]*>([^<]+)</link:label>",
            t,
        ):
            if NEEDLE.lower() in m.group(1).lower() or "депозит" in m.group(2).lower():
                if NEEDLE in t[max(0, m.start() - 500) : m.end() + 100] or NEEDLE.lower() in m.group(1).lower():
                    print(" ", m.group(1), "->", m.group(2)[:120])
        # simpler: windows around needle
        for m in re.finditer(NEEDLE, t):
            frag = t[max(0, m.start() - 100) : m.start() + 400]
            labs = re.findall(r'xml:lang="ru"[^>]*>([^<]+)', frag)
            if labs:
                print(" near:", labs[:3])
                print(" frag:", re.sub(r"\s+", " ", frag)[:300])
                break
        break

    # also check how labels are keyed in our loader - mem-int-lab
    for n in z.namelist():
        if "mem-int" in n and n.endswith("-lab.xml"):
            print("mem-int lab file", n)
            t = z.read(n).decode("utf-8", errors="ignore")
            if NEEDLE in t:
                idx = t.find(NEEDLE)
                print(re.sub(r"\s+", " ", t[idx - 80 : idx + 350])[:400])
            break


if __name__ == "__main__":
    main()
