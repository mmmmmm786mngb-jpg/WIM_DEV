#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Расшифровка замеров производительности 1С (.pff).

Формат .pff - текстовый UTF-8 со строковой таблицей вида "текст".
В таблицу попадают только реально выполнявшиеся строки кода, сгруппированные
по модулю и упорядоченные по номеру строки в модуле. Отсутствие строки в
таблице означает, что она не выполнялась - это и позволяет находить точку,
на которой прервалось выполнение.

Запуск:
    python pff_decode.py <папка_с_pff>

Для каждого файла рядом создаётся <имя>.pff.txt с расшифровкой и печатается
список модулей, попавших в замер.
"""

import glob
import os
import re
import sys

STRING_RE = re.compile(r'"((?:[^"]|"")*)"')
MODULE_RE = re.compile(r"^(?:VTB_Devops )?(?:ОбщийМодуль|Документ|Справочник|Обработка|Отчет|Регистр\w*|ПланОбмена|МодульСеанса)")


def decode(path):
    data = open(path, "rb").read().decode("utf-8", "replace")
    return [s.replace('""', '"') for s in STRING_RE.findall(data)]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    for path in sorted(glob.glob(os.path.join(folder, "*.pff"))):
        strings = decode(path)
        out = path + ".txt"
        with open(out, "w", encoding="utf-8") as f:
            for i, s in enumerate(strings):
                if s.strip():
                    f.write("%05d| %s\n" % (i, s))
        modules = sorted(set(s for s in strings if MODULE_RE.match(s) and len(s) < 120))
        print("=" * 60)
        print(os.path.basename(path) + ": strings=" + str(len(strings)))
        for m in modules:
            print("   " + m)


if __name__ == "__main__":
    main()
