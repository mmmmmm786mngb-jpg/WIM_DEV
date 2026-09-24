#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Создает вариант порога процент от РСА и проставляет его структурным лимитам FO_VOL."""

import pythoncom
import win32com.client

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(
    "File='C:\\1c\\Cursor_1c\\WORK\\WIM_Fo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
)
name = "FO_VOL процент от РСА"
ref = getattr(conn.Справочники, "ВариантыПроверкиПороговЛимитов").НайтиПоНаименованию(name, True)
if ref.Пустая():
    item = getattr(conn.Справочники, "ВариантыПроверкиПороговЛимитов").СоздатьЭлемент()
    item.Наименование = name
else:
    item = ref.ПолучитьОбъект()
item.Вариант = conn.Перечисления.ВариантыПроверкиПороговЛимитов.ПроцентОтРСА
item.ФункцияПроверкиПорога = conn.Перечисления.ВидыФункцийПроверкиПороговЛимитов.ПоОбщемуИтогу
item.Записать()
variant = item.Ссылка
print("variant ok")

query = conn.NewObject("Запрос")
query.Текст = "ВЫБРАТЬ Ссылка ИЗ Справочник.Лимиты ГДЕ Наименование ПОДОБНО \"FO_VOL S%\" ИЛИ Наименование ПОДОБНО \"FO_VOL X%\""
selection = query.Выполнить().Выбрать()
count = 0
while selection.Следующий():
    obj = selection.Ссылка.ПолучитьОбъект()
    obj.ВариантПроверкиПорога = variant
    obj.Записать()
    count += 1
print("limits updated", count)
