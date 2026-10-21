#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Разведочный тест COM-подключения к файловой базе Аванкор Фронт-офис.

Задачи скрипта:
1. Установить COM-соединение с файловой базой.
2. Прочитать состав справочника ЗапросыКДанным (реквизиты + табличная часть Параметры).
3. Выгрузить фактическое содержимое единственной записи в JSON для анализа структуры данных.

Результат пишется в reports/com_probe_result.json (UTF-8).
Консольный вывод - только ASCII.
"""

import json
import os
import sys
import traceback

import pythoncom
import win32com.client

BASE_PATH = r"C:\1c\Cursor_1c\WORK\WIM_Fo"
USER = "admin"
PASSWORD = "1"

REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
REPORT_FILE = os.path.join(REPORT_DIR, "com_probe_result.json")


def safe_print(text):
    """Безопасный вывод в консоль - только ASCII."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(str(text).encode("ascii", "replace").decode("ascii"))


def connect():
    """Устанавливает COM-соединение с файловой базой."""
    connector = win32com.client.Dispatch("V83.COMConnector")
    conn_string = "File='{0}';Usr='{1}';Pwd='{2}';App='PyCOM';Locale=ru_RU;".format(
        BASE_PATH, USER, PASSWORD
    )
    return connector.Connect(conn_string)


def probe_catalog(conn):
    """Читает все элементы справочника ЗапросыКДанным вместе с табличной частью."""
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ\n"
        "    Т.Ссылка КАК Ссылка,\n"
        "    Т.Код КАК Код,\n"
        "    Т.Наименование КАК Наименование,\n"
        "    Т.КодЗапроса КАК КодЗапроса,\n"
        "    Т.ТекстЗапроса КАК ТекстЗапроса,\n"
        "    Т.ДоступныеТипыДанных КАК ДоступныеТипыДанных,\n"
        "    Т.ПометкаУдаления КАК ПометкаУдаления\n"
        "ИЗ\n"
        "    Справочник.ЗапросыКДанным КАК Т"
    )
    table = query.Выполнить().Выгрузить()

    items = []
    for row in table:
        ref = row.Ссылка
        item = {
            "УникальныйИдентификатор": str(ref.УникальныйИдентификатор()),
            "Код": row.Код,
            "Наименование": row.Наименование,
            "КодЗапроса": row.КодЗапроса,
            "ТекстЗапроса": row.ТекстЗапроса,
            "ДоступныеТипыДанных": str(row.ДоступныеТипыДанных),
            "ПометкаУдаления": bool(row.ПометкаУдаления),
            "Параметры": [],
        }

        params_query = conn.NewObject("Запрос")
        params_query.Текст = (
            "ВЫБРАТЬ\n"
            "    П.НомерСтроки КАК НомерСтроки,\n"
            "    П.Тип КАК Тип,\n"
            "    П.Имя КАК Имя,\n"
            "    П.Значение КАК Значение,\n"
            "    П.Внешний КАК Внешний,\n"
            "    П.Идентификатор КАК Идентификатор\n"
            "ИЗ\n"
            "    Справочник.ЗапросыКДанным.Параметры КАК П\n"
            "ГДЕ\n"
            "    П.Ссылка = &Ссылка\n"
            "УПОРЯДОЧИТЬ ПО\n"
            "    П.НомерСтроки"
        )
        params_query.УстановитьПараметр("Ссылка", ref)
        params_table = params_query.Выполнить().Выгрузить()

        for prow in params_table:
            item["Параметры"].append(
                {
                    "НомерСтроки": int(prow.НомерСтроки),
                    "Тип": prow.Тип,
                    "Имя": prow.Имя,
                    "Значение": prow.Значение,
                    "Внешний": bool(prow.Внешний),
                    "Идентификатор": str(prow.Идентификатор),
                }
            )

        items.append(item)

    return items


def probe_additional_processors(conn):
    """Проверяет доступность подсистемы БСП Дополнительные отчеты и обработки."""
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ\n"
        "    Т.Наименование КАК Наименование,\n"
        "    Т.Вид КАК Вид,\n"
        "    Т.Публикация КАК Публикация\n"
        "ИЗ\n"
        "    Справочник.ДополнительныеОтчетыИОбработки КАК Т"
    )
    table = query.Выполнить().Выгрузить()
    return [
        {
            "Наименование": row.Наименование,
            "Вид": str(row.Вид),
            "Публикация": str(row.Публикация),
        }
        for row in table
    ]


def main():
    pythoncom.CoInitialize()
    result = {"connected": False}
    try:
        conn = connect()
        result["connected"] = True
        safe_print("OK - COM connection established")

        result["ЗапросыКДанным"] = probe_catalog(conn)
        safe_print("OK - catalog read, items: %d" % len(result["ЗапросыКДанным"]))

        result["ДополнительныеОтчетыИОбработки"] = probe_additional_processors(conn)
        safe_print(
            "OK - additional processors read, items: %d"
            % len(result["ДополнительныеОтчетыИОбработки"])
        )

        version = conn.NewObject("СистемнаяИнформация")
        result["ВерсияПлатформы"] = version.ВерсияПриложения
        safe_print("Platform version: %s" % result["ВерсияПлатформы"])

    except Exception:
        result["error"] = traceback.format_exc()
        safe_print("ERROR - see report file")
        safe_print(result["error"].encode("ascii", "replace").decode("ascii"))
    finally:
        pythoncom.CoUninitialize()

    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    safe_print("Report saved: %s" % REPORT_FILE)
    return 0 if result.get("connected") and "error" not in result else 1


if __name__ == "__main__":
    sys.exit(main())
