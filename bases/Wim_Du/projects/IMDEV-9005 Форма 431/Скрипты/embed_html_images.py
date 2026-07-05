#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Embed PNG images as base64 data URIs into HTML file."""

import base64
from pathlib import Path

HTML_PATH = Path(__file__).resolve().parent.parent / "Документация" / "imdev-9005_twr_math_response_kirill.html"
TEST_DIR = HTML_PATH.parent.parent / "Тестирование"

IMAGES = [
    "АРПЕЛЬ_2026_07_05_16_05_39_PROD_AVC_Retail_MO_Розничное_ДУ_Admin_Миддл_офис_1.0.3.73.png",
    "1оеПолугодие__2026_07_05_16_05_39_PROD_AVC_Retail_MO_Розничное_ДУ_Admin_Миддл_офис_1.0.3.73.png",
    "ПримерОптимизацииАлгоритмаTWR.png",
]


def main():
    text = HTML_PATH.read_text(encoding="utf-8")
    for name in IMAGES:
        img_path = TEST_DIR / name
        b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
        old = f'src="../Тестирование/{name}"'
        new = f'src="data:image/png;base64,{b64}"'
        if old not in text:
            raise SystemExit(f"Not found in HTML: {name}")
        text = text.replace(old, new)
        print(f"OK: {name} ({len(b64)} base64 chars)")
    HTML_PATH.write_text(text, encoding="utf-8")
    print(f"Done. HTML size: {HTML_PATH.stat().st_size} bytes")


if __name__ == "__main__":
    main()
