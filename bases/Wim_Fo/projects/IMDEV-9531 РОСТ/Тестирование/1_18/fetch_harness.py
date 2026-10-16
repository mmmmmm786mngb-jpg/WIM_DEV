# -*- coding: utf-8 -*-
"""Выгружает из dev ФО тестовую обработку T9530_ТестРОСТ, зарегистрированную сейчас, и ищет в ней сценарии IMDEV-9531."""
import os, zlib, pythoncom, win32com.client
CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
pythoncom.CoInitialize()
c = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
q = c.NewObject("Запрос")
q.Текст = ("ВЫБРАТЬ Д.Ссылка КАК Ссылка, Д.Версия КАК Версия, Д.ИмяОбъекта КАК Имя ИЗ Справочник.ДополнительныеОтчетыИОбработки КАК Д "
           "ГДЕ Д.ИмяОбъекта В (&Имена) И НЕ Д.ПометкаУдаления")
names = c.NewObject("Массив"); names.Добавить("T9530_ТестРОСТ"); names.Добавить("СозданиеТорговыхПорученийРОСТ")
q.УстановитьПараметр("Имена", names)
s = q.Выполнить().Выбрать()
here = os.path.dirname(os.path.abspath(__file__))
while s.Следующий():
    name = c.String(s.Имя)
    path = os.path.join(here, "в_базе_" + name + ".epf")
    s.Ссылка.ПолучитьОбъект().ХранилищеОбработки.Получить().Записать(path)
    b = open(path, 'rb').read()
    found = set()
    for i in range(len(b) - 2):
        try:
            d = zlib.decompressobj(-15).decompress(b[i:i + 300000])
        except Exception:
            continue
        if len(d) > 2000:
            t = d.decode('utf-8', 'ignore')
            for k in ['ОчиститьСделки', 'ПропорцииПрод', 'ПозицияНаВчера', 'ЗадержкаСтакана', 'КешЦенСтакана', 'КешСтакана']:
                if k in t:
                    found.add(k)
    print(name, c.String(s.Версия), os.path.getsize(path), sorted(found))
