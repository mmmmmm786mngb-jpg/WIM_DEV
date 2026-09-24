#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""50 проведенных тестовых поручений FO_VOL для пред-контроля."""

import traceback
from datetime import datetime

import pythoncom
import win32com.client

CONN = "File='C:\\1c\\Cursor_1c\\WORK\\WIM_Fo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
COUNT = 50
MARK = "FO_VOL"


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def main():
    pythoncom.CoInitialize()
    conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК N ИЗ Документ.Поручение "
        "ГДЕ Проведен И КомментарийКлиента = &Метка"
    )
    query.УстановитьПараметр("Метка", MARK)
    selection = query.Выполнить().Выбрать()
    selection.Следующий()
    existing = int(selection.N)
    if existing >= COUNT:
        safe_print("orders already " + str(existing))
        return

    portfolios = conn.NewObject("Запрос")
    portfolios.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 50 Ссылка ИЗ Справочник.Портфели "
        "ГДЕ Наименование ПОДОБНО \"FO_VOL %\" УПОРЯДОЧИТЬ ПО Наименование"
    )
    portfolio_sel = portfolios.Выполнить().Выбрать()
    portfolio_list = []
    while portfolio_sel.Следующий():
        portfolio_list.append(portfolio_sel.Ссылка)
    if len(portfolio_list) < COUNT:
        raise RuntimeError("portfolios %s" % len(portfolio_list))

    asset_query = conn.NewObject("Запрос")
    asset_query.Текст = "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.Активы ГДЕ Наименование = \"EUR\""
    asset_sel = asset_query.Выполнить().Выбрать()
    asset_sel.Следующий()
    asset = asset_sel.Ссылка

    currency_query = conn.NewObject("Запрос")
    currency_query.Текст = "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.Валюты ГДЕ НЕ ПометкаУдаления"
    currency_sel = currency_query.Выполнить().Выбрать()
    currency_sel.Следующий()
    currency = currency_sel.Ссылка

    manager = getattr(conn.Документы, "Поручение")
    created = 0
    for index in range(existing, COUNT):
        doc = manager.СоздатьДокумент()
        doc.ЗаполнитьРеквизитыНовогоПоручения()
        doc.Дата = datetime.now().replace(microsecond=0)
        doc.ВидОперации = conn.Перечисления.ВидыПоручений.Сделка
        doc.Направление = conn.Перечисления.ВидыОперацийСделки.Покупка
        doc.Актив = asset
        doc.Портфель = portfolio_list[index]
        doc.ВалютаРасчетов = currency
        doc.Количество = 10
        doc.ИсходнаяЦена = 100
        doc.ИсходнаяСумма = 1000
        doc.ДатаПоставки = doc.Дата
        doc.ДатаОплаты = doc.Дата
        doc.ЗаполнениеПоПортфелю = False
        doc.КомментарийКлиента = MARK
        line = doc.РаспределениеПоПортфелям.Добавить()
        line.Портфель = portfolio_list[index]
        line.Количество = 10
        doc.Записать(conn.РежимЗаписиДокумента.Проведение)
        created += 1
        if created % 10 == 0:
            safe_print("posted " + str(existing + created))
    safe_print("created " + str(created))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        safe_print(traceback.format_exc()[-1600:])
        raise
