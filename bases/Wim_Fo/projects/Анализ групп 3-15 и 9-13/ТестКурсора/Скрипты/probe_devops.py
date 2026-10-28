#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe whether VTB DevOps code execution is available."""

import traceback

import pythoncom
import win32com.client

CONNECT = "Srvr='localhost';Ref='WIM_PIF';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
OUT = r"C:\1c\Cursor_1c\WIM_DEV\bases\Wim_Fo\projects\Анализ групп 3-15 и 9-13\ТестКурсора\devops_probe.txt"


def main():
    lines = []
    pythoncom.CoInitialize()
    try:
        conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONNECT)
        for name in ("ВТБ_DevOps", "VTB_DevOps", "ВТБ_Devops"):
            module = getattr(conn, name, None)
            lines.append("module %s -> %s" % (name, module is not None))
            if module is not None:
                try:
                    module.ВыполнитьКод("Сообщить(1);")
                    lines.append("call ok " + name)
                except Exception as exc:
                    lines.append("call fail %s: %s" % (name, exc))
        lines.append("DONE")
    except Exception:
        lines.append(traceback.format_exc())
    finally:
        pythoncom.CoUninitialize()
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print("DONE")


if __name__ == "__main__":
    main()
