#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read calculated field expressions and compatibility mode."""

import pythoncom
import win32com.client
import traceback

OUT = r"c:\1c\Cursor_1c\WIM_DEV\drafts\bp-account-analysis\Скрипты\probe_expr.txt"


def main():
    lines = []
    pythoncom.CoInitialize()
    try:
        com = win32com.client.Dispatch("V83.COMConnector")
        conn = com.Connect("File='C:\\1c\\БП_ДЕМО';Usr='Admin';App='PyCOM';Locale=ru_RU;")
        md = conn.Metadata
        try:
            lines.append("compat=" + str(conn.XMLString(md.CompatibilityMode)))
        except Exception as e:
            lines.append("compat err " + str(e)[:400])
        mgr = getattr(getattr(conn, "Отчеты"), "АнализСчета")
        schema = mgr.ПолучитьМакет("СхемаКомпоновкиДанных")
        fields = schema.ВычисляемыеПоля
        for i in range(fields.Count()):
            f = fields.Get(i)
            path = str(f.ПутьКДанным)
            if "Количество" in path:
                lines.append("CALC " + path)
                lines.append("  expr=" + str(f.Выражение))
                lines.append("  title=" + str(f.Заголовок))
                lines.append("  type=" + str(f.ТипЗначения))
        main_schema = mgr.ПолучитьМакет("ОсновнаяСхемаКомпоновкиДанных")
        lines.append("main field templates=" + str(main_schema.МакетыПолей.Count()))
        lines.append("data field templates=" + str(schema.МакетыПолей.Count()))
        lines.append("main layouts=" + str(main_schema.Макеты.Count()))
        lines.append("data layouts=" + str(schema.Макеты.Count()))
    except Exception:
        lines.append(traceback.format_exc())
    finally:
        pythoncom.CoUninitialize()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
