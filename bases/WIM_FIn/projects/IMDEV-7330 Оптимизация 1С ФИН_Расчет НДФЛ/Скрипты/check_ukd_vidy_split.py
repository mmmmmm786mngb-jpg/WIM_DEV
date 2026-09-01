#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMDEV-7330. Проверка гипотезы расхождения по клиенту Платонов Д.В.

Старая база: ИнвестиционныйВычетУКД делал ДВА вызова РасходыПоНКДПоВидуОбращаемости
             (обращающиеся, затем необращающиеся) и складывал строки через ДополнитьТаблицу.
Новая база:  ОДИН вызов с объединённым списком видов обращаемости.

Группировка результата НЕ содержит ВидыОбращаемостиЦБ, поэтому строки с одинаковым
ключом (Актив, Период, Партия, ДатаПартии, Регистратор), но разными видами обращаемости
в новой версии сливаются в одну строку с суммой Sa+Sb.

Потребитель (ОтразитьУКДиНКДВИнвестВычете) берёт МОДУЛЬ суммы каждой строки:
    было:  |Sa| + |Sb|
    стало: |Sa + Sb|
При разных знаках Sa и Sb результат отличается на 2*min(|Sa|,|Sb|).

Скрипт выполняет типовой текст запроса три раза (обращающиеся / необращающиеся /
объединённый список) и печатает суммы модулей по пакету ПоРегистраторам.
Вывод в консоль - только ASCII.

ВАЖНО: нужна база С ДАННЫМИ. На пустых локальных базах для конфигуратора
результат будет нулевым.

Запуск:
    python check_ukd_vidy_split.py "<строка_подключения>" "<ФИО клиента>" [ГГГГ-ММ-ДД]
Пример:
    python check_ukd_vidy_split.py "Srvr='srv';Ref='fin';App='PyCOM';Locale=ru_RU;" "Платонов Дмитрий Вячеславович" 2026-12-31
"""

import io
import os
import re
import sys
import datetime

import pythoncom
import win32com.client

CONN_STRING = "Srvr='localhost';Ref='WIM_FIN';App='PyCOM';Locale=ru_RU;"

CF_MODULE = (r"C:\1c\Cursor_1c\WORK\Wim_Fin_local\SRC\CF\Documents"
             r"\НачислениеНДФЛПоУправляющейКомпании\Ext\ManagerModule.bsl")

CLIENT_NAME = "Платонов Дмитрий Вячеславович"
CALC_DATE = datetime.datetime(2026, 12, 31, 23, 59, 59)

if len(sys.argv) > 1:
    CONN_STRING = sys.argv[1]
if len(sys.argv) > 2:
    CLIENT_NAME = sys.argv[2]
if len(sys.argv) > 3:
    _d = datetime.datetime.strptime(sys.argv[3], "%Y-%m-%d")
    CALC_DATE = datetime.datetime(_d.year, _d.month, _d.day, 23, 59, 59)

REPORT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "check_ukd_vidy_split_result.txt")


def safe_print(text):
    """Безопасный вывод в консоль Windows - только ASCII."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def extract_query_text(path, func_name):
    """Извлекает литерал Запрос.Текст из тела функции модуля BSL.

    Параметры:
        path      - путь к .bsl файлу
        func_name - имя функции, внутри которой искать первый Запрос.Текст

    Возвращает строку с текстом запроса 1С.
    """
    lines = io.open(path, encoding="utf-8-sig", errors="replace").read().split("\n")

    start = None
    for i, line in enumerate(lines):
        if re.match(r"^\s*Функция\s+" + func_name + r"\s*\(", line):
            start = i
            break
    if start is None:
        raise RuntimeError("function not found: " + func_name)

    assign = None
    for i in range(start, len(lines)):
        if "Запрос.Текст" in lines[i] and "=" in lines[i]:
            assign = i
            break
    if assign is None:
        raise RuntimeError("query literal not found")

    tail = lines[assign].split("=", 1)[1].strip()
    parts = []
    idx = assign

    if tail:
        parts.append(tail.lstrip('"'))
    else:
        idx = assign + 1
        parts.append(lines[idx].strip().lstrip('"'))

    while not parts[-1].rstrip().endswith('";'):
        idx += 1
        raw = lines[idx].strip()
        parts.append(raw[1:] if raw.startswith("|") else raw)

    parts[-1] = parts[-1].rstrip()[:-2]
    return "\n".join(parts).replace('""', '"')


def to_array(conn, values):
    """Создаёт объект Массив 1С из списка значений Python."""
    arr = conn.NewObject("Массив")
    for value in values:
        arr.Добавить(value)
    return arr


