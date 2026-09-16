#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import pythoncom
import win32com.client

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", "protection_dump.txt")
EPF = r"C:\1c\Cursor_1c\WIM_DEV\bases\Wim_Pif\projects\nominee-owners-load\build\NomineeOwnersLoad.epf"


def dump(obj, title):
    lines = [title, "type=%s" % type(obj), "str=%s" % obj]
    for attr in (
        "Запретить",
        "Disable",
        "Warn",
        "ПредупреждатьОбОпасныхДействиях",
        "UnsafeActionProtection",
        "DangerousActions",
    ):
        try:
            val = getattr(obj, attr)
            lines.append("GET %s = %r" % (attr, val))
        except Exception as exc:
            lines.append("GET %s FAIL %s" % (attr, exc))
        try:
            setattr(obj, attr, False)
            lines.append("SET %s = False OK" % attr)
        except Exception as exc:
            lines.append("SET %s FAIL %s" % (attr, exc))
    try:
        lines.append("dir=%s" % [x for x in dir(obj) if not x.startswith("_")][:80])
    except Exception as exc:
        lines.append("dir FAIL %s" % exc)
    try:
        lines.append("prop_put=%s" % getattr(obj, "_prop_map_put_", None))
        lines.append("prop_get=%s" % getattr(obj, "_prop_map_get_", None))
    except Exception:
        pass
    return lines


def main():
    pythoncom.CoInitialize()
    com = win32com.client.Dispatch("V83.COMConnector")
    conn = com.Connect("Srvr='localhost';Ref='WIM_PIF';App='PyCOM';Locale=ru_RU;")
    lines = []
    prot = conn.NewObject("ОписаниеЗащитыОтОпасныхДействий")
    lines += dump(prot, "protection object")

    # try Create with third param after setting via COM methods
    mgr = conn.ВнешниеОбработки
    for label, args in [
        ("create_false_prot", (EPF, False, prot)),
        ("create_true_false", (EPF, True)),
    ]:
        try:
            p = mgr.Создать(*args)
            lines.append("%s OK %s" % (label, p))
        except Exception as exc:
            desc = ""
            try:
                desc = exc.args[2][2]
            except Exception:
                desc = repr(exc)
            lines.append("%s FAIL %s" % (label, desc.split("\n")[0]))

    # disable user protection if possible
    try:
        current = conn.ПользователиИнформационнойБазы.ТекущийПользователь()
        lines.append("IB user=%s" % current)
        lines.append("IB user name=%s" % current.Name if hasattr(current, "Name") else "no Name")
        try:
            zap = current.ЗащитаОтОпасныхДействий
            lines += dump(zap, "user protection")
        except Exception as exc:
            lines.append("user protection FAIL %s" % exc)
    except Exception as exc:
        lines.append("IB users FAIL %s" % exc)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(str(x) for x in lines))


if __name__ == "__main__":
    main()
