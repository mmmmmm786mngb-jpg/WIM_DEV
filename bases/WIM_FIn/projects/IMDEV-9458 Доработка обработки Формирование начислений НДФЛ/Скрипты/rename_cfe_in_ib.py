#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Delete old IMAPPS39438 CFE and disable SafeMode on IMDEV9458."""

import sys
import traceback

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pythoncom
import win32com.client


OLD_NAME = "IMAPPS39438_EmptyTurnover"
NEW_NAME = "IMDEV9458_EmptyTurnover"


def main():
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect(
            "Srvr='localhost';Ref='WIM_FIN';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
        )
        print("CONNECTED")
        exts = conn.РасширенияКонфигурации.Получить()
        print("COUNT", exts.Количество())
        for ext in list(exts):
            name = str(ext.Имя)
            active = getattr(ext, "Активно", "?")
            safe = getattr(ext, "БезопасныйРежим", "?")
            print("EXT", name, "active", active, "safemode", safe)
            if name == OLD_NAME:
                try:
                    ext.Удалить()
                    print("DELETED", OLD_NAME)
                except Exception as e:
                    print("DELETE_FAIL", name, e)
                    traceback.print_exc()
            elif name == NEW_NAME:
                try:
                    ext.БезопасныйРежим = False
                    if hasattr(ext, "ЗащитаОтОпасныхДействий"):
                        try:
                            ext.ЗащитаОтОпасныхДействий.ПредупреждатьОбОпасныхДействиях = False
                        except Exception:
                            pass
                    ext.Записать()
                    print("SAFEMODE_OFF", NEW_NAME)
                except Exception as e:
                    print("SAFEMODE_FAIL", e)
                    traceback.print_exc()
        print("--- AFTER ---")
        exts2 = conn.РасширенияКонфигурации.Получить()
        print("COUNT", exts2.Количество())
        for ext in list(exts2):
            print("EXT", ext.Имя, "active", getattr(ext, "Активно", "?"))
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
