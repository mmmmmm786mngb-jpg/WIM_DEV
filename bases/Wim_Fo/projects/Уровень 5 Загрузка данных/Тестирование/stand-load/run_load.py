#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Нагрузочный прогон трех ФО-загрузок уровня 5 на разработческой базе.

Каждая обработка выполняется фоновым заданием (серверный контекст - в нем
доступна подписка УК_* на запись дополнительных сведений). TCRIS выполняется
дважды: первая запись и повтор по тем же значениям. Результат - load_run.json
и записи РС ЗамерыВремени, собранные по ключам прогона.

Запуск: python run_load.py [tcris|mmvb|indexes ...] (без аргументов - все)
"""

import datetime
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PROJECT, "Тестирование", "stand"))
import stand_common as sc  # noqa: E402

BUILD = os.path.join(HERE, "build")
RESULT = os.path.join(HERE, "load_run.json")

PLAN = [
    ("indexes", "внЗагрузкаИндексовФО.epf", 1,
     ["ЗагрузкаИндексов", "ЗагрузкаИндексов.Чтение", "ЗагрузкаИндексов.Запись"]),
    ("tcris", "ЗагрузкаДопРеквизитаTCRIS.epf", 2,
     ["ЗагрузкаTCRIS", "ЗагрузкаTCRIS.ЧтениеRates", "ЗагрузкаTCRIS.Сопоставление", "ЗагрузкаTCRIS.Запись"]),
    ("mmvb", "внЗагрузкаКотировокММВБ.epf", 1,
     ["ЗагрузкаКотировокММВБ", "ЗагрузкаКотировокММВБ.Чтение", "ЗагрузкаКотировокММВБ.Чтение.Разбор",
      "ЗагрузкаКотировокММВБ.Чтение.Поиск", "ЗагрузкаКотировокММВБ.Чтение.Лог", "ЗагрузкаКотировокММВБ.Запись"]),
]


def log(text):
    print("%s %s" % (datetime.datetime.now().strftime("%H:%M:%S"), text), flush=True)


def collect(conn, keys, since):
    names = conn.NewObject("Массив")
    for key in keys:
        names.Добавить(key)
    rows = sc.query_rows(
        conn,
        "ВЫБРАТЬ\n"
        "\tЗамеры.КлючеваяОперация.Имя КАК Ключ,\n"
        "\tЗамеры.ВремяВыполнения КАК Секунды,\n"
        "\tЗамеры.ВесЗамера КАК Вес,\n"
        "\tЗамеры.Комментарий КАК Комментарий,\n"
        "\tЗамеры.ДатаЗаписиЛокальная КАК Дата\n"
        "ИЗ\n"
        "\tРегистрСведений.ЗамерыВремени КАК Замеры\n"
        "ГДЕ\n"
        "\tЗамеры.КлючеваяОперация.Имя В (&Ключи)\n"
        "\tИ Замеры.ДатаЗаписиЛокальная >= &Начало\n"
        "УПОРЯДОЧИТЬ ПО\n"
        "\tЗамеры.ДатаЗаписиЛокальная",
        {"Ключи": names, "Начало": since},
    )
    result = []
    for row in rows:
        result.append({
            "key": row["Ключ"],
            "seconds": float(row["Секунды"]),
            "weight": float(row["Вес"]),
            "comment": str(row["Комментарий"] or "")[:300],
            "stamp": str(row["Дата"]),
        })
    return result


def main():
    only = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
    fo = sc.connect("wim_fo")
    log("connected wim_fo")
    if not fo.Константы.ВыполнятьЗамерыПроизводительности.Получить():
        raise SystemExit("замеры на ФО выключены")

    results = {}
    if os.path.exists(RESULT):
        with open(RESULT, encoding="utf-8") as handle:
            results = json.load(handle)

    for label, epf_name, runs, keys in PLAN:
        if only and label not in only:
            continue
        epf_path = os.path.join(BUILD, epf_name)
        if not os.path.exists(epf_path):
            log("SKIP %s: нет %s" % (label, epf_name))
            continue
        entry = {"runs": [], "error": ""}
        results[label] = entry
        for run_number in range(1, runs + 1):
            since = fo.ТекущаяДатаСеанса() - datetime.timedelta(seconds=10)
            log("start %s run %d" % (label, run_number))
            state, error = sc.run_epf_method_bg(fo, epf_path, "НагрузочныйПрогон", timeout=3600,
                                                job_key="T5L5LOAD_" + label)
            log("state %s %s" % (label, state))
            rows = collect(fo, keys, since)
            entry["runs"].append({"number": run_number, "state": str(state), "rows": rows})
            if error:
                entry["error"] = error[:1500]
                log("ERROR %s: %s" % (label, error[:300]))
                break
            for row in rows:
                log("  %-45s %8.3f с  вес %8.0f" % (row["key"], row["seconds"], row["weight"]))
        with open(RESULT, "w", encoding="utf-8") as handle:
            json.dump(results, handle, ensure_ascii=False, indent=2)
    log("saved " + RESULT)


if __name__ == "__main__":
    main()
