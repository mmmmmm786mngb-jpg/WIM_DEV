#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Proverka konstanty PulRoznicaDU v IB WIM_FIN."""

import pythoncom
import win32com.client


def main():
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("Srvr='localhost';Ref='WIM_FIN';")
        md = conn.Метаданные
        found = False
        for i in range(md.Константы.Count()):
            if md.Константы.Get(i).Name == "ПулРозницаДУ":
                found = True
                break
        print("metadata_PulRoznicaDU:", "OK" if found else "MISSING")
        om = getattr(conn, "ОбщегоНазначенияДУПовтИсп", None)
        if om and found:
            val = om.ПолучитьЗначениеКонстанты("ПулРозницаДУ")
            empty = not val or (hasattr(val, "Пустая") and val.Пустая())
            print("value_filled:", "NO" if empty else "YES")
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
