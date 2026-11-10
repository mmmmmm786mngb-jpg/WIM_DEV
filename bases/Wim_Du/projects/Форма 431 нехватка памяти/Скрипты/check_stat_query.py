# Проверка запросов обработки статистики (Статистика\src, модуль формы) выполнением в dev WIM_MO через COM:
# текст берется из модуля как есть, для обоих типов учета (фактический и плановый регистр оценки).
import os
import re
import sys
from datetime import datetime

import win32com.client

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.join(os.path.dirname(HERE), "Статистика", "src", "СтатистикаМандатов431", "Forms", "Форма", "Ext",
                      "Form", "Module.bsl")


def query_text(src, func):
    i = src.index("Функция " + func + "()")
    j = src.index("КонецФункции", i)
    body = src[i:j]
    k = body.index('"')
    lit = body[k:body.rindex('";') + 1]
    lines = []
    for line in lit.split("\n"):
        s = line.strip()
        if s.startswith('"'):
            s = s[1:]
        elif s.startswith("|"):
            s = s[1:]
        lines.append(s)
    text = "\n".join(lines)
    text = text[:-1] if text.endswith('"') else text
    return text.replace('""', '"')


def main():
    src = open(MODULE, encoding="utf-8-sig").read().replace("\r\n", "\n")
    c = win32com.client.Dispatch("V83.COMConnector").Connect('Srvr="localhost";Ref="WIM_MO";')
    q = c.NewObject("Запрос")
    q.Текст = "ВЫБРАТЬ ПЕРВЫЕ 50 РАЗЛИЧНЫЕ М.НомерДоговора КАК Номер ИЗ Справочник.Мандаты КАК М ГДЕ М.НомерДоговора <> \"\""
    s = q.Выполнить().Выбрать()
    numbers = c.NewObject("Массив")
    while s.Следующий():
        numbers.Добавить(s.Номер)
    print("номеров договоров для проверки:", numbers.Количество())
    for func in ("ТекстЗапросаСоставаИДней", "ТекстЗапросаВалют"):
        for plan in (False, True):
            text = query_text(src, func)
            if plan:
                text = text.replace("РыночнаяСтоимостьПозиции", "РыночнаяСтоимостьПлановойПозиции")
            q = c.NewObject("Запрос")
            q.Текст = text
            q.УстановитьПараметр("НомераДоговоров", numbers)
            q.УстановитьПараметр("КонецПериода", datetime(2026, 10, 31, 23, 59, 59))
            q.УстановитьПараметр("ДатаНачала", datetime(2026, 1, 1))
            q.УстановитьПараметр("ДатаОкончания", datetime(2026, 10, 31))
            try:
                t = q.Выполнить().Выгрузить()
                cols = [t.Колонки.Получить(i).Имя for i in range(t.Колонки.Количество())]
                print(f"OK {func} план={plan}: строк {t.Количество()}, колонки {cols}")
            except Exception as e:
                print(f"FAIL {func} план={plan}:", e.excepinfo[2] if getattr(e, "excepinfo", None) else e)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
