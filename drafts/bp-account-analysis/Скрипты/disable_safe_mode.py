#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turn off safe mode for the price extension after reload."""

import pythoncom
import win32com.client

OUT = r"c:\1c\Cursor_1c\WIM_DEV\drafts\bp-account-analysis\Скрипты\safe_mode.txt"


def main():
    lines = []
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("File='C:\\1c\\БП_ДЕМО';Usr='Admin';App='PyCOM';Locale=ru_RU;")
        extensions = conn.ConfigurationExtensions.Get()
        for ext in extensions:
            name = str(ext.Name)
            lines.append("before " + name + " active=" + str(ext.Active) + " safe=" + str(ext.SafeMode))
            if name == "ЦенаВАнализеСчета":
                ext.SafeMode = False
                ext.Write()
                lines.append("written safe=" + str(ext.SafeMode))
    except Exception as error:
        lines.append(str(error))
    finally:
        pythoncom.CoUninitialize()
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


if __name__ == "__main__":
    main()
