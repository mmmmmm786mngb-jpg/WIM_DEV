#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract embedded PNG pictures from 1C spreadsheet Template.xml."""

import base64
import pathlib
import re
import sys

SRC = pathlib.Path(
    r"C:\1c\Cursor_1c\WORK\Wim_Du\SRC\erf"
    r"\внОтчетУправляющегоДУсогласно482П_v15_erf"
    r"\внОтчетУправляющегоДУсогласно482П_v15\Templates\Макет\Ext\Template.xml"
)
OUT = pathlib.Path(__file__).resolve().parents[1] / "Обработки" / "_logo_extract"


def main() -> int:
    text = SRC.read_text(encoding="utf-8")
    pat = re.compile(
        r"<picture>\s*<index>(\d+)</index>\s*"
        r'<picture t="false">([A-Za-z0-9+/=\r\n]+)</picture>\s*</picture>',
        re.M,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    found = 0
    for match in pat.finditer(text):
        idx = match.group(1)
        b64 = re.sub(r"\s+", "", match.group(2))
        try:
            data = base64.b64decode(b64)
        except Exception as exc:  # noqa: BLE001
            print("bad", idx, exc)
            continue
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            print("not png", idx, data[:20])
            continue
        fp = OUT / f"picture_{idx}.png"
        fp.write_bytes(data)
        print("OK", fp.name, len(data))
        found += 1
    print("total", found)
    return 0


if __name__ == "__main__":
    sys.exit(main())
