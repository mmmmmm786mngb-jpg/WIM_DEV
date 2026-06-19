#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Proverka poley prolongatsii v dogovorakh DU."""

import pythoncom
import win32com.client


def main():
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("Srvr='localhost';Ref='WIM_DU';")
        query = conn.NewObject("Запрос")
        query.Текст = (
            "ВЫБРАТЬ\n"
            "    КОЛИЧЕСТВО(*) КАК Всего,\n"
            "    СУММА(ВЫБОР КОГДА ДоговорДУ.ПролонгацияДоговора ТОГДА 1 ИНАЧЕ 0 КОНЕЦ) КАК СПролонгацией,\n"
            "    СУММА(ВЫБОР КОГДА ДоговорДУ.СрокДействия > 0 ТОГДА 1 ИНАЧЕ 0 КОНЕЦ) КАК ССроком,\n"
            "    МАКСИМУМ(ДоговорДУ.СрокДействия) КАК МаксСрок\n"
            "ИЗ\n"
            "    Справочник.ДоговорДУ КАК ДоговорДУ\n"
            "ГДЕ\n"
            "    НЕ ДоговорДУ.ПометкаУдаления\n"
            "    И ДоговорДУ.ДатаОкончания = ДАТАВРЕМЯ(1, 1, 1)"
        )
        row = query.Выполнить().Выгрузить()[0]
        print(
            "active:", row.Всего,
            "prol:", row.СПролонгацией,
            "term>0:", row.ССроком,
            "max_term:", row.МаксСрок,
        )

        query.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 10\n"
            "    ДоговорДУ.Код,\n"
            "    ДоговорДУ.ДатаНачала,\n"
            "    ДоговорДУ.СрокДействия,\n"
            "    ДоговорДУ.ПролонгацияДоговора\n"
            "ИЗ\n"
            "    Справочник.ДоговорДУ КАК ДоговорДУ\n"
            "ГДЕ\n"
            "    НЕ ДоговорДУ.ПометкаУдаления\n"
            "    И ДоговорДУ.СрокДействия > 0\n"
            "УПОРЯДОЧИТЬ ПО\n"
            "    ДоговорДУ.СрокДействия УБЫВ"
        )
        table = query.Выполнить().Выгрузить()
        print("sample with term:", table.Count())
        for i in range(table.Count()):
            r = table[i]
            print(r.Код, r.ДатаНачала, r.СрокДействия, r.ПролонгацияДоговора)
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
