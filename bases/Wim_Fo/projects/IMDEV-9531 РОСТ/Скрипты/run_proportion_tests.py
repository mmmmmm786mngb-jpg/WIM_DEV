#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Прогон точек входа РОСТ на выборке T9531PROP (пропорции ПРОД).

Покупка: 20 портфелей одного прогона. Продажа: 100 строк. Реинвестирование:
кнопка потоков берет 200 из 6694, как на ПРОД. Цена тестовая, из котировок.
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

NEW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "НОВЫЙ_ОРИГИНАЛ")
EPF = os.path.join(NEW_DIR, "внСозданиеТорговыхПорученийРОСТ.epf")
OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Тестирование",
    "reports",
    "proportion_run.json",
)
SCENARIOS = [
    "Покупка.Команда",
    "Покупка.Форма",
    "Продажа.Команда",
    "Продажа.Форма",
    "Реинвест.Форма",
    "Реинвест.Потоки",
    "Блокировки.Потоки",
]


def main():
    fo = stage4.connect("wim_fo")
    rost_ref = stage4.find_ref(
        fo,
        "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
        "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления",
        {"Имя": "СозданиеТорговыхПорученийРОСТ"},
    )
    settings = rost_ref.ПолучитьОбъект().ХранилищеНастроек.Получить()
    rost_ref = stage4.register_epf(fo, "СозданиеТорговыхПорученийРОСТ", EPF, settings)
    test_ref = stage4.test_epf(fo)
    started = stage4.now_iso(fo)
    steps = []
    for name in SCENARIOS:
        try:
            params = stage4.rost_params(fo, name, rost_ref, test_ref, "замеры")
            out = stage4.run_harness(fo, test_ref, params, name, timeout=7200)
            out["шаг"] = name
            steps.append(out)
            stage4.log("done", name, out.get("длительность_с"), (out.get("ошибка") or "")[:180])
        except Exception:
            steps.append({"шаг": name, "ошибка": traceback.format_exc()[-1500:]})
            stage4.log("FAIL", name)
    fo = stage4.connect("wim_fo")
    measures = stage4.measurements(fo, started)
    payload = {"started": started, "epf": EPF, "steps": steps, "measurements": measures}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)
    stage4.log("saved", OUT, "measures", len(measures))


if __name__ == "__main__":
    main()
