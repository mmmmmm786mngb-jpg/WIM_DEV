#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract TOP-N profiler lines from PFF create session."""

import json
import re
from pathlib import Path

PFF = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects"
    r"\IMDEV-9095 Загрузка отчетов брокера\Тестирование\Замеры_01_07_2026.pff"
)
OBJ = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects"
    r"\IMDEV-9095 Загрузка отчетов брокера\Обработки"
    r"\внРаспределениеДоходовПоЦеннымБумагам_epf"
    r"\внРаспределениеДоходовПоЦеннымБумагам\Ext\ObjectModule.bsl"
)
OUT = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects"
    r"\IMDEV-9095 Загрузка отчетов брокера\Тестирование\reports"
    r"\top5_profiler_lines.json"
)

REC = re.compile(
    r'"},"(?P<mod>[^"]+)",(?P<line>\d+),"(?P<code>.*?)",'
    r'(?P<hits>\d+),(?P<total>[\d.]+),(?P<pure>[\d.]+),'
)


def main():
    text = PFF.read_text(encoding="utf-8")
    obj_lines = OBJ.read_text(encoding="utf-8").splitlines()
    start = text.find("SMSK02MG138U")
    chunk = text[start:]

    rows = []
    for m in REC.finditer(chunk):
        mod = m.group("mod")
        line_no = int(m.group("line"))
        code = m.group("code")
        if "tempstorage" in mod:
            mod_short = "EPF ObjectModule (внРаспределениеДоходовПоЦеннымБумагам)"
            if not code.strip() and 1 <= line_no <= len(obj_lines):
                code = obj_lines[line_no - 1].strip()
        else:
            mod_short = mod
        if not code.strip():
            continue
        if code.strip().startswith("|"):
            continue
        if "tempstorage" in mod and int(m.group("hits")) <= 1 and "Записать" not in code:
            continue
        rows.append(
            {
                "module": mod_short,
                "line": line_no,
                "code": code,
                "hits": int(m.group("hits")),
                "total_sec": round(float(m.group("total")), 3),
                "pure_sec": round(float(m.group("pure")), 3),
                "sec_per_hit": round(float(m.group("total")) / max(int(m.group("hits")), 1), 4),
            }
        )

    rows.sort(key=lambda r: r["total_sec"], reverse=True)
    top5 = rows[:5]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(top5, ensure_ascii=False, indent=2), encoding="utf-8")
    for i, r in enumerate(top5, 1):
        print(i, r["total_sec"], r["hits"], r["line"], r["code"][:80])


if __name__ == "__main__":
    main()
