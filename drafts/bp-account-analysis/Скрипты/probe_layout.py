#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dump account analysis spreadsheet grid and schema template kinds."""

import pythoncom
import win32com.client

OUT = r"c:\1c\Cursor_1c\WIM_DEV\drafts\bp-account-analysis\Скрипты\layout_probe.txt"
MXL = r"c:\1c\Cursor_1c\WIM_DEV\drafts\bp-account-analysis\Тестирование\account_analysis_41_01.mxl"


def main():
    lines = []
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("File='C:\\1c\\БП_ДЕМО';Usr='Admin';App='PyCOM';Locale=ru_RU;")
        doc = conn.NewObject("ТабличныйДокумент")
        doc.Прочитать(MXL)
        height = int(doc.ВысотаТаблицы)
        width = int(doc.ШиринаТаблицы)
        lines.append("size %s x %s" % (height, width))
        last = height if height < 45 else 45
        for row_index in range(1, last + 1):
            cells = []
            for col_index in range(1, width + 1):
                area = doc.Область(row_index, col_index, row_index, col_index)
                text = str(area.Текст).replace("\n", " ").strip()
                cells.append(text if text else ".")
            lines.append("r%02d %s" % (row_index, " | ".join(cells)))

        reports = getattr(conn, "Отчеты")
        manager = getattr(reports, "АнализСчета")
        schema = manager.ПолучитьМакет("СхемаКомпоновкиДанных")
        templates = schema.Макеты
        lines.append("templates %s" % templates.Количество())
        index = 0
        while index < templates.Количество() and index < 30:
            item = templates.Получить(index)
            lines.append("tpl %s type=%s" % (item.Имя, type(item.Макет).__name__ if False else ""))
            try:
                lines.append("  name=%s" % item.Имя)
            except Exception as error:
                lines.append("  err " + str(error)[:200])
            index += 1
    except Exception as error:
        lines.append(str(error))
    finally:
        pythoncom.CoUninitialize()
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


if __name__ == "__main__":
    main()
