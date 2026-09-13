#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seed September 2026 docs so web reports with default ThisMonth show data."""

import pythoncom
import win32com.client
from datetime import datetime

IB = r"C:\1c\Cursor_1c\WORK\OU_Training"


def main():
    pythoncom.CoInitialize()
    com = win32com.client.Dispatch("V83.COMConnector")
    conn = com.Connect(f"File='{IB}';Usr='Admin';Pwd='1';App='PyCOM';Locale=ru_RU;")
    try:
        def cat(name, desc, fill=None):
            m = getattr(conn.Справочники, name)
            ref = m.НайтиПоНаименованию(desc, True)
            if ref is not None and not ref.Пустая():
                return ref
            o = m.СоздатьЭлемент()
            o.Наименование = desc
            if fill:
                fill(o)
            o.Записать()
            return o.Ссылка

        wh = cat("Склады", "WebReport WH")
        sup = cat("Контрагенты", "WebReport Supplier")
        buy = cat("Контрагенты", "WebReport Buyer")

        def fill_g(o):
            o.ТипНоменклатуры = conn.Перечисления.ТипыНоменклатуры.Товар

        goods = cat("Номенклатура", "WebReport Goods", fill_g)

        mgr = conn.РегистрыСведений.УчетнаяПолитикаУУ.СоздатьМенеджерЗаписи()
        mgr.Период = datetime(2026, 1, 1)
        mgr.МетодОценкиЗапасов = conn.Перечисления.МетодыОценкиЗапасов.FIFO
        mgr.Записать()

        r = conn.Документы.ПриходнаяНакладная.СоздатьДокумент()
        r.Дата = datetime(2026, 9, 5, 12, 0, 0)
        r.Склад = wh
        r.Контрагент = sup
        r.Комментарий = "web report seed in"
        row = r.Товары.Добавить()
        row.Номенклатура = goods
        row.Количество = 20
        row.Цена = 100
        row.Сумма = 2000
        r.Записать(conn.РежимЗаписиДокумента.Проведение)
        print("Receipt OK", r.Номер)

        e = conn.Документы.РасходнаяНакладная.СоздатьДокумент()
        e.Дата = datetime(2026, 9, 10, 12, 0, 0)
        e.Склад = wh
        e.Контрагент = buy
        e.Комментарий = "web report seed out"
        row = e.Товары.Добавить()
        row.Номенклатура = goods
        row.Количество = 5
        row.Цена = 300
        row.Сумма = 1500
        e.Записать(conn.РежимЗаписиДокумента.Проведение)
        print("Expense OK", e.Номер, "expected cost 500")
        print("SEED_OK")
    finally:
        del conn
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
