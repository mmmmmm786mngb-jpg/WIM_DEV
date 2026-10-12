# -*- coding: utf-8 -*-
"""Что выводит ПостроительОтчета прежней выгрузки CSV до удаления строк 1-3 и колонки 1.

python probe_builder.py <номер> <раздел>
"""
import os
import sys

import stand


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    conn = stand.connect()
    ref = stand.doc_by_number(conn, sys.argv[1])
    section = sys.argv[2]
    td = conn.NewObject("ТабличныйДокумент")
    b = conn.NewObject("ПостроительОтчета")
    b.ИсточникДанных = conn.NewObject("ОписаниеИсточникаДанных", getattr(ref, section))
    b.ВыводитьПодвалТаблицы = False
    b.ВыбранныеПоля.Очистить()
    for name in ("НомерСтроки", "ДоговорДУ", "НомерСчета" if section == "Раздел8" else "НомерСтроки"):
        pass
    fields = ["НомерСтроки"]
    meta = conn.Метаданные.Документы.Найти(stand.DOC).ТабличныеЧасти.Найти(section).Реквизиты
    for i in range(2):
        fields.append(meta.Получить(i + 1).Имя)
    for f in fields:
        b.ВыбранныеПоля.Добавить(f, f)
    b.ВыбранныеПоля.Добавить("НомерСтроки", "uuid").Представление = "uuid"
    b.Вывести(td)
    print("высота", td.ВысотаТаблицы, "ширина", td.ШиринаТаблицы, "поля", fields + ["uuid"])
    for r in range(1, 7):
        cells = [td.Область(r, c, r, c).Текст for c in range(1, td.ШиринаТаблицы + 1)]
        print(r, cells)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR", exc)
    sys.stdout.flush()
    os._exit(0)
