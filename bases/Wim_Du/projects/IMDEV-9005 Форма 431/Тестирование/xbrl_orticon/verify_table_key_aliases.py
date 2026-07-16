#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify taxonomy table key aliases and Sokr labels for section 2."""

import os
import re
import zipfile
from pathlib import Path

TPL = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-9005 Форма 431"
    r"\Обработки\внВыгрузкаXBRLОртиконВXLSX\Templates\Таксономия_20251230\Ext\Template.bin"
)


def full_key(name):
    name = os.path.basename(name)
    if name.lower().endswith(".xml"):
        name = name[:-4]
    low = name.lower()
    if low.endswith("-rend"):
        name = name[:-5]
    elif low.endswith("-lab"):
        name = name[:-4]
    return name


def form_code(name):
    m = re.search(r"SR_(\d{7})", name, re.I)
    return m.group(1) if m else ""


def section_from_second_sr(name):
    up = name.upper()
    if up.count("SR_") < 2:
        return ""
    p1 = up.find("SR_")
    rest = up[p1 + 3 :]
    p2rel = rest.find("SR_")
    if p2rel < 0:
        return ""
    p2 = p1 + 3 + p2rel
    tail = name[p2 + 3 :]
    m = re.match(r"[0-9_]+", tail)
    if not m:
        return ""
    s = m.group(0).rstrip("_")
    return s if len(s) >= 7 else ""


def short_key(name):
    code = form_code(name)
    if not code:
        return ""
    sec = section_from_second_sr(name)
    if sec:
        return sec
    if "_r2" in name.lower():
        return code + "_r2"
    return code


def aliases(name):
    out = []
    seen = set()
    for k in (full_key(name), short_key(name)):
        if k and k not in seen:
            out.append(k)
            seen.add(k)
    sk = short_key(name)
    code = form_code(name)
    if code and "_r2" in sk.lower():
        alias = code + "_2"
        if alias not in seen:
            out.append(alias)
    return out


def candidates_for_sheet(table_key, name, toc):
    """Mirror КандидатыКлючейМетаданныхЛиста."""
    result = []
    seen = set()

    def add(k):
        if k and k not in seen:
            result.append(k)
            seen.add(k)

    text = ("%s %s %s" % (name, toc, table_key)).lower()
    is_r2 = (
        "раздел 2" in text
        or "_r2" in text
        or (table_key and table_key.upper().count("SR_") >= 2)
    )
    code = form_code(table_key) or (re.search(r"0\d{6}", name) or [None])[0]

    if table_key:
        add(table_key)
        for a in aliases(table_key):
            add(a)
    if is_r2 and code:
        add(code + "_2")
        add(code + "_r2")
    if code:
        add(code)
    return result


def main():
    files = [
        "SR_0420409_m-rend.xml",
        "SR_0420409_m-SR_0420409_2-rend.xml",
        "SR_0420414-rend.xml",
        "SR_0420414_r2-rend.xml",
        "SR_0420459-rend.xml",
        "SR_0420459-SR_0420459_2_1-rend.xml",
    ]
    print("=== key aliases ===")
    for f in files:
        print(f, "->", aliases(f))

    print("\n=== sheet candidates ===")
    print(
        "R2 409:",
        candidates_for_sheet(
            "SR_0420409_m-SR_0420409_2",
            "0420409 Раздел 2. Сведения",
            "0420409 Раздел 2",
        ),
    )
    print(
        "R1 409:",
        candidates_for_sheet(
            "SR_0420409_m",
            "0420409 Раздел 1. Сведения",
            "0420409 Раздел 1",
        ),
    )
    print(
        "R2 414:",
        candidates_for_sheet(
            "SR_0420414_r2",
            "0420414 Раздел 2",
            "0420414 Раздел 2",
        ),
    )

    print("\n=== Sokr labels in labs ===")
    with zipfile.ZipFile(TPL, "r") as z:
        for n in z.namelist():
            bn = os.path.basename(n)
            if "0420409" not in bn or not bn.endswith("-lab.xml") or "_q" in bn:
                continue
            data = z.read(n).decode("utf-8", errors="replace")
            hits = re.findall(r">([^<>]{0,40}окращенн[^<>]{0,120})<", data)
            hits = [re.sub(r"\s+", " ", h).strip() for h in hits]
            hits = [h for h in hits if h]
            uniq = []
            for h in hits:
                if h not in uniq:
                    uniq.append(h)
            print(bn, "aliases", aliases(bn))
            for h in uniq[:4]:
                print("  ", h[:130])


if __name__ == "__main__":
    main()
