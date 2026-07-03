#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generates HH.ru TOP-pattern PDF resume for Alexey Chmykhalov.
Structure: Summary -> Metrics -> Flagship results -> Skills -> Experience (STAR) -> Education/Certs.
Output: Private/Resume HH/Chmykhalov_Alexey_Resume_2026.pdf
"""

from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR.parent
OUTPUT_FILE = OUTPUT_DIR / "Chmykhalov_Alexey_Resume_2026.pdf"

NAVY = colors.HexColor("#0F2744")
ACCENT = colors.HexColor("#C9A227")
ACCENT_SOFT = colors.HexColor("#E8D5A3")
TEXT = colors.HexColor("#1E1E1E")
TEXT_MUTED = colors.HexColor("#5A6472")
RULE = colors.HexColor("#D8DEE6")
BG_LIGHT = colors.HexColor("#F4F6F9")
BG_SKILLS = colors.HexColor("#EEF2F7")
CURSOR_BG = colors.HexColor("#E8F4FD")
CURSOR_BORDER = colors.HexColor("#1A73E8")
WHITE = colors.white

CONTENT_WIDTH = 17 * cm

FLAGSHIP_RESULTS = [
    (
        "<b>ДУ 1.5 — вечерние регламенты:</b> оптимизировал массовые регламенты на портфеле "
        "до 100 000 договоров — 4 ч 25 мин -> 2 ч 43 мин (-38%); окно закрытия дня выдерживается."
    ),
    (
        "<b>ДУ 1.5 — отчет 431 и сделки:</b> ускорил регл. отчет 431 с 1 ч 42 мин до 12 мин "
        "(~x8,6, регрессия идентична); исполнение 100 000 сделок уложил в SLA 2 ч."
    ),
    (
        "<b>Мидл-офис — MV/WAP:</b> сократил ночной пересчет розницы с ~4 ч до ~30 мин (~x8, "
        "~3 000 мандатов); регресс MXL «файлы идентичны»."
    ),
    (
        "<b>Финконтур — закрытие периода:</b> ускорил закрытие ~x3 за счет фильтрации плана "
        "регламентов РДУ; параллельный НДФЛ и перепроведение до 30 000 сделок."
    ),
    (
        "<b>Карьера ВТБ/БКС:</b> интеграции Kafka/HTTP с биржей и НРД — ежедневные операции "
        "без остановки торгового дня; запуск брокерского бэк-офиса ОАЭ."
    ),
]

SKILL_ROWS = [
    (
        "Cursor + ИИ",
        "<b>100% цикл в IDE Cursor</b> (с 2026): аналитика, ТЗ, код 1С, ревью, автотесты, "
        "документация, замеры «было/стало»",
    ),
    (
        "Платформа 1С",
        "1С:Предприятие 8.3 (20+ лет), расширения, БСП, длительные операции, СКД, "
        "управляемые формы, сложные запросы",
    ),
    (
        "Конфигурации",
        "УПП, УТ, ЗУП, ERP; финтех: брокер, депозитарий, доверительное управление (ДУ 1.5)",
    ),
    (
        "Интеграции",
        "Kafka, HTTP/REST, SOAP, HTTP-сервисы, JSON/XML, НРД, RuData, биржа — 15+ лет",
    ),
    (
        "СУБД",
        "MS SQL Server (15+ лет): профилирование, индексы, оптимизация запросов и регламентов, "
        "сверки 1С и SQL",
    ),
    (
        "High-load",
        "Параллельные конвейеры БСП, пакетная обработка, нагрузочные испытания, "
        "стабилизация кластера 1С",
    ),
    (
        "Качество",
        "Vanessa Automation, SonarQube, Git, code review, регрессия на копии ПРОД",
    ),
    (
        "Сертификаты",
        "1С: ERP (Проф + Спец-консультант), УПП, Платформа 8, Руководитель проекта, 7.7",
    ),
]


def register_fonts() -> tuple[str, str, str]:
    fonts_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    pdfmetrics.registerFont(TTFont("Arial", str(fonts_dir / "arial.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-Bold", str(fonts_dir / "arialbd.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-Italic", str(fonts_dir / "ariali.ttf")))
    pdfmetrics.registerFontFamily(
        "Arial",
        normal="Arial",
        bold="Arial-Bold",
        italic="Arial-Italic",
        boldItalic="Arial-Bold",
    )
    return "Arial", "Arial-Bold", "Arial-Italic"


def build_styles(regular: str, bold: str, italic: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "name": ParagraphStyle(
            "Name", parent=base["Normal"], fontName=bold, fontSize=19, leading=23,
            textColor=WHITE, spaceAfter=1,
        ),
        "title": ParagraphStyle(
            "Title", parent=base["Normal"], fontName=regular, fontSize=9.5, leading=12,
            textColor=ACCENT_SOFT, spaceAfter=0,
        ),
        "contact": ParagraphStyle(
            "Contact", parent=base["Normal"], fontName=regular, fontSize=8.3, leading=11,
            textColor=WHITE,
        ),
        "section": ParagraphStyle(
            "Section", parent=base["Normal"], fontName=bold, fontSize=9.5, leading=11,
            textColor=NAVY, spaceBefore=5, spaceAfter=2,
        ),
        "summary": ParagraphStyle(
            "Summary", parent=base["Normal"], fontName=regular, fontSize=9, leading=12.5,
            textColor=TEXT, spaceAfter=2,
        ),
        "body_small": ParagraphStyle(
            "BodySmall", parent=base["Normal"], fontName=regular, fontSize=8.2, leading=10.5,
            textColor=TEXT_MUTED, spaceAfter=2,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["Normal"], fontName=regular, fontSize=8.4, leading=11,
            textColor=TEXT, leftIndent=9, bulletIndent=0, spaceAfter=1.5,
        ),
        "job_title": ParagraphStyle(
            "JobTitle", parent=base["Normal"], fontName=bold, fontSize=9.4, leading=11.5,
            textColor=NAVY, spaceAfter=0,
        ),
        "job_meta": ParagraphStyle(
            "JobMeta", parent=base["Normal"], fontName=italic, fontSize=8.1, leading=10,
            textColor=TEXT_MUTED, spaceAfter=2,
        ),
        "metric_value": ParagraphStyle(
            "MetricValue", parent=base["Normal"], fontName=bold, fontSize=13, leading=15,
            textColor=NAVY, alignment=TA_LEFT,
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel", parent=base["Normal"], fontName=regular, fontSize=6.8, leading=8.5,
            textColor=TEXT_MUTED, alignment=TA_LEFT,
        ),
        "stack_cat": ParagraphStyle(
            "StackCat", parent=base["Normal"], fontName=bold, fontSize=8, leading=9.5,
            textColor=NAVY,
        ),
        "stack_val": ParagraphStyle(
            "StackVal", parent=base["Normal"], fontName=regular, fontSize=8, leading=10,
            textColor=TEXT,
        ),
        "highlight_title": ParagraphStyle(
            "HighlightTitle", parent=base["Normal"], fontName=bold, fontSize=10, leading=12,
            textColor=NAVY, spaceAfter=1,
        ),
        "highlight_body": ParagraphStyle(
            "HighlightBody", parent=base["Normal"], fontName=regular, fontSize=8.8, leading=12,
            textColor=TEXT, spaceAfter=0,
        ),
        "footer_body": ParagraphStyle(
            "FooterBody", parent=base["Normal"], fontName=regular, fontSize=8.3, leading=11,
            textColor=TEXT, spaceAfter=2,
        ),
    }


def draw_header(canvas, doc) -> None:
    canvas.saveState()
    width, height = A4
    header_h = 2.85 * cm
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - header_h, width, header_h, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, height - header_h - 2, width, 2, fill=1, stroke=0)
    canvas.restoreState()


def draw_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Arial", 7)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawString(1.5 * cm, 0.9 * cm, "Chmykhalov A.A. | Vedushchiy programmist 1S | Moskva | ot 650 000 rub.")
    canvas.drawRightString(A4[0] - 1.5 * cm, 0.9 * cm, f"стр. {doc.page}")
    canvas.restoreState()


def metric_card(styles, value: str, label: str, width: float) -> Table:
    t = Table(
        [[Paragraph(value, styles["metric_value"])], [Paragraph(label, styles["metric_label"])]],
        colWidths=[width],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 5),
    ]))
    return t


def panel_box(content: list, bg: colors.Color, border: colors.Color, border_w: float = 1) -> Table:
    t = Table([[item] for item in content], colWidths=[CONTENT_WIDTH], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), border_w, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
    ]))
    return t


def skill_matrix(styles, rows: list[tuple[str, str]]) -> Table:
    data = [[Paragraph(cat, styles["stack_cat"]), Paragraph(val, styles["stack_val"])] for cat, val in rows]
    t = Table(data, colWidths=[3.0 * cm, 14.0 * cm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_SKILLS),
        ("BOX", (0, 0), (-1, -1), 0.25, RULE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def bullets_block(styles, items: list[str]) -> list:
    return [Paragraph(f"<bullet>&bull;</bullet> {text}", styles["bullet"]) for text in items]


def job_block(styles, company, role, period, context, bullets, tech_stack=None):
    items = [
        Paragraph(company, styles["job_title"]),
        Paragraph(f"{role}  |  {period}", styles["job_meta"]),
        Paragraph(context, styles["body_small"]),
    ]
    items.extend(bullets_block(styles, bullets))
    if tech_stack:
        items.append(Spacer(1, 1))
        items.append(Paragraph(f"<b>Стек:</b> {tech_stack}", styles["body_small"]))
    items.append(Spacer(1, 4))
    return items


def build_story(styles) -> list:
    story = [
        Spacer(1, 0.08 * cm),
        Paragraph("Чмыхалов Алексей Анатольевич", styles["name"]),
        Paragraph(
            "Ведущий программист 1С  |  FinTech  |  High-load  |  MS SQL  |  Kafka",
            styles["title"],
        ),
        Paragraph(
            "Cursor + ИИ  |  1С:Предприятие 8.3  |  БСП  |  ДУ  |  брокер  |  депозитарий",
            styles["contact"],
        ),
        Paragraph(
            "+7 (915) 015-74-44  |  a.chmihalov@yandex.ru  |  Москва  |  гибрид / удаленка",
            styles["contact"],
        ),
        Spacer(1, 0.3 * cm),
    ]

    story.append(panel_box([
        Paragraph("CURSOR + ИИ — ОСНОВНОЙ РЕЖИМ РАБОТЫ", styles["highlight_title"]),
        Paragraph(
            "<b>100% разработки и аналитики</b> в IDE Cursor с ИИ: постановки, ТЗ, код 1С, "
            "ревью, автотесты, документация, замеры «было/стало» — полный цикл с 2026 года.",
            styles["highlight_body"],
        ),
    ], CURSOR_BG, CURSOR_BORDER, 2))
    story.append(Spacer(1, 0.1 * cm))

    story.append(Paragraph("ПРОФЕССИОНАЛЬНОЕ РЕЗЮМЕ", styles["section"]))
    story.extend([
        Paragraph(
            "<b>Ведущий программист 1С, 25+ лет (20+ на платформе 8.3).</b> "
            "Специализация — high-load FinTech: доверительное управление, брокер, депозитарий. "
            "Уникальная модель: <b>весь цикл в Cursor + ИИ</b> — от постановки до промышленного "
            "кода с регрессией на копии ПРОД.",
            styles["summary"],
        ),
        Paragraph(
            "<b>Главный результат (ВИМ, 2025-н.в.):</b> оптимизация сквозного контура розницы "
            "(ДУ, мидл-офис, финконтур) на портфеле до 100 000 договоров — MV/WAP ~x8, "
            "отчет 431 ~x8,6, закрытие периода ~x3, 100 000 сделок в SLA 2 ч. "
            "Карьера: интеграции ВТБ/БКС (Kafka, HTTP, НРД), корпоративные УПП/УТ/ЗУП. "
            "Сертификаты ERP, УПП, Платформа 8, РП. Руководил командой до 10 чел.",
            styles["summary"],
        ),
    ])

    mw = 3.35 * cm
    story.append(Spacer(1, 0.08 * cm))
    story.append(Paragraph("КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ", styles["section"]))
    story.append(Table([[
        metric_card(styles, "25+", "лет в 1С, Senior/Lead", mw),
        metric_card(styles, "100%", "Cursor + ИИ: полный цикл", mw),
        metric_card(styles, "x8", "MV/WAP и отчет 431", mw),
        metric_card(styles, "100 000", "сделок в SLA 2 ч", mw),
        metric_card(styles, "x3", "закрытие периода", mw),
    ]], colWidths=[mw] * 5))
    story.append(Spacer(1, 0.08 * cm))

    story.append(Paragraph("ФЛАГМАНСКИЕ РЕЗУЛЬТАТЫ (STAR)", styles["section"]))
    story.extend(bullets_block(styles, FLAGSHIP_RESULTS))
    story.append(Spacer(1, 0.08 * cm))

    story.append(Paragraph("КЛЮЧЕВЫЕ НАВЫКИ", styles["section"]))
    story.append(skill_matrix(styles, SKILL_ROWS))
    story.append(Spacer(1, 0.08 * cm))

    story.append(Paragraph("ОПЫТ РАБОТЫ", styles["section"]))
    story.extend(job_block(
        styles,
        "АО ВИМ Инвестиции  |  Москва",
        "Ведущий программист 1С",
        "июль 2025 — настоящее время",
        "High-load ландшафт ДУ 1.5, мидл-офис и финконтур; портфель до 100 000 договоров розницы.",
        [
            "Веду <b>100% аналитики и разработки в Cursor + ИИ</b>: постановки, код, ревью, "
            "тесты, документация, замеры производительности.",
            "Оптимизировал вечерние регламенты ДУ: 4 ч 25 мин -> 2 ч 43 мин (-38%). "
            "<b>Результат:</b> окно закрытия дня выдерживается при росте портфеля.",
            "Ускорил регл. отчет 431 (1 ч 42 мин -> 12 мин, ~x8,6) и исполнение 100 000 сделок "
            "(SLA 2 ч). Стабилизировал кластер: пакеты по 3 000 дог., пик памяти ~x5,7 ниже.",
            "Сократил пересчет MV/WAP розницы ~4 ч -> ~30 мин (~x8); ускорил закрытие периода "
            "ФИН ~x3; параллельный НДФЛ и перепроведение до 30 000 сделок.",
        ],
        tech_stack="Cursor + ИИ, 1С:Предприятие 8.3, БСП, MS SQL, Kafka, HTTP, Vanessa, Git",
    ))

    story.extend(job_block(
        styles,
        "ООО СБ-Брокер / НРБ банк (группа ВТБ)  |  Москва",
        "Ведущий программист 1С",
        "октябрь 2021 — апрель 2026",
        "Бэк-офис брокера и депозитарий, системно значимая финансовая организация.",
        [
            "Спроектировал интеграции с биржей, НРД и поставщиками данных (Kafka, HTTP). "
            "<b>Результат:</b> ежедневные операции без остановки торгового дня.",
            "Оптимизировал тяжелые запросы отчетности, сверки 1С с MS SQL. "
            "<b>Результат:</b> стабильная работа при пиковых нагрузках бэк-офиса.",
            "Внедрил Vanessa Automation, SonarQube и деперсонализацию данных в процесс команды.",
        ],
        tech_stack="1С:Предприятие 8.3, Kafka, HTTP, НРД, RuData, MS SQL, Vanessa, SonarQube",
    ))

    story.extend(job_block(
        styles,
        "БКС-технологии  |  Москва",
        "Ведущий программист 1С / Руководитель группы",
        "ноябрь 2016 — сентябрь 2021",
        "Бэк-офис брокера 8.2/8.3, мультиюрисдикционный контур (ОАЭ).",
        [
            "Руководил командой брокера ОАЭ (постановка, ревью, координация с бизнесом).",
            "Спроектировал архитектуру доработок для выхода на рынок ОАЭ. "
            "<b>Результат:</b> запуск брокерского бэк-офиса на 1С в согласованные сроки.",
        ],
        tech_stack="1С 8.2/8.3, интеграции, отчетность",
    ))

    story.extend(job_block(
        styles,
        "Корпоративные внедрения  |  2000 — 2016",
        "Ведущий специалист / РП / техдиректор",
        "ИнфоСофт, Ольвия ТПК, Суматра, ВИКОР, Баядера",
        "УПП, УТ, ЗУП на производстве и в дистрибуции; команда до 10 чел.",
        [
            "Внедрил ЗУП на 2 500 сотрудников и УПП в 5-7 филиалах (80-140 пользователей). "
            "<b>Результат:</b> единый учет на предприятиях с филиальной сетью.",
            "Разработал KPI-зарплату «Обувь России»; ввел УПП на стрелочном заводе. "
            "<b>Результат:</b> опубликованное отраслевое решение на 1c.ru.",
        ],
        tech_stack="УПП, УТ, ЗУП, 1С 7.7/8.x",
    ))

    bottom = Table([[

        Paragraph(

            "<b>ОБРАЗОВАНИЕ</b><br/><br/>"

            "Высшее, 1999<br/>"

            "ДНУЖТ им. В. Лазаряна<br/>"

            "ПО ВТ и АС (тех. кибернетика)",

            styles["footer_body"],

        ),

        Paragraph(

            "<b>ПОРТФОЛИО</b><br/><br/>"

            "v8.1c.ru/news/newsAbout.jsp?id=1910<br/>"

            "1c.ru/.../solution.jsp?SolutionID=99734<br/><br/>"

            "<b>ЯЗЫКИ</b><br/>"

            "RU — родной | UA — C2 | EN — техдокументация<br/><br/>"

            "<b>HH.RU</b><br/>"

            "Должность: Ведущий программист 1С<br/>"

            "Профессия: Программист, разработчик<br/>"

            "от <b>650 000</b> руб. на руки, гибрид / удаленка",

            styles["footer_body"],

        ),

    ]], colWidths=[8.5 * cm, 8.5 * cm])

    bottom.setStyle(TableStyle([

        ("VALIGN", (0, 0), (-1, -1), "TOP"),

        ("LEFTPADDING", (0, 0), (-1, -1), 0),

        ("RIGHTPADDING", (0, 0), (-1, -1), 8),

    ]))

    story.append(Spacer(1, 2))

    story.append(bottom)

    return story





def main() -> None:

    regular, bold, italic = register_fonts()

    styles = build_styles(regular, bold, italic)



    doc = BaseDocTemplate(

        str(OUTPUT_FILE),

        pagesize=A4,

        leftMargin=1.5 * cm,

        rightMargin=1.5 * cm,

        topMargin=3.15 * cm,

        bottomMargin=1.5 * cm,

        title="Chmykhalov Alexey - Resume 2026",

        author="Alexey Chmykhalov",

    )

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")

    doc.addPageTemplates([PageTemplate(id="resume", frames=[frame], onPage=draw_header, onPageEnd=draw_footer)])



    doc.build(build_story(styles))

    print(f"OK: {OUTPUT_FILE}")





if __name__ == "__main__":

    main()

