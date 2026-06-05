#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generates premium PDF resume for Alexey Chmykhalov (Russian, HH-ready).
Output: Private/Резюме HH/Chmykhalov_Alexey_Resume_2026.pdf
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
BG_SIDEBAR = colors.HexColor("#F4F6F9")
WHITE = colors.white


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
            "Name", parent=base["Normal"], fontName=bold, fontSize=21, leading=25,
            textColor=WHITE, spaceAfter=2,
        ),
        "title": ParagraphStyle(
            "Title", parent=base["Normal"], fontName=regular, fontSize=10.5, leading=13,
            textColor=ACCENT_SOFT, spaceAfter=0,
        ),
        "contact": ParagraphStyle(
            "Contact", parent=base["Normal"], fontName=regular, fontSize=8.5, leading=12,
            textColor=WHITE,
        ),
        "section": ParagraphStyle(
            "Section", parent=base["Normal"], fontName=bold, fontSize=10, leading=12,
            textColor=NAVY, spaceBefore=7, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"], fontName=regular, fontSize=9, leading=12.5,
            textColor=TEXT, spaceAfter=4,
        ),
        "body_small": ParagraphStyle(
            "BodySmall", parent=base["Normal"], fontName=regular, fontSize=8.5, leading=11,
            textColor=TEXT_MUTED, spaceAfter=3,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["Normal"], fontName=regular, fontSize=8.8, leading=12,
            textColor=TEXT, leftIndent=10, bulletIndent=0, spaceAfter=3,
        ),
        "job_title": ParagraphStyle(
            "JobTitle", parent=base["Normal"], fontName=bold, fontSize=10, leading=12,
            textColor=NAVY, spaceAfter=1,
        ),
        "job_meta": ParagraphStyle(
            "JobMeta", parent=base["Normal"], fontName=italic, fontSize=8.5, leading=11,
            textColor=TEXT_MUTED, spaceAfter=4,
        ),
        "metric_value": ParagraphStyle(
            "MetricValue", parent=base["Normal"], fontName=bold, fontSize=14, leading=16,
            textColor=NAVY, alignment=TA_LEFT,
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel", parent=base["Normal"], fontName=regular, fontSize=7.5, leading=9,
            textColor=TEXT_MUTED, alignment=TA_LEFT,
        ),
        "tag": ParagraphStyle(
            "Tag", parent=base["Normal"], fontName=regular, fontSize=7.5, leading=9, textColor=NAVY,
        ),
    }


def draw_header(canvas, doc) -> None:
    canvas.saveState()
    width, height = A4
    header_h = 3.15 * cm
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - header_h, width, header_h, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, height - header_h - 2, width, 2, fill=1, stroke=0)
    canvas.restoreState()


def draw_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Arial", 7)
    canvas.setFillColor(TEXT_MUTED)
    canvas.setFont("Arial", 7)
    canvas.drawString(1.5 * cm, 1.0 * cm, "Chmykhalov A.A. | Vedyushchiy razrabotchik 1S | Moskva")
    canvas.drawRightString(A4[0] - 1.5 * cm, 1.0 * cm, f"стр. {doc.page}")
    canvas.restoreState()


def metric_card(styles, value: str, label: str, width: float) -> Table:
    t = Table(
        [[Paragraph(value, styles["metric_value"])], [Paragraph(label, styles["metric_label"])]],
        colWidths=[width],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_SIDEBAR),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
    ]))
    return t


