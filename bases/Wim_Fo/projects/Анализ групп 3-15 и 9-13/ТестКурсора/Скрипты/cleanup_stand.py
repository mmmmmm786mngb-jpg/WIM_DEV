#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Удаляет объекты стенда с маркером TESTKURSORA.
Запускать отдельно, после того как замер больше не нужен.
"""

import sys
import traceback

import pythoncom
import win32com.client


CONNECT = "Srvr='localhost';Ref='WIM_PIF';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
MARKER = "TESTKURSORA"


def main():
    pythoncom.CoInitialize()
    try:
        conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONNECT)
        query = conn.NewObject("Запрос")
        query.Текст = (
            "ВЫБРАТЬ РАЗЛИЧНЫЕ Движения.Регистратор КАК Регистратор\n"
            "ИЗ РегистрБухгалтерии.Управленческий КАК Движения\n"
            "ГДЕ Движения.Содержание = &Маркер"
        )
        query.УстановитьПараметр("Маркер", MARKER)
        registrars = query.Выполнить().Выгрузить()
        removed = 0
        for row in registrars:
            record_set = conn.РегистрыБухгалтерии.Управленческий.СоздатьНаборЗаписей()
            record_set.Отбор.Регистратор.Установить(row.Регистратор)
            record_set.Записать()
            document = row.Регистратор.ПолучитьОбъект()
            if document is not None:
                document.Удалить()
            removed += 1
        print("registrars %s" % removed)

        accounts = conn.NewObject("Запрос")
        accounts.Текст = (
            "ВЫБРАТЬ Ссылка ИЗ Справочник.БанковскиеСчета ГДЕ Наименование ПОДОБНО &Маска"
        )
        accounts.УстановитьПараметр("Маска", MARKER + "%")
        for row in accounts.Выполнить().Выгрузить():
            manager = conn.РегистрыСведений.АлгоритмыРасчетаПроцентов.СоздатьНаборЗаписей()
            manager.Отбор.Объект.Установить(row.Ссылка)
            manager.Записать()
            obj = row.Ссылка.ПолучитьОбъект()
            if obj is not None:
                obj.Удалить()

        for catalog_name in ("ПИФ", "Банки"):
            query = conn.NewObject("Запрос")
            query.Текст = "ВЫБРАТЬ Ссылка ИЗ Справочник.%s ГДЕ Наименование ПОДОБНО &Маска" % catalog_name
            query.УстановитьПараметр("Маска", MARKER + "%")
            for row in query.Выполнить().Выгрузить():
                obj = row.Ссылка.ПолучитьОбъект()
                if obj is not None:
                    obj.Удалить()
        print("CLEAN_OK")
        return 0
    except Exception:
        traceback.print_exc()
        print("CLEAN_ERROR")
        return 1
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    sys.exit(main())
