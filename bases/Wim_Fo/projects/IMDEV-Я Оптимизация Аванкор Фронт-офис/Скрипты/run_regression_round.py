#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Эталон или повтор пред- и пост-контроля FO_VOL. Аргумент: baseline или after."""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
spec = importlib.util.spec_from_file_location("pack_base", os.path.join(HERE, "run_pack_baseline.py"))
pack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)


def collect(conn, text):
    query = conn.NewObject("Запрос")
    query.Текст = text
    selection = query.Выполнить().Выбрать()
    refs = []
    while selection.Следующий():
        refs.append(selection.Ссылка)
    return refs


def install_orders(conn, portfolios, limits, limit_class):
    settings = conn.NewObject("Структура")
    settings.Вставить("Порог", 30)
    settings.Вставить("Комментарий", "FO_VOL")
    storage = conn.NewObject("ХранилищеЗначения", settings)
    for portfolio in portfolios:
        query = conn.NewObject("Запрос")
        query.Текст = (
            "ВЫБРАТЬ ПЕРВЫЕ 1 Т.Ссылка КАК Ссылка ИЗ Документ.УстановкаЛимитов КАК Т "
            "ГДЕ Т.Проведен И Т.ОбъектНазначения = &Портфель И НЕ Т.ПометкаУдаления"
        )
        query.УстановитьПараметр("Портфель", portfolio)
        selection = query.Выполнить().Выбрать()
        if not selection.Следующий():
            continue
        doc = selection.Ссылка.ПолучитьОбъект()
        present = {}
        for index in range(doc.Лимиты.Количество()):
            line = doc.Лимиты.Получить(index)
            present[conn.String(line.Лимит)] = line
        changed = False
        for limit_ref in limits:
            key = conn.String(limit_ref)
            line = present.get(key)
            if line is None:
                line = doc.Лимиты.Добавить()
                line.Лимит = limit_ref
                changed = True
            line.НастройкиЛимита = storage
            line.НастройкиУстановлены = True
        if changed:
            doc.Записать(conn.РежимЗаписиДокумента.Проведение)


def rows_of(conn, container):
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ К.Лимит.Наименование КАК Лимит, К.Фокус.Наименование КАК Фокус, "
        "К.Поручение.Номер КАК Номер, К.Зона КАК Зона, К.Отказ КАК Отказ, "
        "К.Базис КАК Базис, К.Описание КАК Описание "
        "ИЗ РегистрСведений.КэшВмКратко КАК К "
        "ГДЕ К.Вместилище = &Вместилище "
        "УПОРЯДОЧИТЬ ПО Лимит, Фокус, Номер"
    )
    query.УстановитьПараметр("Вместилище", container)
    selection = query.Выполнить().Выбрать()
    lines = []
    while selection.Следующий():
        lines.append("%s\t%s\t%s\t%s\t%s\t%s\t%s" % (
            conn.String(selection.Лимит),
            conn.String(selection.Фокус),
            conn.String(selection.Номер),
            conn.String(selection.Зона),
            selection.Отказ,
            selection.Базис,
            conn.String(selection.Описание).replace("\n", " ")[:180],
        ))
    return lines


def measures(conn):
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 6 Замеры.КлючеваяОперация.Наименование КАК Имя, "
        "Замеры.ВремяВыполнения КАК Секунды, Замеры.ВесЗамера КАК Вес "
        "ИЗ РегистрСведений.ЗамерыВремени КАК Замеры "
        "УПОРЯДОЧИТЬ ПО Замеры.ДатаНачалаЗамера УБЫВ"
    )
    selection = query.Выполнить().Выбрать()
    lines = []
    while selection.Следующий():
        lines.append("%s\t%s\t%s" % (conn.String(selection.Имя), selection.Секунды, selection.Вес))
    return lines


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    conn = win32com.client.Dispatch("V83.COMConnector").Connect(pack.CONN)
    portfolios = collect(
        conn,
        "ВЫБРАТЬ Ссылка ИЗ Справочник.Портфели ГДЕ Наименование ПОДОБНО \"FO_VOL %\" УПОРЯДОЧИТЬ ПО Наименование",
    )
    structure = collect(
        conn,
        "ВЫБРАТЬ Ссылка ИЗ Справочник.Лимиты ГДЕ Наименование ПОДОБНО \"FO_VOL S%\" "
        "ИЛИ Наименование ПОДОБНО \"FO_VOL C%\" ИЛИ Наименование ПОДОБНО \"FO_VOL X%\" "
        "УПОРЯДОЧИТЬ ПО Наименование",
    )
    orders_limits = collect(
        conn,
        "ВЫБРАТЬ Ссылка ИЗ Справочник.Лимиты ГДЕ Наименование ПОДОБНО \"FO_VOL O%\" УПОРЯДОЧИТЬ ПО Наименование",
    )
    orders = collect(
        conn,
        "ВЫБРАТЬ Ссылка ИЗ Документ.Поручение ГДЕ Проведен И КомментарийКлиента = \"FO_VOL\"",
    )
    limit_class = collect(
        conn, "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.КлассыЛимитов ГДЕ НЕ ПометкаУдаления")[0]
    install_orders(conn, portfolios[:50], orders_limits, limit_class)
    out = []
    post_elapsed, post_result, post_id = pack.run_post(conn, portfolios, structure)
    out.append("POST")
    out.append("seconds\t%s" % format(post_elapsed, ".3f"))
    out.append("refusal\t%s" % post_result.Отказ)
    out.append("container\t%s" % conn.String(post_id))
    out.append("measures")
    out.extend(measures(conn))
    post_rows = rows_of(conn, post_id)
    out.append("rows\t%s" % len(post_rows))
    out.extend(post_rows)
    pre_elapsed, pre_result, pre_id = pack.run_post(
        conn, portfolios[:50], orders_limits, orders, True)
    out.append("PRE")
    out.append("seconds\t%s" % format(pre_elapsed, ".3f"))
    out.append("refusal\t%s" % pre_result.Отказ)
    out.append("description\t%s" % str(pre_result.Описание).replace("\n", " ")[:300])
    out.append("container\t%s" % conn.String(pre_id))
    out.append("measures")
    out.extend(measures(conn))
    pre_rows = rows_of(conn, pre_id)
    out.append("rows\t%s" % len(pre_rows))
    out.extend(pre_rows)
    path = os.path.join(ROOT, "Тестирование", "reports", "pack_round_%s.txt" % label)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(out))
    pack.safe_print("post %s rows %s refusal %s" % (format(post_elapsed, ".3f"), len(post_rows), post_result.Отказ))
    pack.safe_print("pre %s rows %s refusal %s" % (format(pre_elapsed, ".3f"), len(pre_rows), pre_result.Отказ))
    pack.safe_print(path)


if __name__ == "__main__":
    main()