def skill_tags(styles, skills: list[str], col_width: float) -> Table:
    rows, row = [], []
    for skill in skills:
        row.append(Paragraph(skill, styles["tag"]))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        while len(row) < 3:
            row.append("")
        rows.append(row)
    t = Table(rows, colWidths=[col_width] * 3, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF2F7")),
        ("BOX", (0, 0), (-1, -1), 0.25, RULE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def job_block(styles, company, role, period, context, bullets, achievements=None):
    items = [
        Paragraph(company, styles["job_title"]),
        Paragraph(f"{role}  |  {period}", styles["job_meta"]),
        Paragraph(context, styles["body_small"]),
        Spacer(1, 2),
    ]
    for b in bullets:
        items.append(Paragraph(f"<bullet>&bull;</bullet> {b}", styles["bullet"]))
    if achievements:
        items.append(Spacer(1, 3))
        items.append(Paragraph("<b>Ключевые результаты:</b>", styles["body_small"]))
        for a in achievements:
            items.append(Paragraph(f"<bullet>&bull;</bullet> {a}", styles["bullet"]))
    items.append(Spacer(1, 4))
    return items


def build_story(styles) -> list:
    story = [
        Spacer(1, 0.15 * cm),
        Paragraph("Чмыхалов Алексей Анатольевич", styles["name"]),
        Paragraph("Ведущий разработчик 1С  |  Финтех  |  Интеграции  |  Tech Lead", styles["title"]),
        Spacer(1, 0.12 * cm),
        Paragraph(
            "+7 (915) 015-74-44  |  a.chmihalov@yandex.ru  |  Москва  |  Гибрид / Удаленка",
            styles["contact"],
        ),
        Spacer(1, 0.5 * cm),
    ]

    mw = 3.9 * cm
    metrics = Table([[
        metric_card(styles, "25+", "лет в 1С", mw),
        metric_card(styles, "20+", "лет 1С 8.x", mw),
        metric_card(styles, "10", "чел. в команде", mw),
        metric_card(styles, "2500", "польз. внедрения", mw),
    ]], colWidths=[mw] * 4)
    story.append(metrics)
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("ПРОФЕССИОНАЛЬНЫЙ ПРОФИЛЬ", styles["section"]))
    story.extend([
        Paragraph(
            "Ведущий разработчик 1С с глубокой экспертизой в бэк-офисе брокера и депозитария. "
            "Специализация: высоконагруженные сверки, интеграции с биржей и НРД, потоки Kafka, "
            "налоговый учет, отчетность XBRL, деперсонализация данных в регуляторной среде.",
            styles["body"],
        ),
        Paragraph(
            "Сейчас разрабатываю критичные модули в группе ВТБ (брокер + депозитарий). "
            "Веду разработку в <b>Cursor IDE</b> с AI-ассистентами: ускоряю code review, "
            "автотесты Vanessa Automation, документацию и анализ legacy-кода при соблюдении "
            "стандартов SonarQube.",
            styles["body"],
        ),
        Paragraph(
            "Опыт Tech Lead: команда брокера ОАЭ (БКС), руководство отделом 1С (до 10 инженеров), "
            "внедрения УПП/УТ до 2500 пользователей. Сертификаты 1С: ERP, УПП, платформа. "
            "Опубликованное отраслевое решение на 1c.ru.",
            styles["body"],
        ),
    ])

    story.append(Paragraph("ТЕХНОЛОГИЧЕСКИЙ СТЕК", styles["section"]))
    story.append(skill_tags(styles, [
        "1С 8.3", "HTTP-сервисы", "Apache Kafka", "MS SQL", "REST / SOAP",
        "Vanessa BDD", "SonarQube", "Git", "XBRL", "СКД", "Cursor AI", "Agile / Kanban",
    ], 5.2 * cm))

    story.append(Paragraph("ОПЫТ РАБОТЫ", styles["section"]))
    story.extend(job_block(
        styles,
        "ООО СБ-Брокер / НРБ банк (группа ВТБ)  |  Москва",
        "Ведущий разработчик 1С",
        "октябрь 2021 — настоящее время",
        "Брокерский бэк-офис и депозитарий. Биржевые операции, клиентская отчетность, интеграции с инфраструктурой рынка.",
        [
            "Разработка модулей брокера и депозитария: комиссии, налоговый учет, внебиржевые сделки, деперсонализация",
            "Интеграции: HTTP-сервисы, Kafka, пакеты НРД (K/Z/W), RuData, CBonds, BQ, Московская биржа",
            "Сверки 1С + MS SQL: хранимые процедуры, диагностика расхождений, сверочные отчеты",
            "Регламентированная и управленческая отчетность, в т.ч. XBRL",
            "Автотесты Vanessa Automation, code review, контроль качества SonarQube",
            "Разработка в Cursor IDE: AI-assisted рефакторинг, тесты, документация, анализ legacy",
        ],
        [
            "Интеграционный контур для ежедневных операций брокера с внешними data-провайдерами",
            "Промышленный запуск блоков налогового учета и деперсонализации в compliance-среде",
            "Внедрение автотестирования и статического анализа в процесс разработки команды",
        ],
    ))

    story.extend(job_block(
        styles,
        "БКС-технологии  |  Москва",
        "Ведущий программист 1С / Tech Lead (брокер ОАЭ)",
        "ноябрь 2016 — сентябрь 2021",
        "ИТ-подразделение инвестиционной группы БКС. Бэк-офис брокера на 1С 8.2/8.3.",
        [
            "Разработка блоков бэк-офиса: учет операций, отчетность, интеграции",
            "Руководство командой брокерского направления ОАЭ: постановка задач, ревью, координация с бизнесом",
            "Доработки на управляемых и обычных формах в мультиюрисдикционном контуре",
            "Участие в проектировании архитектуры доработок",
        ],
    ))

    story.extend(job_block(
        styles,
        "ИнфоСофт, Внедренческий центр  |  Новосибирск",
        "Ведущий специалист по внедрению 1С",
        "апрель 2015 — ноябрь 2016",
        "Корпоративные внедрения УПП, ЗУП, Розница.",
        [
            "Модуль расчета зарплаты от KPI — «Обувь России» (УПП, ЗУП, Розница, COM)",
            "Налоговый учет и регламентированные отчеты — ГКНПЦ им. Хруничева",
            "Ввод в эксплуатацию УПП — Новосибирский стрелочный завод",
        ],
    ))

    story.append(Paragraph(
        "<b>Ранний опыт:</b> Ольвия ТПК — начальник отдела 1С (УПП, 80-140 польз.); "
        "Суматра — ведущий инженер (УТП/ЗУП, 2500 сотр.); ВИКОР (1С-франчайзи) — техдиректор (10 чел.); "
        "АКБ Премьербанк — ведущий специалист ДИТ.",
        styles["body_small"],
    ))

    story.append(Paragraph("КЛЮЧЕВЫЕ ДОСТИЖЕНИЯ", styles["section"]))
    for a in [
        "Экспертиза брокер/депозитарий в системно значимых финансовых организациях (ВТБ, БКС)",
        "Сквозная архитектура интеграций: биржа, НРД, market data, событийные потоки Kafka",
        "Руководство командами 3-10 человек в распределенной и регулируемой среде",
        "Enterprise-внедрения от франчайзи до систем на 2500 пользователей",
        "Опубликованное отраслевое решение 1С и патент на изобретение (1999)",
    ]:
        story.append(Paragraph(f"<bullet>&bull;</bullet> {a}", styles["bullet"]))

    bottom = Table([[
        Paragraph(
            "<b>СЕРТИФИКАТЫ 1С</b><br/><br/>"
            "• 1С:Специалист-консультант ERP 2.0<br/>"
            "• 1С:Профессионал ERP<br/>"
            "• 1С:Специалист по УПП<br/>"
            "• 1С:Руководитель проекта<br/>"
            "• 1С:Профессионал (платформа 8)<br/>"
            "• 1С:Специалист 7.7",
            styles["body"],
        ),
        Paragraph(
            "<b>ОБРАЗОВАНИЕ</b><br/><br/>"
            "Высшее, 1999<br/>"
            "ДНУЖТ им. В. Лазаряна<br/>"
            "ПО ВТ и АС (тех. кибернетика)<br/><br/>"
            "<b>ПОРТФОЛИО</b><br/>"
            "v8.1c.ru/news/newsAbout.jsp?id=1910<br/>"
            "1c.ru/.../solution.jsp?SolutionID=99734<br/><br/>"
            "<b>ЯЗЫКИ</b><br/>"
            "RU — родной | UA — C2 | EN — A1",
            styles["body"],
        ),
    ]], colWidths=[8.5 * cm, 8.5 * cm])
    bottom.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(Spacer(1, 4))
    story.append(bottom)

    story.append(Paragraph("ЦЕЛЕВАЯ ПОЗИЦИЯ", styles["section"]))
    story.append(Paragraph(
        "<b>Должность:</b> Ведущий / Senior разработчик 1С или Team Lead (финтех, банк)  |  "
        "<b>Формат:</b> гибрид / удаленка  |  <b>ЗП:</b> 550-650 тыс. на руки  |  "
        "<b>Переезд:</b> нет  |  <b>Командировки:</b> да",
        styles["body"],
    ))

    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "<i>Уникальное сочетание: глубина предметной области брокер/депозитарий + современный "
        "интеграционный стек (Kafka, HTTP, SQL) + инженерия качества (Vanessa, Sonar) + "
        "AI-ускоренная разработка в Cursor без потери корпоративных стандартов.</i>",
        styles["body_small"],
    ))
    return story


def main() -> None:
    regular, bold, italic = register_fonts()
    styles = build_styles(regular, bold, italic)

    doc = BaseDocTemplate(
        str(OUTPUT_FILE),
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=3.45 * cm,
        bottomMargin=1.6 * cm,
        title="Chmykhalov Alexey - Resume 2026",
        author="Alexey Chmykhalov",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="resume", frames=[frame], onPage=draw_header, onPageEnd=draw_footer)])

    doc.build(build_story(styles))
    print(f"OK: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
