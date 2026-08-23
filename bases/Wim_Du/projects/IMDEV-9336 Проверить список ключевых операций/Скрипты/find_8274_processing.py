#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poisk dopolnitelnoj obrabotki IMDEV-8274 v baze WIM_DU."""

import pythoncom
import win32com.client


def main():
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("Srvr='localhost';Ref='WIM_DU';")
        print("OK connected")

        q = conn.NewObject("Запрос")
        q.Текст = """
        ВЫБРАТЬ
            Доп.Ссылка КАК Ссылка,
            Доп.Наименование КАК Наименование,
            Доп.ИмяОбъекта КАК ИмяОбъекта,
            Доп.ИмяФайла КАК ИмяФайла,
            Доп.Вид КАК Вид,
            Доп.Версия КАК Версия,
            Доп.Публикация КАК Публикация
        ИЗ
            Справочник.ДополнительныеОтчетыИОбработки КАК Доп
        ГДЕ
            Доп.Наименование ПОДОБНО &Шаблон1
            ИЛИ Доп.Наименование ПОДОБНО &Шаблон2
            ИЛИ Доп.ИмяОбъекта ПОДОБНО &Шаблон3
            ИЛИ Доп.ИмяФайла ПОДОБНО &Шаблон3
            ИЛИ Доп.Наименование ПОДОБНО &Шаблон4
        """
        q.УстановитьПараметр("Шаблон1", "%отрицательн%")
        q.УстановитьПараметр("Шаблон2", "%аналитическ%")
        q.УстановитьПараметр("Шаблон3", "%Отрицательн%")
        q.УстановитьПараметр("Шаблон4", "%API%сигнал%")
        res = q.Выполнить().Выбрать()
        n = 0
        while res.Следующий():
            n += 1
            print("---")
            print("Name:", res.Наименование)
            print("Object:", res.ИмяОбъекта)
            print("File:", res.ИмяФайла)
            print("Kind:", conn.String(res.Вид))
            print("Ver:", res.Версия)
            print("Pub:", conn.String(res.Публикация))
        print("Matches:", n)

        if n == 0:
            print("Fallback scan by keywords...")
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
            УПОРЯДОЧИТЬ ПО
                Доп.Наименование
            """
            r2 = q2.Выполнить().Выбрать()
            while r2.Следующий():
                name = str(r2.Наименование or "")
                obj = str(r2.ИмяОбъекта or "")
                low = (name + " " + obj).lower()
                if any(x in low for x in ["отриц", "аналит", "сигнал", "реестр платеж", "api"]):
                    print(name, "|", obj, "|", r2.ИмяФайла)
        print("DONE")
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
