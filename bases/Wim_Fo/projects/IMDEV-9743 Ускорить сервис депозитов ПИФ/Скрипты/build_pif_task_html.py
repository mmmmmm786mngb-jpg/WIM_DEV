# -*- coding: utf-8 -*-
"""Собирает постановку задачи по сервису депозитов ПИФ (Документация/Сервис депозитов ПИФ - постановка задачи.html).

Приложение БЫЛО/СТАЛО строится из исходников: функция ТаблицаДепозитов модуля веб-сервиса deposits конфигурации ПИФ
и перехватчик расширения ПИФ_ДепозитыОдноЧтение. Запуск: python build_pif_task_html.py
"""
import difflib
import html
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
CONFIG_MODULE = r"C:\1c\Cursor_1c\WORK\Wim_PIF\SRC\cf\WebServices\deposits\Ext\Module.bsl"
EXT_MODULE = os.path.join(PROJECT, "Расширения", "ПИФ_ДепозитыОдноЧтение", "WebServices", "deposits", "Ext", "Module.bsl")
OUT = os.path.join(PROJECT, "Документация", "Сервис депозитов ПИФ - постановка задачи.html")

FONT = "font-family:Calibri,'Segoe UI',Arial,sans-serif;font-size:11pt;"
H1 = "margin:0 0 4px 0;font-size:16pt;font-weight:bold;color:#1f3864;"
H2 = "margin:20px 0 6px 0;font-size:13pt;font-weight:bold;color:#1f3864;"
P = "margin:0 0 8px 0;"
TH = "border:1px solid #c9c9c9;background:#d9e2f3;padding:5px 9px;font-weight:bold;vertical-align:top;"
TD = "border:1px solid #c9c9c9;padding:5px 9px;vertical-align:top;"
TDR = TD + "text-align:right;white-space:nowrap;"
CODE = ("font-family:Consolas,'Courier New',monospace;font-size:8.5pt;white-space:pre-wrap;overflow-wrap:anywhere;padding:1px 6px;"
        "border-right:1px solid #c9c9c9;vertical-align:top;")
DEL = "background:#fde2e2;color:#9c0006;"
INS = "background:#e2f0d9;color:#375623;"
SAME = "background:#ffffff;color:#1f1f1f;"
EMPTY = "background:#f2f2f2;"


def read_lines(path):
    return open(path, encoding="utf-8-sig").read().replace("\r\n", "\n").split("\n")


def query_text(line):
    """Строка текста запроса без отступа модуля и символа продолжения строки."""
    stripped = line.lstrip("\t ")
    return stripped[1:] if stripped.startswith("|") else stripped


def fragments():
    original = read_lines(CONFIG_MODULE)
    extension = read_lines(EXT_MODULE)
    start = extension.index("#Вставка") + 1
    inserted = extension[start:extension.index("#КонецВставки")]
    # Строки 136-188 модуля конфигурации заменяются вставкой, строки 189-193 (хвост части ПервоначальныеСуммы) общие.
    before = [query_text(line) for line in original[135:193]]
    after = [query_text(line) for line in inserted + original[188:193]]
    return before, after


def diff_rows(before, after):
    rows = []
    matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            rows += [(before[i], SAME, after[j1 + k], SAME) for k, i in enumerate(range(i1, i2))]
            continue
        left = before[i1:i2] if tag in ("delete", "replace") else []
        right = after[j1:j2] if tag in ("insert", "replace") else []
        for k in range(max(len(left), len(right))):
            rows.append((left[k] if k < len(left) else None, DEL,
                         right[k] if k < len(right) else None, INS))
    return rows


def code_cell(text, style):
    if text is None:
        return '<td style="%s%s">&nbsp;</td>' % (CODE, EMPTY)
    return '<td style="%s%s">%s</td>' % (CODE, style, html.escape(text.replace("\t", "    ")) or "&nbsp;")


