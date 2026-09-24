#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пост-контроль портфелей FO_FO по лимитам группы 482-п ДУ.
Полные строки не выгружаются. Метка запуска передается первым аргументом.
"""

import importlib.util
import os
import sys

import pythoncom
import win32com.client

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
spec = importlib.util.spec_from_file_location("shape", os.path.join(HERE, "run_shape_round.py"))
shape = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shape)


def xml_of(conn, value):
    return conn.XMLСтрока(value)


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "fo3000"
    pythoncom.CoInitialize()
    conn = win32com.client.Dispatch("V83.COMConnector").Connect(shape.pack.CONN)
    portfolios = shape.collect(
        conn,
        "ВЫБРАТЬ Ссылка ИЗ Справочник.Портфели "
        "ГДЕ Наименование ПОДОБНО \"FO_FO %\" "
        "УПОРЯДОЧИТЬ ПО Наименование",
    )
    mode = sys.argv[2] if len(sys.argv) > 2 else "all"
    limit_text = (
        "ВЫБРАТЬ Ссылка ИЗ Справочник.Лимиты "
        "ГДЕ НЕ ЭтоГруппа И Родитель.Наименование = \"482-п ДУ\" "
    )
    if mode == "structure":
        limit_text += "И ВидЛимита = ЗНАЧЕНИЕ(Перечисление.ВидыЛимитов.Структура) "
    limit_text += "УПОРЯДОЧИТЬ ПО Код"
    limits = shape.collect(conn, limit_text)
    shape.pack.safe_print("portfolios %s limits %s" % (len(portfolios), len(limits)))
    elapsed, result, container = shape.pack.run_post(conn, portfolios, limits)
    shape.pack.safe_print("post finished %s refusal %s" % (format(elapsed, ".3f"), result.Отказ))
    lines = [
        "label\t%s" % label,
        "portfolios\t%s" % len(portfolios),
        "limits\t%s" % len(limits),
        "seconds\t%s" % format(elapsed, ".3f"),
        "refusal\t%s" % result.Отказ,
        "container\t%s" % xml_of(conn, container),
    ]
    count = conn.NewObject("Запрос")
    count.Текст = (
        "ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК N ИЗ РегистрСведений.КэшВмКратко КАК К "
        "ГДЕ К.Вместилище = &Вместилище"
    )
    count.УстановитьПараметр("Вместилище", container)
    selection = count.Выполнить().Выбрать()
    selection.Следующий()
    lines.append("rows\t%s" % selection.N)
    lines.append("measures")
    lines.extend(shape.measures(conn))
    lines.append("zones")
    lines.extend(shape.zones(conn, container))
    path = os.path.join(ROOT, "Тестирование", "reports", "fo_volume_%s.txt" % label)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    shape.pack.safe_print("VOLUME DONE %s rows %s" % (label, selection.N))


if __name__ == "__main__":
    main()
