#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract text from docx measurements file."""

import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_paragraphs(docx_path: Path):
    with zipfile.ZipFile(docx_path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    root = ET.fromstring(xml)
    lines = []
    for para in root.iter(f"{W_NS}p"):
        parts = []
        for node in para.iter(f"{W_NS}t"):
            if node.text:
                parts.append(node.text)
            if node.tail:
                parts.append(node.tail)
        line = "".join(parts).strip()
        if line:
            lines.append(line)
    return lines


def main():
    docx = Path(
        r"bases/Wim_Du/projects/IMDEV-9005 Форма 431/Замеры 431 форма Т-1 в журнал регистрации.docx"
    )
    out = docx.parent / "Скрипты" / "extracted_measurements_t1.txt"
    lines = extract_paragraphs(docx)
    out.write_text("\n".join(f"{i}|{line}" for i, line in enumerate(lines, 1)), encoding="utf-8")
    print(f"OK: {len(lines)} lines -> {out}")


if __name__ == "__main__":
    main()