def table(header, rows, right_columns=()):
    out = ['<table cellpadding="0" cellspacing="0" style="border-collapse:collapse;width:100%%;margin:0 0 12px 0;%s">'
           % FONT, "<tr>" + "".join('<td style="%s">%s</td>' % (TH, h) for h in header) + "</tr>"]
    for row in rows:
        cells = []
        for index, value in enumerate(row):
            cells.append('<td style="%s">%s</td>' % (TDR if index in right_columns else TD, value))
        out.append("<tr>" + "".join(cells) + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def ul(items):
    return ('<ul style="margin:0 0 10px 0;padding-left:22px;">'
            + "".join('<li style="margin:0 0 5px 0;">%s</li>' % item for item in items) + "</ul>")


def build():
    before, after = fragments()
    rows = diff_rows(before, after)
    parts = []
    add = parts.append

    add('<p style="%s">Постановка задачи: ускорение веб-сервиса deposits (getDeposits) базы Аванкор ПИФ</p>' % H1)
    add('<p style="margin:0 0 14px 0;color:#595959;">От: аналитик. Кому: разработка; для передачи вендору Аванкор '
        'с целью внесения изменения в базовую конфигурацию. Дата: 28.10.2026. Объект: веб-сервис deposits, '
        'операция getDeposits, функция ТаблицаДепозитов модуля веб-сервиса. Конфигурация ПаевыеФонды 2.12.9.5.</p>')

    add('<p style="%s">1. Причина</p>' % H2)
    add('<p style="%s">Загрузка депозитов во Фронт-офисе запускается каждый день в 05:00 и ждет ответ ПИФ. '
        'При вызове из Фронт-офиса getDeposits отвечает 685-692 секунды (72 депозита), обработка на стороне '
        'Фронт-офиса занимает секунды. Сервис вызывают две базы Фронт-офиса одновременно, поэтому ПИФ выполняет '
        'запрос дважды.</p>' % P)

    add('<p style="%s">2. Где уходит время</p>' % H2)
    add('<p style="%s">Функция ТаблицаДепозитов выполняет пакет из шести запросов к регистру бухгалтерии '
        'Управленческий. Пакет выполнен по частям с общим менеджером временных таблиц на копии ПРОД 28.10.2026 '
        '(67 действующих депозитных счетов, 115 млн проводок регистра). Время внутри сервера:</p>' % P)
    add(table(["Часть пакета", "Что читает", "Прогон 1, с", "Прогон 2, с"], [
        ["1. ОстаткиДепозитов", "Остатки счетов 51, 52, 55 по депозитным счетам", "2,0", "5,2"],
        ["2. ПроцентыПоДепозитам", "Обороты 76.20.2 в корреспонденции с 91.01.2 и 000 за всю историю", "6,5", "19,1"],
        ["3. ПроцентыЗаДень", "Те же обороты за день запроса", "0,1", "0,3"],
        ["<b>4. ДатыВыдачи</b>", "<b>ДвиженияССубконто за всю историю: минимальный период дебета по счету</b>",
         "<b>162,4</b>", "<b>225,2</b>"],
        ["<b>5. ПервоначальныеСуммы</b>",
         "<b>ДвиженияССубконто за всю историю повторно: сумма дебета найденного периода</b>",
         "<b>283,1</b>", "<b>189,1</b>"],
        ["6. Итог и сборка ответа", "Соединение частей, срез АлгоритмыРасчетаПроцентов", "0,1", "0,1"],
        ["<b>Всего</b>", "", "<b>454,2</b>", "<b>439,1</b>"],
    ], right_columns=(2, 3)))
    add('<p style="%s">Части 4 и 5 занимают 94-98%% времени. Обе обращаются к одной и той же виртуальной таблице '
        'ДвиженияССубконто с одинаковым отбором: первая ради минимального периода, вторая ради суммы проводки '
        'этого периода. ДвиженияССубконто раскрывает каждую проводку регистра по субконто, поэтому каждое '
        'обращение стоит 2,5-4,5 минуты.</p>' % P)

    add('<p style="%s">3. Решение</p>' % H2)
    add('<p style="%s">Читать ДвиженияССубконто один раз: поместить движения выдачи (счет, валюта, период, сумма) '
        'во временную таблицу ДвиженияВыдачи, минимальный период и сумму проводки этого периода считать по ней. '
        'Отбор виртуальной таблицы, способ выбора суммы (валютная сумма для валютного счета, иначе сумма), '
        'сравнение валют через наименование, имена временных таблиц ДатыВыдачи и ПервоначальныеСуммы и поле '
        'initialvalue не меняются. Части 1-3, итоговый запрос, цикл формирования ответа и операция getDeposits '
        'не меняются. Код БЫЛО и СТАЛО - в приложении.</p>' % P)

    add('<p style="%s">4. Замеры решения</p>' % H2)
    add(table(["Среда", "Было", "Стало", "Сверка ответа"], [
        ["Копия ПРОД, чтение движений выдачи",
         "445 с (два чтения: 162 + 283)", "229 с (одно чтение)",
         "ДатыВыдачи 67 из 67 и ПервоначальныеСуммы 72 из 72 строк совпали"],
        ["Копия ПРОД, весь пакет (оценка)", "454 с", "около 240 с", "-"],
        ["Разработческая база, вызов getDeposits по SOAP (3 вызова)",
         "0,64 с", "0,39-0,46 с", "16 из 16 строк совпали по всем полям ответа"],
    ]))
    add('<p style="%s">На копии ПРОД время чтения движений сокращается почти вдвое. Ожидаемое время ответа '
        'getDeposits при вызове из Фронт-офиса - около 4 минут вместо 11,5.</p>' % P)

    add('<p style="%s">5. Проверенные и отклоненные варианты</p>' % H2)
    add(table(["Вариант", "Результат проверки", "Решение"], [
        ["Начало периода у ДвиженияССубконто и оборотов процентов по самой ранней дате открытия действующих "
         "депозитов (24.03.2022)",
         "Выигрыша нет: подсчет движений выдачи без начала периода 135 с, с началом 148 с. На 2022-2026 годы "
         "приходится 77% проводок регистра", "Не делать"],
        ["Соединение временных таблиц по ссылке на валюту, отбор среза АлгоритмыРасчетаПроцентов по счетам",
         "Ответ не меняется, выигрыш доли секунды", "Не делать: лишние строки правки"],
        ["Начальная сумма из реквизита НоминалДепозита банковского счета",
         "Совпадает у 63 из 67 счетов, у 4 счетов номинал не заполнен", "Не делать: источник суммы не меняется"],
        ["Кэш ответа на дату", "Обе базы Фронт-офиса вызывают сервис одновременно, второй вызов кэш не застает",
         "Не делать"],
        ["marketvalue по остатку счета 76.20.2 вместо оборотов", "Сейчас совпадает у всех 72 строк; часть 2 "
         "занимает 6-19 с", "Не делать: меняется смысл поля"],
    ]))

    add('<p style="%s">6. Реализация и передача вендору</p>' % H2)
    add(ul([
        "Расширение <b>ПИФ_ДепозитыОдноЧтение</b> версии 1.0.0.1 (файл ПИФ_ДепозитыОдноЧтение.cfe): назначение "
        "Исправление, режим совместимости 8.3.12, основной режим запуска Обычное приложение. Заимствован только "
        "веб-сервис deposits, новых объектов и ролей нет.",
        "В модуле веб-сервиса один перехватчик <b>&amp;ИзменениеИКонтроль(\"ТаблицаДепозитов\")</b>: тело функции "
        "повторяет конфигурацию, изменение размечено блоками #Удаление и #Вставка внутри текста запроса. "
        "Если вендор изменит функцию ТаблицаДепозитов, платформа сообщит, что расширение не применяется, и "
        "старая логика не будет работать незаметно.",
        "При подключении снять флажок Безопасный режим (проверено в этом режиме).",
        "Для внесения в базовую конфигурацию: в функции ТаблицаДепозитов модуля веб-сервиса deposits заменить "
        "часть ДатыВыдачи и начало части ПервоначальныеСуммы текстом из правой колонки приложения. После "
        "установки версии конфигурации с этим изменением расширение удалить.",
    ]))

    add('<p style="%s">7. Приемка</p>' % H2)
    add(ul([
        "На одну дату ответ getDeposits до и после изменения совпадает построчно по всем полям: id, source, name, "
        "marketvalue, day_interest, initialvalue, currentvalue, currency, datestart, datematurity, interest.",
        "Число строк ответа не меняется (на копии ПРОД 28.10.2026 - 72).",
        "Время ответа на копии ПРОД при вызове из Фронт-офиса - не более 5 минут.",
    ]))

    add('<p style="%s">8. Вне этой задачи</p>' % H2)
    add(ul([
        "Задвоение депозита: у одного счета в момент первой выдачи 6 проводок с одинаковым периодом, поэтому "
        "сервис отдает 72 строки на 67 счетов. Изменение сохраняет текущее поведение; исправление требует "
        "решения, какая сумма считается начальной, и выполняется отдельной задачей.",
        "Цель в 1 минуту этим изменением не достигается. Следующий шаг - хранить вычисленную начальную сумму "
        "по счету и читать движения только по новым счетам; требует отдельного замера на копии ПРОД.",
        "Загрузку депозитов в ФО Розница проверить на необходимость: при ее отключении ПИФ в 05:00 выполняет "
        "один запрос вместо двух.",
    ]))

    add('<p style="%s">Приложение. Код БЫЛО и СТАЛО</p>' % H2)
    add('<p style="%s">Фрагмент текста запроса функции ТаблицаДепозитов между частью ПроцентыЗаДень и итоговым '
        'ВЫБРАТЬ. <span style="%spadding:0 4px;">Красным</span> - удаляемые строки, '
        '<span style="%spadding:0 4px;">зеленым</span> - добавляемые, без выделения - строки без изменений. '
        'Остальной текст функции не меняется.</p>' % (P, DEL, INS))
    out = ['<table cellpadding="0" cellspacing="0" style="border-collapse:collapse;width:100%;'
           'border:1px solid #c9c9c9;margin:0 0 12px 0;table-layout:fixed;">',
           '<tr><td style="%swidth:50%%;">БЫЛО (конфигурация)</td><td style="%swidth:50%%;">СТАЛО (расширение)</td></tr>'
           % (TH, TH)]
    for left, left_style, right, right_style in rows:
        out.append("<tr>%s%s</tr>" % (code_cell(left, left_style), code_cell(right, right_style)))
    out.append("</table>")
    add("\n".join(out))

    page = ('<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
            '<title>Сервис депозитов ПИФ - постановка задачи</title>\n</head>\n'
            '<body style="margin:0;padding:24px;background:#ffffff;">\n'
            '<div style="max-width:1200px;%sline-height:1.45;color:#1f1f1f;">\n%s\n</div>\n</body>\n</html>\n'
            % (FONT, "\n\n".join(parts)))
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(page)
    changed = sum(1 for r in rows if r[1] == DEL and r[0] is not None)
    added = sum(1 for r in rows if r[3] == INS and r[2] is not None)
    print("строк приложения %d, удалено %d, добавлено %d, файл %s" % (len(rows), changed, added, OUT))


if __name__ == "__main__":
    build()
