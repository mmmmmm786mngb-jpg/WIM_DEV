#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick COM smoke after reboot: connect and open EPF."""
import os
import pythoncom
import win32com.client

EPF = r"C:\1c\Cursor_1c\WIM_DEV\bases\Wim_Pif\projects\nominee-owners-load\build\NomineeOwnersLoad.epf"
OUT = r"C:\1c\Cursor_1c\WIM_DEV\bases\Wim_Pif\projects\nominee-owners-load\Тестирование\reports\smoke_after_reboot.txt"


def main():
    pythoncom.CoInitialize()
    lines = []
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("Srvr='localhost';Ref='WIM_PIF';App='PyCOM';Locale=ru_RU;")
        lines.append("COM connect OK")
        prot = conn.NewObject("ОписаниеЗащитыОтОпасныхДействий")
        prot.ПредупреждатьОбОпасныхДействиях = False
        proc = conn.ВнешниеОбработки.Создать(EPF, False, prot)
        sved = proc.СведенияОВнешнейОбработке()
        lines.append("EPF create OK version=%s" % sved.Версия)
        q = conn.NewObject("Запрос")
        q.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Наименование, Публикация "
            "ИЗ Справочник.ДополнительныеОтчетыИОбработки "
            "ГДЕ ИмяОбъекта = &Имя"
        )
        q.УстановитьПараметр("Имя", "ЗаполнениеСпискаВладельцевНД")
        res = q.Выполнить()
        if res.Пустой():
            lines.append("CATALOG MISSING")
        else:
            row = res.Выгрузить()[0]
            lines.append("CATALOG OK %s" % row.Наименование)
    except Exception as exc:
        desc = repr(exc)
        try:
            desc = str(exc.args[2][2])
        except Exception:
            pass
        lines.append("FAIL %s" % desc)
    pythoncom.CoUninitialize()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
