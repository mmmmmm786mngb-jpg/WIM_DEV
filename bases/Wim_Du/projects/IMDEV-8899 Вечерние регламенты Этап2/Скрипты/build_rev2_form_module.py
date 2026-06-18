#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка Module.bsl перехвата формы РегламентныйПериод для расширения rev2."""

from pathlib import Path

BASE_MODULE = Path(
    r"c:\1c\Cursor_1c\WORK\Wim_Du\SRC\CF\Catalogs\РегламентныеПериоды"
    r"\Forms\РегламентныйПериод\Ext\Form\Module.bsl"
)
OUT_MODULE = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-8899 Вечерние регламенты Этап2"
    r"\Расширения\rev2\Catalogs\РегламентныеПериоды\Forms\РегламентныйПериод\Ext\Form\Module.bsl"
)

INDEX_BLOCK = """\t#Вставка
\t// IMDEV-8899 3.6: составной индекс под НайтиСтроки в СформироватьДокументыЗакрытияПериода
\tСписокОпераций.Индексы.Добавить("ДоговорДУ,ГруппаОперацийПользователя");
\t#КонецВставки"""

DOC_INDEX_BLOCK = """\t#Вставка
\t// IMDEV-8899 3.6
\tДокументыПоДоговорам.Индексы.Добавить("ДоговорДУ,ГруппаОперацийПользователя");
\t#КонецВставки"""

HEADER = [
    "&НаСервере",
    '&ИзменениеИКонтроль("ПолучитьДоговораДУпоДинамическомуСписку")',
    "Функция rev2_ПолучитьДоговораДУпоДинамическомуСписку(УчитыватьВыполненные)",
]


def main() -> None:
    lines = BASE_MODULE.read_text(encoding="utf-8-sig").splitlines()
    part1 = lines[1158:1232]
    part2_before_docs = lines[1232:1286]
    part3 = lines[1286:]
    result = (
        HEADER
        + part1
        + INDEX_BLOCK.splitlines()
        + part2_before_docs
        + DOC_INDEX_BLOCK.splitlines()
        + part3
    )
    OUT_MODULE.parent.mkdir(parents=True, exist_ok=True)
    OUT_MODULE.write_text("\n".join(result) + "\n", encoding="utf-8-sig")
    print(f"OK: {len(result)} lines -> {OUT_MODULE}")


if __name__ == "__main__":
    main()
