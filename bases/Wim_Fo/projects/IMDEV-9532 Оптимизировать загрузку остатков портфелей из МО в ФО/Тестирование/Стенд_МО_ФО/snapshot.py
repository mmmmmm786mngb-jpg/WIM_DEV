# -*- coding: utf-8 -*-
"""Снимок данных ФО по тестовым портфелям для сверки прогонов "без расширения" и "с расширением".

Снимаются все записи регистров, которые пишет загрузка остатков и перерасчет РСА, по портфелям с префиксом
PREFIX. Каждая запись превращается в строку "поле=значение; ..." (ссылки - уникальным идентификатором),
записи сортируются, поэтому снимки двух прогонов сравниваются построчно.
Отметки времени прогона (дата с ненулевым временем) и поля из VOLATILE заменяются маркером: они
законно различаются между прогонами.

Запуск отдельно: python snapshot.py <файл.json>            - снять снимок
                 python snapshot.py --compare <a.json> <b.json> - сравнить два снимка
"""
import json
import re
import sys

from stand_common import PREFIX, connect

# Регистр -> поле с портфелем.
REGISTERS = {
    "ДополнительныеСведения": "Объект",
    "ФактическаяПозиция": "Портфель",
    "РегистрРСА_СЧА": "Портфель",
    "ДатаАктуальностиФактическойПозиции": "Портфель",
}
# Поля, значения которых различаются между прогонами по построению (идентификаторы сеанса и т.п.).
VOLATILE = {"ИдентификаторСеанса", "ИдентификаторСеансаОбмена"}
RUN_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T(?!00:00:00)\d{2}:\d{2}:\d{2}$")


def _value(conn, value):
    if value is None:
        return "Неопределено"
    if isinstance(value, bool):
        return "Истина" if value else "Ложь"
    if isinstance(value, (int, float)):
        return repr(round(float(value), 6))
    if isinstance(value, str):
        return value
    try:
        text = conn.XMLСтрока(value)
    except Exception:  # noqa: BLE001 - тип без XML-представления
        text = conn.String(value)
    return "<время прогона>" if RUN_TIME.match(text) else text


def take(conn):
    """Снимок: {регистр: [строки записей по возрастанию]}; свойство доп. сведений - по наименованию."""
    result = {}
    for register, field in REGISTERS.items():
        if conn.Метаданные.РегистрыСведений.Найти(register) is None:
            continue
        q = conn.NewObject("Запрос")
        q.Текст = (f"ВЫБРАТЬ * ИЗ РегистрСведений.{register} КАК Р "
                   f"ГДЕ ВЫРАЗИТЬ(Р.{field} КАК Справочник.Портфели).ВнешнийКод ПОДОБНО &Маска")
        q.УстановитьПараметр("Маска", PREFIX + "%")
        table = q.Выполнить().Выгрузить()
        columns = [table.Колонки.Получить(i).Имя for i in range(table.Колонки.Количество())]
        rows = []
        for i in range(table.Количество()):
            row = table.Получить(i)
            parts = []
            for j, column in enumerate(columns):
                value = "<переменное>" if column in VOLATILE else _value(conn, row.Получить(j))
                if register == "ДополнительныеСведения" and column == "Свойство":
                    value = conn.String(row.Получить(j))
                parts.append(f"{column}={value}")
            rows.append("; ".join(parts))
        result[register] = sorted(rows)
    return result


def compare(a, b, limit=20):
    """Возвращает список расхождений (строки есть только в одном снимке) по каждому регистру."""
    diffs = []
    for register in sorted(set(a) | set(b)):
        left, right = set(a.get(register, [])), set(b.get(register, []))
        only_a, only_b = sorted(left - right), sorted(right - left)
        if only_a or only_b:
            diffs.append({"регистр": register, "только_в_первом": len(only_a), "только_во_втором": len(only_b),
                          "примеры_первый": only_a[:limit], "примеры_второй": only_b[:limit]})
    return diffs


def summary(snapshot):
    return {register: len(rows) for register, rows in snapshot.items()}


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "--compare":
        with open(sys.argv[2], encoding="utf-8") as f:
            a = json.load(f)
        with open(sys.argv[3], encoding="utf-8") as f:
            b = json.load(f)
        print("Первый:", summary(a))
        print("Второй:", summary(b))
        diffs = compare(a, b)
        print("Расхождений по регистрам:", len(diffs))
        for d in diffs:
            print(json.dumps(d, ensure_ascii=False, indent=2))
        return
    conn = connect("wim_fo")
    snap = take(conn)
    with open(sys.argv[1], "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    print(summary(snap))


if __name__ == "__main__":
    main()
