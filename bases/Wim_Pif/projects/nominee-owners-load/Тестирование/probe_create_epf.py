#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import pythoncom
import win32com.client

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", "create_error.txt")
EPF = r"C:\1c\Cursor_1c\WIM_DEV\bases\Wim_Pif\projects\nominee-owners-load\build\NomineeOwnersLoad.epf"


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pythoncom.CoInitialize()
    com = win32com.client.Dispatch("V83.COMConnector")
    conn = com.Connect("Srvr='localhost';Ref='WIM_PIF';App='PyCOM';Locale=ru_RU;")
    lines = ["exists=%s size=%s" % (os.path.isfile(EPF), os.path.getsize(EPF) if os.path.isfile(EPF) else 0)]
    mgr = conn.ВнешниеОбработки
    lines.append("manager=%s" % mgr)
    try:
        proc = mgr.Создать(EPF, False)
        lines.append("Create2 OK %s" % proc)
    except Exception as exc:
        lines.append("Create2 FAIL")
        lines.append(repr(exc))
        try:
            lines.append(str(exc.args[2][2]))
        except Exception:
            pass
    try:
        name = mgr.Подключить(EPF, "NomineeOwnersLoad", False)
        lines.append("Podklyuchit OK name=%s" % name)
        proc = mgr.Создать(name)
        lines.append("Create by name OK %s" % proc)
    except Exception as exc:
        lines.append("Podklyuchit FAIL")
        lines.append(repr(exc))
        try:
            lines.append(str(exc.args[2][2]))
        except Exception:
            pass
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
