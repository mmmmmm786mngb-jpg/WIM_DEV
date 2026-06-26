#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract images from optimization DOCX in document order."""

import re
import zipfile
from pathlib import Path

DOCX_PATH = Path(__file__).resolve().parents[1] / "ОптимизацияЧтения_БылоСталоРегресс.docx"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "Документация" / "test_results_images"

CAPTIONS = [
    "BYLO: obshchiy zamер Prochitat (1 den)",
    "BYLO: detalizatsiya ProchitatObekty",
    "BYLO: SQL i tsikly ERS",
    "STALO: obshchiy zamер Prochitat (1 den)",
    "STALO: detalizatsiya ProchitatObekty",
    "Regress: sravnenie MXL 1106_bylo / 1106_stalo",
]


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(DOCX_PATH) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
        rels = archive.read("word/_rels/document.xml.rels").decode("utf-8")
        rid_map = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels))

        order: list[str] = []
        for rid in re.findall(r'r:embed="(rId\d+)"', xml):
            target = rid_map.get(rid, "")
            if "media/" in target:
                order.append(target)

        manifest = []
        for index, target in enumerate(order, start=1):
            source = "word/" + target.replace("../", "")
            data = archive.read(source)
            filename = f"test_{index:02d}_{Path(target).name}"
            (OUTPUT_DIR / filename).write_bytes(data)
            caption = CAPTIONS[index - 1] if index <= len(CAPTIONS) else filename
            manifest.append({"file": filename, "caption": caption})
            print(f"OK {filename} ({len(data)} bytes)")

    (OUTPUT_DIR / "manifest.txt").write_text(
        "\n".join(f"{item['file']}\t{item['caption']}" for item in manifest),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
