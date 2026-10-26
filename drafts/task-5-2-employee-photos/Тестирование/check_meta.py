# -*- coding: utf-8 -*-
import pythoncom
import win32com.client

pythoncom.CoInitialize()
conn = win32com.client.Dispatch("V83.COMConnector").Connect(
    "File='C:\\Users\\Acer\\Documents\\1C\\EmployeePhotos';App='PyCOM';Locale=ru_RU;"
)
modules = [item.Имя for item in conn.Метаданные.ОбщиеМодули]
forms = [item.Имя for item in conn.Метаданные.ОбщиеФормы]
attrs = [item.Имя for item in conn.Метаданные.Справочники.Сотрудники.Реквизиты]
print("modules", ",".join(modules))
print("forms", ",".join(forms))
print("has attr", "ИдентификаторМестаРождения" in attrs)
pythoncom.CoUninitialize()
