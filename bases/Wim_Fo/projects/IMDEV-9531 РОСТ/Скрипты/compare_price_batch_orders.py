#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сверка поручений двух прогонов 16.10.2026: 1.16 и 1.16.9531."""

import datetime
import json
import os
import sys

STAND = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "IMDEV-9530  Замеры ФО",
    "Тестирование",
    "Стенд_замеры",
)
sys.path.insert(0, STAND)
import run_stage4_tests as stage4  # noqa: E402

OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Тестирование",
    "reports",
    "price_batch_orders_compare.json",
)


def window_name(moment):
    if datetime.datetime(2026, 10, 16, 11, 40, 0) <= moment <= datetime.datetime(2026, 10, 16, 11, 42, 30):
        return "1.16"
    if datetime.datetime(2026, 10, 16, 11, 50, 20) <= moment <= datetime.datetime(2026, 10, 16, 11, 53, 0):
        return "1.16.9531"
    return "other"


def num(value):
    if value is None:
        return None
    return round(float(value), 4)


def main():
    fo = stage4.connect("wim_fo")
    rows = stage4.query(fo, """
        ВЫБРАТЬ
            П.Портфель.ВнешнийКод КАК Код,
            П.Актив.Наименование КАК Актив,
            П.Направление КАК Направление,
            П.Количество КАК Количество,
            П.Котировка КАК Котировка,
            П.ЦенаВВалютеРасчетов КАК Цена,
            П.СуммаПоручения КАК Сумма,
            П.Проведен КАК Проведен,
            П.ПометкаУдаления КАК Удален,
            П.Дата КАК Дата
        ИЗ
            Документ.Поручение КАК П
        ГДЕ
            П.Портфель.ВнешнийКод ПОДОБНО "T9531PROP%"
            И П.Дата >= &Начало
            И П.ВидОперации = ЗНАЧЕНИЕ(Перечисление.ВидыПоручений.Сделка)
        """, {"Начало": stage4.date_1c(fo, datetime.datetime(2026, 10, 16, 0, 0, 0))})

    grouped = {"1.16": {}, "1.16.9531": {}, "other": {}}
    for row in rows:
        moment = datetime.datetime(
            row["Дата"].year, row["Дата"].month, row["Дата"].day,
            row["Дата"].hour, row["Дата"].minute, row["Дата"].second,
        )
        name = window_name(moment)
        key = (
            str(row["Код"]),
            str(row["Актив"]),
            str(row["Направление"]),
        )
        bucket = grouped[name].setdefault(key, [])
        bucket.append({
            "qty": num(row["Количество"]),
            "price": num(row["Цена"]),
            "quote": num(row["Котировка"]),
            "sum": num(row["Сумма"]),
            "posted": bool(row["Проведен"]),
            "deleted": bool(row["Удален"]),
            "time": moment.strftime("%H:%M:%S"),
        })

    keys = set(grouped["1.16"]) | set(grouped["1.16.9531"])
    mismatches = []
    only_old = []
    only_new = []
    same = 0
    for key in sorted(keys):
        old = grouped["1.16"].get(key, [])
        new = grouped["1.16.9531"].get(key, [])
        if not old:
            only_new.append({"key": key, "new": new})
            continue
        if not new:
            only_old.append({"key": key, "old": old})
            continue
        def body(item):
            return (item["qty"], item["price"], item["quote"], item["sum"], item["posted"], item["deleted"])

        old_s = sorted(old, key=body)
        new_s = sorted(new, key=body)
        if [body(item) for item in old_s] == [body(item) for item in new_s]:
            same += 1
        else:
            mismatches.append({"key": list(key), "old": old_s, "new": new_s})

    def totals(name):
        docs = [item for items in grouped[name].values() for item in items]
        return {
            "documents": len(docs),
            "keys": len(grouped[name]),
            "deleted": sum(1 for item in docs if item["deleted"]),
            "not_posted": sum(1 for item in docs if not item["posted"]),
        }

    payload = {
        "same_keys": same,
        "mismatch_keys": len(mismatches),
        "only_old": len(only_old),
        "only_new": len(only_new),
        "totals": {name: totals(name) for name in ("1.16", "1.16.9531", "other")},
        "mismatches": mismatches[:40],
        "only_old_sample": only_old[:20],
        "only_new_sample": only_new[:20],
    }
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    def prefix_counts(name):
        counts = {}
        for key, items in grouped[name].items():
            code = key[0]
            prefix = code.split("_")[1][:1] if "_" in code else "?"
            counts[prefix] = counts.get(prefix, 0) + len(items)
        return counts

    def prefix_of(code):
        return code.split("_")[1][:1] if "_" in code else "?"

    def stats(name, prefix):
        items = [
            item for key, docs in grouped[name].items() if prefix_of(key[0]) == prefix for item in docs
        ]
        if not items:
            return None
        qtys = [item["qty"] for item in items]
        prices = sorted(set(item["price"] for item in items))
        return {
            "n": len(items),
            "qty_min": min(qtys),
            "qty_max": max(qtys),
            "prices": prices[:8],
            "deleted": sum(1 for item in items if item["deleted"]),
        }

    codes = {name: {prefix_of(key[0]): set() for key in grouped[name]} for name in grouped}
    for name, bucket in grouped.items():
        for key in bucket:
            codes[name].setdefault(prefix_of(key[0]), set()).add(key[0])
    overlap = {
        "sale_old_new": len(codes["1.16"].get("S", set()) & codes["1.16.9531"].get("S", set())),
        "reinvest_old_new": len(codes["1.16"].get("R", set()) & codes["1.16.9531"].get("R", set())),
        "reinvest_old_other": len(codes["1.16"].get("R", set()) & codes["other"].get("R", set())),
        "reinvest_new_other": len(codes["1.16.9531"].get("R", set()) & codes["other"].get("R", set())),
        "purchase_new": len(codes["1.16.9531"].get("P", set())),
    }

    print("same", same)
    print("mismatch", len(mismatches))
    print("only_old", len(only_old))
    print("only_new", len(only_new))
    print("overlap", overlap)
    print("sale", stats("1.16", "S"), stats("1.16.9531", "S"))
    print("reinvest", stats("1.16", "R"), stats("1.16.9531", "R"), stats("other", "R"))
    print("purchase_new", stats("1.16.9531", "P"))


if __name__ == "__main__":
    main()
