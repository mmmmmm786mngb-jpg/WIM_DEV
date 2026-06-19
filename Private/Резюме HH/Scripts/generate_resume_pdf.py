#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generates PDF resume for Alexey Chmykhalov (Russian, HH.ru, ТК РФ).
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
            "Name", parent=base["Normal"], fontName=bold, fontSize=20, leading=24,
            textColor=WHITE, spaceAfter=2,
        ),
        "title": ParagraphStyle(
            "Title", parent=base["Normal"], fontName=regular, fontSize=10, leading=12.5,
            textColor=ACCENT_SOFT, spaceAfter=0,
        ),
        "contact": ParagraphStyle(
            "Contact", parent=base["Normal"], fontName=regular, fontSize=8.5, leading=12,
            textColor=WHITE,
        ),
        "section": ParagraphStyle(
            "Section", parent=base["Normal"], fontName=bold, fontSize=10, leading=12,
            textColor=NAVY, spaceBefore=6, spaceAfter=3,
        ),
        "summary": ParagraphStyle(
            "Summary", parent=base["Normal"], fontName=regular, fontSize=9.2, leading=13,
            textColor=TEXT, spaceAfter=3,
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
            "Bullet", parent=base["Normal"], fontName=regular, fontSize=8.7, leading=11.5,
            textColor=TEXT, leftIndent=10, bulletIndent=0, spaceAfter=2,
        ),
        "job_title": ParagraphStyle(
            "JobTitle", parent=base["Normal"], fontName=bold, fontSize=9.8, leading=12,
            textColor=NAVY, spaceAfter=1,
        ),
        "job_meta": ParagraphStyle(
            "JobMeta", parent=base["Normal"], fontName=italic, fontSize=8.3, leading=10.5,
            textColor=TEXT_MUTED, spaceAfter=3,
        ),
        "metric_value": ParagraphStyle(
            "MetricValue", parent=base["Normal"], fontName=bold, fontSize=15, leading=17,
            textColor=NAVY, alignment=TA_LEFT,
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel", parent=base["Normal"], fontName=regular, fontSize=7.3, leading=9,
            textColor=TEXT_MUTED, alignment=TA_LEFT,
        ),
        "stack_cat": ParagraphStyle(
            "StackCat", parent=base["Normal"], fontName=bold, fontSize=8.2, leading=10,
            textColor=NAVY,
        ),
        "stack_val": ParagraphStyle(
            "StackVal", parent=base["Normal"], fontName=regular, fontSize=8.2, leading=10.5,
            textColor=TEXT,
        ),
    }


def draw_header(canvas, doc) -> None:
    canvas.saveState()
    width, height = A4
    header_h = 3.0 * cm
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - header_h, width, header_h, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, height - header_h - 2, width, 2, fill=1, stroke=0)
    canvas.restoreState()


def draw_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Arial", 7)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawString(1.5 * cm, 1.0 * cm, "Chmykhalov A.A. | Vedushchiy programmist 1S | Moskva")
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
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 7),
    ]))
    return t


