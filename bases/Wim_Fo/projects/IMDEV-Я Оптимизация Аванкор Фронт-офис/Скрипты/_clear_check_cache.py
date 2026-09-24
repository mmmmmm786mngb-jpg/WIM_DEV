#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Очищает кэш результатов проверки, чтобы файловая база смогла принять новый прогон."""

import pythoncom
import win32com.client

CONN = "File='C:\\1c\\Cursor_1c\\WORK\\WIM_Fo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
NAMES = (
    "КэшВмКратко",
    "КэшВмДетально",
    "КэшВмКраткоЭмитенты",
    "КэшВмПозиция",
    "КэшВмБуфер",
    "КэшВмНакопитель",
    "КэшВмОписания",
    "КэшВмПланПроверки",
    "КэшВмКотировки",
    "КэшВмСвязи",
    "КэшВмПороги",
)

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
query = conn.NewObject("Запрос")
for name in NAMES:
    query.Текст = "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК N ИЗ РегистрСведений." + name
    try:
        selection = query.Выполнить().Выбрать()
        selection.Следующий()
        count = selection.N
    except Exception as error:
        print("count fail", name, str(error)[:120])
        continue
    print("before", name, count)
    if count == 0:
        continue
    record_set = getattr(conn.РегистрыСведений, name).СоздатьНаборЗаписей()
    record_set.Записать()
    print("cleared", name)
query.Текст = (
    "ВЫБРАТЬ ВидЛимита КАК Вид, КОЛИЧЕСТВО(*) КАК N "
    "ИЗ Справочник.Лимиты "
    "ГДЕ НЕ ЭтоГруппа И Родитель.Наименование = \"482-п ДУ\" "
    "СГРУППИРОВАТЬ ПО ВидЛимита"
)
selection = query.Выполнить().Выбрать()
while selection.Следующий():
    print("kind", conn.String(selection.Вид), selection.N)
