#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract tabular section attribute names from document metadata XML."""

import re
from pathlib import Path

DOC_XML = Path(r"C:\1c\Cursor_1c\WORK\Wim_Du\SRC\CF\Documents\РО_XBRL7_1_0420431_СведенияОДеятельностиПоУправлениюЦБ_7119У.xml")
FILLED = [
    "Раздел1_Подраздел1_1",
    "Раздел1_Подраздел1_2",
    "Раздел1_Подраздел1_3",
    "Раздел2",
    "Раздел3",
    "Раздел4",
    "Раздел5",
    "Раздел6",
    "Раздел7",
    "РеестрЦенныхБумаг",
]


def main() -> None:
    text = DOC_XML.read_text(encoding="utf-8-sig")
    parts = re.split(r"<TabularSection uuid=", text)
    for part in parts[1:]:
        m = re.search(r"<Name>([^<]+)</Name>", part)
        if not m:
            continue
        ts_name = m.group(1)
        if ts_name not in FILLED:
            continue
        ts_block = part.split("</TabularSection>")[0]
        attrs = re.findall(
            r'<Attribute uuid="[^"]+">.*?<Properties>.*?<Name>([^<]+)</Name>',
            ts_block,
            re.S,
        )
        print("===", ts_name, "===")
        for a in attrs:
            print(a)
        print("COUNT", len(attrs))
        print()


if __name__ == "__main__":
    main()
