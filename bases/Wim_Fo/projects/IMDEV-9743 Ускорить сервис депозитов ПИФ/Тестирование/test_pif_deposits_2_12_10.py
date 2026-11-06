# -*- coding: utf-8 -*-
"""Регресс и замер пакета ТаблицаДепозитов на dev ПИФ (WIM_PIF, базовая конфигурация 2.12.10.0, без расширения).

На одних и тех же данных выполняются два текста пакета запроса функции ТаблицаДепозитов модуля веб-сервиса deposits:
  - ДО: текст версии 2.12.8.0 (копия оригинала из расширения ПИФ_ДепозитыОдноЧтение, блоки #Вставка убраны);
  - ПОСЛЕ: текст из выгрузки текущей конфигурации dev ПИФ 2.12.10.0 (WebServices/deposits/Ext/Module.bsl).
Для каждой даты запроса результаты сравниваются построчно по всем полям, время замеряется попеременно (ДО, ПОСЛЕ).
Дополнительно по временным таблицам версии ПОСЛЕ считается, сколько движений выдачи на счет и есть ли счета с двумя
проводками выдачи в один период (случай, при котором в ответе две строки по депозиту).

    python test_pif_deposits_2_12_10.py [повторов]

Данные не записываются. Лог - Тестирование/reports/base_2_12_10_<время>.txt.
"""
import datetime
import json
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
STAND = os.path.join(os.path.dirname(PROJECT), "IMDEV-9532 Оптимизировать загрузку остатков портфелей из МО в ФО",
                     "Тестирование", "Стенд_МО_ФО")
sys.path.insert(0, STAND)
import stand_common  # noqa: E402

EXT_MODULE = os.path.join(PROJECT, "Расширения", "ПИФ_ДепозитыОдноЧтение", "WebServices", "deposits", "Ext", "Module.bsl")
# Путь из реестра баз (configSrc) там записан с неэкранированным "\1", поэтому выгрузка ПИФ задана явно.
NEW_MODULE = r"C:\1c\Cursor_1c\WORK\Wim_PIF\SRC\cf\WebServices\deposits\Ext\Module.bsl"
DATES = [
    ("до первой выдачи", datetime.datetime(2024, 1, 14)),
    ("день выдачи, начало дня", datetime.datetime(2024, 1, 15)),
    ("следующий день после выдачи", datetime.datetime(2024, 1, 16)),
    ("середина периода", datetime.datetime(2025, 6, 30)),
    ("дата прогонов 29.10", datetime.datetime(2026, 10, 29)),
    ("текущая дата", datetime.datetime(2026, 11, 6)),
]


def function_lines(path, header):
    lines = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n").split("\n")
    start = next(i for i, line in enumerate(lines) if re.match(header, line))
    end = next(i for i in range(start, len(lines)) if lines[i].startswith("КонецФункции"))
    return lines[start:end + 1]


def old_function():
    result, mode = [], None
    for line in function_lines(EXT_MODULE, r"Функция ПИФД_ТаблицаДепозитов"):
        marker = line.strip()
        if marker in ("#Вставка", "#Удаление"):
            mode = marker
            continue
        if marker in ("#КонецВставки", "#КонецУдаления"):
            mode = None
            continue
        if mode != "#Вставка":
            result.append(line)
    return result


def query_text(lines):
    start = next(i for i, line in enumerate(lines) if "Запрос.Текст =" in line)
    text = []
    for line in lines[start + 1:]:
        body = line.strip()
        if body.startswith('"'):
            body = body[1:]
        elif body.startswith("|"):
            body = body[1:]
        else:
            continue
        done = body.endswith('";')
        text.append(body[:-2] if done else body)
        if done:
            break
    return "\n".join(text)


def value_str(conn, value):
    if value is None:
        return "NULL"
    if isinstance(value, (int, float, str, bool)):
        return repr(value) if isinstance(value, float) else str(value)
    try:
        return conn.XMLСтрока(value)
    except Exception:  # noqa: BLE001 - значения дат COM и прочие
        return str(value)


def run(conn, text, params, keep_temp=False):
    q = conn.NewObject("Запрос")
    q.Текст = text
    manager = None
    if keep_temp:
        manager = conn.NewObject("МенеджерВременныхТаблиц")
        q.МенеджерВременныхТаблиц = manager
    for name, value in params.items():
        q.УстановитьПараметр(name, value)
    started = time.perf_counter()
    table = q.Выполнить().Выгрузить()
    elapsed = (time.perf_counter() - started) * 1000
    columns = [table.Колонки.Получить(i).Имя for i in range(table.Колонки.Количество())]
    rows = []
    for i in range(table.Количество()):
        row = table.Получить(i)
        rows.append({c: value_str(conn, row.Получить(j)) for j, c in enumerate(columns)})
    return rows, columns, elapsed, manager


