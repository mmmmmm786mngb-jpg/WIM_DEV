#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare PFF before/after for IMDEV-9095."""

import json
import re
from collections import defaultdict
from pathlib import Path

BASE = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects"
    r"\IMDEV-9095 Загрузка отчетов брокера\Тестирование"
)
BEFORE = BASE / "Замеры_01_06_2026_БЫЛО.pff"
AFTER = BASE / "Замеры_01_06_2026_СТАЛО.pff"
OUT = BASE / "reports" / "zamery_01_06_2026_comparison.json"

RECORD_RE = re.compile(
    r'"},"(?P<module>[^"]+)",(?P<line>\d+),"(?P<code>.*?)",'
    r'(?P<hits>\d+),(?P<total>[\d.]+),(?P<pure>[\d.]+),'
    r'(?P<pct_total>[\d.]+),(?P<pct_pure>[\d.]+),'
)

KEY_LINES = [
    ("EPF", "СоздатьВсёНаСервере", "внРаспределениеДоходовПоЦеннымБумагам", 122, "СоздатьВсёНаСервере"),
    ("EPF", "Записать НКД", "внРаспределениеДоходовПоЦеннымБумагам", 258, "ОбОперация.Записать"),
    ("EPF", "Записать погашение", "внРаспределениеДоходовПоЦеннымБумагам", 529, "ОбОперация.Записать"),
    ("P1", "Индекс ДокументОснование", "ОбщегоНазначенияДУ", 2447, "Запрос.Выполнить"),
    ("P3 base", "Остатки (база стр.1219)", "УчетДоходовРасходовСервер", 1219, "Запрос.Выполнить"),
    ("P3 zob", "Остатки (zob стр.221)", "zob ОбщийМодуль.УчетДоходовРасходовСервер", 221, "Запрос.Выполнить"),
    ("P3 fn", "ПодготовитьТаблицу...", "УчетДоходовРасходовСервер", 1010, "ПодготовитьТаблицуВалютных"),
    ("VU", "Формирование ВУ", "ОперацияПоСчетуБрокера", 1614, "ФормированиеДокументаОтражение"),
    ("zob", "zob_ПолучитьТип...", "zob ОбщийМодуль.УчетДоходовРасходовСервер", 211, "zob_ПолучитьТип"),
    ("zob", "zob_УстановитьВыразить...", "zob ОбщийМодуль.УчетДоходовРасходовСервер", 215, "zob_УстановитьВыразить"),
]


def parse_records(text):
    records = []
    for m in RECORD_RE.finditer(text):
        records.append(
            {
                "module": m.group("module"),
                "line": int(m.group("line")),
                "code": m.group("code"),
                "hits": int(m.group("hits")),
                "total": float(m.group("total")),
                "pure": float(m.group("pure")),
                "pct_pure": float(m.group("pct_pure")),
            }
        )
    return records


def find_key(records, module_part, line, code_part):
    for r in records:
        if module_part in r["module"] and r["line"] == line and code_part in r["code"]:
            return r
    return None


def module_totals(records, module_part):
    total = 0.0
    hits = 0
    for r in records:
        if module_part in r["module"]:
            total += r["total"]
            hits += r["hits"]
    return round(total, 3), hits


def main():
    before_recs = parse_records(BEFORE.read_text(encoding="utf-8"))
    after_recs = parse_records(AFTER.read_text(encoding="utf-8"))

  # Main session metrics from EPF root
    b_create = find_key(before_recs, "внРаспределениеДоходовПоЦеннымБумагам", 122, "СоздатьВсёНаСервере")
    a_create = find_key(after_recs, "внРаспределениеДоходовПоЦеннымБумагам", 122, "СоздатьВсёНаСервере")

    comparison = []
    for tag, name, mod, line, code in KEY_LINES:
        b = find_key(before_recs, mod, line, code)
        a = find_key(after_recs, mod, line, code)
        row = {
            "tag": tag,
            "name": name,
            "module": mod,
            "line": line,
            "before": None,
            "after": None,
        }
        if b:
            row["before"] = {
                "hits": b["hits"],
                "total_sec": round(b["total"], 3),
                "pure_sec": round(b["pure"], 3),
                "pct_pure": round(b["pct_pure"], 3),
            }
        if a:
            row["after"] = {
                "hits": a["hits"],
                "total_sec": round(a["total"], 3),
                "pure_sec": round(a["pure"], 3),
                "pct_pure": round(a["pct_pure"], 3),
            }
        if row["before"] and row["after"]:
            bt = row["before"]["total_sec"]
            at = row["after"]["total_sec"]
            row["delta_sec"] = round(at - bt, 3)
            row["delta_pct"] = round((at - bt) / bt * 100, 1) if bt else None
        comparison.append(row)

    mod_compare = []
    for mod, label in [
        ("ОбщегоНазначенияДУ", "ОбщегоНазначенияДУ"),
        ("УчетДоходовРасходовСервер", "УчетДоходовРасходовСервер"),
        ("ОперацияПоСчетуБрокера", "ОперацияПоСчетуБрокера"),
        ("zob ОбщийМодуль.УчетДоходовРасходовСервер", "zob (расширение)"),
    ]:
        bt, bh = module_totals(before_recs, mod)
        at, ah = module_totals(after_recs, mod)
        mod_compare.append(
            {
                "module": label,
                "before_sec": bt,
                "after_sec": at,
                "delta_sec": round(at - bt, 3),
                "delta_pct": round((at - bt) / bt * 100, 1) if bt else None,
                "before_hits": bh,
                "after_hits": ah,
            }
        )

    out = {
        "before_file": str(BEFORE),
        "after_file": str(AFTER),
        "base": "AVC_REGR_CLEAN_DU",
        "scenario": "Создать всё (EPF внРаспределениеДоходовПоЦеннымБумагам)",
        "summary": {
            "create_all_before_sec": b_create["total"] if b_create else None,
            "create_all_after_sec": a_create["total"] if a_create else None,
            "create_all_delta_sec": round(a_create["total"] - b_create["total"], 3) if b_create and a_create else None,
            "create_all_delta_pct": round((a_create["total"] - b_create["total"]) / b_create["total"] * 100, 1) if b_create and a_create else None,
            "documents_nkd_before": find_key(before_recs, "внРаспределениеДоходовПоЦеннымБумагам", 258, "Записать")["hits"] if find_key(before_recs, "внРаспределениеДоходовПоЦеннымБумагам", 258, "Записать") else None,
            "documents_nkd_after": find_key(after_recs, "внРаспределениеДоходовПоЦеннымБумагам", 258, "Записать")["hits"] if find_key(after_recs, "внРаспределениеДоходовПоЦеннымБумагам", 258, "Записать") else None,
        },
        "key_lines": comparison,
        "modules": mod_compare,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
