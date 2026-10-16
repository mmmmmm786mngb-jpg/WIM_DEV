#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сверка 1.16 и 1.16.9531 на одних и тех же портфелях T9531PROP.

Перед каждой версией удаляются сегодняшние сделки этих портфелей и заново
ставятся статусы. Неторговые вводы не удаляются.
"""

import datetime
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
OUT = os.path.join(ROOT, "Тестирование", "reports", "price_batch_regression.json")
SCENARIOS = ["Покупка.Команда", "Продажа.Команда", "Реинвест.Потоки"]


def num(value):
    if value is None:
        return None
    return round(float(value), 4)


def scenario(fo, test_ref, name, title):
    params = fo.NewObject("Структура")
    params.Вставить("Сценарий", name)
    out = stage4.run_harness(fo, test_ref, params, title, timeout=7200)
    stage4.log(title, out.get("состояние"), out.get("длительность_с"), (out.get("ошибка") or out.get("лог") or "")[:220])
    return {
        "шаг": name,
        "длительность_с": out.get("длительность_с"),
        "состояние": out.get("состояние"),
        "ошибка": out.get("ошибка") or "",
        "лог": (out.get("лог") or "")[-400:],
    }


def snapshot(fo):
    rows = stage4.query(fo, """
        ВЫБРАТЬ
            П.Портфель.ВнешнийКод КАК Код,
            П.Актив.Наименование КАК Актив,
            ПРЕДСТАВЛЕНИЕ(П.Направление) КАК Направление,
            П.Количество КАК Количество,
            П.ЦенаВВалютеРасчетов КАК Цена,
            П.СуммаПоручения КАК Сумма,
            П.Проведен КАК Проведен,
            П.ПометкаУдаления КАК Удален
        ИЗ
            Документ.Поручение КАК П
        ГДЕ
            П.Портфель.ВнешнийКод ПОДОБНО "T9531PROP%"
            И П.Дата >= &Начало
            И П.ВидОперации = ЗНАЧЕНИЕ(Перечисление.ВидыПоручений.Сделка)
        """, {"Начало": stage4.date_1c(fo, datetime.datetime(2026, 10, 16, 0, 0, 0))})
    grouped = {}
    for row in rows:
        key = (stage4.to_text(fo, row["Код"]), stage4.to_text(fo, row["Актив"]), stage4.to_text(fo, row["Направление"]))
        grouped.setdefault(key, []).append({
            "qty": num(row["Количество"]),
            "price": num(row["Цена"]),
            "sum": num(row["Сумма"]),
            "posted": bool(row["Проведен"]),
            "deleted": bool(row["Удален"]),
        })
    return grouped


def run_version(label, path, delay=0):
    fo = stage4.connect("wim_fo")
    test_ref = stage4.test_epf(fo)
    cleared = scenario(fo, test_ref, "ОчиститьСделки", "очистка " + label)
    if cleared["ошибка"]:
        return {"версия": label, "ошибка_очистки": cleared}
    prepared = [
        scenario(fo, test_ref, "ПропорцииПрод", "пропорции " + label),
        scenario(fo, test_ref, "ПозицияНаВчера", "вчера " + label),
    ]
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
            params = stage4.rost_params(fo, name, rost_ref, test_ref, "замеры",
                                         {"ЗадержкаСтакана": delay} if delay else None)
            out = stage4.run_harness(fo, test_ref, params, name, timeout=7200)
            steps.append({
                "шаг": name,
                "длительность_с": out.get("длительность_с"),
                "состояние": out.get("состояние"),
                "ошибка": out.get("ошибка") or "",
            })
            stage4.log("done", label, name, out.get("длительность_с"), (out.get("ошибка") or "")[:160])
        except Exception:
            steps.append({"шаг": name, "ошибка": traceback.format_exc()[-1500:]})
            stage4.log("FAIL", label, name)
    fo = stage4.connect("wim_fo")
    orders = snapshot(fo)
    portable = {
        "|".join(key): docs for key, docs in orders.items()
    }
    measures = stage4.measurements(fo, started)
    return {
        "версия": label,
        "очистка": cleared,
        "подготовка": prepared,
        "шаги": steps,
        "поручения": portable,
        "замеры": [
            {"ключ": row["ключ"], "время_с": row["время_с"], "вес": row["вес"]}
            for row in measures
            if "Цена" in row["ключ"] or row["ключ"].count(".") == 1
        ],
    }


def compare(old, new):
    old_keys = set(old)
    new_keys = set(new)
    same = 0
    diffs = []
    for key in sorted(old_keys & new_keys):
        def body(item):
            return (item["qty"], item["price"], item["sum"], item["posted"], item["deleted"])
        left = sorted(old[key], key=body)
        right = sorted(new[key], key=body)
        if [body(item) for item in left] == [body(item) for item in right]:
            same += 1
        else:
            diffs.append({"key": key, "old": left, "new": right})
    return {
        "совпало": same,
        "расхождения": diffs,
        "только_1_16": sorted(old_keys - new_keys),
        "только_1_16_9531": sorted(new_keys - old_keys),
    }


def main():
    delay = 1.1 if "--delay" in sys.argv else 0
    out_path = os.path.join(ROOT, "Тестирование", "reports",
                            "price_batch_delay.json" if delay else "price_batch_regression.json")
    report = {"задержка_стакана_с": delay}
    versions = []
    for label, path in EPF.items():
        versions.append(run_version(label, path, delay))
        report["версии"] = versions
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        stage4.log("saved partial", label)
    if len(versions) == 2 and "поручения" in versions[0] and "поручения" in versions[1]:
        report["сверка"] = compare(versions[0]["поручения"], versions[1]["поручения"])
        for item in versions:
            item["поручений"] = len(item.pop("поручения"))
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    check = report.get("сверка", {})
    stage4.log(
        "compare",
        "delay", delay,
        "same", check.get("совпало"),
        "diff", len(check.get("расхождения", [])),
        "only_old", len(check.get("только_1_16", [])),
        "only_new", len(check.get("только_1_16_9531", [])),
    )


if __name__ == "__main__":
    main()
