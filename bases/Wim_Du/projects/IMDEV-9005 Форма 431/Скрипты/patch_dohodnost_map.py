#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Patch ObjectModule.bsl: use ДоходностьПоМандатам instead of НайтиСтроки."""

import pathlib
import sys


def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[1] / "Обраб"
    files = list(root.rglob("ObjectModule.bsl"))
    if not files:
        print("ERROR: ObjectModule.bsl not found")
        return 1

    path = files[0]
    text = path.read_text(encoding="utf-8")

    old_block = (
        '\t\t\t  \tОтбор = Соединение.NewObject("Структура");\n'
        '\t\t\t    Отбор.Вставить("Разделитель", ТекСтрока.Мандат);\n'
        '\t\t\t    СтрокиДоходности = ДанныеДоходности.НайтиСтроки(Отбор);\t\t\t\t\t\n'
        '\t\t\t\tЕсли СтрокиДоходности.Количество() = 0 Тогда \n'
        '\t\t\t\t\tНоваяСтрока.ДоходностьСтратегии = 0;\t\n'
        '\t\t\t\t\tПродолжить;\n'
        '\t\t\t\tКонецЕсли;\t\n'
    )

    new_block = (
        '\t\t\t\t// IMDEV-9005 ++\n'
        '\t\t\t\tСтрокиДоходности = ДоходностьПоМандатам.Получить(ТекСтрока.Мандат);\n'
        '\t\t\t\tЕсли СтрокиДоходности = Неопределено Или СтрокиДоходности.Количество() = 0 Тогда\n'
        '\t\t\t\t\tНоваяСтрока.ДоходностьСтратегии = 0;\n'
        '\t\t\t\t\tПродолжить;\n'
        '\t\t\t\tКонецЕсли;\n'
        '\t\t\t\t// IMDEV-9005 --\n'
    )

    if old_block not in text:
        print("ERROR: OLD block not found")
        return 1

    new_text = text.replace(old_block, new_block, 1)

    if "СтрокиДоходности.Получить(КоличествоСтрок)" not in new_text:
        print("ERROR: Получить(КоличествоСтрок) already patched or missing")
        return 1

    new_text = new_text.replace(
        "СтрокиДоходности.Получить(КоличествоСтрок)",
        "СтрокиДоходности[КоличествоСтрок]",
        1,
    )

    path.write_text(new_text, encoding="utf-8")
    print("OK patched:", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
