#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Снимает безопасный режим расширения IM9434 через COM."""

import sys
import traceback


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def main():
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    conn = None
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("Srvr='localhost';Ref='WIM_DU';App='PyCOM';Locale=ru_RU;")
        safe_print("connected")

        ext_mgr = getattr(conn, "РасширенияКонфигурации", None)
        if ext_mgr is None:
            safe_print("ERROR: ConfigurationExtensions manager missing")
            return 1

        extensions = ext_mgr.Получить()
        safe_print("extensions count=" + str(extensions.Количество()))
        found = False
        for i in range(extensions.Количество()):
            ext = extensions.Получить(i)
            name = str(ext.Имя)
            safe_print("ext=" + name)
            if name != "IM9434":
                continue
            found = True
            safe_print("before SafeMode=" + str(ext.БезопасныйРежим))
            safe_print("before Active=" + str(ext.Активно))
            ext.БезопасныйРежим = False
            try:
                desc = conn.NewObject("ОписаниеЗащитыОтОпасныхДействий")
                desc.ПредупреждатьОбОпасныхДействиях = False
                ext.ЗащитаОтОпасныхДействий = desc
                safe_print("protection object set")
            except Exception as prot_exc:
                safe_print("protection skip: " + str(prot_exc))
                try:
                    ext.ЗащитаОтОпасныхДействий = False
                    safe_print("protection bool set")
                except Exception as prot_exc2:
                    safe_print("protection bool skip: " + str(prot_exc2))
            ext.Записать()
            safe_print("after SafeMode=" + str(ext.БезопасныйРежим))
            safe_print("OK written")
        if not found:
            safe_print("ERROR: IM9434 not found")
            return 1
        return 0
    except Exception as exc:
        safe_print("ERROR: " + str(exc))
        safe_print(traceback.format_exc())
        return 1
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    sys.exit(main())
