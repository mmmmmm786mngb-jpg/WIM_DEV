#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""COM: check DefaultForm of built EPF."""

import pythoncom
import win32com.client

EPF = r"C:\1c\Cursor_1c\WIM_DEV\bases\Wim_Pif\projects\nominee-owners-load\build\NomineeOwnersLoad.epf"


def main():
    pythoncom.CoInitialize()
    com = win32com.client.Dispatch("V83.COMConnector")
    conn = com.Connect("Srvr='localhost';Ref='WIM_PIF';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;")
    prot = conn.NewObject("ОписаниеЗащитыОтОпасныхДействий")
    prot.ПредупреждатьОбОпасныхДействиях = False
    proc = conn.ВнешниеОбработки.Создать(EPF, False, prot)
    md = proc.Метаданные()
    print("name", md.Имя)
    print("syn", md.Синоним)
    df = md.ОсновнаяФорма
    print("default", None if df is None else df.Имя)
    sved = proc.СведенияОВнешнейОбработке()
    print("version", sved.Версия)
    print("safe", sved.БезопасныйРежим)
    print("forms")
    for form in md.Формы:
        form_type = ""
        try:
            form_type = str(form.ТипФормы)
        except Exception as exc:
            form_type = repr(exc)
        print(" -", form.Имя, form_type)
    print("attrs")
    for attr in md.Реквизиты:
        print(" -", attr.Имя)
    print("tables")
    for tab in md.ТабличныеЧасти:
        print(" -", tab.Имя)
    pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
