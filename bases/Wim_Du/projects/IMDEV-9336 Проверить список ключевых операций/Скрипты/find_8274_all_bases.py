#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poisk obrabotki po vsem bazam localhost i spisok kandidatov."""

import pythoncom
import win32com.client


BASES = ["WIM_DU", "Wim_Du", "AVC_UAT_DU", "PROD_AVC_DU", "AVC_DU", "DU"]


def search_base(ref):
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        try:
            conn = com.Connect("Srvr='localhost';Ref='%s';" % ref)
        except Exception as e:
            print("[%s] connect FAIL: %s" % (ref, e))
            return
        print("[%s] OK" % ref)
        q = conn.NewObject("Запрос")
        q.Текст = """
        ВЫБРАТЬ
            Доп.Наименование КАК Наименование,
            Доп.ИмяОбъекта КАК ИмяОбъекта,
            Доп.ИмяФайла КАК ИмяФайла,
            Доп.Версия КАК Версия
        ИЗ
            Справочник.ДополнительныеОтчетыИОбработки КАК Доп
        ГДЕ
            НЕ Доп.ПометкаУдаления
            И (
                Доп.Наименование ПОДОБНО &A
                ИЛИ Доп.Наименование ПОДОБНО &B
                ИЛИ Доп.ИмяОбъекта ПОДОБНО &C
                ИЛИ Доп.ИмяФайла ПОДОБНО &C
                ИЛИ Доп.Наименование ПОДОБНО &D
            )
        """
        q.УстановитьПараметр("A", "%отрицательн%")
        q.УстановитьПараметр("B", "%аналитическ%")
        q.УстановитьПараметр("C", "%Отрицательн%")
        q.УстановитьПараметр("D", "%остатки по аналитическ%")
        res = q.Выполнить().Выбрать()
        n = 0
        while res.Следующий():
            n += 1
            print("  *", res.Наименование, "|", res.ИмяОбъекта, "|", res.ИмяФайла, "|", res.Версия)
        if n == 0:
            # show recent-looking names with Отчет/Сверка
            q2 = conn.NewObject("Запрос")
            q2.Текст = """
            ВЫБРАТЬ
                Доп.Наименование КАК Наименование,
                Доп.ИмяОбъекта КАК ИмяОбъекта,
                Доп.ИмяФайла КАК ИмяФайла
            ИЗ
                Справочник.ДополнительныеОтчетыИОбработки КАК Доп
            ГДЕ
                НЕ Доп.ПометкаУдаления
                И (
                    Доп.Наименование ПОДОБНО &P1
                    ИЛИ Доп.Наименование ПОДОБНО &P2
                )
            УПОРЯДОЧИТЬ ПО
                Доп.Наименование
            """
            q2.УстановитьПараметр("P1", "%Отчет%")
            q2.УстановитьПараметр("P2", "%Сверка%")
            r2 = q2.Выполнить().Выбрать()
            print("  candidates (Отчет/Сверка):")
            while r2.Следующий():
                name = str(r2.Наименование or "")
                if any(k in name.lower() for k in ["отриц", "аналит", "р/с", "рс ", "ввод", "пул", "рду"]):
                    print("   ~", name, "|", r2.ИмяОбъекта, "|", r2.ИмяФайла)
        print("[%s] done matches=%s" % (ref, n))
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    for b in BASES:
        search_base(b)
