# -*- coding: utf-8 -*-
"""
IMAPPS-40325, часть B: ожидание порций после отмены видит только порции своего запуска.

Через интерфейс отмену не поймать: запуск на стенде идет ~4 с. Поэтому проверка компонентная, через
внешнее соединение (расширение IMAPPS40325 в нем подключено): запускаются подставные фоновые задания
VTB_ОбщийМодуль.Пауза с ключами порций запуска X, затем вызываются функции модуля менеджера.

Ожидаемо:
  ЕстьАктивныеПорцииЗапуска(Д, X) = Истина, (Д, Y) = Ложь, (Д, "") = Истина;
  ЕстьАктивныеПорцииРегламентаЗаДату(Д) = Истина (типовая функция, видит все порции за дату);
  ОжидатьЗавершенияПорцийРегламентаЗаДату с ИдентификаторЗапуска = Y возвращается сразу,
  с ИдентификаторЗапуска = X - после завершения порций X.
"""
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stand  # noqa: E402

PAUSE_SEC = 12
RESULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Тестирование",
                      "проверка_ожидания_порций.json")


def main():
    c = stand.connect()
    periods = c.Справочники.РегламентныеПериоды
    day = stand.make_date(c, *stand.TEST_DAY)
    ymd = "%04d%02d%02d" % stand.TEST_DAY
    run_x = str(uuid.uuid4())
    run_y = str(uuid.uuid4())
    report = {"run_x": run_x, "run_y": run_y, "checks": []}

    def check(name, actual, expected):
        ok = actual == expected
        report["checks"].append({"проверка": name, "ожидалось": expected, "получено": actual, "итог": "OK" if ok else "FAIL"})
        print(("OK   " if ok else "FAIL ") + name, "=", actual)

    jobs = []
    for portion in (1, 2):
        args = c.NewObject("Массив")
        args.Добавить(PAUSE_SEC)
        key = "IM8663_%s_%s_0_%d_T40325" % (ymd, run_x, portion)
        jobs.append(c.ДлительныеОперации.ЗапуститьФоновоеЗаданиеСКонтекстомКлиента(
            "VTB_ОбщийМодуль.Пауза", args, key, "T40325 подставная порция %d" % portion))
    time.sleep(2)

    check("ЕстьАктивныеПорцииЗапуска(Д, X)", bool(periods.ЕстьАктивныеПорцииЗапуска(day, run_x)), True)
    check("ЕстьАктивныеПорцииЗапуска(Д, Y)", bool(periods.ЕстьАктивныеПорцииЗапуска(day, run_y)), False)
    check("ЕстьАктивныеПорцииЗапуска(Д, пусто)", bool(periods.ЕстьАктивныеПорцииЗапуска(day, "")), True)
    check("ЕстьАктивныеПорцииРегламентаЗаДату(Д) - типовая", bool(periods.ЕстьАктивныеПорцииРегламентаЗаДату(day)), True)

    def wait_seconds(run_id):
        params = c.NewObject("Структура")
        params.Вставить("ДатаПериода", day)
        params.Вставить("ИдентификаторЗапуска", run_id)
        address = c.PutToTempStorage(None, c.NewObject("УникальныйИдентификатор"))
        started = time.time()
        periods.ОжидатьЗавершенияПорцийРегламентаЗаДату(params, address)
        return round(time.time() - started, 1)

    seconds_y = wait_seconds(run_y)
    check("Ожидание порций запуска Y вернулось сразу (< 2 с)", seconds_y < 2, True)
    report["wait_y_seconds"] = seconds_y
    seconds_x = wait_seconds(run_x)
    check("Ожидание порций запуска X дождалось их завершения (>= 5 с)", seconds_x >= 5, True)
    report["wait_x_seconds"] = seconds_x
    check("После ожидания порций X активных нет", bool(periods.ЕстьАктивныеПорцииЗапуска(day, run_x)), False)

    os.makedirs(os.path.dirname(RESULT), exist_ok=True)
    with open(RESULT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("ожидание Y, с:", seconds_y, "ожидание X, с:", seconds_x)
    print("Итог:", "OK" if all(x["итог"] == "OK" for x in report["checks"]) else "FAIL")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
