#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сравнение кода расширения NDFL_RDU (IMDEV-7330) с базовой конфигурацией WIM_FIn,
в которую вендор (Аванкор) внедрил доработки.

Логика:
  1. Парсим BSL-модули расширения и соответствующие модули базовой CF.
  2. Из имён процедур/функций расширения убираем префикс NDFL_RDU_.
  3. Ищем одноимённую процедуру/функцию в модуле CF и сравниваем тела.
  4. Печатаем сводку и подробные диффы в файл-отчёт (JSON + текст).

Вывод только ASCII в консоль (см. правила проекта).
"""

import json
import os
import re
import sys
import difflib

EXT_ROOT = os.path.join(
    r"C:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects",
    "IMDEV-7330 Оптимизация 1С ФИН_Расчет НДФЛ",
    "Расширения", "NDFL_RDU")
CF_ROOT = r"C:\1c\Cursor_1c\WORK\WIM_FIn\src\cf"
OUT_DIR = os.path.join(
    r"C:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects",
    "IMDEV-7330 Оптимизация 1С ФИН_Расчет НДФЛ",
    "Документация")

PREFIX = "NDFL_RDU_"

# Пары модулей: (ключ блока, путь в расширении, путь в CF)
MODULE_PAIRS = [
    ("dp_manager",
     r"DataProcessors\ФормированиеНачисленийНДФЛ\Ext\ManagerModule.bsl",
     r"DataProcessors\ФормированиеНачисленийНДФЛ\Ext\ManagerModule.bsl"),
    ("dp_object",
     r"DataProcessors\ФормированиеНачисленийНДФЛ\Ext\ObjectModule.bsl",
     r"DataProcessors\ФормированиеНачисленийНДФЛ\Ext\ObjectModule.bsl"),
    ("dp_form",
     r"DataProcessors\ФормированиеНачисленийНДФЛ\Forms\Форма\Ext\Form\Module.bsl",
     r"DataProcessors\ФормированиеНачисленийНДФЛ\Forms\Форма\Ext\Form\Module.bsl"),
    ("doc_portfel_object",
     r"Documents\НачислениеНДФЛПоПортфелю\Ext\ObjectModule.bsl",
     r"Documents\НачислениеНДФЛПоПортфелю\Ext\ObjectModule.bsl"),
    ("doc_uk_manager",
     r"Documents\НачислениеНДФЛПоУправляющейКомпании\Ext\ManagerModule.bsl",
     r"Documents\НачислениеНДФЛПоУправляющейКомпании\Ext\ManagerModule.bsl"),
    ("doc_uk_object",
     r"Documents\НачислениеНДФЛПоУправляющейКомпании\Ext\ObjectModule.bsl",
     r"Documents\НачислениеНДФЛПоУправляющейКомпании\Ext\ObjectModule.bsl"),
    ("cancel_manager",
     r"DataProcessors\ОтменаПроведенияНачисленийНДФЛ\Ext\ManagerModule.bsl",
     r"DataProcessors\ОтменаПроведенияНачисленийНДФЛ\Ext\ManagerModule.bsl"),
    ("cancel_object",
     r"DataProcessors\ОтменаПроведенияНачисленийНДФЛ\Ext\ObjectModule.bsl",
     r"DataProcessors\ОтменаПроведенияНачисленийНДФЛ\Ext\ObjectModule.bsl"),
    ("cancel_form",
     r"DataProcessors\ОтменаПроведенияНачисленийНДФЛ\Forms\Форма\Ext\Form\Module.bsl",
     r"DataProcessors\ОтменаПроведенияНачисленийНДФЛ\Forms\Форма\Ext\Form\Module.bsl"),
]

DECL_RE = re.compile(r"^\s*(Процедура|Функция)\s+([A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё0-9_]*)\s*\(", re.IGNORECASE)
END_RE = re.compile(r"^\s*(КонецПроцедуры|КонецФункции)\s*(//.*)?$", re.IGNORECASE)
ANNOT_RE = re.compile(r"^\s*&", re.IGNORECASE)


def read_lines(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read().replace("\r\n", "\n").split("\n")


def parse_module(path):
    """Возвращает список словарей с описанием процедур/функций модуля."""
    lines = read_lines(path)
    result = []
    i = 0
    n = len(lines)
    while i < n:
        m = DECL_RE.match(lines[i])
        if m:
            # собираем аннотации выше объявления
            annots = []
            j = i - 1
            while j >= 0 and (ANNOT_RE.match(lines[j]) or lines[j].strip() == ""):
                if ANNOT_RE.match(lines[j]):
                    annots.insert(0, lines[j].strip())
                    j -= 1
                else:
                    break
            start = i
            k = i
            while k < n and not END_RE.match(lines[k]):
                k += 1
            body = lines[start:k + 1]
            result.append({
                "kind": m.group(1),
                "name": m.group(2),
                "annotations": annots,
                "start": start + 1,
                "end": k + 1,
                "lines": body,
            })
            i = k + 1
        else:
            i += 1
    return result


def norm_ext_line(line):
    """Нормализация строки расширения: снимаем префикс NDFL_RDU_."""
    return line.replace(PREFIX, "")


def norm_for_compare(lines, strip_prefix):
    out = []
    for ln in lines:
        s = ln
        if strip_prefix:
            s = norm_ext_line(s)
        s = s.replace("\t", "    ").rstrip()
        out.append(s)
    # убираем пустые строки в конце
    while out and out[-1] == "":
        out.pop()
    return out


def signature(lines):
    """Полная сигнатура (может быть многострочной) до закрывающей скобки."""
    buf = []
    depth = 0
    for ln in lines:
        buf.append(ln.strip())
        depth += ln.count("(") - ln.count(")")
        if depth <= 0 and "(" in "".join(buf):
            break
    return " ".join(buf)


def main():
    report = []
    for key, ext_rel, cf_rel in MODULE_PAIRS:
        ext_path = os.path.join(EXT_ROOT, ext_rel)
        cf_path = os.path.join(CF_ROOT, cf_rel)
        block = {
            "key": key,
            "ext_path": ext_rel,
            "cf_path": cf_rel,
            "ext_exists": os.path.exists(ext_path),
            "cf_exists": os.path.exists(cf_path),
            "items": [],
        }
        if not block["ext_exists"] or not block["cf_exists"]:
            report.append(block)
            continue

        ext_procs = parse_module(ext_path)
        cf_procs = parse_module(cf_path)
        cf_by_name = {}
        for p in cf_procs:
            cf_by_name.setdefault(p["name"], []).append(p)

        for p in ext_procs:
            target = p["name"]
            has_prefix = target.startswith(PREFIX)
            if has_prefix:
                target = target[len(PREFIX):]
            candidates = cf_by_name.get(target, [])
            item = {
                "ext_name": p["name"],
                "cf_name_expected": target,
                "annotations": p["annotations"],
                "ext_lines": len(p["lines"]),
                "ext_start": p["start"],
                "found": bool(candidates),
                "cf_start": candidates[0]["start"] if candidates else None,
                "cf_lines": len(candidates[0]["lines"]) if candidates else None,
                "cf_dup": len(candidates),
                "ext_signature": signature(p["lines"]),
                "cf_signature": signature(candidates[0]["lines"]) if candidates else None,
                "identical": None,
                "diff": None,
                "ext_body": "\n".join(p["lines"]),
                "cf_body": "\n".join(candidates[0]["lines"]) if candidates else None,
            }
            if candidates:
                a = norm_for_compare(p["lines"], strip_prefix=True)
                b = norm_for_compare(candidates[0]["lines"], strip_prefix=False)
                item["identical"] = (a == b)
                if not item["identical"]:
                    d = list(difflib.unified_diff(a, b, fromfile="EXT", tofile="CF", lineterm="", n=3))
                    item["diff"] = "\n".join(d)
                    # чистое количество изменённых строк
                    item["diff_add"] = sum(1 for x in d if x.startswith("+") and not x.startswith("+++"))
                    item["diff_del"] = sum(1 for x in d if x.startswith("-") and not x.startswith("---"))
            block["items"].append(item)
        report.append(block)

    out_json = os.path.join(OUT_DIR, "imdev7330_compare_raw.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    # Консольная сводка (ASCII)
    for block in report:
        print("=" * 78)
        print("BLOCK: %s  ext=%s cf=%s" % (block["key"], block["ext_exists"], block["cf_exists"]))
        if not block["items"]:
            continue
        for it in block["items"]:
            if not it["found"]:
                status = "NOT FOUND IN CF"
            elif it["identical"]:
                status = "IDENTICAL"
            else:
                status = "DIFF +%d/-%d" % (it.get("diff_add", 0), it.get("diff_del", 0))
            print("  %-60s %s" % (it["cf_name_expected"][:60], status))
    print()
    print("JSON saved: %s" % out_json)


if __name__ == "__main__":
    main()
