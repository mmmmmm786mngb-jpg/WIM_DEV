#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mark test PIF as used so the choice form filter Используется=True shows them."""

import pythoncom
import win32com.client


def main():
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("Srvr='localhost';Ref='WIM_PIF';App='PyCOM';Locale=ru_RU;")
        query = conn.NewObject("Запрос")
        query.Текст = (
            "ВЫБРАТЬ Ссылка, Наименование, Используется "
            "ИЗ Справочник.ПИФ "
            "ГДЕ Наименование ПОДОБНО &П1 ИЛИ Наименование ПОДОБНО &П2"
        )
        query.УстановитьПараметр("П1", "WEBFIX_%")
        query.УстановитьПараметр("П2", "TEST_ND_%")
        table = query.Выполнить().Выгрузить()
        n = 0
        for i in range(table.Количество()):
            row = table[i]
            obj = row.Ссылка.ПолучитьОбъект()
            obj.Используется = True
            obj.ОбменДанными.Загрузка = True
            obj.Записать()
            n += 1
            print("OK " + str(row.Наименование))
        print("PATCHED=%d" % n)
        return 0
    except Exception as exc:
        desc = str(exc)
        try:
            desc = str(exc.args[2][2])
        except Exception:
            pass
        print("FAIL " + desc.encode("ascii", "replace").decode("ascii"))
        return 1
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    raise SystemExit(main())
