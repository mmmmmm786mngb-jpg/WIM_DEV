#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Данные нагрузочного стенда уровня 5 на разработческой ФО.

Создает с префиксом T5L5: 520 контрагентов с ИНН (T5L5K0001..), 100 акций с
листингом ММВБ и активами (T5L5S001..), 389 индексов (T5L5IX001..).
Повторный запуск досоздает недостающее. Удаление - cleanup_load.py.
"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PROJECT, "Тестирование", "stand"))
import stand_common as sc  # noqa: E402

COUNTERPARTIES = 520
SHARES = 100
INDEXES = 389


def log(text):
    print(text, flush=True)


def existing_names(conn, text, params):
    return {row["Имя"] for row in sc.query_rows(conn, text, params)}


def ensure_counterparties(fo):
    have = existing_names(
        fo,
        "ВЫБРАТЬ К.Наименование КАК Имя ИЗ Справочник.Контрагенты КАК К "
        "ГДЕ К.Наименование ПОДОБНО &Маска",
        {"Маска": "T5L5K%"},
    )
    created = 0
    for number in range(1, COUNTERPARTIES + 1):
        name = "T5L5K%04d" % number
        if name in have:
            continue
        obj = fo.Справочники.Контрагенты.СоздатьЭлемент()
        obj.Наименование = name
        obj.НаименованиеПолное = name + " нагрузочный стенд"
        obj.ИНН = "99%08d" % number
        obj.Записать()
        created += 1
        if created % 50 == 0:
            log("counterparties created %d" % created)
    log("counterparties total new %d, existed %d" % (created, len(have)))


def ensure_shares(fo):
    sample = sc.query_rows(
        fo,
        "ВЫБРАТЬ ПЕРВЫЕ 1 А.Ссылка КАК Ссылка ИЗ Справочник.Акции КАК А "
        "ГДЕ НЕ А.ПометкаУдаления И А.Эмитент <> ЗНАЧЕНИЕ(Справочник.Контрагенты.ПустаяСсылка) "
        "И НЕ А.Наименование ПОДОБНО &Маска УПОРЯДОЧИТЬ ПО А.Наименование",
        {"Маска": "T5L5%"},
    )
    if not sample:
        raise SystemExit("no sample share on FO")
    sample_ref = sample[0]["Ссылка"]
    have = existing_names(
        fo,
        "ВЫБРАТЬ Листинг.Тикер КАК Имя ИЗ Справочник.Акции.БиржиЛистинга КАК Листинг "
        "ГДЕ Листинг.Тикер ПОДОБНО &Маска",
        {"Маска": "T5L5S%"},
    )
    mmvb = fo.Справочники.Биржи.ММВБ
    created = 0
    for number in range(1, SHARES + 1):
        code = "T5L5S%03d" % number
        if code in have:
            continue
        obj = sample_ref.Скопировать()
        obj.Наименование = "T5L5 Akciya %s" % code
        obj.НаименованиеПолное = obj.Наименование
        obj.КраткоеНаименование = code
        obj.ВнешнийКод = code
        obj.ISIN = ""
        obj.НомерГосРегистрацииВыпуска = ""
        obj.СобиратьНаименованиеАвтоматически = False
        obj.БиржиЛистинга.Очистить()
        row = obj.БиржиЛистинга.Добавить()
        row.Биржа = mmvb
        row.Тикер = code
        obj.Записать()
        asset = fo.Справочники.Активы.СоздатьЭлемент()
        asset.Объект = obj.Ссылка
        asset.ВидАктива = obj.ВидАктива
        asset.Эмитент = obj.Эмитент
        asset.ВалютаНоминальнойСтоимости = obj.ВалютаНоминальнойСтоимости
        asset.Наименование = obj.Наименование
        asset.ВнешнийКод = code
        asset.Записать()
        created += 1
        if created % 20 == 0:
            log("shares created %d" % created)
    log("shares total new %d, existed %d" % (created, len(have)))


def ensure_indexes(fo):
    have = existing_names(
        fo,
        "ВЫБРАТЬ Инд.КодИндекса КАК Имя ИЗ Справочник.Индексы КАК Инд "
        "ГДЕ Инд.КодИндекса ПОДОБНО &Маска",
        {"Маска": "T5L5IX%"},
    )
    rub = fo.Справочники.Валюты.НайтиПоНаименованию("RUB")
    mmvb = fo.Справочники.Биржи.ММВБ
    created = 0
    for number in range(1, INDEXES + 1):
        code = "T5L5IX%03d" % number
        if code in have:
            continue
        obj = fo.Справочники.Индексы.СоздатьЭлемент()
        obj.Наименование = "T5L5 Indeks %s" % code
        obj.КодИндекса = code
        obj.ВнешнийКод = code
        obj.Валюта = rub
        obj.Биржа = mmvb
        obj.Записать()
        created += 1
        if created % 50 == 0:
            log("indexes created %d" % created)
    log("indexes total new %d, existed %d" % (created, len(have)))


def main():
    fo = sc.connect("wim_fo")
    log("connected wim_fo")
    ensure_counterparties(fo)
    ensure_shares(fo)
    ensure_indexes(fo)
    log("prepare done")


if __name__ == "__main__":
    main()
