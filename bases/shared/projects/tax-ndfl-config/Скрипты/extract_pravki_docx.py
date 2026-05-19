#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Извлечение содержимого файла "Правки к ТЗ НДФЛ.docx" в структурированный
markdown-файл. Сохраняет порядок абзацев, нумерацию пунктов и таблицы.
"""

import os
import sys
import json
from docx import Document

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DOCX = os.path.join(
    BASE_DIR,
    "КорректировкаОтПользователя_1",
    "Правки к ТЗ НДФЛ.docx",
)
OUT_DIR = os.path.join(BASE_DIR, "КорректировкаОтПользователя_1", "_extracted")
os.makedirs(OUT_DIR, exist_ok=True)


def iter_block_items(parent):
    """Итерируем абзацы и таблицы в порядке их появления в документе."""
    from docx.document import Document as _Document
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import _Cell, Table
    from docx.text.paragraph import Paragraph

    if isinstance(parent, _Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError("Unknown parent type")

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def para_text(p):
    txt = (p.text or "").rstrip()
    return txt


def para_style(p):
    try:
        return (p.style.name or "").strip()
    except Exception:
        return ""


def list_level(p):
    try:
        pf = p.paragraph_format
        ind = pf.left_indent
        if ind is None:
            return 0
        return max(0, int(ind.pt // 18))
    except Exception:
        return 0


def is_numbered(p):
    try:
        numpr = p._p.pPr is not None and p._p.pPr.find(
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr"
        ) is not None
        return bool(numpr)
    except Exception:
        return False


def table_to_md(tbl):
    rows = []
    for row in tbl.rows:
        cells = []
        for c in row.cells:
            ct = " ".join((c.text or "").split())
            cells.append(ct)
        rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    for r in rows:
        while len(r) < width:
            r.append("")
    out = []
    out.append("| " + " | ".join(rows[0]) + " |")
    out.append("|" + "|".join(["---"] * width) + "|")
    for r in rows[1:]:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def main():
    if not os.path.exists(INPUT_DOCX):
        print(f"NOT FOUND: {INPUT_DOCX}")
        sys.exit(1)

    doc = Document(INPUT_DOCX)

    md_lines = []
    md_lines.append("# Правки к ТЗ НДФЛ (извлечение из .docx)\n")
    md_lines.append(f"Исходник: `{os.path.basename(INPUT_DOCX)}`\n\n")

    raw_blocks = []
    for block in iter_block_items(doc):
        if block.__class__.__name__ == "Paragraph":
            t = para_text(block)
            if not t:
                continue
            style = para_style(block)
            numbered = is_numbered(block)
            lvl = list_level(block)
            raw_blocks.append({
                "type": "p",
                "text": t,
                "style": style,
                "numbered": numbered,
                "level": lvl,
            })
            if style.startswith("Heading 1") or style.startswith("Заголовок 1"):
                md_lines.append(f"\n## {t}\n")
            elif style.startswith("Heading 2") or style.startswith("Заголовок 2"):
                md_lines.append(f"\n### {t}\n")
            elif style.startswith("Heading 3") or style.startswith("Заголовок 3"):
                md_lines.append(f"\n#### {t}\n")
            elif numbered:
                indent = "  " * lvl
                md_lines.append(f"{indent}1. {t}")
            else:
                md_lines.append(t)
                md_lines.append("")
        else:
            md = table_to_md(block)
            if md:
                raw_blocks.append({"type": "table", "md": md})
                md_lines.append("")
                md_lines.append(md)
                md_lines.append("")

    out_md = os.path.join(OUT_DIR, "pravki.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    out_json = os.path.join(OUT_DIR, "pravki.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(raw_blocks, f, ensure_ascii=False, indent=2)

    print(f"OK: {out_md}")
    print(f"OK: {out_json}")
    print(f"Blocks: {len(raw_blocks)}")


if __name__ == "__main__":
    main()
