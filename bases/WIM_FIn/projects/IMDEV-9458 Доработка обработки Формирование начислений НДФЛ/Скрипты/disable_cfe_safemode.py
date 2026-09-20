#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Otkljuchit SafeMode dlya IMDEV9458_EmptyTurnover v WIM_FIN (bez avtorizacii)."""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pythoncom
import win32com.client

NAME = "IMDEV9458_EmptyTurnover"
CONN = "Srvr='localhost';Ref='WIM_FIN';App='PyCOM';Locale=ru_RU;"


def main():
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect(CONN)
        print("CONNECTED")
        exts = conn.РасширенияКонфигурации.Получить()
        found = False
        for i in range(exts.Количество()):
            e = exts.Получить(i)
            print(
                "EXT",
                e.Имя,
                "Ver",
                getattr(e, "Версия", None),
                "Safe",
                e.БезопасныйРежим,
                "Active",
                e.Активно,
            )
            if e.Имя == NAME:
                found = True
                if e.БезопасныйРежим:
                    e.БезопасныйРежим = False
                    e.Записать()
                    print("SafeMode OFF written")
                else:
                    print("SafeMode already OFF")
        if not found:
            print("NOT FOUND")
            return 1
        return 0
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    raise SystemExit(main())
