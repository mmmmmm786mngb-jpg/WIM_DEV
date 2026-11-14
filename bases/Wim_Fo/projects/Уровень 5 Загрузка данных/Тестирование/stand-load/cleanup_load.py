#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Уборка данных нагрузочного стенда уровня 5 с разработческой ФО.

Удаляет записи, созданные прогоном, затем объекты T5L5 этого стенда:
дополнительные сведения контрагентов T5L5K, данные и составы индексов T5L5IX,
строки котировок по активам T5L5S (документ целиком, если все строки стенда),
затем контрагентов, индексы, активы и акции. Запуск: python cleanup_load.py
"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PROJECT, "Тестирование", "stand"))
import stand_common as sc  # noqa: E402


def log(text):
    print(text, flush=True)


def refs(fo, text, params=None):
    return [row["Ссылка"] for row in sc.query_rows(fo, text, params or {})]


def delete_objects(fo, links, label):
    deleted = 0
    for ref in links:
        obj = ref.ПолучитьОбъект()
        if obj is None:
            continue
        obj.ОбменДанными.Загрузка = True
        obj.Удалить()
        deleted += 1
    log("%s deleted %d" % (label, deleted))


def clear_addl_info(fo):
    rows = sc.query_rows(
        fo,
        "ВЫБРАТЬ Св.Объект КАК Объект, Св.Свойство КАК Свойство "
        "ИЗ РегистрСведений.ДополнительныеСведения КАК Св "
        "ГДЕ Св.Объект ССЫЛКА Справочник.Контрагенты "
        "И ВЫРАЗИТЬ(Св.Объект КАК Справочник.Контрагенты).Наименование ПОДОБНО &Маска",
        {"Маска": "T5L5K%"},
    )
    for row in rows:
        record_set = fo.РегистрыСведений.ДополнительныеСведения.СоздатьНаборЗаписей()
        record_set.Отбор.Объект.Установить(row["Объект"])
        record_set.Отбор.Свойство.Установить(row["Свойство"])
        record_set.ОбменДанными.Загрузка = True
        record_set.Записать()
    log("addl info cleared %d" % len(rows))


def clear_index_records(fo):
    rows = sc.query_rows(
        fo,
        "ВЫБРАТЬ РАЗЛИЧНЫЕ Рег.Индекс КАК Индекс ИЗ РегистрСведений.ДанныеИндекса КАК Рег "
        "ГДЕ Рег.Индекс.КодИндекса ПОДОБНО &Маска",
        {"Маска": "T5L5IX%"},
    )
    # Отбор.Индекс в COM конфликтует с методом коллекции, поэтому менеджер записи по ключу
    records = sc.query_rows(
        fo,
        "ВЫБРАТЬ * ИЗ РегистрСведений.ДанныеИндекса КАК Рег ГДЕ Рег.Индекс.КодИндекса ПОДОБНО &Маска",
        {"Маска": "T5L5IX%"},
    )
    deleted = 0
    for record in records:
        manager = fo.РегистрыСведений.ДанныеИндекса.СоздатьМенеджерЗаписи()
        for column, value in record.items():
            try:
                setattr(manager, column, value)
            except Exception:
                pass
        manager.Прочитать()
        if manager.Выбран():
            manager.Удалить()
            deleted += 1
    log("ДанныеИндекса deleted %d of %d (indexes %d)" % (deleted, len(records), len(rows)))
    docs = refs(
        fo,
        "ВЫБРАТЬ РАЗЛИЧНЫЕ Д.Ссылка КАК Ссылка ИЗ Документ.УстановкаСоставаИндекса КАК Д "
        "ГДЕ Д.Индекс.КодИндекса ПОДОБНО &Маска",
        {"Маска": "T5L5IX%"},
    )
    delete_objects(fo, docs, "УстановкаСоставаИндекса docs")


def clear_quotes(fo):
    docs = sc.query_rows(
        fo,
        "ВЫБРАТЬ РАЗЛИЧНЫЕ Строки.Ссылка КАК Ссылка ИЗ Документ.КотировкиЦБНаБирже.Котировки КАК Строки "
        "ГДЕ Строки.Актив.ВнешнийКод ПОДОБНО &Маска",
        {"Маска": "T5L5S%"},
    )
    for row in docs:
        doc = row["Ссылка"].ПолучитьОбъект()
        if doc is None:
            continue
        total = doc.Котировки.Количество()
        stand_rows = []
        for index in range(total):
            line = doc.Котировки.Получить(index)
            if str(line.Актив.ВнешнийКод).startswith("T5L5S"):
                stand_rows.append(line)
        doc.ОбменДанными.Загрузка = True
        if len(stand_rows) == total:
            doc.Удалить()
            log("quotes document deleted (%d rows)" % total)
        else:
            for line in stand_rows:
                doc.Котировки.Удалить(line)
            doc.Записать()
            log("quotes rows removed %d of %d" % (len(stand_rows), total))


