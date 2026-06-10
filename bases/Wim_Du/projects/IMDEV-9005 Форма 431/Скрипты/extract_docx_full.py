#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract paragraphs and tables from docx measurements file."""

import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def cell_text(cell):
    parts = []
    for node in cell.iter(f"{W_NS}t"):
        if node.text:
            parts.append(node.text)
        if node.tail:
            parts.append(node.tail)
    return "".join(parts).strip()


def extract(docx_path: Path):
    with zipfile.ZipFile(docx_path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    root = ET.fromstring(xml)
    body = root.find(f"{W_NS}body")
    result = {"paragraphs": [], "tables": []}

    for child in body:
        tag = child.tag.replace(W_NS, "")
        if tag == "p":
            parts = []
            for node in child.iter(f"{W_NS}t"):
                if node.text:
                    parts.append(node.text)
                if node.tail:
                    parts.append(node.tail)
            line = "".join(parts).strip()
            if line:
                result["paragraphs"].append(line)
        elif tag == "tbl":
            table = []
            for row in child.findall(f"{W_NS}tr"):
                row_data = []
                for cell in row.findall(f"{W_NS}tc"):
                    row_data.append(cell_text(cell))
                if any(row_data):
                    table.append(row_data)
            if table:
                result["tables"].append(table)
    return result


def main():
    docx = Path(
        r"bases/Wim_Du/projects/IMDEV-9005 Форма 431/Замеры 431 форма Т-1 в журнал регистрации.docx"
    )
    data = extract(docx)
    out = docx.parent / "Скрипты" / "extracted_measurements_t1.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"paragraphs: {len(data['paragraphs'])}, tables: {len(data['tables'])}")
    for ti, table in enumerate(data["tables"]):
        print(f"\n=== TABLE {ti + 1} ===")
        for row in table:
            print(" | ".join(row))


if __name__ == "__main__":
    main()
