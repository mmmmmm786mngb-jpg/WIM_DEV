#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare sample XLSX export and XTDD XML export for same 0420431 document."""

from pathlib import Path
import zipfile
import re
import xml.etree.ElementTree as ET
from collections import Counter

BASE = Path(__file__).resolve().parent / "Обработки"
XLSX = next(BASE.glob("*.xlsx"))
XTDD = next(BASE.glob("*.xtdd"))


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def analyze_xlsx(path: Path):
    safe_print("=== XLSX ===")
    safe_print(f"file: {path.name}")
    safe_print(f"size: {path.stat().st_size}")
    with zipfile.ZipFile(path) as z:
        wb = z.read("xl/workbook.xml").decode("utf-8", errors="replace")
        sheets = re.findall(r'name="([^"]+)"', wb)
        safe_print(f"sheets ({len(sheets)}):")
        for s in sheets:
            safe_print(f"  - {s}")
        # sample first sheet shared strings count
        ss = z.read("xl/sharedStrings.xml").decode("utf-8", errors="replace") if "xl/sharedStrings.xml" in z.namelist() else ""
        safe_print(f"sharedStrings chars: {len(ss)}")
        # peek sheet1 dimensions via worksheet
        ws1 = z.read("xl/worksheets/sheet1.xml").decode("utf-8", errors="replace")
        dim = re.search(r'ref="([^"]+)"', ws1)
        rows = len(re.findall(r"<row ", ws1))
        safe_print(f"sheet1 dim: {dim.group(1) if dim else '?'} rows_approx: {rows}")


def local(tag):
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def analyze_xtdd(path: Path):
    safe_print("=== XTDD ===")
    safe_print(f"file: {path.name}")
    safe_print(f"size: {path.stat().st_size}")
    with open(path, "rb") as f:
        magic = f.read(4)
    safe_print(f"magic: {magic!r}")

    # try zip
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            safe_print(f"ZIP entries: {len(names)}")
            for n in names[:40]:
                safe_print(f"  {n}")
            if len(names) > 40:
                safe_print(f"  ... +{len(names)-40}")
            # peek main xml
            xml_names = [n for n in names if n.lower().endswith((".xml", ".xtdd"))]
            target = xml_names[0] if xml_names else names[0]
            data = z.read(target)
            text = data.decode("utf-8", errors="replace")
            safe_print(f"main entry: {target} bytes={len(data)}")
            safe_print("--- head ---")
            safe_print(text[:1500])
            parse_xml_structure(text)
            return
    except zipfile.BadZipFile:
        safe_print("not a ZIP, plain XML/binary")

    # plain text/xml
    raw = path.read_bytes()
    # try encodings
    for enc in ("utf-8-sig", "utf-8", "utf-16", "cp1251"):
        try:
            text = raw.decode(enc)
            safe_print(f"decoded as {enc}, chars={len(text)}")
            safe_print("--- head ---")
            safe_print(text[:1500])
            parse_xml_structure(text)
            return
        except Exception as e:
            safe_print(f"decode {enc} fail: {e}")


def parse_xml_structure(text: str):
    safe_print("--- structure ---")
    # namespaces in root
    root_m = re.search(r"<([A-Za-z0-9_:.-]+)([^>]*)>", text)
    if root_m:
        safe_print(f"root tag: {root_m.group(1)}")
        attrs = root_m.group(2)
        ns = re.findall(r'xmlns(?::([A-Za-z0-9_]+))?="([^"]+)"', attrs)
        for pref, uri in ns[:20]:
            safe_print(f"  xmlns{':' + pref if pref else ''}: {uri}")

    try:
        # strip BOM already handled
        root = ET.fromstring(text)
    except Exception as e:
        safe_print(f"ET parse fail: {e}")
        # try fix common issues
        return

    safe_print(f"root local: {local(root.tag)}")
    # child tag frequency at level 1-2
    children = [local(c.tag) for c in root]
    safe_print(f"level1 children count: {len(children)}")
    ctr = Counter(children)
    safe_print("level1 tag counts (top 40):")
    for name, cnt in ctr.most_common(40):
        safe_print(f"  {name}: {cnt}")

    # deeper: unique tag set under each top block
    by_parent = {}
    for c in list(root)[:50]:
        pname = local(c.tag)
        tags = [local(x.tag) for x in c.iter()]
        by_parent.setdefault(pname, Counter())
        by_parent[pname].update(tags)

    # sample first 5 distinct top children structure
    seen = set()
    samples = 0
    for c in root:
        pname = local(c.tag)
        if pname in seen:
            continue
        seen.add(pname)
        samples += 1
        kids = [local(k.tag) for k in c]
        attrs = list(c.attrib.keys())
        # leaf values
        leaves = []
        for el in c.iter():
            if list(el) == [] and (el.text or "").strip():
                leaves.append((local(el.tag), (el.text or "").strip()[:80]))
        safe_print(f"SAMPLE [{pname}] attrs={attrs[:10]} kids={kids[:20]} leaves={leaves[:15]}")
        if samples >= 8:
            break

    # find table-like repeating groups
    safe_print("--- repeating groups ---")
    for c in root:
        pname = local(c.tag)
        # if many grandchildren with same tag - table
        gtags = [local(g.tag) for g in c]
        gctr = Counter(gtags)
        repeats = [(t, n) for t, n in gctr.items() if n >= 3]
        if repeats:
            safe_print(f"  {pname}: {repeats[:10]}")


def compare_headers(xlsx_sheets, xtdd_text):
    pass


def main():
    analyze_xlsx(XLSX)
    safe_print("")
    analyze_xtdd(XTDD)


if __name__ == "__main__":
    main()
