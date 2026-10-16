#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сравнение 1.16 и 1.16.9531 на выборке T9531PROP.
Перед каждой версией статусы и позиция готовятся заново. Цена тестовая.
"""

import json
import os
import sys
import traceback

STAND = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "IMDEV-9530  Замеры ФО",
    "Тестирование",
    "Стенд_замеры",
)
sys.path.insert(0, STAND)
import run_stage4_tests as stage4  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPF = {
    "1.16": os.path.join(ROOT, "НОВЫЙ_ОРИГИНАЛ", "внСозданиеТорговыхПорученийРОСТ.epf"),
    "1.16.9531": os.path.join(ROOT, "ОПТИМИЗИРОВАННО", "внСозданиеТорговыхПорученийРОСТ.epf"),
}
OUT = os.path.join(ROOT, "Тестирование", "reports", "price_batch_compare.json")
SCENARIOS = ["Покупка.Команда", "Продажа.Команда", "Реинвест.Потоки"]


def prepare(fo, test_ref):
    steps = []
    for scenario, title in (("ПропорцииПрод", "пропорции"), ("ПозицияНаВчера", "позиция на вчера")):
        params = fo.NewObject("Структура")
        params.Вставить("Сценарий", scenario)
        out = stage4.run_harness(fo, test_ref, params, title, timeout=7200)
        steps.append({
            "шаг": scenario,
            "длительность_с": out.get("длительность_с"),
            "ошибка": out.get("ошибка"),
            "лог": (out.get("лог") or "")[-500:],
        })
        stage4.log("prep", scenario, out.get("состояние"), out.get("длительность_с"), (out.get("ошибка") or "")[:200])
    return steps


def price_totals(measures):
    totals = {}
    for row in measures:
        key = row["ключ"]
        if "ЦенаИзСтакана" not in key and "ЦенаИзКеша" not in key and key.count(".") != 1:
            continue
        bucket = totals.setdefault(key, {"записей": 0, "вес": 0.0, "время_на_вес_с": 0.0, "вклад_с": 0.0})
        bucket["записей"] += 1
        bucket["вес"] += row["вес"]
        bucket["вклад_с"] += row["время_с"] * row["вес"]
    for bucket in totals.values():
        if bucket["вес"]:
            bucket["время_на_вес_с"] = round(bucket["вклад_с"] / bucket["вес"], 6)
        bucket["вклад_с"] = round(bucket["вклад_с"], 3)
        bucket["вес"] = round(bucket["вес"], 3)
    return totals


def run_version(label, path):
    fo = stage4.connect("wim_fo")
    test_ref = stage4.test_epf(fo)
    prep = prepare(fo, test_ref)
    fo = stage4.connect("wim_fo")
    rost_ref = stage4.find_ref(
        fo,
        "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
        "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления",
        {"Имя": "СозданиеТорговыхПорученийРОСТ"},
    )
    settings = rost_ref.ПолучитьОбъект().ХранилищеНастроек.Получить()
    rost_ref = stage4.register_epf(fo, "СозданиеТорговыхПорученийРОСТ", path, settings)
    test_ref = stage4.test_epf(fo)
    started = stage4.now_iso(fo)
    steps = []
    for name in SCENARIOS:
        try:
            params = stage4.rost_params(fo, name, rost_ref, test_ref, "замеры")
            out = stage4.run_harness(fo, test_ref, params, name, timeout=7200)
            log = out.get("лог") or ""
            steps.append({
                "шаг": name,
                "длительность_с": out.get("длительность_с"),
                "состояние": out.get("состояние"),
                "ошибка": out.get("ошибка"),
                "пакетных_запросов": log.count("пакетный запрос стакана"),
                "лог_хвост": log[-800:],
            })
            stage4.log("done", label, name, out.get("длительность_с"), (out.get("ошибка") or "")[:160])
        except Exception:
            steps.append({"шаг": name, "ошибка": traceback.format_exc()[-1500:]})
            stage4.log("FAIL", label, name)
    fo = stage4.connect("wim_fo")
    measures = stage4.measurements(fo, started)
    return {
        "версия": label,
        "epf": path,
        "подготовка": prep,
        "шаги": steps,
        "цены": price_totals(measures),
        "замеров": len(measures),
    }


def main():
    report = []
    for label, path in EPF.items():
        report.append(run_version(label, path))
        with open(OUT, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, default=str)
        stage4.log("saved partial", label)
    stage4.log("saved", OUT)


if __name__ == "__main__":
    main()
