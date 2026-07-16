#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find decimals/fractionDigits for CZB_Sobst_kol and related 415 qty concepts."""

import re
import zipfile
from pathlib import Path

TAX = Path(r"C:\Users\Acer\AppData\Local\XBRLConverter\Taxonomies\20251230.zip")
CONCEPTS = (
    "CZB_Sobst_kol",
    "CZB_Sobst_kol_Obrem",
    "KolCZBbezPrekrPrizNaVozvratOsnove",
    "KolCZBvDoveritelnoeUpravlenie",
    "CZB_Uchtenn_BB",
    "Kolczb",
)


def main():
    if not TAX.exists():
        print("missing tax", TAX)
        return
    z = zipfile.ZipFile(TAX)
    # search xsd for concept + decimals
    for concept in CONCEPTS:
        print("===", concept)
        found = False
        for n in z.namelist():
            if not n.endswith(".xsd"):
                continue
            if "purcb" not in n.lower() and "dic" not in n.lower():
                continue
            t = z.read(n).decode("utf-8", errors="ignore")
            if f'name="{concept}"' not in t and f"name='{concept}'" not in t:
                continue
            # extract element block
            m = re.search(
                rf'<[^>]*name="{re.escape(concept)}"[^>]*>.*?</(?:xs:)?element>',
                t,
                re.DOTALL | re.IGNORECASE,
            )
            if not m:
                m = re.search(
                    rf'<[^>]*name="{re.escape(concept)}"[^/]*/>',
                    t,
                    re.IGNORECASE,
                )
            frag = m.group(0) if m else ""
            if not frag:
                # wider window
                idx = t.find(f'name="{concept}"')
                frag = t[max(0, idx - 200) : idx + 800]
            print(" file", n[-70:])
            print(" frag:", re.sub(r"\s+", " ", frag)[:500])
            # type name
            tm = re.search(r'type="([^"]+)"', frag)
            if tm:
                typ = tm.group(1)
                print(" type:", typ)
                local = typ.split(":")[-1]
                # find simpleType / complexType
                for n2 in z.namelist():
                    if not n2.endswith(".xsd"):
                        continue
                    t2 = z.read(n2).decode("utf-8", errors="ignore")
                    if local not in t2:
                        continue
                    for pat in (
                        rf'<[^>]*(?:simpleType|complexType)[^>]*name="{re.escape(local)}".*?</(?:xs:)?(?:simpleType|complexType)>',
                        rf'name="{re.escape(local)}"[^>]*>.*?fractionDigits[^<]*',
                    ):
                        m2 = re.search(pat, t2, re.DOTALL | re.IGNORECASE)
                        if m2:
                            block = re.sub(r"\s+", " ", m2.group(0))[:600]
                            if "fraction" in block.lower() or "decimal" in block.lower() or "totalDigits" in block.lower() or "restriction" in block.lower():
                                print("  typeDef", n2[-50:], block)
                                found = True
                                break
                    if found:
                        break
            found = True
            break
        if not found:
            print("  not found")

    # also search labels / reference for format
    print("\n=== fractionDigits near CZB_Sobst ===")
    cnt = 0
    for n in z.namelist():
        if not n.endswith(".xsd"):
            continue
        t = z.read(n).decode("utf-8", errors="ignore")
        if "CZB_Sobst" not in t and "KolCZB" not in t:
            continue
        if "fractionDigits" not in t and "decimals" not in t.lower():
            continue
        for m in re.finditer(r".{0,80}fractionDigits[^/]*/>.{0,40}", t):
            frag = m.group(0).replace("\n", " ")
            if "nonNegative" in frag or "decimal" in frag.lower() or "shares" in frag.lower():
                print(n[-60:], frag[:200])
                cnt += 1
                if cnt > 15:
                    break
        if cnt > 15:
            break

    # common monetary/shares types in purcb-dic
    print("\n=== types with fractionDigits in purcb ===")
    for n in z.namelist():
        if "purcb" in n.lower() and n.endswith(".xsd"):
            t = z.read(n).decode("utf-8", errors="ignore")
            types = re.findall(
                r'name="([^"]+)"[^>]*>.*?fractionDigits[^>]*value="(\d+)"',
                t,
                re.DOTALL,
            )
            # also separate
            for m in re.finditer(
                r'<xs:simpleType\s+name="([^"]+)"(.*?</xs:simpleType>)',
                t,
                re.DOTALL,
            ):
                name, body = m.group(1), m.group(2)
                fm = re.search(r'fractionDigits[^>]*value="(\d+)"', body)
                if fm:
                    print(f"  {name}: fractionDigits={fm.group(1)}")


if __name__ == "__main__":
    main()
