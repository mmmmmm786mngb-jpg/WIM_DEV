#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Второй разведочный тест: детали, важные для проектирования обработки выгрузки/загрузки.

Проверяет:
1. Значение константы ИспользоватьДополнительныеОтчетыИОбработки (нужна для регистрации обработки).
2. Формат внутренней сериализации ЗначениеВСтрокуВнутр для ссылочного значения
   (ключевой вопрос переносимости JSON между базами).
3. Корректное чтение UUID (реквизит Идентификатор табличной части и идентификатор ссылки).

Результат: reports/com_probe2_result.json (UTF-8). Консоль - только ASCII.
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
REPORT_FILE = os.path.join(REPORT_DIR, "com_probe2_result.json")


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


def main():
    pythoncom.CoInitialize()
    result = {}
    try:
        conn = connect()
        safe_print("OK - connected")

        # 1. Константа подсистемы БСП.
        result["ИспользоватьДополнительныеОтчетыИОбработки"] = bool(
            conn.Константы.ИспользоватьДополнительныеОтчетыИОбработки.Получить()
        )

        # 2. Формат внутренней сериализации ссылки и примитивов.
        samples = {}
        samples["Строка"] = conn.ЗначениеВСтрокуВнутр("Тест")
        samples["Число"] = conn.ЗначениеВСтрокуВнутр(123.45)
        samples["Булево"] = conn.ЗначениеВСтрокуВнутр(True)
        samples["ПустаяСсылкаАктивы"] = conn.ЗначениеВСтрокуВнутр(
            conn.Справочники.Активы.ПустаяСсылка()
        )

        # Берём реальную (непустую) ссылку справочника Активы, если она есть.
        query = conn.NewObject("Запрос")
        query.Текст = "ВЫБРАТЬ ПЕРВЫЕ 1 А.Ссылка КАК Ссылка ИЗ Справочник.Активы КАК А"
        table = query.Выполнить().Выгрузить()
        if table.Количество() > 0:
            ref = table[0].Ссылка
            samples["ЗаполненнаяСсылкаАктивы"] = conn.ЗначениеВСтрокуВнутр(ref)
            samples["ПредставлениеСсылкиАктивы"] = conn.String(ref)
            samples["УИДСсылкиАктивы"] = conn.String(ref.УникальныйИдентификатор())

        result["ПримерыСериализации"] = samples

        # 3. Чтение UUID табличной части.
        query = conn.NewObject("Запрос")
        query.Текст = (
            "ВЫБРАТЬ\n"
            "    П.Ссылка КАК Ссылка,\n"
            "    П.Имя КАК Имя,\n"
            "    П.Идентификатор КАК Идентификатор\n"
            "ИЗ\n"
            "    Справочник.ЗапросыКДанным.Параметры КАК П"
        )
        table = query.Выполнить().Выгрузить()
        rows = []
        for row in table:
            rows.append(
                {
                    "УИДСсылки": conn.String(row.Ссылка.УникальныйИдентификатор()),
                    "Имя": row.Имя,
                    "Идентификатор": conn.String(row.Идентификатор),
                }
            )
        result["ПараметрыUUID"] = rows

        safe_print("OK - probe finished")

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
    return 1 if "error" in result else 0


if __name__ == "__main__":
    sys.exit(main())
