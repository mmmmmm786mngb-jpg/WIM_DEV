# -*- coding: utf-8 -*-
"""Повторные прогоны реинвестирования 1.16 и 1.18 вперемешку: разброс проверки и отправки пачки.

Перед каждым прогоном - ОчиститьСделки (сделки T9531PROP за сегодня удаляются, список реинвестирования снова полный).
Позиции и статусы после прогона run_1_18_tests.py уже подготовлены и реинвестирование их не меняет. Сценарий -
Реинвест.Потоки (пакет 200 в 10 потоках, затем отправка пачки), ответ стакана 1 с (stakan_mock.py должен работать).

    python run_reinvest_repeat.py [повторов] [задержка]     по умолчанию 3 на версию, задержка 1 с
"""
import datetime
import json
import os
import sys

import run_1_18_tests as base

stage4 = base.stage4
OUT = os.path.join(base.REPORTS, "reinvest_repeat.json")


def one_run(label, path, number, delay=1.0):
    fo = stage4.connect("wim_fo")
    test_ref = base.harness_ref(fo)
    cleared = base.service(fo, test_ref, "ОчиститьСделки", "очистка " + label)
    rost_ref = stage4.find_ref(
        fo,
        "ВЫБРАТЬ Д.Ссылка КАК Ссылка ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
        "ГДЕ Д.ИмяОбъекта = &Имя И НЕ Д.ПометкаУдаления",
        {"Имя": stage4.ROST_OBJECT},
    )
    settings = rost_ref.ПолучитьОбъект().ХранилищеНастроек.Получить()
    rost_ref = stage4.register_epf(fo, stage4.ROST_OBJECT, path, settings)
    started = stage4.now_iso(fo)
    base.mock("/reset")
    params = stage4.rost_params(fo, "Реинвест.Потоки", rost_ref, test_ref, "замеры", {"ЗадержкаСтакана": delay} if delay else None)
    out = stage4.run_harness(fo, test_ref, params, "Реинвест.Потоки " + label, timeout=7200)
    stakan = base.mock_count()
    fo = stage4.connect("wim_fo")
    measures = stage4.measurements(fo, started)
    threads = [m for m in measures if m["ключ"] == "СозданиеТорговыхПорученийРОСТ.Реинвестирование"]
    send = [m for m in measures if m["ключ"] == "СозданиеТорговыхПорученийРОСТ.ОтправкаПачки"]
    first_start = min(m["начало_мс"] for m in threads) if threads else 0
    last_end = max(m["начало_мс"] + m["время_с"] * 1000 for m in threads) if threads else 0
    write = [m["время_с"] * m["вес"] for m in measures
             if m["ключ"] == "СозданиеТорговыхПорученийРОСТ.Реинвестирование.ЗаписьПоручения"]
    result = {
        "версия": label,
        "номер": number,
        "задержка_с": delay,
        "очистка": cleared["состояние"] + " " + cleared["ошибка"][:200],
        "время_с": out.get("длительность_с"),
        "ошибка": out.get("ошибка") or out.get("ошибка_задания") or "",
        "поручений": len(out.get("документы") or []),
        "запросов_стакана": stakan,
        "окно_потоков_с": round((last_end - first_start) / 1000, 1),
        "запись_на_поток_с": round(sum(write) / len(write), 2) if write else None,
        "отправка_пачки_с": round(send[0]["время_с"], 1) if send else None,
    }
    stage4.log("RUN", json.dumps(result, ensure_ascii=False))
    return result


def main():
    repeats = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    delay = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    out_path = OUT if delay == 1.0 else OUT.replace(".json", "_delay_%s.json" % str(delay).replace(".", "_"))
    base.mock("/stats")
    report = {"дата": datetime.datetime.now().isoformat(timespec="seconds"), "прогоны": []}
    for number in range(1, repeats + 1):
        for label, path in base.BUILDS.items():
            report["прогоны"].append(one_run(label, path, number, delay))
            with open(out_path, "w", encoding="utf-8") as handle:
                json.dump(report, handle, ensure_ascii=False, indent=2, default=str)
    stage4.log("DONE", out_path)


if __name__ == "__main__":
    main()
