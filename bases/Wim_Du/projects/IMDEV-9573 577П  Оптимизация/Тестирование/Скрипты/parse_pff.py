# -*- coding: utf-8 -*-
"""Разбор замера производительности (.pff) кнопки «Заполнить» документа 577-П.

python parse_pff.py <файл.pff>
Печатает: шапку замера, чистое время по модулям, все строки модуля формы документа,
верх строк модуля объекта по чистому времени и итоги процедур ЗаполнитьРазделN.
"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROW = re.compile(r'\},"((?:[^"]|"")*)",(\d+),"((?:[^"]|"")*)",(\d+),([0-9.]+),([0-9.]+),([0-9.]+),([0-9.]+),')
DOC = "Документ.РО_XBRL6_1_ОтчетПоВнутреннемуУчету_577П"
FORM = DOC + ".Форма.ФормаДокумента.Форма"
OBJ = DOC + ".МодульОбъекта"


def load(path):
    text = open(path, encoding="utf-8-sig").read()
    rows = []
    for m in ROW.finditer(text):
        rows.append({"module": m.group(1), "line": int(m.group(2)),
                     "code": re.sub(r"\s+", " ", m.group(3).replace('""', '"')),
                     "count": int(m.group(4)), "total": float(m.group(5)), "pure": float(m.group(6))})
    return text, rows


def main():
    text, rows = load(sys.argv[1])
    print(text[:400].replace("\r", ""))
    print(len(rows), "строк замера")
    by_module = {}
    for r in rows:
        by_module[r["module"]] = by_module.get(r["module"], 0) + r["pure"]
    print("\n== Чистое время по модулям")
    for name, pure in sorted(by_module.items(), key=lambda x: -x[1])[:8]:
        print(f"{pure:9.2f}  {name}")
    print("\n== Модуль формы документа (все строки)")
    for r in sorted((r for r in rows if r["module"] == FORM), key=lambda r: r["line"]):
        print(f"{r['line']:4} n={r['count']:<6} всего={r['total']:9.2f} чистое={r['pure']:9.2f}  {r['code'][:90]}")
    print("\n== Модуль объекта: 45 строк с наибольшим чистым временем")
    for r in sorted((r for r in rows if r["module"] == OBJ), key=lambda r: -r["pure"])[:45]:
        print(f"{r['line']:5} n={r['count']:<9} всего={r['total']:9.2f} чистое={r['pure']:8.2f}  {r['code'][:95]}")
    print("\n== Вызовы процедур заполнения (полное время строки вызова)")
    for r in sorted((r for r in rows if r["module"] == OBJ and re.match(r"Заполнить\w*\(", r["code"])),
                    key=lambda r: r["line"]):
        print(f"{r['line']:5} n={r['count']:<4} всего={r['total']:9.2f}  {r['code'][:80]}")
    print("\n== Добавление строк в разделы")
    for r in sorted((r for r in rows if r["module"] == OBJ and re.search(r"Раздел\d+\.Добавить\(\)", r["code"])),
                    key=lambda r: r["line"]):
        print(f"{r['line']:5} n={r['count']:<9} {r['code'][:80]}")


if __name__ == "__main__":
    main()
