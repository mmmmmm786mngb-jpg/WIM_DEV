#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""List WIM_DU configuration extensions and look for the deal-loader module."""
import pythoncom
import win32com.client

OUT = r"C:\1c\Cursor_1c\WIM_DEV\drafts\list_du_extensions.txt"
lines = []

pythoncom.CoInitialize()
try:
    com = win32com.client.Dispatch("V83.COMConnector")
    conn = com.Connect("Srvr='localhost';Ref='WIM_DU';")
    extensions = conn.РасширенияКонфигурации.Получить()
    lines.append("extensions:")
    for ext in extensions:
        name = str(ext.Имя)
        syn = ""
        ver = ""
        try:
            syn = str(ext.Синоним)
        except Exception:
            pass
        try:
            ver = str(ext.Версия)
        except Exception:
            pass
        active = ""
        try:
            active = str(ext.Активно)
        except Exception:
            pass
        lines.append(f"{name} | {syn} | {ver} | active={active}")
    # metadata common modules containing the name
    lines.append("--- modules ---")
    modules = conn.Метаданные.ОбщиеМодули
    count = modules.Количество()
    lines.append("module_count=" + str(count))
    for i in range(count):
        mod = modules.Получить(i)
        name = str(mod.Имя)
        if "Загруз" in name or "Сдел" in name or "Генер" in name or "Паралл" in name:
            lines.append("MOD " + name)
except Exception as exc:
    lines.append("ERROR " + str(exc))
finally:
    pythoncom.CoUninitialize()

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("done", len(lines))
