#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Execute source queries with empty refs so the platform actually compiles them."""

import datetime
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pythoncom
import win32com.client

EPF = (
    r"c:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects\IMDEV-9458 "
    r"Доработка обработки Формирование начислений НДФЛ"
    r"\Тестирование\IMDEV9458_DiagEmptyUKClients.epf"
)


def main():
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("Srvr='localhost';Ref='WIM_FIN';App='PyCOM';Locale=ru_RU;")
        print("CONNECTED")

        empty_cli = conn.Справочники.Контрагенты.ПустаяСсылка()
        empty_uk = empty_cli
        dt = datetime.datetime(2026, 12, 31, 23, 59, 59)

        queries = []

        q1 = conn.NewObject("Запрос")
        q1.Текст = """
ВЫБРАТЬ
    СтрокиНачислений.КодДохода.Код КАК КодДохода,
    СтрокиНачислений.Ссылка.Портфель КАК Портфель,
    СУММА(СтрокиНачислений.СуммаДохода) КАК СуммаДохода,
    СУММА(СтрокиНачислений.СуммаВычета) КАК СуммаВычета,
    КОЛИЧЕСТВО(*) КАК Количество
ИЗ
    Документ.НачислениеНДФЛПоПортфелю.Начисления КАК СтрокиНачислений
ГДЕ
    СтрокиНачислений.Ссылка.Портфель.Клиент = &Клиент
    И СтрокиНачислений.Ссылка.Портфель.УправляющаяКомпания = &УК
    И СтрокиНачислений.Ссылка.Дата = &Дата
    И Не СтрокиНачислений.Ссылка.ПометкаУдаления

СГРУППИРОВАТЬ ПО
    СтрокиНачислений.КодДохода.Код,
    СтрокиНачислений.Ссылка.Портфель

УПОРЯДОЧИТЬ ПО
    КодДохода
"""
        q1.УстановитьПараметр("Клиент", empty_cli)
        q1.УстановитьПараметр("УК", empty_uk)
        q1.УстановитьПараметр("Дата", dt)
        queries.append(("PF TCH", q1))

        q2 = conn.NewObject("Запрос")
        q2.Текст = """
ВЫБРАТЬ
    Обороты.КодДохода.Код КАК КодДохода,
    Обороты.Портфель КАК Портфель,
    Обороты.Система КАК Система,
    СУММА(Обороты.СуммаДоходаОборот) КАК СуммаДохода,
    СУММА(Обороты.СуммаВычетаОборот) КАК СуммаВычета
ИЗ
    РегистрНакопления.НДФЛСведенияОДоходах.Обороты(
            &НачалоПериода,
            &КонецПериода,
            ,
            УправляющаяКомпания = &УК
                И Клиент = &Клиент) КАК Обороты

СГРУППИРОВАТЬ ПО
    Обороты.КодДохода.Код,
    Обороты.Портфель,
    Обороты.Система

УПОРЯДОЧИТЬ ПО
    КодДохода
"""
        q2.УстановитьПараметр("НачалоПериода", datetime.datetime(2026, 1, 1))
        q2.УстановитьПараметр("КонецПериода", dt)
        q2.УстановитьПараметр("Клиент", empty_cli)
        q2.УстановитьПараметр("УК", empty_uk)
        queries.append(("register incomes", q2))

        q3 = conn.NewObject("Запрос")
        q3.Текст = """
ВЫБРАТЬ
    ДоходыУК.КодДохода.Код КАК КодДохода,
    СУММА(ДоходыУК.СуммаДохода) КАК СуммаДохода,
    СУММА(ДоходыУК.СуммаВычета) КАК СуммаВычета
ИЗ
    РегистрНакопления.НДФЛСведенияОДоходахПоУправляющейКомпании КАК ДоходыУК
ГДЕ
    ДоходыУК.СведенияИзВнешнейСистемы = ИСТИНА
    И ДоходыУК.Период < &КонецПериода
    И ДоходыУК.УправляющаяКомпания = &УК
    И ДоходыУК.Клиент = &Клиент
    И ДоходыУК.Активность

СГРУППИРОВАТЬ ПО
    ДоходыУК.КодДохода.Код
"""
        q3.УстановитьПараметр("КонецПериода", dt)
        q3.УстановитьПараметр("Клиент", empty_cli)
        q3.УстановитьПараметр("УК", empty_uk)
        queries.append(("UK external", q3))

        for title, q in queries:
            try:
                res = q.Выполнить()
                n = res.Выбрать().Количество()
                print("OK", title, "rows=", n)
            except Exception as exc:
                print("FAIL", title, exc)
                return 1

        ext = conn.ExternalDataProcessors.Create(EPF)
        names = conn.NewObject("Массив")
        names.Add("Львов Павел Глебович")
        params = conn.NewObject("Структура")
        params.Insert("ДатаОкончания", datetime.datetime(2026, 12, 31))
        params.Insert("ИменаКлиентов", names)
        text = str(ext.ВыполнитьДиагностикуИсточников(params))
        print("EPF sources len", len(text))
        print(text[-400:])
        return 0
    except Exception as exc:
        print("ERROR", type(exc).__name__, exc)
        import traceback

        traceback.print_exc()
        return 1
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    raise SystemExit(main())
