#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import zipfile
import re
from pathlib import Path

z = zipfile.ZipFile(r"C:\Users\Acer\AppData\Local\XBRLConverter\Taxonomies\20251230.zip")
text = z.read("final_7_1/www.cbr.ru/xbrl/udr/dom/mem-int-label.xml").decode("utf-8")

for key in ["OKATO74000HersonskayaObl", "OKATO70000TulskayaOblast"]:
    print("===", key)
    # all label resources linked from this member
    # find resource labels via arcs from locator
    for loc in re.findall(
        r'xlink:href="[^"]*' + re.escape(key) + r'[^"]*"[^>]*xlink:label="([^"]+)"',
        text,
    ) + re.findall(
        r'xlink:label="([^"]+)"[^>]*xlink:href="[^"]*' + re.escape(key),
        text,
    ):
        print(" locator:", loc)
        for res in re.findall(
            r'xlink:from="' + re.escape(loc) + r'"[^>]*xlink:to="([^"]+)"', text
        ):
            # find label element
            m = re.search(
                r'<link:label[^>]*xlink:label="'
                + re.escape(res)
                + r'"[^>]*>([^<]*)</link:label>',
                text,
            )
            if not m:
                m = re.search(
                    r'<label[^>]*xlink:label="'
                    + re.escape(res)
                    + r'"[^>]*>([^<]*)</label>',
                    text,
                )
            # get full attrs
            m2 = re.search(
                r'<[^>]*xlink:label="' + re.escape(res) + r'"[^>]*>', text
            )
            attrs = m2.group(0) if m2 else ""
            role = ""
            rm = re.search(r'xlink:role="([^"]+)"', attrs)
            if rm:
                role = rm.group(1)
            lang = ""
            lm = re.search(r'xml:lang="([^"]+)"', attrs)
            if lm:
                lang = lm.group(1)
            val = m.group(1) if m else "?"
            print(f"  res={res} lang={lang} role=...{role[-40:]} text={val!r}")