def main():
    fo = sc.connect("wim_fo")
    log("connected wim_fo")
    # ДопСведения чистятся фоновым заданием (run_cleanup_addl.py): подписка УК_*
    clear_index_records(fo)
    clear_quotes(fo)
    delete_objects(fo, refs(
        fo, "ВЫБРАТЬ К.Ссылка КАК Ссылка ИЗ Справочник.Контрагенты КАК К ГДЕ К.Наименование ПОДОБНО &Маска",
        {"Маска": "T5L5K%"}), "counterparties")
    delete_objects(fo, refs(
        fo, "ВЫБРАТЬ Инд.Ссылка КАК Ссылка ИЗ Справочник.Индексы КАК Инд ГДЕ Инд.КодИндекса ПОДОБНО &Маска",
        {"Маска": "T5L5IX%"}), "indexes")
    delete_objects(fo, refs(
        fo, "ВЫБРАТЬ А.Ссылка КАК Ссылка ИЗ Справочник.Активы КАК А ГДЕ А.ВнешнийКод ПОДОБНО &Маска",
        {"Маска": "T5L5S%"}), "assets")
    delete_objects(fo, refs(
        fo, "ВЫБРАТЬ А.Ссылка КАК Ссылка ИЗ Справочник.Акции КАК А ГДЕ А.ВнешнийКод ПОДОБНО &Маска",
        {"Маска": "T5L5S%"}), "shares")
    clear_fo_received(fo)
    clear_fo_quote_docs(fo)
    log("fo cleanup done")
    mo_cleanup()
    log("cleanup done")





def clear_fo_received(fo):
    """Объекты, созданные на ФО приемом пакетов мандатов: портфели и субпортфели T5L5."""
    delete_objects(fo, refs(
        fo, "ВЫБРАТЬ П.Ссылка КАК Ссылка ИЗ Справочник.Субпортфели КАК П ГДЕ П.ВнешнийКод ПОДОБНО &Маска",
        {"Маска": "T5L5%"}), "fo subportfolios")
    delete_objects(fo, refs(
        fo, "ВЫБРАТЬ П.Ссылка КАК Ссылка ИЗ Справочник.Портфели КАК П ГДЕ П.ВнешнийКод ПОДОБНО &Маска",
        {"Маска": "T5L5%"}), "fo portfolios")
    for catalog in ("Контрагенты", "Стратегии", "МестаХранения"):
        delete_objects(fo, refs(
            fo, "ВЫБРАТЬ Т.Ссылка КАК Ссылка ИЗ Справочник.%s КАК Т ГДЕ Т.Наименование ПОДОБНО &Маска" % catalog,
            {"Маска": "T5L5%"}), "fo " + catalog)


def clear_fo_quote_docs(fo):
    """Строки котировок, принятые от МО по датам нагрузки, и документы стенда целиком."""
    docs = refs(
        fo, "ВЫБРАТЬ РАЗЛИЧНЫЕ Д.Ссылка КАК Ссылка ИЗ Документ.КотировкиЦБНаБирже КАК Д "
            "ГДЕ Д.Комментарий ПОДОБНО &Маска", {"Маска": "%T5L5%"})
    delete_objects(fo, docs, "fo quote docs by comment")


def mo_cleanup():
    mo = sc.connect("wim_mo")
    log("connected wim_mo")
    for catalog, field in (("СчетаМандатов", "КодСчета"), ("Мандаты", "КодМандата")):
        links = refs(
            mo, "ВЫБРАТЬ Т.Ссылка КАК Ссылка ИЗ Справочник.%s КАК Т ГДЕ Т.%s ПОДОБНО &Маска" % (catalog, field),
            {"Маска": "T5L5_%"})
        deleted = 0
        for ref in links:
            obj = ref.ПолучитьОбъект()
            if obj is None:
                continue
            obj.ОбменДанными.Загрузка = True
            obj.ДополнительныеСвойства.Вставить("ОтключитьМеханизмРегистрацииОбъектов", True)
            obj.Удалить()
            deleted += 1
        log("mo %s deleted %d" % (catalog, deleted))
    for catalog in ("СчетаДЕПО", "БанковскиеСчета"):
        links = refs(
            mo, "ВЫБРАТЬ Т.Ссылка КАК Ссылка ИЗ Справочник.%s КАК Т ГДЕ Т.КодМестаХранения ПОДОБНО &Маска" % catalog,
            {"Маска": "T5L5_%"})
        deleted = 0
        for ref in links:
            obj = ref.ПолучитьОбъект()
            if obj is None:
                continue
            obj.ОбменДанными.Загрузка = True
            obj.ДополнительныеСвойства.Вставить("ОтключитьМеханизмРегистрацииОбъектов", True)
            obj.Удалить()
            deleted += 1
        log("mo %s deleted %d" % (catalog, deleted))
    was_on = False
    mo.Константы.ВыполнятьЗамерыПроизводительности.Установить(was_on)
    log("mo constant returned to %s" % was_on)

if __name__ == "__main__":
    main()
