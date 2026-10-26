#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка файловой базы "Задача 5.2. Фотографии сотрудников".
Хранение снимка в ХранилищеЗначения и в файле каталога константы.
"""

import base64
import os
import sys

import pythoncom
import win32com.client


BASE_PATH = r"C:\Users\Acer\Documents\1C\EmployeePhotos"
PHOTO_DIR = r"C:\Users\Acer\Documents\1C\EmployeePhotosFiles"
CONNECT = "File='%s';App='PyCOM';Locale=ru_RU;" % BASE_PATH

# PNG 1x1, красный пиксель.
PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def safe_print(text):
    """Вывод в консоль только в кодировке, которую переваривает Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def fail(message):
    safe_print("ERROR " + message)
    raise SystemExit(1)


def main():
    os.makedirs(PHOTO_DIR, exist_ok=True)
    png_path = os.path.join(PHOTO_DIR, "sample.png")
    png_bytes = base64.b64decode(PNG_BASE64)
    with open(png_path, "wb") as png_file:
        png_file.write(png_bytes)

    pythoncom.CoInitialize()
    try:
        connector = win32com.client.Dispatch("V83.COMConnector")
        conn = connector.Connect(CONNECT)
        safe_print("OK connect")
        check_metadata(conn)
        check_query(conn)
        set_constant(conn)
        check_database_photo(conn, png_path, png_bytes)
        check_file_photo(conn, png_path, png_bytes)
        check_list_query(conn)
        safe_print("OK all checks passed")
    finally:
        pythoncom.CoUninitialize()


def check_metadata(conn):
    catalogs = conn.Метаданные.Справочники
    catalog = catalogs.Сотрудники
    names = []
    for attribute in catalog.Реквизиты:
        names.append(attribute.Имя)
    expected = ["СпособХраненияФотографии", "Фотография", "ИмяФайлаФотографии"]
    for name in expected:
        if name not in names:
            fail("missing attribute " + name)

    form_names = []
    for form in catalog.Формы:
        form_names.append(form.Имя)
    if "ФормаЭлемента" not in form_names:
        fail("missing form FormaElementa")

    constant = conn.Метаданные.Константы.КаталогФотографийСотрудников
    if constant.Имя != "КаталогФотографийСотрудников":
        fail("constant name mismatch")

    enum_item = conn.Метаданные.Перечисления.СпособыХраненияФотографий
    enum_names = []
    for value in enum_item.ЗначенияПеречисления:
        enum_names.append(value.Имя)
    if "ВИнформационнойБазе" not in enum_names or "ВКаталогеНаДиске" not in enum_names:
        fail("enum values missing")

    safe_print("OK metadata attributes=%s forms=%s" % (len(names), len(form_names)))


def check_query(conn):
    query = conn.NewObject("Запрос")
    query.Текст = "ВЫБРАТЬ 1 КАК Один"
    result = query.Выполнить().Выгрузить()
    value = result[0].Один
    if int(value) != 1:
        fail("simple query returned %s" % value)
    safe_print("OK query select 1")


def set_constant(conn):
    constants = conn.Константы.КаталогФотографийСотрудников
    constants.Установить(PHOTO_DIR)
    stored = constants.Получить()
    if str(stored) != PHOTO_DIR:
        fail("constant roundtrip failed: " + str(stored))
    safe_print("OK constant")


def enum_xml(conn, value):
    return str(conn.XMLСтрока(value))


def check_database_photo(conn, png_path, png_bytes):
    binary = conn.NewObject("ДвоичныеДанные", png_path)
    compression = conn.NewObject("СжатиеДанных", 9)
    storage = conn.NewObject("ХранилищеЗначения", binary, compression)

    manager = conn.NewObject("СправочникМенеджер.Сотрудники")
    item = manager.СоздатьЭлемент()
    item.Наименование = "Тест фото в базе"
    item.СпособХраненияФотографии = conn.Перечисления.СпособыХраненияФотографий.ВИнформационнойБазе
    item.Фотография = storage
    item.ИмяФайлаФотографии = ""
    item.Записать()

    reread = item.Ссылка.ПолучитьОбъект()
    mode = enum_xml(conn, reread.СпособХраненияФотографии)
    if mode != "ВИнформационнойБазе":
        fail("db mode xml is " + mode)
    if str(reread.ИмяФайлаФотографии) != "":
        fail("db item has file name")

    restored = reread.Фотография.Получить()
    out_path = os.path.join(PHOTO_DIR, "restored_from_db.png")
    restored.Записать(out_path)
    with open(out_path, "rb") as restored_file:
        restored_bytes = restored_file.read()
    if restored_bytes != png_bytes:
        fail("db photo bytes differ: %s vs %s" % (len(restored_bytes), len(png_bytes)))
    safe_print("OK database photo bytes=%s" % len(restored_bytes))


def check_file_photo(conn, png_path, png_bytes):
    file_name = "employee-file-photo.png"
    target = os.path.join(PHOTO_DIR, file_name)
    with open(target, "wb") as target_file:
        target_file.write(png_bytes)

    manager = conn.NewObject("СправочникМенеджер.Сотрудники")
    item = manager.СоздатьЭлемент()
    item.Наименование = "Тест фото в файле"
    item.СпособХраненияФотографии = conn.Перечисления.СпособыХраненияФотографий.ВКаталогеНаДиске
    item.ИмяФайлаФотографии = file_name
    item.Записать()

    reread = item.Ссылка.ПолучитьОбъект()
    mode = enum_xml(conn, reread.СпособХраненияФотографии)
    if mode != "ВКаталогеНаДиске":
        fail("file mode xml is " + mode)
    if str(reread.ИмяФайлаФотографии) != file_name:
        fail("file name mismatch: " + str(reread.ИмяФайлаФотографии))

    full_path = os.path.join(str(conn.Константы.КаталогФотографийСотрудников.Получить()), file_name)
    if not os.path.isfile(full_path):
        fail("photo file missing")
    with open(full_path, "rb") as photo_file:
        stored_bytes = photo_file.read()
    if stored_bytes != png_bytes:
        fail("file photo bytes differ")
    safe_print("OK file photo bytes=%s" % len(stored_bytes))


def check_list_query(conn):
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ\n"
        "    Сотрудники.Наименование КАК Наименование,\n"
        "    ПРЕДСТАВЛЕНИЕ(Сотрудники.СпособХраненияФотографии) КАК Место,\n"
        "    Сотрудники.ИмяФайлаФотографии КАК ИмяФайла\n"
        "ИЗ\n"
        "    Справочник.Сотрудники КАК Сотрудники\n"
        "УПОРЯДОЧИТЬ ПО\n"
        "    Наименование"
    )
    selection = query.Выполнить().Выбрать()
    count = 0
    while selection.Следующий():
        count += 1
        safe_print(
            "ROW %s | %s | %s"
            % (selection.Наименование, selection.Место, selection.ИмяФайла)
        )
    if count < 2:
        fail("expected 2 employees, got %s" % count)
    safe_print("OK list query rows=%s" % count)


if __name__ == "__main__":
    main()
