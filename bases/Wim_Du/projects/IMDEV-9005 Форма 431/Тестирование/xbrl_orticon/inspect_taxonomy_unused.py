#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""What taxonomy parts exist vs what we already use."""

from zipfile import ZipFile
from pathlib import Path
import os
import re
import sys


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def main():
    zip_path = (
        Path(os.environ["LOCALAPPDATA"])
        / "XBRLConverter"
        / "Taxonomies"
        / "20251230.zip"
    )
    with ZipFile(zip_path) as z:
        base = "final_7_1/www.cbr.ru/xbrl/nso/purcb/rep/2025-12-30/tab/SR_0420409_m/"
        for fname in [
            "SR_0420409_m-presentation.xml",
            "SR_0420409_m-rend.xml",
            "SR_0420409_m-definition.xml",
            "SR_0420409_m-formula.xml",
            "SR_0420409_m-lab.xml",
        ]:
            text = z.read(base + fname).decode("utf-8")
            safe_print("=== %s (%d bytes) ===" % (fname, len(text)))
            for tag in [
                "presentationArc",
                "parent-child",
                "aspectNode",
                "tagSelector",
                "PeriodStart",
                "PeriodEnd",
                "dimensionAspect",
                "breakdown",
                "definitionArc",
                "assertion",
                "label:label",
                "formula:concept",
            ]:
                c = text.count(tag)
                if c:
                    safe_print("  %s: %d" % (tag, c))
            labs = re.findall(r'xml:lang="ru"[^>]*>([^<]{8,100})', text)
            if labs:
                safe_print("  ru samples: %s" % labs[:5])

        ep = (
            "final_7_1/www.cbr.ru/xbrl/nso/purcb/rep/2025-12-30/ep/"
            "ep_nso_purcb_m_10rd_ex_reestr_0420417_ex_mal.xsd"
        )
        eptext = z.read(ep).decode("utf-8")
        imports = re.findall(r'schemaLocation="([^"]+)"', eptext)
        tabs = sorted({i.split("/tab/")[-1].split("/")[0] for i in imports if "/tab/" in i})
        safe_print("\n=== EP tables (%d) ===" % len(tabs))
        for t in tabs:
            safe_print("  %s" % t)

        # secondary tables count (pivot splits)
        secondaries = [
            n
            for n in z.namelist()
            if "/purcb/rep/2025-12-30/tab/" in n and n.endswith("-rend.xml") and n.count("SR_") >= 2
        ]
        safe_print("\nSecondary/pivot rend files: %d" % len(secondaries))
        for n in secondaries[:12]:
            safe_print("  %s" % n.split("/tab/")[-1])

        # axis label for typed dimension
        rend = z.read(base + "SR_0420409_m-rend.xml").decode("utf-8")
        lab = z.read(base + "SR_0420409_m-lab.xml").decode("utf-8")
        safe_print("\n=== Row axis ===")
        m = re.search(r"dimensionAspect[^>]*>([^<]+)", rend)
        safe_print("aspect: %s" % (m.group(1) if m else None))
        if "Идентификатор банковского счета" in lab:
            safe_print("lab has row axis RU label: YES")
        else:
            # search presentation / dic
            safe_print("lab has row axis RU label: NO (maybe from dim-int)")
            dimlab = z.read(
                "final_7_1/www.cbr.ru/xbrl/udr/dim/dim-int-label.xml"
            ).decode("utf-8")
            i = dimlab.find("Rek_kred_org_i_scheta")
            if i >= 0:
                chunk = dimlab[i : i + 800]
                labs2 = re.findall(r'xml:lang="ru"[^>]*>([^<]+)', chunk)
                safe_print("dim-int labels: %s" % labs2[:5])

    return 0


if __name__ == "__main__":
    sys.exit(main())
