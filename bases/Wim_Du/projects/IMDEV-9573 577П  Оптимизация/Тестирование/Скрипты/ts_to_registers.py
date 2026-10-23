# -*- coding: utf-8 -*-
"""Стенд ДУ 1.5.30.6: переложить строки табличных частей разделов 3, 4, 5, 6, 7, 9 документа 577-П
в регистры сведений Отчет577П_РазделN, чтобы проверить выгрузку CSV из регистров на тех же данных.

python ts_to_registers.py <номер> fill    - записать (по документу и дню, порциями)
python ts_to_registers.py <номер> clear   - удалить записи документа из шести регистров

ПорядковыйНомер = НомерСтроки табличной части. Для регистров с измерением Дата строки раскладываются
по дням периода документа в порядке номера строки (дата не убывает с номером), как при заполнении
по дням. Тестовые данные стенда, не для поставки.
"""
import os
import sys
import time

import stand

SECTIONS = [3, 4, 5, 6, 7, 9]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    number, mode = sys.argv[1], sys.argv[2]
    conn = stand.connect()
    ref = stand.doc_by_number(conn, number)
    start = ref.НачалоПериода
    days = (stand.query(conn, f"ВЫБРАТЬ РАЗНОСТЬДАТ(Д.НачалоПериода, Д.КонецПериода, ДЕНЬ) + 1 КАК Дней "
                              f"ИЗ Документ.{stand.DOC} КАК Д ГДЕ Д.Ссылка = &С", С=ref).Получить(0).Дней)
    for n in SECTIONS:
        reg_name = f"Отчет577П_Раздел{n}"
        manager = getattr(conn.РегистрыСведений, reg_name)
        clear = manager.СоздатьНаборЗаписей()
        clear.Отбор.Отчет.Установить(ref)
        clear.Записать()
        if mode != "fill":
            print(reg_name, "очищен")
            continue
        total = int(stand.query(conn, f"ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК К ИЗ Документ.{stand.DOC}.Раздел{n} КАК Т ГДЕ Т.Ссылка = &С",
                                С=ref).Получить(0).К)
        has_date = conn.Метаданные.РегистрыСведений.Найти(reg_name).Измерения.Найти("Дата") is not None
        per_day = max(1, -(-total // int(days)))
        t0 = time.time()
        written = 0
        if has_date:
            portions = [(d, d * per_day + 1, (d + 1) * per_day) for d in range(int(days)) if d * per_day < total]
        else:
            portions = [(None, s, s + 99999) for s in range(1, total + 1, 100000)]
        for day, first, last in portions:
            text = (f"ВЫБРАТЬ Т.*, Т.Ссылка КАК Отчет, Т.НомерСтроки КАК ПорядковыйНомер, "
                    f"ДОБАВИТЬКДАТЕ(&Начало, ДЕНЬ, &День) КАК Дата "
                    f"ИЗ Документ.{stand.DOC}.Раздел{n} КАК Т "
                    f"ГДЕ Т.Ссылка = &С И Т.НомерСтроки МЕЖДУ &От И &До УПОРЯДОЧИТЬ ПО Т.НомерСтроки")
            table = stand.query(conn, text, С=ref, Начало=start, День=day or 0, От=first, До=last)
            records = manager.СоздатьНаборЗаписей()
            records.Отбор.Отчет.Установить(ref)
            if has_date:
                records.Отбор.Дата.Установить(table.Получить(0).Дата)
            records.Загрузить(table)
            records.Записать(has_date)  # без Даты - одна порция на раздел до 100 тыс. строк
            written += table.Количество()
        print(f"{reg_name}: строк {written} из {total}, порций {len(portions)}, {time.time() - t0:.1f} s")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR", exc)
    sys.stdout.flush()
    os._exit(0)
