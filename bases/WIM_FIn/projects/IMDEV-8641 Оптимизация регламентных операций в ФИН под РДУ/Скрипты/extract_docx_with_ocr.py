#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Извлечение текста и OCR с изображений из docx (КакВыглядитВКоде.docx).
"""

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def extract_paragraphs(document_xml: bytes) -> list[str]:
    root = ET.fromstring(document_xml)
    paragraphs = []
    for p in root.iter(f"{{{NS['w']}}}p"):
        parts = []
        for t in p.iter(f"{{{NS['w']}}}t"):
            if t.text:
                parts.append(t.text)
            if t.tail:
                parts.append(t.tail)
        line = "".join(parts).strip()
        if line:
            paragraphs.append(line)
    return paragraphs


def main() -> None:
    project = Path(__file__).resolve().parents[1]
    avancor = project / "ДоработкиОтАванкор"
    docx_path = avancor / "КакВыглядитВКоде.docx"
    media_dir = avancor / "how_it_looks_in_code_media"
    out_md = avancor / "how_it_looks_in_code_from_docx.md"

    media_dir.mkdir(parents=True, exist_ok=True)

    paragraphs: list[str] = []
    image_files: list[Path] = []

    with zipfile.ZipFile(docx_path) as zf:
        paragraphs = extract_paragraphs(zf.read("word/document.xml"))
        for name in sorted(zf.namelist()):
            if name.startswith("word/media/") and not name.endswith("/"):
                data = zf.read(name)
                out_name = Path(name).name
                out_path = media_dir / out_name
                out_path.write_bytes(data)
                image_files.append(out_path)

    ocr_blocks: list[tuple[str, str]] = []
    try:
        import easyocr  # type: ignore
        import numpy as np
        from PIL import Image

        reader = easyocr.Reader(["ru", "en"], gpu=False, verbose=False)
        for img_path in image_files:
            # OpenCV/easyocr na Windows ne chitaet puti s kirillicej — chitaem cherez PIL
            with Image.open(img_path) as pil_img:
                img_array = np.array(pil_img.convert("RGB"))
            results = reader.readtext(img_array, detail=0, paragraph=True)
            text = "\n".join(results).strip()
            ocr_blocks.append((img_path.name, text))
    except Exception as exc:
        for img_path in image_files:
            ocr_blocks.append((img_path.name, f"[OCR failed: {exc}]"))

    lines = [
        "# Kak vyglyadit v kode (extract from docx)",
        "",
        "Source: `КакВыглядитВКоде.docx`",
        "Author note in docx: Koцarev Pavel, 2026-06-01 — solution in delivery 2.8.5.0",
        "",
        "## Text from document",
        "",
    ]
    for p in paragraphs:
        lines.append(p)
        lines.append("")

    for idx, (img_name, ocr_text) in enumerate(ocr_blocks, start=1):
        lines.append(f"## Screenshot {idx}: `{img_name}`")
        lines.append("")
        lines.append(f"![{img_name}](how_it_looks_in_code_media/{img_name})")
        lines.append("")
        lines.append("### OCR / recognized text")
        lines.append("")
        lines.append("```bsl")
        lines.append(ocr_text if ocr_text else "[empty]")
        lines.append("```")
        lines.append("")

    lines.append("## Related files (from docx)")
    lines.append("")
    lines.append("- `ПримерВнешнейОбработкиПоЗакрытиюПериода.epf` — template EPF with comments")
    lines.append("- `Релиз___2_8_5_0.txt` — instruction")
    lines.append("")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"OK: {out_md}")
    print(f"Media: {media_dir} ({len(image_files)} images)")


if __name__ == "__main__":
    main()
