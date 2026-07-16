#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Map ruleNode -> concept + members for 415 PR1_3 X-axis."""

import zipfile
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from collections import defaultdict

TAX = Path(r"C:\Users\Acer\AppData\Local\XBRLConverter\Taxonomies\20251230.zip")
z = zipfile.ZipFile(TAX)
rend = [n for n in z.namelist() if "sr_0420415_r1_pr1_3" in n.lower() and n.endswith("-rend.xml")][0]
lab = [n for n in z.namelist() if "sr_0420415_r1_pr1_3" in n.lower() and n.endswith("-lab.xml")][0]
rt = z.read(rend).decode("utf-8")
lt = z.read(lab).decode("utf-8")


def local(tag):
    return tag.split("}")[-1]


root = ET.fromstring(rt)

# id -> element
by_id = {}
by_label = {}
for el in root.iter():
    attrs = {local(k): v for k, v in el.attrib.items()}
    if "id" in attrs:
        by_id[attrs["id"]] = el
    if "label" in attrs:
        by_label[attrs["label"]] = el

# arcs from->tos with order
children = defaultdict(list)
for el in root.iter():
    if "Arc" not in local(el.tag) and "arc" not in local(el.tag):
        continue
    fr = to = order = axis = None
    for k, v in el.attrib.items():
        kl = local(k)
        if kl == "from":
            fr = v
        elif kl == "to":
            to = v
        elif kl == "order":
            order = float(v)
        elif kl == "axis":
            axis = v
    if fr and to:
        children[fr].append((order or 0, to, axis, local(el.tag)))


def qnames_in(el):
    out = []
    for ch in el.iter():
        if local(ch.tag) in ("concept", "member", "dimensionAspect", "qname"):
            t = (ch.text or "").strip()
            if t:
                out.append((local(ch.tag), t))
            for k, v in ch.attrib.items():
                if "href" in k:
                    out.append((local(ch.tag) + "@href", v))
    return out


def walk(node_id, path=None, depth=0):
    path = path or []
    el = by_id.get(node_id) or by_label.get(node_id)
    if el is None:
        return
    ln = local(el.tag)
    qn = qnames_in(el)
    abstract = any(local(k) == "abstract" and v == "true" for k, v in el.attrib.items())
    indent = "  " * depth
    qn_s = ", ".join(f"{a}={b}" for a, b in qn[:6])
    print(f"{indent}{ln}:{node_id} abstract={abstract} [{qn_s}]")
    kids = sorted(children.get(node_id, []), key=lambda x: x[0])
    # also try label as key
    if not kids:
        lab = None
        for k, v in el.attrib.items():
            if local(k) == "label":
                lab = v
        if lab:
            kids = sorted(children.get(lab, []), key=lambda x: x[0])
    for order, to, axis, atype in kids:
        walk(to, path + [node_id], depth + 1)


print("=== X breakdownY tree ===")
walk("breakdownY")

print("\n=== Y breakdown_4 tree ===")
walk("breakdown_4")

# lab: locator href -> label text via arcs
print("\n=== lab: ruleNode labels ===")
# parse locators
locs = re.findall(
    r'xlink:label="([^"]+)"[^>]*xlink:href="[^"]*#([^"]+)"',
    lt,
)
locs += re.findall(
    r'xlink:href="[^"]*#([^"]+)"[^>]*xlink:label="([^"]+)"',
    lt,
)
# normalize to label->id
lab2id = {}
for a, b in locs:
    if a.startswith("label") or len(a) < len(b):
        # might be swapped forms
        pass
# simpler
for m in re.finditer(r"<link:loc[^>]+/?>", lt):
    tag = m.group(0)
    lab_m = re.search(r'xlink:label="([^"]+)"', tag)
    href_m = re.search(r'xlink:href="[^"]*#([^"]+)"', tag)
    if lab_m and href_m:
        lab2id[lab_m.group(1)] = href_m.group(1)

# label resources
res = {}
for m in re.finditer(
    r'<link:label[^>]*xlink:label="([^"]+)"[^>]*xml:lang="ru"[^>]*>([^<]+)</link:label>',
    lt,
):
    res[m.group(1)] = m.group(1) and m.group(2)
for m in re.finditer(
    r'<link:label[^>]*xml:lang="ru"[^>]*xlink:label="([^"]+)"[^>]*>([^<]+)</link:label>',
    lt,
):
    res[m.group(1)] = m.group(2)

arcs = re.findall(
    r'xlink:from="([^"]+)"[^>]*xlink:to="([^"]+)"',
    lt,
)
id2ru = {}
for fr, to in arcs:
    # from locator to resource
    node = lab2id.get(fr, fr)
    text = res.get(to)
    if text:
        id2ru[node] = text

for node, text in sorted(id2ru.items(), key=lambda x: x[0])[:50]:
    if "ruleNode" in node or node.startswith("SR_"):
        print(f"  {node[:60]:60} {text[:70]}")
