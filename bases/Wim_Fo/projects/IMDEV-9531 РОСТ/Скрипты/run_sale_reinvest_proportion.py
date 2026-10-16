#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Копия позиции на вчера и прогон продажи и реинвестирования в тестовом режиме."""

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

OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Тестирование",
    "reports",
    "proportion_run_sale_reinvest.json",
)
SCENARIOS = ["Продажа.Команда", "Продажа.Форма", "Реинвест.Потоки", "Блокировки.Потоки"]


def main():
    fo = stage4.connect("wim_fo")
    test_ref = stage4.test_epf(fo)
    params = fo.NewObject("Структура")
    params.Вставить("Сценарий", "ПозицияНаВчера")
    copied = stage4.run_harness(fo, test_ref, params, "позиция на вчера", timeout=7200)
    stage4.log("copy", copied.get("состояние"), copied.get("лог"), (copied.get("ошибка") or "")[:400])

    rost_ref = stage4.find_ref(
        fo,
        "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
        "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления",
        {"Имя": "СозданиеТорговыхПорученийРОСТ"},
    )
    started = stage4.now_iso(fo)
    steps = [{"шаг": "ПозицияНаВчера", "лог": copied.get("лог"), "ошибка": copied.get("ошибка"),
              "длительность_с": copied.get("длительность_с")}]
    for name in SCENARIOS:
        try:
            run = stage4.rost_params(fo, name, rost_ref, test_ref, "замеры")
            out = stage4.run_harness(fo, test_ref, run, name, timeout=7200)
            out["шаг"] = name
            steps.append(out)
            stage4.log("done", name, out.get("длительность_с"), (out.get("ошибка") or "")[:160])
        except Exception:
            steps.append({"шаг": name, "ошибка": traceback.format_exc()[-1200:]})
            stage4.log("FAIL", name)
    fo = stage4.connect("wim_fo")
    measures = stage4.measurements(fo, started)
    payload = {"started": started, "steps": steps, "measurements": measures}
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)
    stage4.log("saved", len(measures))


if __name__ == "__main__":
    main()
