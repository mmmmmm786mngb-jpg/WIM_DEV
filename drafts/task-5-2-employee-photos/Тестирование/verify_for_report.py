#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Только чтение: проверяет снимки сотрудников и пишет JSON для HTML-отчета.
Новых элементов не создает.
"""

import json
import os

import pythoncom
import win32com.client

BASE_PATH = r"C:\Users\Acer\Documents\1C\EmployeePhotos"
PHOTO_DIR = r"C:\Users\Acer\Documents\1C\EmployeePhotosFiles"
CONNECT = "File='%s';App='PyCOM';Locale=ru_RU;" % BASE_PATH
OUT_PATH = os.path.join(os.path.dirname(__file__), "reports", "verify_data.json")

QUERY = (
    "ВЫБРАТЬ\n"
    "    Сотрудники.Наименование КАК Наименование,\n"
    "    Сотрудники.Код КАК Код,\n"
    "    ПРЕДСТАВЛЕНИЕ(Сотрудники.СпособХраненияФотографии) КАК Место,\n"
    "    Сотрудники.СпособХраненияФотографии КАК Способ,\n"
    "    Сотрудники.ИмяФайлаФотографии КАК ИмяФайла,\n"
    "    Сотрудники.Ссылка КАК Ссылка\n"
    "ИЗ\n"
    "    Справочник.Сотрудники КАК Сотрудники\n"
    "УПОРЯДОЧИТЬ ПО\n"
    "    Наименование"
)


def main():
    pythoncom.CoInitialize()
    try:
        conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONNECT)
        catalog = conn.Метаданные.Справочники.Сотрудники
        attributes = [attribute.Имя for attribute in catalog.Реквизиты]
        forms = [form.Имя for form in catalog.Формы]
        enum_item = conn.Метаданные.Перечисления.СпособыХраненияФотографий
        enum_values = [value.Имя for value in enum_item.ЗначенияПеречисления]
        constant_value = str(conn.Константы.КаталогФотографийСотрудников.Получить())

        simple = conn.NewObject("Запрос")
        simple.Текст = "ВЫБРАТЬ 1 КАК Один"
        simple_value = int(simple.Выполнить().Выгрузить()[0].Один)

        query = conn.NewObject("Запрос")
        query.Текст = QUERY
        table = query.Выполнить().Выгрузить()
        file_mode = str(conn.XMLСтрока(conn.Перечисления.СпособыХраненияФотографий.ВКаталогеНаДиске))

        rows = []
        db_count = 0
        file_count = 0
        photo_ok = 0
        for row in table:
            mode_xml = str(conn.XMLСтрока(row.Способ))
            is_file = mode_xml == file_mode
            item = row.Ссылка.ПолучитьОбъект()
            size = 0
            photo_status = "empty"
            file_exists = False
            if is_file:
                file_count += 1
                file_name = str(row.ИмяФайла)
                full_path = os.path.join(constant_value.strip(), file_name)
                file_exists = os.path.isfile(full_path)
                if file_exists:
                    size = os.path.getsize(full_path)
                    photo_status = "file"
                    photo_ok += 1
            else:
                db_count += 1
                data = item.Фотография.Получить()
                if data is not None:
                    temp_path = os.path.join(PHOTO_DIR, "_report_probe.bin")
                    data.Записать(temp_path)
                    size = os.path.getsize(temp_path)
                    os.remove(temp_path)
                    if size > 0:
                        photo_status = "database"
                        photo_ok += 1
            rows.append({
                "name": str(row.Наименование),
                "code": str(row.Код),
                "place": str(row.Место),
                "fileName": str(row.ИмяФайла),
                "bytes": size,
                "status": photo_status,
                "fileExists": file_exists,
            })

        payload = {
            "simpleQuery": simple_value,
            "attributes": attributes,
            "forms": forms,
            "enumValues": enum_values,
            "constant": constant_value,
            "employees": len(rows),
            "databaseCount": db_count,
            "fileCount": file_count,
            "photoOk": photo_ok,
            "rows": rows,
        }
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as out_file:
            json.dump(payload, out_file, ensure_ascii=False, indent=2)
        print("OK employees=%s photo_ok=%s db=%s file=%s" % (len(rows), photo_ok, db_count, file_count))
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
