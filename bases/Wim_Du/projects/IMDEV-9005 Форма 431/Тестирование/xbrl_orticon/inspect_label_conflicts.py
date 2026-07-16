#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find concepts with different RU labels across section lab files."""

import os
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

TPL = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-9005 Форма 431"
    r"\Обработки\внВыгрузкаXBRLОртиконВXLSX\Templates\Таксономия_20251230\Ext\Template.bin"
)


def local(tag):
    return tag.split("}")[-1] if "}" in tag else tag


def parse_labels(data):
    root = ET.fromstring(data)
    locs = {}  # xlink:label -> concept name
    texts = {}  # xlink:label -> text
    arcs = []  # (from, to)

    for el in root.iter():
        name = local(el.tag)
        href = None
        xlab = None
        xfrom = None
        xto = None
        for k, v in el.attrib.items():
            lk = k.split("}")[-1] if "}" in k else k
            if lk == "href":
                href = v
            elif lk == "label" and "xlink" in k:
                xlab = v
            elif lk == "from":
                xfrom = v
            elif lk == "to":
                xto = v
            elif lk == "label" and xlab is None:
                # gen:label sometimes
                pass

        if name == "loc" and href and xlab:
            concept = href.split("#")[-1]
            locs[xlab] = concept
        elif name == "label" and xlab is not None:
            t = " ".join((el.text or "").split())
            if t:
                texts[xlab] = t
        elif name.endswith("Arc") or name == "labelArc":
            if xfrom and xto:
                arcs.append((xfrom, xto))

    out = {}
    for frm, to in arcs:
        concept = locs.get(frm)
        text = texts.get(to)
        if concept and text:
            prev = out.get(concept, "")
            if len(text) >= len(prev):
                out[concept] = text
        # reverse just in case
        concept = locs.get(to)
        text = texts.get(frm)
        if concept and text:
            prev = out.get(concept, "")
            if len(text) >= len(prev):
                out[concept] = text
    return out


def conflicts_for_code(z, code, exclude_q=True):
    labs = []
    for n in z.namelist():
        bn = os.path.basename(n)
        if code not in bn or not bn.endswith("-lab.xml"):
            continue
        if "/tab/" not in n.replace("\\", "/"):
            continue
        if exclude_q and "_q" in bn:
            continue
        labs.append(n)

    by_file = {}
    for n in sorted(labs):
        bn = os.path.basename(n)
        by_file[bn] = parse_labels(z.read(n).decode("utf-8"))

    all_concepts = set()
    for d in by_file.values():
        all_concepts |= set(d)

    conflicts = []
    for c in sorted(all_concepts):
        variants = {}
        for bn, d in by_file.items():
            if c in d:
                variants.setdefault(d[c], []).append(bn)
        if len(variants) > 1:
            conflicts.append((c, variants))
    return by_file, conflicts


def main():
    with zipfile.ZipFile(TPL, "r") as z:
        for code in ("0420409", "0420414", "0420431", "0420459"):
            by_file, conflicts = conflicts_for_code(z, code)
            print("===", code, "labs", len(by_file), "conflict_concepts", len(conflicts), "===")
            for bn, d in list(by_file.items())[:3]:
                print(" sample", bn, "n=", len(d))
                for i, (c, t) in enumerate(list(d.items())[:2]):
                    print("   ", c, "=>", t[:90])
            for c, variants in conflicts[:20]:
                print(" CONFLICT", c)
                for text, files in variants.items():
                    print("  ", text[:110])
                    print("    ", files)
            if len(conflicts) > 20:
                print("  ... total conflicts", len(conflicts))


if __name__ == "__main__":
    main()
