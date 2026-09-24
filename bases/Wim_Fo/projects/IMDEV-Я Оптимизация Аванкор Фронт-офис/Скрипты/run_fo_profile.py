#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Запускает проверку лимитов на сервере фоновым заданием.
Внешнее соединение не компилирует модули без этого контекста,
поэтому сама проверка идет в серверном задании.
"""

import os
import sys
import pythoncom
import win32com.client
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CONN = "Srvr='localhost';Ref='WIN_FO_server';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"


def safe_print(text):
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"), flush=True)


def collect(conn, text):
    query = conn.NewObject("Запрос")
    query.Текст = text
    selection = query.Выполнить().Выбрать()
    refs = []
    while selection.Следующий():
        refs.append(selection.Ссылка)
    return refs


def empty_date(conn):
    query = conn.NewObject("Запрос")
    query.Текст = "ВЫБРАТЬ ДАТАВРЕМЯ(1, 1, 1) КАК D"
    selection = query.Выполнить().Выбрать()
    selection.Следующий()
    return selection.D


def new_array(conn, values):
    array = conn.NewObject("Массив")
    for value in values:
        array.Add(value)
    return array


def build_params(conn, portfolios, limits):
    today = datetime.now().replace(microsecond=0)
    blank = empty_date(conn)
    container = conn.NewObject("УникальныйИдентификатор")
    params = conn.NewObject("Структура")
    params.Вставить("Вид", conn.Перечисления.ВидыРаспорядителей.ПроверкаИОтправка)
    params.Вставить("Метод", "Распорядители.ПроверкаИОтправка")
    params.Вставить("МетодНаКлиенте", "РаспорядителиКлиент.ПроверкаИОтправка_Вход")
    params.Вставить("Наименование", "FO profile")
    params.Вставить("ЭраРаспорядителей", True)
    params.Вставить("АдресРезультатаРасш", "")
    params.Вставить("ИспользоватьФоновыеЗадания", False)
    params.Вставить("ФормироватьЛогОтладки", False)
    params.Вставить("ВестиУчетПоСубпортфелям", False)
    params.Вставить("РежимТестирования", True)
    params.Вставить("РежимТестированияЛимитов", True)
    params.Вставить("Профиль", conn.Справочники.НастройкиПрофилейБлоттера.ПустаяСсылка())
    params.Вставить("ИдентификаторФормы", None)
    params.Вставить("КлючеваяОперация", conn.Справочники.КлючевыеОперации.Проверка)
    params.Вставить("ПоказатьРезультатОбработки", False)
    params.Вставить("ОписаниеОперации", "FO profile")
    params.Вставить("ФормуИнициаторЗакрыть", False)
    params.Вставить("Поручения", new_array(conn, []))
    params.Вставить("Портфели", new_array(conn, portfolios))
    params.Вставить("Лимиты", new_array(conn, limits))
    params.Вставить("ОтправитьПослеПроверки", False)
    params.Вставить("ДатаПроверки", today)
    params.Вставить("ДатаФактПозиции", blank)
    params.Вставить("ДатаОграниченияПлановойПозиции", blank)
    params.Вставить("СоставПозиции", new_array(conn, []))
    params.Вставить("ЭтоПретрейд", False)
    params.Вставить("ПроверкаПоручений", False)
    params.Вставить("ИспользоватьДатуАктуальности", True)
    params.Вставить("СоставПозицииИзДополнительныхНастроек", new_array(conn, []))
    params.Вставить("ВыводитьПредупрежденияПриПретрейде", False)
    params.Вставить("ВозможенЗапускПроверки", True)
    params.Вставить("ВозможенЗапускПроверкиОписание", "")
    params.Вставить("Вместилище", container)
    params.Вставить("РазослатьВедомости", False)
    params.Вставить("РазослатьВедомостиПоручений", False)
    params.Вставить("ОбновлятьРасширения", False)
    params.Вставить("ПланПроверки", conn.NewObject("ХранилищеЗначения", ""))
    params.Вставить("КонтролироватьОтклонениеЦены", False)
    params.Вставить("БезВопросаПодтверждения", True)
    params.Вставить("ОткрыватьСправкуРасчетПриНарушениях", False)
    return params


def main():
    portfolio_count = sys.argv[1] if len(sys.argv) > 1 else "1000"
    limit_count = sys.argv[2] if len(sys.argv) > 2 else "128"
    pythoncom.CoInitialize()
    conn = win32com.client.Dispatch("V83.COMConnector").Connect(CONN)
    portfolios = collect(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ %s Ссылка ИЗ Справочник.Портфели "
        "ГДЕ Наименование ПОДОБНО \"FO_FO %%\" УПОРЯДОЧИТЬ ПО Наименование" % portfolio_count,
    )
    limits = collect(
        conn,
        "ВЫБРАТЬ ПЕРВЫЕ %s Ссылка ИЗ Справочник.Лимиты "
        "ГДЕ НЕ ЭтоГруппа И Родитель.Наименование = \"482-п ДУ\" УПОРЯДОЧИТЬ ПО Код" % limit_count,
    )
    safe_print("portfolios %s limits %s" % (len(portfolios), len(limits)))
    params = build_params(conn, portfolios, limits)
    arguments = conn.NewObject("Массив")
    arguments.Add(params)
    job = conn.ФоновыеЗадания.Выполнить(
        "FO_LimitProfile_Замеры.Запустить", arguments, "FO_LimitProfileClean", "FO profile")
    safe_print("job started")
    updated = job.ОжидатьЗавершенияВыполнения(1800)
    safe_print("job state " + conn.String(updated.Состояние))
    info = updated.ИнформацияОбОшибке
    if info is not None:
        try:
            safe_print("job error " + conn.String(info.ПодробноеПредставлениеОшибки)[:800])
        except Exception:
            safe_print("job error present")
    messages = updated.ПолучитьСообщенияПользователю()
    safe_print("messages %s" % messages.Count())
    index = 0
    for message in messages:
        safe_print("msg " + conn.String(message.Текст)[:200])
        index += 1
        if index > 30:
            break
    safe_print("PROFILE DONE")


if __name__ == "__main__":
    main()
