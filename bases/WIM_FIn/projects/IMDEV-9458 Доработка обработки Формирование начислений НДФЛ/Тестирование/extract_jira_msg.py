#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract readable text from Outlook MSG."""

import pathlib
import re


def main():
    p = pathlib.Path(
        r"bases/WIM_FIn/projects/IMDEV-9458 Доработка обработки Формирование начислений НДФЛ/"
        r"JIRA Updates for IMDEV-9458 Доработка обработки Формирование начислений НДФЛ.msg"
    )
    data = p.read_bytes()
    out_path = pathlib.Path(
        r"bases/WIM_FIn/projects/IMDEV-9458 Доработка обработки Формирование начислений НДФЛ/"
        r"Тестирование/jira_msg_extract.txt"
    )

    parts = []
    for enc in ("utf-16le", "utf-8", "cp1251"):
        try:
            text = data.decode(enc, errors="ignore")
        except Exception:
            continue
        chunks = re.findall(r".{20,400}", text)
        useful = []
        for chunk in chunks:
            if re.search(r"[А-Яа-я]{4,}", chunk) or "IMAPPS" in chunk or "RDU" in chunk or "МИИ" in chunk:
                t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", chunk)
                t = re.sub(r"\s+", " ", t).strip()
                if len(t) >= 20:
                    useful.append(t)
        if useful:
            parts.append("===== " + enc + " =====")
            parts.extend(useful[:200])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")
    print("WROTE", out_path)
    print("LINES", len(parts))


if __name__ == "__main__":
    main()