def skill_matrix(styles, rows: list[tuple[str, str]]) -> Table:
    data = [[Paragraph(cat, styles["stack_cat"]), Paragraph(val, styles["stack_val"])] for cat, val in rows]
    t = Table(data, colWidths=[3.2 * cm, 13.8 * cm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF2F7")),
        ("BOX", (0, 0), (-1, -1), 0.25, RULE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def hooks_panel(styles, hooks: list[str]) -> Table:
    rows = [[Paragraph(f"<bullet>&bull;</bullet> {text}", styles["bullet"])] for text in hooks]
    t = Table(rows, colWidths=[17 * cm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF9E6")),
        ("BOX", (0, 0), (-1, -1), 1, ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def job_block(styles, company, role, period, context, bullets, results=None, tech_stack=None):
    items = [
        Paragraph(company, styles["job_title"]),
        Paragraph(f"{role}  |  {period}", styles["job_meta"]),
        Paragraph(context, styles["body_small"]),
        Spacer(1, 1),
    ]
    if bullets:
        items.append(Paragraph("<b>Ключевые достижения:</b>", styles["body_small"]))
        for b in bullets:
            items.append(Paragraph(f"<bullet>&bull;</bullet> {b}", styles["bullet"]))
    if results:
        items.append(Spacer(1, 2))
        items.append(Paragraph("<b>Результат:</b>", styles["body_small"]))
        for r in results:
            items.append(Paragraph(f"<bullet>&bull;</bullet> {r}", styles["bullet"]))
    if tech_stack:
        items.append(Spacer(1, 2))
        items.append(Paragraph(f"<b>Технологии:</b> {tech_stack}", styles["body_small"]))
    items.append(Spacer(1, 3))
    return items


def build_story(styles) -> list:
    story = [
        Spacer(1, 0.12 * cm),
        Paragraph("Чмыхалов Алексей Анатольевич", styles["name"]),
        Paragraph(
            "Ведущий программист 1С  |  Высоконагруженные системы  |  FinTech, Kafka, MS SQL",
            styles["title"],
        ),
        Paragraph(
            "Профессия HH: Программист, разработчик  |  Cursor  |  Финтех · Высоконагруженные системы",
            styles["contact"],
        ),
        Paragraph(
            "+7 (915) 015-74-44  |  a.chmihalov@yandex.ru  |  Москва  |  Гибрид / Удаленка",
            styles["contact"],
        ),
        Spacer(1, 0.45 * cm),
    ]

    story.append(Paragraph("КЛЮЧЕВЫЕ ПРЕИМУЩЕСТВА", styles["section"]))
    story.append(Paragraph(
        "<i>Совпадение с тем, что HR и ATS ищут в первые 7 секунд (hh.ru, форумы 1С, 2026)</i>",
        styles["body_small"],
    ))
    story.append(hooks_panel(styles, [
        "<b>25+ лет, 20+ на 1С 8.3</b> — уровень Senior/Lead; стабильная карьера в 1С без смены профессии",
        "<b>Сертификаты 1С:</b> ERP (Профессионал + Спец-консультант), УПП, Платформа 8, "
        "Руководитель проекта — ключевой маркер для HR и автоматического отбора",
        "<b>Конфигурации:</b> УПП, УТ, ЗУП, ERP + финтех (брокер, депозитарий, ДУ) — "
        "закрывает большинство фильтров вакансий",
        "<b>Интеграции 15+ лет:</b> Kafka, HTTP/REST, НРД, обмены — топ-требование "
        "Senior-вакансий в банках и финтехе",
        "<b>Оптимизация high-load:</b> MS SQL, профилирование, ×3 ускорение критичного пути, "
        "портфель 100 000 договоров — редкий масштаб для 1С",
        "<b>Работодатели:</b> ВТБ (системно значимый банк), БКС, ВИМ — финтех, не «общий IT»",
        "<b>Современный процесс:</b> Vanessa Automation, Git, SonarQube, БСП, расширения; "
        "с 2026 — полный цикл в <b>Cursor</b> (ИИ-ассистенты)",
        "<b>Руководитель команды до 10 чел.</b> — готов к ведущей и Lead-позиции",
    ]))
    story.append(Spacer(1, 0.15 * cm))

    story.append(Paragraph("О СЕБЕ", styles["section"]))
    story.extend([
        Paragraph(
            "<b>С 2026 года вся аналитика и разработка ведутся в среде Cursor:</b> разбор задач, "
            "проектирование, код, ревью, автотесты и замеры «было/стало» с ИИ-ассистентами "
            "при соблюдении SonarQube.",
            styles["summary"],
        ),
        Paragraph(
            "<b>Ведущий программист 1С и архитектор решений, 25+ лет (20+ на 8.x).</b> "
            "Всю карьеру — проектирование и развитие учетных систем: корпоративные внедрения "
            "УПП/УТ/ЗУП, брокер и депозитарий (ВТБ, БКС), интеграции Kafka/HTTP/НРД. "
            "<b>Сейчас (ВИМ):</b> оптимизация высоконагруженного ландшафта доверительного "
            "управления на портфеле до 100 000 договоров — массовые регламенты, "
            "параллельные конвейеры расчетов, ускорение критичного пути закрытия дня "
            "примерно <b>в 3 раза</b>.",
            styles["summary"],
        ),
        Paragraph(
            "Сильные стороны: архитектура интеграций, оптимизация запросов и регламентов "
            "в MS SQL, нагрузочные испытания, замеры «было/стало», постановки вендору. "
            "Руководил командой до 10 чел. Стек: 8.3, БСП, Kafka, HTTP, MS SQL, "
            "Vanessa, Git, <b>Cursor</b>.",
            styles["summary"],
        ),
    ])
    story.append(Spacer(1, 0.12 * cm))

    mw = 3.9 * cm
    story.append(Paragraph("КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ", styles["section"]))
    story.append(Table([[
        metric_card(styles, "25+", "лет: архитектура и интеграции", mw),
        metric_card(styles, "100 000", "договоров — текущий масштаб", mw),
        metric_card(styles, "×3", "ускорение критичного пути", mw),
        metric_card(styles, "2 500", "сотр. — внедрение ЗУП", mw),
    ]], colWidths=[mw] * 4))
    story.append(Spacer(1, 0.15 * cm))

    story.append(Paragraph("КЛЮЧЕВЫЕ ДОСТИЖЕНИЯ ДЛЯ БИЗНЕСА", styles["section"]))

    project_blocks = [
        (
            "<b>Сейчас — оптимизация высоконагруженных систем (ВИМ):</b> ускорил массовые "
            "регламенты и расчеты на критичном пути закрытия дня при портфеле до 100 000 "
            "договоров; внедрил параллельные конвейеры тяжелых операций; операционное окно "
            "и закрытие периода укладываются в регламент."
        ),
        (
            "<b>Карьера — интеграции и архитектура (ВТБ, БКС):</b> построил контур брокера "
            "и депозитария с биржей, НРД и поставщиками данных; ежедневные операции "
            "без остановки торгового дня; запуск брокерского бэк-офиса ОАЭ."
        ),
        (
            "<b>Карьера — корпоративные системы (2000–2016):</b> внедрения УПП/УТ/ЗУП "
            "на производстве и в рознице: 2 500 сотрудников, 5–7 филиалов, 80–140 "
            "пользователей; опубликованное решение на 1c.ru."
        ),
        (
            "<b>Надежность и масштаб:</b> нагрузочные испытания, стабилизация вечерних "
            "регламентов, согласованный обмен между контурами ландшафта; приемка "
            "доработок у вендора с регрессией на копии ПРОД."
        ),
    ]
    for block in project_blocks:
        story.append(Paragraph(f"<bullet>&bull;</bullet> {block}", styles["bullet"]))
    story.append(Spacer(1, 0.12 * cm))

    story.append(Paragraph("ПРОФЕССИОНАЛЬНЫЕ НАВЫКИ", styles["section"]))
    story.append(skill_matrix(styles, [
        ("Оптимизация", "высоконагруженные системы, массовые регламенты, параллельные "
         "конвейеры, профилирование, нагрузочные испытания, замеры «было/стало»"),
        ("Платформа 1С", "8.3 (20+ лет), расширения, БСП, длительные операции, СКД, запросы"),
        ("Интеграции", "Kafka, HTTP/REST, SOAP, НРД, RuData, биржа, обмены — 15+ лет"),
        ("СУБД", "MS SQL (15+ лет): оптимизация запросов и регламентов, сверки 1С и SQL"),
        ("Корпоративный опыт", "УПП, УТ, ЗУП, ERP, внедрения на производстве и в рознице"),
        ("Качество", "Vanessa, SonarQube, Git, ревью кода, регрессия на копии ПРОД, Cursor"),
        ("Сертификаты", "1С: ERP (Проф + Спец-консультант), УПП, Платформа 8, РП, 7.7"),
    ]))
    story.append(Spacer(1, 0.15 * cm))

    story.append(Paragraph("ОПЫТ РАБОТЫ", styles["section"]))
    story.extend(job_block(
        styles,
        "АО ВИМ Инвестиции  |  Москва",
        "Ведущий программист 1С",
        "июль 2025 — настоящее время",
        "Оптимизация высоконагруженного ландшафта доверительного управления "
        "(4 конфигурации, портфель до 100 000 договоров розницы).",
        [
            "Провел профилирование и оптимизацию массовых регламентов на критичном пути "
            "закрытия дня. <b>Результат:</b> ускорение ключевых операций примерно в 3 раза, "
            "операционное окно выдерживается при росте портфеля.",
            "Спроектировал параллельные конвейеры для тяжелых массовых расчетов. "
            "<b>Результат:</b> длительные операции не блокируют закрытие дня и периода.",
            "Организовал нагрузочные испытания и стабилизацию вечерних регламентов. "
            "<b>Результат:</b> ландшафт готов к дальнейшему росту нагрузки.",
            "Веду постановки, ревью и приемку доработок вендора; разработка в среде "
            "<b>Cursor</b>.",
        ],
        tech_stack="1С 8.3, БСП, MS SQL, Kafka, HTTP, профилировщик, Vanessa, Git, Cursor",
    ))

    story.extend(job_block(
        styles,
        "ООО СБ-Брокер / НРБ банк (группа ВТБ)  |  Москва",
        "Ведущий программист 1С",
        "октябрь 2021 — апрель 2026",
        "Бэк-офис брокера и депозитарий в системно значимой финансовой организации.",
        [
            "Спроектировал интеграционный контур с биржей, НРД и поставщиками рыночных "
            "данных (Kafka, HTTP). <b>Результат:</b> ежедневные операции без остановки "
            "торгового дня.",
            "Разработал сверки 1С с MS SQL, оптимизировал тяжелые запросы отчетности. "
            "<b>Результат:</b> стабильная работа при пиковых нагрузках бэк-офиса.",
            "Внедрил деперсонализацию данных и Vanessa/SonarQube в процесс команды.",
        ],
        tech_stack="1С 8.3, Kafka, HTTP, НРД, RuData, MS SQL, Vanessa, SonarQube",
    ))

    story.extend(job_block(
        styles,
        "БКС-технологии  |  Москва",
        "Ведущий программист 1С / Руководитель группы (брокер ОАЭ)",
        "ноябрь 2016 — сентябрь 2021",
        "Бэк-офис брокера 8.2/8.3, мультиюрисдикционный контур.",
        [
            "Руководил командой брокера ОАЭ: постановка, ревью, координация с бизнесом.",
            "Спроектировал архитектуру доработок для выхода на рынок ОАЭ. "
            "<b>Результат:</b> запуск брокерского бэк-офиса на 1С в согласованные сроки.",
        ],
        tech_stack="1С 8.2/8.3, интеграции, отчетность",
    ))

    story.extend(job_block(
        styles,
        "Корпоративные внедрения: торговля и производство  |  2000 — 2016",
        "Ведущий специалист / РП / техдиректор",
        "ИнфоСофт, Ольвия ТПК, Суматра, ВИКОР, Баядера",
        "Корпоративные внедрения УПП, УТ, ЗУП на производстве и в дистрибуции.",
        [
            "Внедрил ЗУП на 2 500 сотрудников и УПП в 5–7 филиалах (80–140 пользователей). "
            "<b>Результат:</b> единый учет на предприятиях с филиальной сетью.",
            "Разработал KPI-зарплату «Обувь России»; ввел УПП на стрелочном заводе. "
            "<b>Результат:</b> опубликованное отраслевое решение на 1c.ru.",
            "Как техдиректор франчайзи управлял командой до 10 чел.",
        ],
        tech_stack="УПП, УТ, ЗУП, 7.7/8.x",
    ))

    bottom = Table([[
        Paragraph(
            "<b>ОБРАЗОВАНИЕ</b><br/><br/>"
            "Высшее, 1999<br/>"
            "ДНУЖТ им. В. Лазаряна<br/>"
            "ПО ВТ и АС (тех. кибернетика)",
            styles["body"],
        ),
        Paragraph(
            "<b>ПОРТФОЛИО</b><br/><br/>"
            "v8.1c.ru/news/newsAbout.jsp?id=1910<br/>"
            "1c.ru/.../solution.jsp?SolutionID=99734<br/><br/>"
            "<b>ЯЗЫКИ</b><br/>"
            "RU — родной | UA — C2 | EN — техдокументация<br/><br/>"
            "<b>ЖЕЛАЕМАЯ ДОЛЖНОСТЬ</b><br/>"
            "Ведущий программист 1С<br/>"
            "Высоконагруженные системы · FinTech<br/>"
            "Профессия HH: Программист, разработчик<br/>"
            "финтех · банк · доверительное управление<br/>"
            "от <b>650 000</b> руб. на руки, гибрид / удаленка, Москва",
            styles["body"],
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
        topMargin=3.3 * cm,
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