def temp_stats(conn, manager):
    q = conn.NewObject("Запрос")
    q.МенеджерВременныхТаблиц = manager
    q.Текст = (
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Строк, КОЛИЧЕСТВО(РАЗЛИЧНЫЕ ДвиженияВыдачи.БанковскийСчет) КАК Счетов\n"
        "ИЗ ДвиженияВыдачи КАК ДвиженияВыдачи\n"
        ";\n"
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Строк ИЗ ДатыВыдачи КАК ДатыВыдачи\n"
        ";\n"
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Строк ИЗ ПервоначальныеСуммы КАК ПервоначальныеСуммы\n"
        ";\n"
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Счетов ИЗ (ВЫБРАТЬ ДвиженияВыдачи.БанковскийСчет КАК БанковскийСчет\n"
        "    ИЗ ДвиженияВыдачи КАК ДвиженияВыдачи СГРУППИРОВАТЬ ПО ДвиженияВыдачи.БанковскийСчет\n"
        "    ИМЕЮЩИЕ КОЛИЧЕСТВО(*) > 1) КАК Несколько")
    results = q.ВыполнитьПакет()
    get = lambda k, field: results.Получить(k).Выгрузить().Получить(0).Получить(0)
    return {
        "движений_выдачи": get(0, 0), "счетов_с_выдачей": results.Получить(0).Выгрузить().Получить(0).Получить(1),
        "строк_ДатыВыдачи": get(1, 0), "строк_ПервоначальныеСуммы": get(2, 0), "счетов_с_несколькими_движениями": get(3, 0),
    }


def main():
    repeats = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    db = stand_common._registry_db("wim_pif")
    new_module = NEW_MODULE
    text_old = query_text(old_function())
    text_new = query_text(function_lines(new_module, r"Функция ТаблицаДепозитов\("))
    conn = stand_common.connect("wim_pif")
    out = []
    say = lambda s="": (out.append(s), print(s))
    say("Регресс пакета ТаблицаДепозитов: 2.12.8.0 (ДО) против 2.12.10.0 (ПОСЛЕ) на одних данных")
    say("Дата прогона: %s" % datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
    say("База: %s, конфигурация %s %s" % (db["ref"], conn.Метаданные.Имя, conn.Метаданные.Версия))
    exts = [(e.Имя, e.Активно) for e in conn.РасширенияКонфигурации.Получить()]
    say("Расширения базы: %s" % ", ".join("%s(%s)" % (n, "акт" if a else "выкл") for n, a in exts))
    say("Расширение ПИФ_ДепозитыОдноЧтение в базе: %s" % ("ЕСТЬ" if any(n == "ПИФ_ДепозитыОдноЧтение" for n, _ in exts) else "нет"))
    say("Обращений к ДвиженияССубконто в тексте: ДО %d, ПОСЛЕ %d" % (text_old.count("ДвиженияССубконто("), text_new.count("ДвиженияССубконто(")))
    say("Повторов на дату: %d" % repeats)
    currency = conn.ОбщегоНазначения.ПолучитьЗначениеРеквизита(conn.ПараметрыСеанса.ВалютаРегл, "Наименование")
    say("Валюта регламентированного учета: %s" % currency)
    say()
    say("Дата | Случай | СтрокДО | СтрокПОСЛЕ | Совпадает | ДО мс (мин/сред) | ПОСЛЕ мс (мин/сред) | Временные таблицы ПОСЛЕ")
    summary = []
    for label, day in DATES:
        params = {"ДатаЗапроса": stand_common.date_1c(conn, day),
                  "ПустаяДата": stand_common.date_1c(conn, datetime.datetime(1, 1, 1)),
                  "НаименованиеВалютыРегламентированногоУчета": currency}
        times_old, times_new = [], []
        rows_old = rows_new = None
        for _ in range(repeats):
            rows_old, cols_old, t_old, _m = run(conn, text_old, params)
            rows_new, cols_new, t_new, manager = run(conn, text_new, params, keep_temp=True)
            times_old.append(t_old)
            times_new.append(t_new)
        stats = temp_stats(conn, manager)
        canon = lambda rows: sorted(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows)
        same = cols_old == cols_new and canon(rows_old) == canon(rows_new)
        summary.append(same)
        say("%s | %s | %d | %d | %s | %.0f/%.0f | %.0f/%.0f | %s" % (
            day.strftime("%d.%m.%Y"), label, len(rows_old), len(rows_new), "ДА" if same else "НЕТ",
            min(times_old), sum(times_old) / repeats, min(times_new), sum(times_new) / repeats,
            ", ".join("%s=%s" % kv for kv in stats.items())))
        if not same:
            only_old = [r for r in canon(rows_old) if r not in canon(rows_new)]
            only_new = [r for r in canon(rows_new) if r not in canon(rows_old)]
            for r in (only_old[:5] + only_new[:5]):
                say("    РАСХОЖДЕНИЕ " + r)
    say()
    say("ИТОГ | дат=%d | совпало=%d | расхождений=%d" % (len(DATES), sum(summary), len(DATES) - sum(summary)))
    path = os.path.join(HERE, "reports", "base_2_12_10_%s.txt" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(out) + "\n")
    print("лог:", path)


if __name__ == "__main__":
    main()
