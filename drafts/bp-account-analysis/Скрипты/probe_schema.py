#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspect account analysis schemas and sample 41.01 balances."""

import pythoncom
import win32com.client
import traceback

OUT = r"c:\1c\Cursor_1c\WIM_DEV\drafts\bp-account-analysis\Скрипты\probe_schema.txt"


def main():
    lines = []
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("File='C:\\1c\\БП_ДЕМО';Usr='Admin';App='PyCOM';Locale=ru_RU;")
        md = conn.Metadata
        lines.append("CompatibilityMode=" + str(md.CompatibilityMode))
        lines.append("Version=" + str(md.Version))

        reports = getattr(conn, "Отчеты")
        mgr = getattr(reports, "АнализСчета")
        for name in ("ОсновнаяСхемаКомпоновкиДанных", "СхемаКомпоновкиДанных"):
            schema = mgr.ПолучитьМакет(name)
            lines.append("--- template " + name + " type=" + str(type(schema)))
            try:
                sets = schema.НаборыДанных
                lines.append("datasets=" + str(sets.Count()))
                for i in range(sets.Count()):
                    ds = sets.Get(i)
                    lines.append("  ds " + str(ds.Name) + " / " + str(ds.Имя))
            except Exception as e:
                lines.append("datasets err " + str(e)[:300])
            try:
                fields = schema.ВычисляемыеПоля
                lines.append("calc=" + str(fields.Count()))
                shown = 0
                for i in range(fields.Count()):
                    f = fields.Get(i)
                    path = str(f.ПутьКДанным)
                    if "Колич" in path or "Показател" in path or "БУ" in path or "Цена" in path:
                        lines.append("  calc " + path)
                        shown += 1
                        if shown > 40:
                            break
            except Exception as e:
                lines.append("calc err " + str(e)[:300])
            try:
                totals = schema.ПоляИтога
                lines.append("totals=" + str(totals.Count()))
                shown = 0
                for i in range(totals.Count()):
                    f = totals.Get(i)
                    path = str(f.ПутьКДанным)
                    if "Колич" in path or "Сумма" in path or "БУ" in path:
                        lines.append("  total " + path + " = " + str(f.Выражение)[:180])
                        shown += 1
                        if shown > 30:
                            break
            except Exception as e:
                lines.append("totals err " + str(e)[:400])

        query = conn.NewObject("Запрос")
        query.Текст = """
ВЫБРАТЬ ПЕРВЫЕ 15
    ХозрасчетныйОстаткиИОбороты.Субконто1 КАК Номенклатура,
    ХозрасчетныйОстаткиИОбороты.КоличествоНачальныйОстаток КАК КолНач,
    ХозрасчетныйОстаткиИОбороты.СуммаНачальныйОстаток КАК СумНач,
    ХозрасчетныйОстаткиИОбороты.КоличествоОборотДт КАК КолДт,
    ХозрасчетныйОстаткиИОбороты.СуммаОборотДт КАК СумДт,
    ХозрасчетныйОстаткиИОбороты.КоличествоОборотКт КАК КолКт,
    ХозрасчетныйОстаткиИОбороты.СуммаОборотКт КАК СумКт,
    ХозрасчетныйОстаткиИОбороты.КоличествоКонечныйОстаток КАК КолКон,
    ХозрасчетныйОстаткиИОбороты.СуммаКонечныйОстаток КАК СумКон
ИЗ
    РегистрБухгалтерии.Хозрасчетный.ОстаткиИОбороты(&Начало, &Конец, , , Счет = &Счет, , Организация = &Организация) КАК ХозрасчетныйОстаткиИОбороты
"""
        query.УстановитьПараметр("Начало", conn.Date(2020, 1, 1))
        query.УстановитьПараметр("Конец", conn.CurrentDate())
        accounts = getattr(conn, "ПланыСчетов").Хозрасчетный
        query.УстановитьПараметр("Счет", accounts.НайтиПоКоду("41.01"))
        orgs = getattr(conn, "Справочники").Организации
        query.УстановитьПараметр("Организация", orgs.НайтиПоНаименованию("Конфетпром ООО", True))
        data = query.Выполнить().Выгрузить()
        lines.append("rows=" + str(data.Count()))
        for row in data:
            lines.append(
                "  " + str(row.Номенклатура)
                + " qty0=" + str(row.КолНач) + " sum0=" + str(row.СумНач)
                + " qtyDt=" + str(row.КолДт) + " sumDt=" + str(row.СумДт)
                + " qtyKt=" + str(row.КолКт) + " sumKt=" + str(row.СумКт)
                + " qty1=" + str(row.КолКон) + " sum1=" + str(row.СумКон)
            )
    except Exception:
        lines.append(traceback.format_exc())
    finally:
        pythoncom.CoUninitialize()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
