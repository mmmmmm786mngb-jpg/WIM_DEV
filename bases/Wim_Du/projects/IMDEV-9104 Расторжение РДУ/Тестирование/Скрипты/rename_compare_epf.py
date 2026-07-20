#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rename scaffold to внТестСравнениеПлатежнойПозиции."""

import re
import uuid
from pathlib import Path

BASE = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-9104 "
    r"Расторжение РДУ\Тестирование\внТестСравнениеПлатежнойПозиции_epf"
)
OLD = "внТестРасторжениеДоговоровРДУ"
NEW = "внТестСравнениеПлатежнойПозиции"


def main() -> None:
    for p in BASE.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".xml", ".bsl"}:
            text = p.read_text(encoding="utf-8")
            text2 = text.replace(OLD, NEW)
            if text2 != text:
                p.write_text(text2, encoding="utf-8")
                print("renamed", p.relative_to(BASE))

    root = BASE / f"{NEW}.xml"
    text = root.read_text(encoding="utf-8")
    text = re.sub(
        r'(<ExternalDataProcessor uuid=")[^"]+(")',
        rf'\g<1>{uuid.uuid4()}\2',
        text,
        count=1,
    )
    text = re.sub(
        r"(<xr:ObjectId>)[^<]+(</xr:ObjectId>)",
        rf"\g<1>{uuid.uuid4()}\2",
        text,
        count=1,
    )
    text = re.sub(
        r"(<xr:TypeId>)[^<]+(</xr:TypeId>)",
        rf"\g<1>{uuid.uuid4()}\2",
        text,
        count=1,
    )
    text = re.sub(
        r"(<xr:ValueId>)[^<]+(</xr:ValueId>)",
        rf"\g<1>{uuid.uuid4()}\2",
        text,
        count=1,
    )
    text = text.replace(
        "Тест расторжения договоров РДУ (без ДО)",
        "IMDEV-9104 сравнение платежной позиции ПП (было/стало)",
    )
    text = text.replace(
        "IMDEV-9104: имитация расторжения без внешних систем + замеры",
        "IMDEV-9104 P2: ПлатежныеПозицииПоСчетамДС по-старому vs пакет",
    )
    root.write_text(text, encoding="utf-8")
    print("OK", root)


if __name__ == "__main__":
    main()