def run_variant(conn, query_text, client_ref, vidy):
    """Выполняет пакет запроса для одного набора видов обращаемости.

    Возвращает кортеж (количество строк, сумма модулей) по пакету ПоРегистраторам.
    """
    plans = conn.ПланыСчетов.Хозрасчетный
    chars = conn.ПланыВидовХарактеристик.ВидыСубконтоХозрасчетные

    query = conn.NewObject("Запрос")
    query.Текст = query_text

    vidy_subkonto = to_array(conn, [chars.ЦенныеБумаги, chars.ВидыОбращаемостиЦБ])

    money = to_array(conn, [plans.РасчетныеСчета, plans.ТекущиеСчета,
                            plans.ТранзитныеСчета, plans.РасчетыБрокераПоСделкам55,
                            plans.РасчетыБрокераПоСделкам])

    query.УстановитьПараметр("РасчетыПоОблигациям", plans.РасчетыПоОблигациям)
    query.УстановитьПараметр("ДоходыПоНКД", plans.СчетаПоСтроке("91.01.02"))
    query.УстановитьПараметр("РасходыПоУплаченномуНКД", plans.СчетаПоСтроке("91.02.02"))
    query.УстановитьПараметр("УплаченныйНКД", plans.СчетаПоСтроке("76.05.1"))
    query.УстановитьПараметр("АктивыСЛьготируемымКДРоссийскихОрганизаций", to_array(conn, []))
    query.УстановитьПараметр("АктивыСЛьготируемымКДРФИСоюзныхГосударств", to_array(conn, []))
    query.УстановитьПараметр("ВидыСубконто", vidy_subkonto)
    query.УстановитьПараметр("СчетаДенежныхСредств", money)
    query.УстановитьПараметр("НачалоПериода", datetime.datetime(CALC_DATE.year, 1, 1))
    query.УстановитьПараметр("КонецПериода", CALC_DATE)
    query.УстановитьПараметр("Клиент", client_ref)
    query.УстановитьПараметр("ОбращающиесяЦБ", conn.Перечисления.ВидыОбращаемостиЦБ.ОбращающиесяВиды())
    query.УстановитьПараметр("ВидыОбращаемости", vidy)

    batch = query.ВыполнитьПакет()
    table = batch[batch.Количество() - 2].Выгрузить()

    rows = []
    for row in table:
        rows.append((row.Партия, row.Регистратор, row.Актив, row.Период, float(row.Сумма)))
    return rows


def main():
    pythoncom.CoInitialize()
    report = []
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect(CONN_STRING)

        query_text = extract_query_text(CF_MODULE, "РасходыПоНКДПоВидуОбращаемости")
        report.append("Query text length: %d" % len(query_text))

        finder = conn.NewObject("Запрос")
        finder.Текст = ("ВЫБРАТЬ ПЕРВЫЕ 5 К.Ссылка КАК Ссылка, К.Наименование КАК Наименование "
                        "ИЗ Справочник.Контрагенты КАК К "
                        "ГДЕ К.Наименование ПОДОБНО &Имя")
        finder.УстановитьПараметр("Имя", "%" + CLIENT_NAME + "%")
        found = finder.Выполнить().Выгрузить()
        if found.Количество() == 0:
            safe_print("ERROR: client not found")
            return
        client_ref = found[0].Ссылка
        report.append("Client: " + str(found[0].Наименование))
        report.append("Candidates found: %d" % found.Количество())

        obr = conn.Перечисления.ВидыОбращаемостиЦБ.ОбращающиесяВиды()
        neobr = conn.Перечисления.ВидыОбращаемостиЦБ.НеОбращающиесяВиды()

        both = conn.NewObject("Массив")
        for i in range(obr.Количество()):
            both.Добавить(obr.Получить(i))
        for i in range(neobr.Количество()):
            both.Добавить(neobr.Получить(i))

        rows_obr = run_variant(conn, query_text, client_ref, obr)
        rows_neobr = run_variant(conn, query_text, client_ref, neobr)
        rows_both = run_variant(conn, query_text, client_ref, both)

        old_abs = sum(abs(r[4]) for r in rows_obr) + sum(abs(r[4]) for r in rows_neobr)
        new_abs = sum(abs(r[4]) for r in rows_both)

        report.append("rows OBRASCH   : %d, sum=%.2f, sum|.|=%.2f"
                      % (len(rows_obr), sum(r[4] for r in rows_obr),
                         sum(abs(r[4]) for r in rows_obr)))
        report.append("rows NEOBRASCH : %d, sum=%.2f, sum|.|=%.2f"
                      % (len(rows_neobr), sum(r[4] for r in rows_neobr),
                         sum(abs(r[4]) for r in rows_neobr)))
        report.append("rows UNION     : %d, sum=%.2f, sum|.|=%.2f"
                      % (len(rows_both), sum(r[4] for r in rows_both),
                         sum(abs(r[4]) for r in rows_both)))
        report.append("")
        report.append("OLD (two calls) sum|.| = %.2f" % old_abs)
        report.append("NEW (one call)  sum|.| = %.2f" % new_abs)
        report.append("DELTA (OLD - NEW)      = %.2f" % (old_abs - new_abs))
        report.append("")

        # Ключи, склеенные объединённым вызовом: одинаковый ключ в обеих выборках.
        keys_obr = {}
        for partiya, reg, aktiv, period, summa in rows_obr:
            keys_obr.setdefault((str(partiya), str(reg), str(aktiv), str(period)), 0.0)
            keys_obr[(str(partiya), str(reg), str(aktiv), str(period))] += summa
        keys_neobr = {}
        for partiya, reg, aktiv, period, summa in rows_neobr:
            keys_neobr.setdefault((str(partiya), str(reg), str(aktiv), str(period)), 0.0)
            keys_neobr[(str(partiya), str(reg), str(aktiv), str(period))] += summa

        overlap = set(keys_obr) & set(keys_neobr)
        report.append("Overlapping keys (merged by union call): %d" % len(overlap))
        for key in sorted(overlap):
            sa = keys_obr[key]
            sb = keys_neobr[key]
            report.append("  Sa=%.2f Sb=%.2f  |Sa|+|Sb|=%.2f  |Sa+Sb|=%.2f  delta=%.2f"
                          % (sa, sb, abs(sa) + abs(sb), abs(sa + sb),
                             abs(sa) + abs(sb) - abs(sa + sb)))
            report.append("    Partiya=%s" % key[0])
            report.append("    Registrator=%s" % key[1])
            report.append("    Aktiv=%s Period=%s" % (key[2], key[3]))

    finally:
        pythoncom.CoUninitialize()

    io.open(REPORT_PATH, "w", encoding="utf-8").write("\n".join(report))
    safe_print("Report written: " + REPORT_PATH)
    for line in report:
        safe_print(line.encode("ascii", "replace").decode("ascii"))


if __name__ == "__main__":
    main()
