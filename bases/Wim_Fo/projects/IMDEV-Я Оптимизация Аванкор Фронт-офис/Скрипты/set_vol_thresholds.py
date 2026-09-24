#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Один порог 50 процентов от РСА на все портфели для структурных лимитов FO_VOL."""

from datetime import datetime
import pythoncom
import win32com.client

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(
    "File='C:\\1c\\Cursor_1c\\WORK\\WIM_Fo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
)

name = "FO_VOL порог 50"
manager = getattr(conn.Справочники, "НастройкиПороговДляПроверкиЛимитов")
ref = manager.НайтиПоНаименованию(name, True)
item = manager.СоздатьЭлемент() if ref.Пустая() else ref.ПолучитьОбъект()
item.Наименование = name
item.ИспользоватьРасширеннуюУстановкуПорогов = False
item.СложныеПороги.Очистить()
row = item.СложныеПороги.Добавить()
row.ПоУмолчанию = True
row.МаксДоляЖелтаяЗона = 40
row.МаксДоляКраснаяЗона = 50
item.Записать()
setting = item.Ссылка
print("setting ok")

limits = conn.NewObject("Запрос")
limits.Текст = (
    "ВЫБРАТЬ Ссылка ИЗ Справочник.Лимиты "
    "ГДЕ Наименование ПОДОБНО \"FO_VOL S%\" ИЛИ Наименование ПОДОБНО \"FO_VOL X%\""
)
selection = limits.Выполнить().Выбрать()
register = getattr(conn.РегистрыСведений, "ПорогиЛимитов")
empty_portfolio = getattr(conn.Справочники, "Портфели").ПустаяСсылка()
count = 0
while selection.Следующий():
    record = register.СоздатьМенеджерЗаписи()
    record.Период = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    record.Лимит = selection.Ссылка
    record.Портфель = empty_portfolio
    record.НастройкаПороговДляПроверкиЛимитов = setting
    record.Записать()
    count += 1
print("threshold rows", count)
