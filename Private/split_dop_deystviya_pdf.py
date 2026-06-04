#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Razbivka PDF "Dopolnitelnye deystviya pri vnedrenii" na 3 chasti:
pered obnovleniem, vo vremya, posle.
"""

from __future__ import annotations

import sys
from pathlib import Path

import fitz


def add_clipped_page(
    dst: fitz.Document,
    src: fitz.Document,
    page_index: int,
    clip: fitz.Rect,
) -> None:
    """Dobavit v dst stranicu s vyrezkoy clip iz src."""
    src_page = src[page_index]
    height = clip.height
    width = clip.width
    if height <= 0 or width <= 0:
        raise ValueError(f"Invalid clip size: {clip}")

    new_page = dst.new_page(width=width, height=height)
    target = fitz.Rect(0, 0, width, height)
    new_page.show_pdf_page(target, src, page_index, clip=clip)


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    src_path = base_dir / "ДополнительныеДействияПриВнедрении.pdf"

    if not src_path.is_file():
        print("ERROR: source PDF not found")
        return 1

    outputs = [
        (
            base_dir / "ДополнительныеДействия_1_ПередОбновлением.pdf",
            "pered",
        ),
        (
            base_dir / "ДополнительныеДействия_2_ВоВремяОбновления.pdf",
            "vo_vremya",
        ),
        (
            base_dir / "ДополнительныеДействия_3_ПослеОбновления.pdf",
            "posle",
        ),
    ]

    src = fitz.open(src_path)
    if src.page_count < 2:
        print("ERROR: expected at least 2 pages")
        src.close()
        return 1

    page1 = src[0].rect
    page2 = src[1].rect
    margin = 4.0
    footer_top = 810.0

    clips = {
        "pered": [
            (0, fitz.Rect(0, 0, page1.width, 365.0)),
        ],
        "vo_vremya": [
            (0, fitz.Rect(0, 363.0, page1.width, footer_top)),
        ],
        "posle": [
            (1, fitz.Rect(0, 35.0, page2.width, footer_top)),
        ],
    }

    for out_path, key in outputs:
        part = fitz.open()
        for page_index, clip in clips[key]:
            add_clipped_page(part, src, page_index, clip)
        part.save(out_path)
        part.close()
        print(f"OK: {out_path.name} ({key}, pages={len(clips[key])})")

    src.close()
    print("DONE: 3 PDF files created in Private/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
