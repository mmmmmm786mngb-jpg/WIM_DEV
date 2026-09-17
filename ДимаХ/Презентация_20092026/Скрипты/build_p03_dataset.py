#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Датасет презентации 03: vibe-coding под дедлайн регулятора (кейс IMDEV-9182).

Это не портфель задач и не экономия часов (это презентации 01 и 02).
Здесь один оперативный кейс: увидеть XBRL в Excel до сдачи пакета в Банк России.
"""

import json
import os
import re
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(SCRIPTS)
OUT = os.path.join(SCRIPTS, "p03_dataset.json")

TZ = os.path.join(
    r"C:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects",
    "IMDEV-9182 Конвертация XBRL в Excel",
    "Документация",
    "tz_xbrl_orticon_to_excel.html",
)
BSL = os.path.join(
    r"C:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects",
    "IMDEV-9182 Конвертация XBRL в Excel",
    "внВыгрузкаXBRLОртиконВXLSX",
    "Ext",
    "ObjectModule.bsl",
)


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def parse_volume():
    sheets = []
    if os.path.isfile(TZ):
        text = open(TZ, "r", encoding="utf-8").read()
        part = text.split("Полный перечень листов")[-1]
        for form, name, rows in re.findall(
            r'<td class="col-num">\d+</td><td><code>([^<]+)</code></td>'
            r"<td>([^<]+)</td><td>[^<]+</td>"
            r'<td class="num">(\d+)</td></tr>',
            part,
        ):
            sheets.append({
                "form": form.strip(),
                "sheet": name.strip(),
                "rows": int(rows),
            })
    by_form = {}
    for s in sheets:
        agg = by_form.setdefault(s["form"], {"form": s["form"], "sheets": 0, "rows": 0})
        agg["sheets"] += 1
        agg["rows"] += s["rows"]
    forms = sorted(by_form.values(), key=lambda x: -x["rows"])
    total_rows = sum(s["rows"] for s in sheets)
    max_sheet = max(sheets, key=lambda s: s["rows"]) if sheets else {"rows": 114086, "form": "0420431"}
    return {
        "package_mb_stated": 500,
        "sheets_data": 77,
        "sheets_total": 78,
        "tables": 77,
        "form_431_sheets": 26,
        "rows_total": total_rows,
        "max_rows_one_sheet": max_sheet["rows"],
        "max_rows_form": max_sheet.get("form", "0420431"),
        "nonzero_sheets": sum(1 for s in sheets if s["rows"] > 0),
        "by_form": forms,
    }


def bsl_lines():
    if os.path.isfile(BSL):
        with open(BSL, "r", encoding="utf-8") as fh:
            return sum(1 for _ in fh)
    return 5332


def main():
    volume = parse_volume()
    lines = bsl_lines()

    payload = {
        "summary": {
            "key": "IMDEV-9182",
            "title": "Конвертация XBRL ОРТИКОН в Excel (таксономия 7.1)",
            "effect": "Снижение регуляторного риска / дедлайн",
            "created": "2026-07-17",
            "resolved": "2026-08-12",
            "hours": 14.0,
            "hours_source": "timesheet",
            "reporter": "Karaseva, Olga",
            "assignee": "Chmykhalov, Aleksey",
            "department": "IM Back-Office Settle",
            "component": "ДУ",
            "labels": ["CAB", "XBRL"],
            "version": "1.4.10",
            "bsl_lines": lines,
            "taxonomy": "7.1",
        },
        "window": {
            "working_days": 10,
            "entry_point": "ep_nso_purcb_*_10rd",
            "rule": "НСО ПУРЦБ: отчётность в Банк России в течение 10 рабочих дней после отчетной даты",
            "report_date": "2026-07-31",
            "report_label": "июль 2026",
            "deadline": "2026-08-14",
            "days": [
                {"date": "2026-08-03", "n": 1, "label": "3 авг"},
                {"date": "2026-08-04", "n": 2, "label": "4 авг"},
                {"date": "2026-08-05", "n": 3, "label": "5 авг"},
                {"date": "2026-08-06", "n": 4, "label": "6 авг"},
                {"date": "2026-08-07", "n": 5, "label": "7 авг"},
                {"date": "2026-08-10", "n": 6, "label": "10 авг"},
                {"date": "2026-08-11", "n": 7, "label": "11 авг"},
                {"date": "2026-08-12", "n": 8, "label": "12 авг", "event": "задача закрыта"},
                {"date": "2026-08-13", "n": 9, "label": "13 авг"},
                {"date": "2026-08-14", "n": 10, "label": "14 авг", "event": "дедлайн ЦБ"},
            ],
            "closed_day": 8,
            "days_before_deadline": 2,
            "jira_after_june": True,
            "june_deadline": "2026-07-14",
        },
        "volume": volume,
        "paths": [
            {
                "id": "portal",
                "name": "Портал Аванкор XBRL",
                "time": "> 8 ч",
                "hours": 8.0,
                "fits": False,
                "note": "загрузка и проверка пакета. Как инструмент визуализации непригоден.",
            },
            {
                "id": "converter",
                "name": "Внешний XBRL-конвертер",
                "time": "> 1 ч",
                "hours": 1.0,
                "fits": False,
                "note": "только частями, возможны сбои. Чужое ПО, доработать нельзя.",
            },
            {
                "id": "vendor",
                "name": "Классическая разработка / вендор",
                "time": "недели",
                "hours": 80.0,
                "fits": False,
                "note": "парсер таксономии 7.1 и 77 таблиц не помещается в окно 10 дней.",
            },
            {
                "id": "vibe",
                "name": "Vibe-coding, обработка 1С",
                "time": "4 мин",
                "hours": 0.07,
                "fits": True,
                "note": "весь пакет одним запуском. Эталон июня 2026: 4 мин 3 с (v1.4.10, режим таксономии).",
            },
        ],
        "conversion": {
            "june_label": "4 мин",
            "june_exact": "4 мин 3 с",
            "june_file": "эталон июня 2026, обработка v1.4.10, режим таксономии",
            "january_label": "29 с",
            "january_note": "меньший пакет (январь)",
            "vs_converter": ">1 ч частями",
            "vs_portal": ">8 ч",
        },
        "quotes": [
            {
                "tag": "Зачем",
                "text": "Для нас это абсолютно необходимый инструмент, позволяющий оценить качество и правильность данных в форме.",
            },
            {
                "tag": "Проблема",
                "text": "Пакет уже ~500 МБ. Конвертер выгружает только частями: больше часа, возможны сбои. Портал Аванкор — свыше 8 часов.",
            },
            {
                "tag": "Просьба",
                "text": "Предложите решение, которое позволит выгружать форму в Excel в полном объеме, за вменяемое время и без сбоев.",
            },
        ],
        "quote": (
            "Для нас это абсолютно необходимый инструмент, позволяющий оценить "
            "качество и правильность данных в форме."
        ),
        "quote_who": "Karaseva, Olga / IM Back-Office Settle, постановка IMDEV-9182, приоритет High",
        "acceptance": {
            "reporter": "Karaseva, Olga",
            "department": "IM Back-Office Settle",
            "priority": "High",
            "status": "Closed",
            "resolution": "Done",
            "resolved": "2026-08-12",
            "updated": "2026-08-19",
            "has_comment_text": False,
            "note": "Постановщик заявки — Карасева. Задача закрыта с резолюцией Done 12.08.2026. "
                    "В выгрузке Jira нет отдельного комментария приёмки; зафиксированы статус Closed, "
                    "резолюция Done и приоритет High.",
        },
        "risk": {
            "article": "ст. 19.7.3 КоАП РФ",
            "article_title": "Непредставление информации в Банк России",
            "legal_min": 500000,
            "legal_max": 700000,
            "officer_min": 20000,
            "officer_max": 30000,
            "disqualification": "до 1 года",
            "also": [
                "технический контроль и отклонение пакета XBRL",
                "повторная сдача в том же 10-дневном окне",
                "надзорный и репутационный след",
            ],
        },
        "sources": [
            {
                "who": "Постановка IMDEV-9182, Karaseva Olga, 17.07.2026, приоритет High",
                "what": "Пакеты ~500 МБ; конвертер >1 ч частями и сбои; портал Аванкор >8 ч; "
                        "нужна выгрузка 431-й (и далее всего пакета) в Excel без сбоев.",
            },
            {
                "who": "Jira IMDEV-9182, выгрузка 17.09.2026",
                "what": "Reporter Karaseva Olga; Status Closed; Resolution Done 12.08.2026; "
                        "Updated 19.08.2026. Текста комментария приёмки в выгрузке нет — "
                        "зафиксированы постановщик, приоритет High и закрытие с резолюцией Done.",
            },
            {
                "who": "Эталон конвертации июня 2026, обработка v1.4.10, режим таксономии",
                "what": "Полный пакет в Excel за 4 мин 3 с (замер в имени эталона). "
                        "Меньший январский пакет — 29 с. Критерий ТЗ: минуты / десятки минут, не часы.",
            },
            {
                "who": "Банк России, точки входа НСО ПУРЦБ",
                "what": "ep_nso_purcb_*_10rd: отчетность в течение 10 рабочих дней после отчетной даты.",
            },
            {
                "who": "ст. 19.7.3 КоАП РФ",
                "what": "Непредставление / просрочка / недостоверность информации в Банк России: "
                        "юрлицо 500-700 тыс. руб.; должностное лицо 20-30 тыс. или дисквалификация до года.",
            },
            {
                "who": "McKinsey, corporate and investment banks / gen AI",
                "what": "Code assistants сжимают time-to-market релизов (в опыте McKinsey - до половины). "
                        "Gen AI закрывает time-consuming задачи reporting и compliance, не заменяя контроль.",
            },
            {
                "who": "McKinsey / Merck, regulatory submissions",
                "what": "Тот же класс эффекта: gen AI сжимает цикл регуляторной сдачи, где цена опоздания "
                        "не в часах разработки, а в срыве окна.",
            },
        ],
    }

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    safe_print("OK dataset written")
    safe_print("rows_total=%s max_sheet=%s bsl=%s" % (
        volume.get("rows_total"), volume.get("max_rows_one_sheet"), lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
