#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seeding WIM_PIF for WEB test of nominee owners processing.
Creates fund, nominee, one shareholder with NRD id and Garant xlsx.
"""

import datetime
import json
import os
import sys

import pythoncom
import win32com.client

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPF = os.path.join(PROJECT_DIR, "build", "NomineeOwnersLoad.epf")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
SEED_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", "web_seed.json")
RUN_ID = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
PREFIX = "WEBFIX_%s_" % RUN_ID
ADDRESS = "- 614007,Permskiy kray,g Perm,ul Testovaya,d 1,kv 9"


def find_by_name(conn, catalog, name, is_folder=None):
    query = conn.NewObject("Запрос")
    if is_folder is True:
        query.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.%s "
            "ГДЕ Наименование = &Наименование И ЭтоГруппа"
        ) % catalog
    elif is_folder is False:
        query.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.%s "
            "ГДЕ Наименование = &Наименование И НЕ ЭтоГруппа"
        ) % catalog
    else:
        query.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.%s ГДЕ Наименование = &Наименование"
        ) % catalog
    query.УстановитьПараметр("Наименование", name)
    result = query.Выполнить()
    if result.Пустой():
        return None
    return result.Выгрузить()[0].Ссылка


def date1c(conn, year, month, day):
    query = conn.NewObject("Запрос")
    query.Текст = "ВЫБРАТЬ ДАТАВРЕМЯ(%d, %d, %d) КАК ЗначениеДаты" % (year, month, day)
    return query.Выполнить().Выгрузить()[0].ЗначениеДаты


def main():
    pythoncom.CoInitialize()
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(SEED_JSON), exist_ok=True)
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("Srvr='localhost';Ref='WIM_PIF';App='PyCOM';Locale=ru_RU;")
        protection = conn.NewObject("ОписаниеЗащитыОтОпасныхДействий")
        protection.ПредупреждатьОбОпасныхДействиях = False
        proc = conn.ВнешниеОбработки.Создать(EPF, False, protection)
        prop = proc.ОбеспечитьСвойствоНРДid()
        period = date1c(conn, 2026, 8, 31)
        birth = date1c(conn, 1955, 3, 24)

        fund_name = PREFIX + "FUND"
        fund = find_by_name(conn, "ПИФ", fund_name)
        if fund is None:
            manager = conn.NewObject("СправочникМенеджер.ПИФ")
            obj = manager.СоздатьЭлемент()
            obj.Наименование = fund_name
            obj.ОбменДанными.Загрузка = True
            obj.Записать()
            fund = obj.Ссылка

        group_name = PREFIX + "GROUP"
        group = find_by_name(conn, "Контрагенты", group_name, is_folder=True)
        if group is None:
            manager = conn.NewObject("СправочникМенеджер.Контрагенты")
            obj = manager.СоздатьГруппу()
            obj.Наименование = group_name
            obj.ОбменДанными.Загрузка = True
            obj.Записать()
            group = obj.Ссылка

        nominee_name = PREFIX + "NOMINEE"
        nominee = find_by_name(conn, "Контрагенты", nominee_name)
        if nominee is None:
            manager = conn.NewObject("СправочникМенеджер.Контрагенты")
            obj = manager.СоздатьЭлемент()
            obj.Наименование = nominee_name
            obj.НаименованиеПолное = nominee_name
            obj.Пайщик = True
            obj.ЮрФизЛицо = conn.Перечисления.ЮрФизЛицо.ЮрЛицо
            obj.ИНН = "7700000099"
            obj.Родитель = group
            obj.ОбменДанными.Загрузка = True
            obj.Записать()
            nominee = obj.Ссылка

        qls = conn.NewObject("Запрос")
        qls.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.ЛицевыеСчетаПайщиков "
            "ГДЕ Владелец = &Фонд И Пайщик = &Пайщик"
        )
        qls.УстановитьПараметр("Фонд", fund)
        qls.УстановитьПараметр("Пайщик", nominee)
        if qls.Выполнить().Пустой():
            ls = conn.NewObject("СправочникМенеджер.ЛицевыеСчетаПайщиков").СоздатьЭлемент()
            ls.Код = "WEBND0001"
            ls.Владелец = fund
            ls.Пайщик = nominee
            ls.ВидЛицевогоСчета = conn.Перечисления.ВидыЛицевыхСчетов.СчетНоминальногоДержателя
            ls.ОбменДанными.Загрузка = True
            ls.Записать()

        fio = PREFIX + "Ivanov Ivan Ivanovich"
        nrd = "01_%s_WEB" % RUN_ID
        card = find_by_name(conn, "Контрагенты", fio)
        if card is None:
            manager = conn.NewObject("СправочникМенеджер.Контрагенты")
            obj = manager.СоздатьЭлемент()
            obj.Наименование = fio
            obj.НаименованиеПолное = fio
            obj.Пайщик = True
            obj.ЮрФизЛицо = conn.Перечисления.ЮрФизЛицо.ФизЛицо
            obj.ДатаРождения = birth
            obj.Родитель = group
            obj.ОбменДанными.Загрузка = True
            obj.Записать()
            card = obj.Ссылка
        rec = conn.РегистрыСведений.ФИОФизЛиц.СоздатьМенеджерЗаписи()
        rec.ФизЛицо = card
        rec.Период = period
        rec.Фамилия = "Ivanov"
        rec.Имя = "Ivan"
        rec.Отчество = "Ivanovich"
        rec.Записать(True)
        recn = conn.РегистрыСведений.ЗначенияСвойствОбъектов.СоздатьМенеджерЗаписи()
        recn.Объект = card
        recn.Свойство = prop
        recn.Значение = nrd
        recn.Записать()

        xlsx_path = os.path.join(OUT_DIR, "web_garant.xlsx")
        tab_doc = conn.NewObject("ТабличныйДокумент")
        values = {
            5: ADDRESS,
            6: fio,
            7: "10",
            8: ADDRESS,
            9: "24.03.1955",
            16: "111111",
            17: "6500",
            19: nrd,
        }
        for col, value in values.items():
            tab_doc.Область(3, col).Текст = str(value)
        tab_doc.Записать(xlsx_path, conn.ТипФайлаТабличногоДокумента.XLSX)

        seed = {
            "runId": RUN_ID,
            "prefix": PREFIX,
            "fund": fund_name,
            "nominee": nominee_name,
            "fio": fio,
            "nrd": nrd,
            "xlsx": xlsx_path,
            "epf": EPF,
        }
        with open(SEED_JSON, "w", encoding="utf-8") as f:
            json.dump(seed, f, ensure_ascii=False, indent=2)
        print("SEED_OK " + SEED_JSON)
        print("FUND=" + fund_name)
        print("XLSX=" + xlsx_path)
        return 0
    except Exception as exc:
        desc = str(exc)
        try:
            desc = str(exc.args[2][2])
        except Exception:
            pass
        print("SEED_FAIL " + desc.encode("ascii", "replace").decode("ascii"))
        return 1
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    sys.exit(main())
