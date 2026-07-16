#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse taxonomy rend for SR_0420415_R1_PR1_3 - breakdown structure."""

import zipfile
import re
from pathlib import Path
from xml.etree import ElementTree as ET

TAX = Path(r"C:\Users\Acer\AppData\Local\XBRLConverter\Taxonomies\20251230.zip")
z = zipfile.ZipFile(TAX)

# find rend
rend_name = None
lab_name = None
for n in z.namelist():
    nl = n.replace("\\", "/").lower()
    if "sr_0420415_r1_pr1_3" in nl and n.endswith("-rend.xml"):
        rend_name = n
    if "sr_0420415_r1_pr1_3" in nl and n.endswith("-lab.xml"):
        lab_name = n
print("rend:", rend_name)
print("lab:", lab_name)

NS = {
    "link": "http://www.xbrl.org/2003/linkbase",
    "xlink": "http://www.w3.org/1999/xlink",
    "table": "http://xbrl.org/2014/table",
    "formula": "http://xbrl.org/2008/formula",
    "gen": "http://xbrl.org/2008/generic",
}


def local(tag):
    return tag.split("}")[-1] if "}" in tag else tag


rt = z.read(rend_name).decode("utf-8")
# namespace-agnostic parse
root = ET.fromstring(rt)

print("\n=== Elements summary ===")
counts = {}
for el in root.iter():
    counts[local(el.tag)] = counts.get(local(el.tag), 0) + 1
for k, v in sorted(counts.items(), key=lambda x: -x[1])[:30]:
    print(f"  {v:4} {k}")

print("\n=== table:breakdown / aspect nodes ===")
for el in root.iter():
    ln = local(el.tag)
    if ln in (
        "breakdown",
        "ruleNode",
        "aspectNode",
        "dimensionRelationshipNode",
        "conceptRelationshipNode",
        "table",
    ):
        attrs = {local(k) if "}" in k else k: v for k, v in el.attrib.items()}
        # compact
        interesting = {
            k: v
            for k, v in attrs.items()
            if k
            in (
                "id",
                "parentChildOrder",
                "axis",
                "label",
                "merge",
                "abstract",
                "href",
                "dimension",
            )
            or "axis" in k.lower()
            or "label" in k.lower()
            or k.endswith("}href")
            or "href" in k
        }
        # get xlink attrs
        for k, v in el.attrib.items():
            if "href" in k or "label" in k or "role" in k:
                interesting[k.split("}")[-1]] = v[:80]
        text_dim = None
        for ch in el:
            if local(ch.tag) in ("dimension", "concept"):
                text_dim = (ch.text or "").strip()
                for k, v in ch.attrib.items():
                    if "href" in k or "dimension" in k:
                        text_dim = v
        if interesting or text_dim:
            print(f"  <{ln}> {interesting} dim/concept={text_dim}")

# breakdownTreeArc order
print("\n=== arcs (breakdownTreeArc / definitionNodeSubtreeArc) ===")
arcs = []
for el in root.iter():
    ln = local(el.tag)
    if "Arc" in ln or "arc" in ln:
        fr = to = order = ""
        for k, v in el.attrib.items():
            kl = k.split("}")[-1]
            if kl == "from":
                fr = v
            elif kl == "to":
                to = v
            elif kl == "order":
                order = v
            elif kl == "axis":
                order = order + f" axis={v}"
        arcs.append((ln, order, fr, to))
for a in arcs[:80]:
    print(f"  {a[0]:30} order={a[1]:8} {a[2]} -> {a[3]}")
print(f"  ... total arcs {len(arcs)}")

# labels from lab
print("\n=== lab labels (ru) sample ===")
lt = z.read(lab_name).decode("utf-8")
# resource labels
labels = re.findall(
    r'xlink:label="([^"]+)"[^>]*xml:lang="ru"[^>]*>([^<]+)<',
    lt,
)
if not labels:
    labels = re.findall(
        r'xml:lang="ru"[^>]*xlink:label="([^"]+)"[^>]*>([^<]+)<',
        lt,
    )
print(f"ru labels: {len(labels)}")
for lab, text in labels[:40]:
    print(f"  {lab[:50]:50} {text[:70]}")

# also dump raw aspectNode / dimension bits with regex
print("\n=== dimensionAspect / conceptAspect regex ===")
for m in re.finditer(r"<(?:\w+:)?(aspectNode|ruleNode|breakdown)[^>]*>", rt):
    pass
dims = re.findall(r"dimensionAspect[^>]*>([^<]+)<", rt)
if not dims:
    dims = re.findall(r"<[^>]*dimensionAspect[^>]*qname[^>]*>([^<]+)<", rt)
print("dimensionAspect:", dims[:20])
concepts = re.findall(r"conceptAspect[^>]*>?[^<]*", rt)
print("conceptAspect count", len(re.findall(r"conceptAspect", rt)))

# explicit qnames in rend
qnames = sorted(set(re.findall(r">([a-zA-Z0-9_-]+:[A-Za-z0-9_]+)<", rt)))
print("qnames sample:", qnames[:40])
