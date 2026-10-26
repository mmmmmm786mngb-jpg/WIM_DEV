#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Раскладывает портреты по сотрудникам.
Часть снимков пишет в хранилище значения, часть - файлом в каталог константы.
Имена вымышленные: фото взяты как примеры, это не паспорта этих людей.
"""

import os
import shutil
import uuid

import pythoncom
import win32com.client

PHOTO_DIR = r"C:\Users\Acer\Documents\1C\EmployeePhotosFiles"
PORTRAITS = os.path.join(PHOTO_DIR, "portraits")
CONNECT = "File='C:\\Users\\Acer\\Documents\\1C\\EmployeePhotos';App='PyCOM';Locale=ru_RU;"

# mode: db | file
PEOPLE = [
    ("Соколова Мария", "p32.jpg", "db"),
    ("Орлов Дмитрий", "p11.jpg", "file"),
    ("Кузнецова Елена", "p25.jpg", "db"),
    ("Волков Игорь", "p60.jpg", "file"),
    ("Морозова Ольга", "p44.jpg", "db"),
    ("Новиков Павел", "p68.jpg", "file"),
    ("Лебедева Анна", "p16.jpg", "db"),
    ("Громов Алексей", "p33.jpg", "file"),
    ("Тест фото в базе", "p49.jpg", "db"),
    ("Тест фото в файле", "p52.jpg", "file"),
    ("Тест PNG из базы", "p5.jpg", "file"),
]


def save_as_file(conn, item, source_path):
    file_name = str(uuid.uuid4()) + ".jpg"
    target = os.path.join(PHOTO_DIR, file_name)
    shutil.copyfile(source_path, target)
    item.СпособХраненияФотографии = conn.Перечисления.СпособыХраненияФотографий.ВКаталогеНаДиске
    item.ИмяФайлаФотографии = file_name
    item.Фотография = conn.NewObject("ХранилищеЗначения", None)
    return file_name, os.path.getsize(target)


def save_in_database(conn, item, source_path):
    binary = conn.NewObject("ДвоичныеДанные", source_path)
    storage = conn.NewObject("ХранилищеЗначения", binary, conn.NewObject("СжатиеДанных", 9))
    item.СпособХраненияФотографии = conn.Перечисления.СпособыХраненияФотографий.ВИнформационнойБазе
    item.Фотография = storage
    item.ИмяФайлаФотографии = ""
    return os.path.getsize(source_path)


def upsert(conn, name):
    manager = conn.NewObject("СправочникМенеджер.Сотрудники")
    ref = manager.НайтиПоНаименованию(name, True)
    if ref.Пустая():
        return manager.СоздатьЭлемент(), "created"
    return ref.ПолучитьОбъект(), "updated"


def main():
    pythoncom.CoInitialize()
    lines = []
    try:
        conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONNECT)
        catalog = str(conn.Константы.КаталогФотографийСотрудников.Получить()).strip()
        if catalog != PHOTO_DIR:
            conn.Константы.КаталогФотографийСотрудников.Установить(PHOTO_DIR)
        for name, portrait, mode in PEOPLE:
            source = os.path.join(PORTRAITS, portrait)
            if not os.path.isfile(source):
                raise RuntimeError("missing portrait " + portrait)
            item, action = upsert(conn, name)
            item.Наименование = name
            if mode == "file":
                file_name, size = save_as_file(conn, item, source)
                detail = "file " + file_name + " bytes=" + str(size)
            else:
                size = save_in_database(conn, item, source)
                detail = "db bytes=" + str(size)
            item.Записать()
            lines.append(action + " | " + mode + " | " + detail)
        report = os.path.join(os.path.dirname(__file__), "portraits_assigned.txt")
        with open(report, "w", encoding="utf-8") as report_file:
            report_file.write("\n".join(lines) + "\n")
        print("OK assigned " + str(len(lines)))
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
