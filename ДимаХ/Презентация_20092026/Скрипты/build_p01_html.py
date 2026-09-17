#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка Презентации 01 "Экономика: стоимость доработок силами Аванкор" в HTML.

Читает p01_dataset.json и генерирует слайд-дек с встроенным CSS и
диаграммами в виде inline SVG (без внешних CDN - работает офлайн на проекторе).
"""

import json
import os
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)

# Единые правила отображения чисел для всего пакета презентаций
from fmt import hrs, money_head, money_mln, nice_max, num_ths, ratio, rub

BASE = os.path.dirname(SCRIPTS)
DATA = os.path.join(SCRIPTS, "p01_dataset.json")
OUT = os.path.join(BASE, "01_avancor_economy.html")

# Корпоративная палитра пакета презентаций
C_NAVY = "#0b1f3a"
C_NAVY_MID = "#163a66"
C_TEAL = "#0e7c6b"
C_AMBER = "#c47a12"
C_LINE = "#d7dde8"
C_MUTED = "#6b7588"


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def esc(text):
    """Экранирование для HTML/SVG-текста."""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def short_title(text, limit=54):
    """Сокращает наименование задачи для подписи в таблице/диаграмме."""
    text = str(text).strip()
    # Убираем префиксы вида "IMAPPS-30448  " и служебные скобки вендора
    for prefix in ("[Аванкор] ", "[Аванокр] ", "[Аванкор]", "[для Аванкор] "):
        if text.startswith(prefix):
            text = text[len(prefix):]
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "\u2026"


MONTHS_RU = {
    "01": "янв", "02": "фев", "03": "мар", "04": "апр", "05": "май", "06": "июн",
    "07": "июл", "08": "авг", "09": "сен", "10": "окт", "11": "ноя", "12": "дек",
}


def month_label(stamp):
    """'2026-07' -> 'июл 26'."""
    year, month = stamp.split("-")
    return "%s %s" % (MONTHS_RU.get(month, month), year[2:])


# ----------------------------------------------------------------------------
# Диаграммы (inline SVG)
# ----------------------------------------------------------------------------

def svg_bars(tasks):
    """Горизонтальные парные столбцы: факт интеграции vs гипотеза полной разработки."""
    rows = sorted(tasks, key=lambda t: -t["hypo_cost"])
    ticks = 5
    max_cost = nice_max(max(t["hypo_cost"] for t in rows), ticks)

    # Пропорции подобраны так, чтобы диаграмма целиком укладывалась в слайд 16:9
    label_w = 200
    plot_w = 880
    row_h = 25
    bar_h = 9
    gap = 2
    top = 44
    height = top + len(rows) * row_h + 32
    width = label_w + plot_w + 120

    parts = ['<svg viewBox="0 0 %d %d" class="chart" role="img" '
             'aria-label="Сравнение фактической и гипотетической стоимости по задачам">' % (width, height)]

    # Сетка и подписи оси X
    for i in range(ticks + 1):
        value = max_cost * i / ticks
        x = label_w + plot_w * i / ticks
        parts.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="1"/>'
                     % (x, top - 12, x, height - 30, C_LINE))
        parts.append('<text x="%.1f" y="%d" class="ax" text-anchor="middle">%s</text>'
                     % (x, top - 20, num_ths(value)))
    parts.append('<text x="%.1f" y="%d" class="ax-title" text-anchor="middle">'
                 'Стоимость, тыс. \u20bd</text>' % (label_w + plot_w / 2, height - 12))

    for idx, t in enumerate(rows):
        y = top + idx * row_h
        w_hypo = plot_w * t["hypo_cost"] / max_cost
        w_fact = plot_w * t["fact_cost"] / max_cost

        parts.append('<text x="%d" y="%.1f" class="lbl" text-anchor="end">%s</text>'
                     % (label_w - 10, y + 12, esc(t["key"])))
        # Гипотеза - полная разработка вендором
        parts.append('<rect x="%d" y="%.1f" width="%.1f" height="%d" rx="2" fill="%s" '
                     'fill-opacity="0.88"/>' % (label_w, y, w_hypo, bar_h, C_NAVY_MID))
        # Факт - оплачена только интеграция
        parts.append('<rect x="%d" y="%.1f" width="%.1f" height="%d" rx="2" fill="%s"/>'
                     % (label_w, y + bar_h + gap, max(w_fact, 1.5), bar_h, C_AMBER))
        parts.append('<text x="%.1f" y="%.1f" class="val">%s</text>'
                     % (label_w + w_hypo + 6, y + 9, num_ths(t["hypo_cost"])))
        parts.append('<text x="%.1f" y="%.1f" class="val val-dim">%s</text>'
                     % (label_w + max(w_fact, 1.5) + 6, y + bar_h + gap + 9, num_ths(t["fact_cost"])))

    parts.append("</svg>")
    return "".join(parts)


def svg_donut(fact, saving):
    """Кольцевая диаграмма: доля экономии в гипотетическом объеме работ."""
    total = fact + saving
    size = 260
    cx = cy = size / 2
    r = 92
    stroke = 34
    circumference = 2 * 3.141592653589793 * r
    saving_len = circumference * saving / total
    pct = 100.0 * saving / total

    parts = ['<svg viewBox="0 0 %d %d" class="donut" role="img" '
             'aria-label="Доля экономии в гипотетической стоимости">' % (size, size)]
    parts.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="%s" '
                 'stroke-width="%d"/>' % (cx, cy, r, C_AMBER, stroke))
    parts.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="%s" '
                 'stroke-width="%d" stroke-dasharray="%.2f %.2f" stroke-linecap="butt" '
                 'transform="rotate(-90 %.1f %.1f)"/>'
                 % (cx, cy, r, C_TEAL, stroke, saving_len, circumference - saving_len, cx, cy))
    parts.append('<text x="%.1f" y="%.1f" class="donut-num" text-anchor="middle">%.0f%%</text>'
                 % (cx, cy - 6, pct))
    parts.append('<text x="%.1f" y="%.1f" class="donut-cap" text-anchor="middle">экономия</text>'
                 % (cx, cy + 16))
    parts.append('<text x="%.1f" y="%.1f" class="donut-sum" text-anchor="middle">%s \u20bd</text>'
                 % (cx, cy + 42, money_mln(saving)))
    parts.append("</svg>")
    return "".join(parts)


def svg_timeline(timeline):
    """Линейный график накопленной экономии по месяцам."""
    if not timeline:
        return ""
    width, height = 1000, 250
    pad_l, pad_r, pad_t, pad_b = 78, 24, 26, 50
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    ticks = 5
    max_val = nice_max(max(p["cumulative"] for p in timeline), ticks)
    step = plot_w / max(len(timeline) - 1, 1)

    def px(i):
        return pad_l + i * step

    def py(v):
        return pad_t + plot_h - plot_h * v / max_val

    parts = ['<svg viewBox="0 0 %d %d" class="chart" role="img" '
             'aria-label="Накопленная экономия по месяцам">' % (width, height)]

    # Горизонтальная сетка
    for i in range(ticks + 1):
        value = max_val * i / ticks
        y = py(value)
        parts.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1"/>'
                     % (pad_l, y, width - pad_r, y, C_LINE))
        parts.append('<text x="%d" y="%.1f" class="ax" text-anchor="end">%s</text>'
                     % (pad_l - 8, y + 4, num_ths(value)))

    # Область под линией
    area = " ".join("%.1f,%.1f" % (px(i), py(p["cumulative"])) for i, p in enumerate(timeline))
    parts.append('<polygon points="%.1f,%.1f %s %.1f,%.1f" fill="%s" fill-opacity="0.12"/>'
                 % (px(0), pad_t + plot_h, area, px(len(timeline) - 1), pad_t + plot_h, C_TEAL))
    parts.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="3" '
                 'stroke-linejoin="round"/>' % (area, C_TEAL))

    for i, p in enumerate(timeline):
        x, y = px(i), py(p["cumulative"])
        parts.append('<circle cx="%.1f" cy="%.1f" r="4.5" fill="#fff" stroke="%s" '
                     'stroke-width="2.5"/>' % (x, y, C_TEAL))
        parts.append('<text x="%.1f" y="%.1f" class="val" text-anchor="middle">%s</text>'
                     % (x, y - 12, num_ths(p["cumulative"])))
        parts.append('<text x="%.1f" y="%d" class="ax" text-anchor="middle">%s</text>'
                     % (x, height - 30, month_label(p["month"])))

    parts.append('<text x="%.1f" y="%d" class="ax-title" text-anchor="middle">'
                 'Накопленная экономия, тыс. \u20bd (по месяцу закрытия задачи)</text>'
                 % (pad_l + plot_w / 2, height - 8))
    parts.append("</svg>")
    return "".join(parts)


def svg_split(fact, saving, caption=""):
    """Единая полоса: из гипотетического объема оплачено vs сэкономлено (для темного слайда).

    Параметры:
      fact    - Число - фактически оплаченная вендору сумма, руб.
      saving  - Число - экономия компании, руб.
      caption - Строка - уточнение сценария в подписи над полосой
    """
    total = fact + saving
    width, height = 1000, 128
    x0, bar_w = 4, width - 8
    bar_y, bar_h = 40, 44
    fact_w = bar_w * fact / total
    save_w = bar_w - fact_w

    parts = ['<svg viewBox="0 0 %d %d" class="chart chart--flat" role="img" '
             'aria-label="Распределение гипотетической стоимости">' % (width, height)]
    parts.append('<text x="%d" y="20" class="d-cap">Гипотетическая стоимость полной '
                 'разработки вендором: %s \u20bd%s</text>'
                 % (x0, money_mln(total), esc(caption)))
    parts.append('<rect x="%d" y="%d" width="%.1f" height="%d" rx="4" fill="%s"/>'
                 % (x0, bar_y, fact_w, bar_h, C_AMBER))
    parts.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="4" fill="%s"/>'
                 % (x0 + fact_w, bar_y, save_w, bar_h, C_TEAL))

    parts.append('<text x="%.1f" y="%d" class="d-val" text-anchor="middle">%s \u20bd</text>'
                 % (x0 + fact_w / 2, bar_y + 28, money_head(fact)))
    parts.append('<text x="%.1f" y="%d" class="d-val" text-anchor="middle">%s \u20bd</text>'
                 % (x0 + fact_w + save_w / 2, bar_y + 28, money_head(saving)))
    parts.append('<text x="%.1f" y="%d" class="d-lbl" text-anchor="middle">'
                 'Оплачено вендору (интеграция) &#183; %.0f%%</text>'
                 % (x0 + fact_w / 2, bar_y + bar_h + 22, 100.0 * fact / total))
    parts.append('<text x="%.1f" y="%d" class="d-lbl" text-anchor="middle">'
                 'Экономия компании &#183; %.0f%%</text>'
                 % (x0 + fact_w + save_w / 2, bar_y + bar_h + 22, 100.0 * saving / total))
    parts.append("</svg>")
    return "".join(parts)


def svg_unpaid(tasks):
    """Горизонтальные столбцы: часы нашей команды по бесплатным задачам вендора.

    Гарантийные задачи (Bug) выделены отдельным цветом - они не попадают в экономию.
    """
    rows = [t for t in tasks if t["our_hours"] > 0]
    ticks = 4
    max_h = nice_max(max(t["our_hours"] for t in rows), ticks)

    # Пропорции ближе к квадрату: диаграмма заполняет высоту слайда
    label_w = 170
    plot_w = 470
    row_h = 36
    bar_h = 19
    top = 44
    height = top + len(rows) * row_h + 36
    width = label_w + plot_w + 100

    parts = ['<svg viewBox="0 0 %d %d" class="chart" role="img" '
             'aria-label="Часы нашей команды по бесплатным задачам вендора">' % (width, height)]

    for i in range(ticks + 1):
        value = max_h * i / ticks
        x = label_w + plot_w * i / ticks
        parts.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="1"/>'
                     % (x, top - 12, x, height - 30, C_LINE))
        parts.append('<text x="%.1f" y="%d" class="ax" text-anchor="middle">%s</text>'
                     % (x, top - 20, hrs(value)))
    parts.append('<text x="%.1f" y="%d" class="ax-title" text-anchor="middle">'
                 'Часы нашей команды</text>' % (label_w + plot_w / 2, height - 10))

    for idx, t in enumerate(rows):
        y = top + idx * row_h
        w = plot_w * t["our_hours"] / max_h
        warranty = t.get("warranty")
        parts.append('<text x="%d" y="%.1f" class="lbl" text-anchor="end">%s</text>'
                     % (label_w - 10, y + 14, esc(t["key"])))
        parts.append('<rect x="%d" y="%.1f" width="%.1f" height="%d" rx="2" fill="%s"/>'
                     % (label_w, y, max(w, 1.5), bar_h, C_MUTED if warranty else C_TEAL))
        tail = " &#183; гарантия, не в счет" if warranty else ""
        parts.append('<text x="%.1f" y="%.1f" class="val val-big">%s ч%s</text>'
                     % (label_w + max(w, 1.5) + 7, y + 15, hrs(t["our_hours"]), tail))

    parts.append("</svg>")
    return "".join(parts)


def svg_scenarios(scenarios):
    """Столбцы по сценариям: экономия делится на платные и бесплатные задачи."""
    # Пропорции ближе к квадрату: диаграмма заполняет высоту слайда
    width, height = 700, 404
    pad_l, pad_t, pad_b = 70, 38, 84
    plot_w = width - pad_l - 24
    plot_h = height - pad_t - pad_b
    ticks = 4
    max_val = nice_max(max(sc["saving_total"] for sc in scenarios), ticks)
    slot = plot_w / len(scenarios)
    bar_w = min(slot * 0.5, 128)

    parts = ['<svg viewBox="0 0 %d %d" class="chart" role="img" '
             'aria-label="Экономия по сценариям оценки">' % (width, height)]

    for i in range(ticks + 1):
        value = max_val * i / ticks
        y = pad_t + plot_h - plot_h * value / max_val
        parts.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1"/>'
                     % (pad_l, y, width - 28, y, C_LINE))
        parts.append('<text x="%d" y="%.1f" class="ax" text-anchor="end">%s</text>'
                     % (pad_l - 8, y + 4, num_ths(value)))

    for i, sc in enumerate(scenarios):
        x = pad_l + slot * i + (slot - bar_w) / 2
        h_paid = plot_h * sc["paid_saving"] / max_val
        h_free = plot_h * sc["free_hypo"] / max_val
        y_paid = pad_t + plot_h - h_paid
        y_free = y_paid - h_free

        # Экономия по платным задачам (основание столбца)
        parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                     % (x, y_paid, bar_w, h_paid, C_TEAL))
        # Экономия по бесплатным задачам (надстройка)
        if h_free > 0.5:
            parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                         % (x, y_free, bar_w, h_free, C_AMBER))
            parts.append('<text x="%.1f" y="%.1f" class="val" text-anchor="middle">+%s</text>'
                         % (x + bar_w / 2, y_free + h_free / 2 + 4, num_ths(sc["free_hypo"])))

        parts.append('<text x="%.1f" y="%.1f" class="val val-big" text-anchor="middle">%s \u20bd</text>'
                     % (x + bar_w / 2, y_free - 10, money_head(sc["saving_total"])))
        parts.append('<text x="%.1f" y="%d" class="lbl" text-anchor="middle">%s</text>'
                     % (x + bar_w / 2, height - 62, esc(sc["name"])))
        parts.append('<text x="%.1f" y="%d" class="ax ax-dim" text-anchor="middle">%s</text>'
                     % (x + bar_w / 2, height - 47, esc(sc["tag"])))
        parts.append('<text x="%.1f" y="%d" class="ax ax-dim" text-anchor="middle">'
                     'надбавка +%d%% &#183; сопровождение %d%%</text>'
                     % (x + bar_w / 2, height - 30, sc["overhead_pct"], sc["support_pct"]))

    parts.append('<text x="%.1f" y="%d" class="ax-title" text-anchor="middle">'
                 'Экономия компании, тыс. \u20bd</text>' % (pad_l + plot_w / 2, height - 8))
    parts.append("</svg>")
    return "".join(parts)


def svg_components(components):
    """Столбцы экономии по конфигурациям Аванкор (широкий компактный формат)."""
    width, height = 1000, 200
    pad_l, pad_b, pad_t = 64, 54, 24
    plot_w = width - pad_l - 24
    plot_h = height - pad_t - pad_b
    ticks = 3
    max_val = nice_max(max(c["saving"] for c in components), ticks)
    slot = plot_w / len(components)
    bar_w = min(slot * 0.42, 120)

    parts = ['<svg viewBox="0 0 %d %d" class="chart chart--flat" role="img" '
             'aria-label="Экономия по конфигурациям">' % (width, height)]
    for i in range(ticks + 1):
        value = max_val * i / ticks
        y = pad_t + plot_h - plot_h * value / max_val
        parts.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1"/>'
                     % (pad_l, y, width - 24, y, C_LINE))
        parts.append('<text x="%d" y="%.1f" class="ax" text-anchor="end">%s</text>'
                     % (pad_l - 8, y + 4, num_ths(value)))

    palette = [C_NAVY_MID, C_TEAL, C_AMBER, C_MUTED]
    for i, c in enumerate(components):
        x = pad_l + slot * i + (slot - bar_w) / 2
        h = plot_h * c["saving"] / max_val
        y = pad_t + plot_h - h
        parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3" fill="%s"/>'
                     % (x, y, bar_w, h, palette[i % len(palette)]))
        parts.append('<text x="%.1f" y="%.1f" class="val val-big" text-anchor="middle">%s \u20bd</text>'
                     % (x + bar_w / 2, y - 8, money_head(c["saving"])))
        parts.append('<text x="%.1f" y="%d" class="lbl" text-anchor="middle">%s</text>'
                     % (x + bar_w / 2, height - 34, esc(c["component"].replace("Avancore", ""))))
        parts.append('<text x="%.1f" y="%d" class="ax ax-dim" text-anchor="middle">'
                     '%d задач / %s ч нашей команды</text>'
                     % (x + bar_w / 2, height - 19, c["tasks"], hrs(c["our_hours"])))
    parts.append('<text x="%.1f" y="%d" class="ax-title" text-anchor="middle">'
                 'Экономия по конфигурациям, тыс. \u20bd</text>'
                 % (pad_l + plot_w / 2, height - 4))
    parts.append("</svg>")
    return "".join(parts)


# ----------------------------------------------------------------------------
# Таблица задач
# ----------------------------------------------------------------------------

def table_rows(tasks):
    """HTML-строки таблицы задач, отсортированные по экономии."""
    rows = sorted(tasks, key=lambda t: -t["saving"])
    out = []
    for t in rows:
        note = ' <span class="flag" title="Смета вендора не закрыта: разработка не оценена">смета открыта</span>' if t.get("estimate_open") else ""
        out.append(
            "<tr>"
            '<td class="k">%s</td>'
            '<td class="t">%s%s</td>'
            '<td class="c">%s</td>'
            '<td class="n">%s</td>'
            '<td class="n">%s</td>'
            '<td class="n">%s</td>'
            '<td class="n">%s</td>'
            '<td class="n hypo">%s</td>'
            '<td class="n save">%s</td>'
            "</tr>"
            % (esc(t["key"]), esc(short_title(t["summary"])), note,
               esc(t["component"].replace("Avancore", "")),
               hrs(t["our_hours"]), hrs(t["avancor_norm_hours"] or 0),
               rub(t["rate_used"]), rub(t["fact_cost"]),
               rub(t["hypo_cost"]), rub(t["saving"]))
        )
    return "\n".join(out)


# ----------------------------------------------------------------------------
# Сборка HTML
# ----------------------------------------------------------------------------

def build(payload):
    s = payload["summary"]
    tasks = [t for t in payload["tasks"] if t["paid"] == "yes" and t["avancor_cost"]]

    sc_min = next(x for x in payload["scenarios"] if x["id"] == "min")
    sc_real = next(x for x in payload["scenarios"] if x["id"] == "real")
    all_hours = s["our_hours_priced"] + s["unpaid_hours"]

    # KPI: крупное округленное число, под ним точное значение или пояснение
    kpis = [
        ("%s\u2013%s" % (money_mln(s["saving_min"]).replace("\u00a0млн", ""),
                         money_mln(s["saving_max"])), "\u20bd", "Экономия компании",
         "диапазон сценариев: %s \u2013 %s \u20bd" % (rub(s["saving_min"]), rub(s["saving_max"]))),
        ("\u00d7%s\u2013%s" % (ratio(sc_min["cost_ratio"]), ratio(sc_real["cost_ratio"])), "",
         "Во столько раз дороже вендор",
         "полная разработка против фактически оплаченной интеграции"),
        ("%d" % round(all_hours), "ч", "Работы нашей команды",
         "%d платных задач (%s ч) + %d без счета (%s ч)"
         % (s["tasks_priced"], hrs(s["our_hours_priced"]), s["tasks_unpaid"], hrs(s["unpaid_hours"]))),
        (rub(s["base_rate"]), "\u20bd/час", "Ставка Аванкор за нормо-час",
         "из смет вендора, диапазон %s\u2013%s \u20bd" % (rub(s["rate_min"]), rub(s["rate_max"]))),
    ]
    kpi_html = "\n".join(
        '<div class="kpi"><div class="kpi-num">%s<span class="kpi-unit">%s</span></div>'
        '<div class="kpi-lbl">%s</div><div class="kpi-sub">%s</div></div>'
        % (esc(num), esc(unit), esc(label), esc(sub)) for num, unit, label, sub in kpis
    )

    comp_rows = "\n".join(
        "<tr><td>%s</td><td class=\"n\">%d</td><td class=\"n\">%s</td>"
        "<td class=\"n\">%s</td><td class=\"n\">%s</td>"
        "<td class=\"n hypo\">%s</td><td class=\"n save\">%s</td></tr>"
        % (esc(c["component"]), c["tasks"], hrs(c["our_hours"]), hrs(c["avancor_hours"]),
           num_ths(c["fact_cost"]), num_ths(c["hypo_cost"]), num_ths(c["saving"]))
        for c in payload["by_component"]
    )

    # Разрез бесплатных задач по типу: гарантия помечается отдельно
    unpaid_type_rows = "\n".join(
        "<tr><td>%s</td><td class=\"n\">%d</td><td class=\"n\">%s</td><td>%s</td></tr>"
        % (esc(u["issue_type"]), u["tasks"], hrs(u["hours"]),
           '<span class="flag">гарантия, не в счет</span>' if u["warranty"] else "учитывается")
        for u in payload["unpaid_by_type"]
    )

    # Сценарии: допущения и итоговая экономия
    scen_rows = "\n".join(
        '<tr%s><td><strong>%s</strong><span class="sub">%s</span></td>'
        '<td class="n">%s</td><td class="n">%d%%</td>'
        '<td class="n save"><strong>%s &#8381;</strong></td></tr>'
        % (' class="row-hi"' if sc["id"] == "real" else "",
           esc(sc["name"]), esc(sc["tag"]),
           ("+%d%%" % sc["overhead_pct"]) if sc["overhead_pct"] else "нет",
           sc["support_pct"], money_head(sc["saving_total"]))
        for sc in payload["scenarios"]
    )

    # Сценарии в сводке на темном слайде выводов
    scen_sum_rows = "\n".join(
        '<tr><td class="lab">%s<span class="sub sub--dark">%s</span></td>'
        '<td class="v %s">%s &#8381;<span class="v-ex">%s &#8381;</span></td></tr>'
        % (esc(sc["name"]), esc(sc["tag"]),
           "v-save" if sc["id"] == "real" else "v-hypo",
           money_head(sc["saving_total"]), rub(sc["saving_total"]))
        for sc in payload["scenarios"]
    )

    ts_rows = "\n".join(
        "<tr><td>%s</td><td class=\"n\">%d</td><td class=\"n\">%s</td></tr>"
        % (esc(f["file"]), f["rows"], hrs(f["hours"]))
        for f in s["timesheet_files"]
    )

    html = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Презентация 01. Экономика: стоимость доработок силами Аванкор</title>
<style>
  :root {
    --ink: #0c1524;
    --ink-soft: #3a4558;
    --muted: %(muted)s;
    --line: %(line)s;
    --paper: #ffffff;
    --navy: %(navy)s;
    --navy-mid: %(navy_mid)s;
    --teal: %(teal)s;
    --teal-soft: #d8f3ee;
    --amber: %(amber)s;
    --amber-soft: #f8ecd8;
    --sky: #e4eef9;
    --slide-bg: #f5f7fb;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%%; margin: 0; }
  body {
    font-family: "Manrope", "Segoe UI", Arial, sans-serif;
    color: var(--ink);
    background: #0a1220;
    overflow: hidden;
  }
  .serif { font-family: "Instrument Serif", Georgia, "Times New Roman", serif; font-weight: 400; }

  .deck { position: relative; height: 100vh; overflow: hidden; }
  .slides { display: flex; height: 100%%; transition: transform .45s cubic-bezier(.4,0,.2,1); }
  .slide {
    flex: 0 0 100%%;
    height: 100%%;
    padding: 34px 5vw 78px;
    background: var(--slide-bg);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
  }
  .slide--title {
    background:
      radial-gradient(900px 420px at 88%% 6%%, rgba(14,124,107,.35), transparent 60%%),
      linear-gradient(135deg, #0b1f3a 0%%, #163a66 52%%, #0e5f57 100%%);
    color: #f4f7fb;
    justify-content: center;
  }
  .slide--dark {
    background: linear-gradient(150deg, #0f1d33 0%%, #1c3a5e 100%%);
    color: #e6edf6;
  }

  .eyebrow {
    font-size: 11px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase;
    color: var(--teal); margin-bottom: 10px;
  }
  .slide--title .eyebrow, .slide--dark .eyebrow { color: #6fdcc6; }
  h1 { font-size: clamp(1.9rem, 4vw, 3rem); line-height: 1.1; margin: 0 0 16px; letter-spacing: -.01em; }
  h2 { font-size: clamp(1.4rem, 2.6vw, 2.05rem); line-height: 1.15; margin: 0 0 8px; letter-spacing: -.01em; }
  .lead { font-size: clamp(.95rem, 1.5vw, 1.08rem); color: var(--muted); margin: 0 0 20px; max-width: 62rem; }
  .slide--title .lead, .slide--dark .lead { color: rgba(226,234,244,.86); }

  .kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-top: 26px; }
  .kpi {
    background: rgba(255,255,255,.09);
    border: 1px solid rgba(255,255,255,.16);
    border-radius: 16px; padding: 18px 16px 16px; backdrop-filter: blur(6px);
  }
  .kpi-num {
    font-size: clamp(1.6rem, 3vw, 2.5rem); font-weight: 800; letter-spacing: -.025em;
    color: #fff; line-height: 1.05; white-space: nowrap;
  }
  .kpi-unit { font-size: .5em; font-weight: 700; margin-left: 5px; color: rgba(244,247,251,.72); letter-spacing: 0; }
  .kpi-lbl { font-size: 13px; font-weight: 700; margin-top: 8px; color: rgba(244,247,251,.94); }
  .kpi-sub { font-size: 11.5px; margin-top: 5px; color: rgba(226,234,244,.62); line-height: 1.4; }

  .card {
    background: var(--paper); border: 1px solid var(--line); border-radius: 16px;
    padding: 16px 18px; box-shadow: 0 10px 30px rgba(11,31,58,.06);
  }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }
  .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
  .grid-donut { display: grid; grid-template-columns: 290px 1fr; gap: 16px; align-items: stretch; }
  .grid-unpaid { display: grid; grid-template-columns: 1.15fr 1fr; gap: 16px; align-items: start; }
  .grid-scen { display: grid; grid-template-columns: 1.25fr 1fr; gap: 16px; align-items: start; }
  .card--center { display: flex; flex-direction: column; justify-content: center; }
  /* Карточка на темном фоне (титул, выводы) */
  .card--glass {
    background: rgba(255,255,255,.07); border-color: rgba(255,255,255,.16);
    box-shadow: none; margin-top: 26px;
  }

  table { width: 100%%; border-collapse: collapse; font-size: 12.5px; }
  th, td { text-align: left; padding: 5px 9px; border-bottom: 1px solid var(--line); vertical-align: top; }
  th {
    background: var(--navy); color: #eef3f9; font-size: 10.5px; font-weight: 700;
    letter-spacing: .06em; text-transform: uppercase; position: sticky; top: 0;
  }
  td.n, th.n { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
  td.k { font-weight: 700; color: var(--navy-mid); white-space: nowrap; }
  td.c { color: var(--muted); white-space: nowrap; font-size: 12px; }
  td.hypo { color: var(--navy-mid); font-weight: 700; }
  td.save { color: #0a5c50; font-weight: 800; background: #f0faf7; }
  /* Полосатость только для светлых таблиц: .sum на темном слайде исключена */
  table:not(.sum) tbody tr:nth-child(even) td { background: #fafbfd; }
  table:not(.sum) tbody tr:nth-child(even) td.save { background: #e9f6f2; }
  tr.total td {
    background: var(--navy) !important; color: #fff; font-weight: 800; font-size: 13px;
    border-bottom: 0; position: sticky; bottom: 0;
  }
  /* Подсветка рекомендуемого сценария */
  tr.row-hi td { background: #eef7f4 !important; }
  tr.row-hi td.save { background: #ddf1eb !important; }
  /* Пояснение под названием в первой колонке */
  td .sub { display: block; font-size: 10.5px; font-weight: 600; color: var(--muted); margin-top: 1px; }
  td .sub--dark { color: rgba(226,234,244,.5); }
  .table-wrap { overflow: auto; max-height: 71vh; border: 1px solid var(--line); border-radius: 12px; background: #fff; }

  /* Сводная таблица на темном слайде: без светлой заливки строк */
  .sum { width: 100%%; border-collapse: collapse; font-size: 14px; }
  .sum td { padding: 9px 2px; border-bottom: 1px solid rgba(255,255,255,.13); background: transparent; }
  .sum tr:last-child td { border-bottom: 0; }
  .sum td.lab { color: rgba(226,234,244,.82); }
  .sum td.v {
    text-align: right; font-weight: 800; font-size: 17px; font-variant-numeric: tabular-nums;
    white-space: nowrap; letter-spacing: -.01em;
  }
  .sum td.v-hypo { color: #ffffff; }
  .sum td.v-fact { color: #f3c98a; }
  .sum td.v-save { color: #6fdcc6; }
  /* Точное значение мелким шрифтом под округленным */
  .v-ex {
    display: block; font-size: 10.5px; font-weight: 600; letter-spacing: 0;
    color: rgba(226,234,244,.45); margin-top: 1px;
  }

  .flag {
    display: inline-block; font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 999px;
    background: var(--amber-soft); color: #8a550c; border: 1px solid #edd9b0; white-space: nowrap;
  }

  .legend { display: flex; gap: 18px; flex-wrap: wrap; margin: 2px 0 10px; font-size: 12.5px; color: var(--ink-soft); }
  .legend span { display: inline-flex; align-items: center; gap: 7px; font-weight: 600; }
  .legend i { width: 13px; height: 13px; border-radius: 3px; display: inline-block; }

  /* max-height - страховка: SVG сохраняет пропорции и не выходит за слайд */
  .chart { width: 100%%; height: auto; max-height: 63vh; display: block; }
  .chart--flat { max-height: 30vh; }
  .donut { width: 100%%; max-width: 240px; height: auto; display: block; margin: 0 auto; }
  .chart text, .donut text { font-family: "Manrope", "Segoe UI", Arial, sans-serif; }
  .ax { font-size: 11px; fill: %(muted)s; }
  .ax-dim { font-size: 10px; fill: #94a0b3; }
  .ax-title { font-size: 11.5px; fill: %(muted)s; font-weight: 700; }
  .lbl { font-size: 11.5px; fill: #2c3a4f; font-weight: 700; }
  .val { font-size: 10.5px; fill: #2c3a4f; font-weight: 700; }
  .val-dim { fill: #8a6415; }
  .val-big { font-size: 14px; fill: #142a44; font-weight: 800; }
  /* Подписи диаграмм на темном слайде */
  .d-cap { font-size: 13px; fill: rgba(226,234,244,.72); font-weight: 700; }
  .d-val { font-size: 17px; fill: #0d2036; font-weight: 800; }
  .d-lbl { font-size: 12.5px; fill: rgba(226,234,244,.85); font-weight: 700; }
  .donut-num { font-size: 46px; font-weight: 800; fill: #0a5c50; }
  .donut-cap { font-size: 13px; fill: %(muted)s; font-weight: 700; }
  .donut-sum { font-size: 19px; font-weight: 800; fill: #0d2036; }

  .facts { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
  .facts li { display: flex; gap: 11px; align-items: flex-start; font-size: 14px; color: var(--ink-soft); }
  .facts .b {
    flex: 0 0 auto; width: 22px; height: 22px; border-radius: 7px; background: var(--teal);
    color: #fff; font-size: 11.5px; font-weight: 800; display: grid; place-items: center; margin-top: 1px;
  }
  .facts strong { color: var(--ink); }
  .slide--dark .facts li { color: rgba(226,234,244,.9); }
  .slide--dark .facts strong { color: #fff; }

  .formula {
    background: var(--sky); border: 1px solid #cfdff2; border-radius: 12px;
    padding: 13px 15px; font-size: 14px; color: #14314f; line-height: 1.6;
  }
  .formula code {
    font-family: ui-monospace, Consolas, monospace; font-size: 13px; background: #fff;
    padding: 2px 6px; border-radius: 5px; border: 1px solid #cfdff2;
  }
  .note {
    background: var(--amber-soft); border: 1px solid #edd9b0; border-radius: 12px;
    padding: 12px 14px; font-size: 12.5px; color: #6f4a10; line-height: 1.55;
  }
  .h4 {
    font-size: 11px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase;
    color: var(--muted); margin: 0 0 9px;
  }
  .improve {
    margin-top: auto; padding-top: 16px; display: flex; align-items: center; gap: 12px;
    flex-wrap: wrap; border-top: 1px dashed rgba(255,255,255,.25);
  }
  .improve .lbl2 { font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: rgba(226,234,244,.6); }
  .improve .badge {
    display: inline-flex; align-items: center; gap: 8px; padding: 8px 14px; border-radius: 999px;
    font-size: 13px; font-weight: 800; background: rgba(14,124,107,.24); color: #a8ebda;
    border: 1px solid rgba(111,220,198,.45);
  }
  .improve .badge::before { content: ""; width: 8px; height: 8px; border-radius: 50%%; background: #6fdcc6; }

  .src { margin-top: 14px; font-size: 11.5px; color: var(--muted); line-height: 1.5; }
  .slide--dark .src, .slide--title .src { color: rgba(226,234,244,.6); }

  /* Навигация */
  .nav {
    position: fixed; left: 0; right: 0; bottom: 0; height: 56px; display: flex;
    align-items: center; justify-content: space-between; padding: 0 5vw;
    background: rgba(10,18,32,.9); color: #cbd6e6; font-size: 12.5px; z-index: 20;
  }
  .dots { display: flex; gap: 7px; }
  .dot {
    width: 9px; height: 9px; border-radius: 50%%; background: #3d4c63; border: 0;
    cursor: pointer; padding: 0; transition: background .2s, transform .2s;
  }
  .dot.on { background: #6fdcc6; transform: scale(1.35); }
  .nav-btns { display: flex; gap: 8px; }
  .nav button.arrow {
    background: #1c2b44; color: #dbe5f2; border: 1px solid #35486a; border-radius: 8px;
    width: 34px; height: 30px; font-size: 14px; cursor: pointer;
  }
  .nav button.arrow:hover { background: #26395a; }
  .counter { font-variant-numeric: tabular-nums; font-weight: 700; }
  .deck-title { font-weight: 700; opacity: .75; }

  @media (max-width: 1080px) {
    .kpi-row, .grid-2, .grid-3 { grid-template-columns: 1fr 1fr; }
    .grid-donut { grid-template-columns: 1fr; }
  }
  @media (max-width: 680px) {
    .kpi-row, .grid-2, .grid-3 { grid-template-columns: 1fr; }
    .slide { padding: 26px 20px 74px; }
  }
  @media print {
    body, .deck { height: auto; overflow: visible; background: #fff; }
    .slides { display: block; transform: none !important; }
    .slide { height: auto; page-break-after: always; overflow: visible; }
    .nav { display: none; }
    .table-wrap { max-height: none; }
  }
</style>
</head>
<body>
<div class="deck">
  <div class="slides" id="slides">

    <!-- 1. Титул -->
    <section class="slide slide--title">
      <div class="eyebrow">Презентация 01 &middot; Пакет 20.09.2026</div>
      <h1 class="serif">Сколько стоили бы наши доработки,<br>если бы их делал Аванкор</h1>
      <p class="lead">
        По %(tasks_priced)d платным задачам вендор выставил счет только за интеграцию наших готовых
        решений &mdash; %(fact_h)s &#8381;. Ещё %(tasks_unpaid)d задач он закрыл вообще без счета.
        Если бы всю разработку вел Аванкор, компания заплатила бы кратно больше.
      </p>
      <div class="kpi-row">
%(kpi)s
      </div>
      <div class="card card--glass">
%(split)s
      </div>
      <div class="improve">
        <span class="lbl2">Вид улучшения</span>
        <span class="badge">Снижение внешних затрат (cost avoidance)</span>
      </div>
      <div class="src">
        Источники: выгрузка Jira по платным задачам вендора (%(tasks_total)d задач, из них %(tasks_paid)d
        с признаком оплаты), отчеты учета времени команды (%(ts_files)d файла, %(ts_hours)s ч по %(ts_tasks)d задачам).
        Ставка и нормо-часы &mdash; из смет самого вендора.
      </div>
    </section>

    <!-- 2. Методика -->
    <section class="slide">
      <div class="eyebrow">Методика расчета</div>
      <h2>Как считаем: только фактические данные, без допущений о ставке</h2>
      <p class="lead">
        Ставку вендора не оценивали экспертно &mdash; она вычислена из его собственных смет,
        где указаны и нормо-часы, и сумма в рублях.
      </p>
      <div class="grid-2">
        <div class="card">
          <p class="h4">Что берем из источников</p>
          <ul class="facts">
            <li><span class="b">1</span><span><strong>Часы нашей команды</strong> &mdash; из отчетов учета
              времени (Time Sheet) по каждой задаче; при отсутствии записей &mdash; Time Spent из Jira.</span></li>
            <li><span class="b">2</span><span><strong>Нормо-часы и сумма вендора</strong> &mdash; из поля сметы
              в задаче Jira: например, &laquo;5 нормо-часов. Стоимость составляет 19 500 руб&raquo;.</span></li>
            <li><span class="b">3</span><span><strong>Ставка</strong> = сумма / нормо-часы. По %(tasks_priced)d
              задачам она составила %(rate_min)s&ndash;%(rate_max)s &#8381;, преобладающая &mdash; %(base_rate)s &#8381;.</span></li>
            <li><span class="b">4</span><span><strong>Две группы задач.</strong> %(tasks_priced)d платных &mdash;
              вендор выставил счет за интеграцию нашего решения. %(tasks_unpaid)d бесплатных &mdash; счета
              не было вовсе, работу целиком закрыла наша команда.</span></li>
            <li><span class="b">5</span><span><strong>Что не берем в расчет.</strong> Гарантийные баги в
              продукте вендора и подзадачи без собственного учета времени.</span></li>
          </ul>
        </div>
        <div class="card">
          <p class="h4">Формула сравнения</p>
          <div class="formula">
            <div><strong>Факт</strong> = <code>сумма сметы вендора</code><br>
            <span style="color:#4a6280">вендор оплачен только за интеграцию готового решения</span></div>
            <div style="margin-top:11px"><strong>Гипотеза</strong> =
              <code>(наши часы &times; надбавка + нормо-часы вендора) &times; ставка</code><br>
            <span style="color:#4a6280">полный цикл разработки силами вендора</span></div>
            <div style="margin-top:11px"><strong>Бесплатные задачи</strong> =
              <code>часы &times; (1 &minus; доля сопровождения) &times; надбавка &times; ставка</code><br>
            <span style="color:#4a6280">вендор принял наш результат и не выставил счет</span></div>
            <div style="margin-top:11px"><strong>Экономия</strong> = <code>Гипотеза &minus; Факт</code></div>
          </div>
          <div class="note" style="margin-top:12px">
            <strong>Два коэффициента вместо одной цифры.</strong> <em>Надбавка</em> &mdash; насколько
            больше времени нужно вендору на аналитику и вхождение в контекст. <em>Доля
            сопровождения</em> &mdash; какую часть бесплатных задач он закрыл бы даром и сам.
            Оба коэффициента меняются по сценариям, поэтому результат &mdash; диапазон, а не точка.
          </div>
        </div>
      </div>
      <div class="src">
        Выборка: %(tasks_priced)d платных задач вендора и %(tasks_unpaid)d задач, закрытых без счета
        (%(unpaid_hours)s ч нашей команды). Обе группы разобраны на отдельных слайдах.
      </div>
    </section>

    <!-- 3. Диаграмма по задачам -->
    <section class="slide">
      <div class="eyebrow">Сравнение по задачам</div>
      <h2>Факт интеграции против полной разработки у вендора</h2>
      <div class="legend">
        <span><i style="background:%(navy_mid)s"></i>Гипотеза: полная разработка силами Аванкор</span>
        <span><i style="background:%(amber)s"></i>Факт: оплачена только интеграция</span>
      </div>
      <div class="card">
%(bars)s
      </div>
      <div class="src">
        Задачи отсортированы по гипотетической стоимости. Все суммы &mdash; в тысячах рублей;
        точные значения до рубля приведены в таблице на следующем слайде.
      </div>
    </section>

    <!-- 4. Таблица -->
    <section class="slide">
      <div class="eyebrow">Детализация</div>
      <h2>Все платные задачи: часы, ставки, суммы</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Задача</th>
              <th>Наименование</th>
              <th>Контур</th>
              <th class="n">Наши часы</th>
              <th class="n">Нормо-часы вендора</th>
              <th class="n">Ставка, &#8381;</th>
              <th class="n">Факт, &#8381;</th>
              <th class="n">Гипотеза, &#8381;</th>
              <th class="n">Экономия, &#8381;</th>
            </tr>
          </thead>
          <tbody>
%(rows)s
            <tr class="total">
              <td colspan="3">ИТОГО по %(tasks_priced)d задачам</td>
              <td class="n">%(our_hours)s</td>
              <td class="n">%(av_hours)s</td>
              <td class="n">&mdash;</td>
              <td class="n">%(fact)s</td>
              <td class="n">%(hypo)s</td>
              <td class="n">%(saving)s</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="src">
        &laquo;Смета открыта&raquo; &mdash; вендор оценил только анализ, стоимость разработки не зафиксирована;
        для такой задачи в расчет взята уже выставленная сумма.
      </div>
    </section>

    <!-- 5. Бесплатные задачи вендора -->
    <section class="slide">
      <div class="eyebrow">Скрытая часть экономии</div>
      <h2>Ещё %(tasks_unpaid)d задач вендор закрыл без счета &mdash; потому что работу сделали мы</h2>
      <p class="lead">
        По этим задачам вендор не выставил счет вообще: мы передали готовое решение, ему осталось
        принять результат. Если бы разработку вел он, часть этих задач стала бы платной.
      </p>
      <div class="grid-unpaid">
        <div class="card">
%(unpaid_bars)s
        </div>
        <div>
          <div class="card">
            <p class="h4">Из чего состоят %(tasks_unpaid)d задач</p>
            <table>
              <thead>
                <tr><th>Тип задачи</th><th class="n">Задач</th><th class="n">Часы</th><th>В расчете</th></tr>
              </thead>
              <tbody>
%(unpaid_type_rows)s
                <tr class="total">
                  <td>ИТОГО</td>
                  <td class="n">%(tasks_unpaid)d</td>
                  <td class="n">%(unpaid_hours)s</td>
                  <td>%(unpaid_billable_hours)s ч</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="note" style="margin-top:14px">
            <strong>Коэффициент сопровождения.</strong> Честно признаем: часть этих задач вендор
            закрыл бы бесплатно и сам &mdash; по гарантии на свой продукт или в рамках договора
            сопровождения. Поэтому в расчет берется не весь объем: гарантийные баги
            (%(unpaid_warranty_hours)s ч) исключены полностью, а из оставшихся
            %(unpaid_billable_hours)s ч в экономию попадает только доля, не покрытая
            сопровождением &mdash; от 0%% до 70%% в зависимости от сценария.
          </div>
        </div>
      </div>
      <div class="src">
        %(unpaid_no_hours_tasks)d задач из %(tasks_unpaid)d &mdash; подзадачи без собственного учета времени
        (часы отнесены на родительскую задачу), поэтому в расчете они не участвуют.
        Ставка для оценки &mdash; преобладающая %(base_rate)s &#8381; за нормо-час.
      </div>
    </section>

    <!-- 6. Сценарии оценки -->
    <section class="slide">
      <div class="eyebrow">Диапазон оценки</div>
      <h2>Три сценария: от заведомо заниженного до реалистичного</h2>
      <p class="lead">
        Единственная цифра всегда спорна, поэтому показываем диапазон. Сценарии различаются двумя
        допущениями: сколько времени вендору нужно на аналитику и какую часть бесплатных задач
        он закрыл бы сам.
      </p>
      <div class="grid-scen">
        <div class="card">
%(scenarios_chart)s
          <div class="legend" style="justify-content:center;margin:6px 0 0">
            <span><i style="background:%(teal)s"></i>Экономия по %(tasks_priced)d платным задачам</span>
            <span><i style="background:%(amber)s"></i>Экономия по бесплатным задачам</span>
          </div>
        </div>
        <div class="card">
          <p class="h4">Допущения и результат</p>
          <table>
            <thead>
              <tr>
                <th>Сценарий</th>
                <th class="n">Надбавка вендора</th>
                <th class="n">Ушло бы в сопровождение</th>
                <th class="n">Экономия</th>
              </tr>
            </thead>
            <tbody>
%(scen_rows)s
            </tbody>
          </table>
          <div class="note" style="margin-top:12px">
            <strong>Откуда надбавка +40%%.</strong> В задаче IMAPPS-32896 вендор выставил
            16 нормо-часов только за анализ (74 880 &#8381;) при 3,5 часах нашей команды на всю
            задачу &mdash; и разработку в той смете еще не оценил. Надбавка 40%% на аналитику и
            вхождение в контекст на этом фоне остается осторожной.
          </div>
        </div>
      </div>
      <div class="src">
        Надбавка применяется к часам нашей команды: вендору нужно самому проанализировать проблему,
        изучить контекст конфигурации и согласовать решение. Нормо-часы интеграции берутся из смет без надбавки.
      </div>
    </section>

    <!-- 5. Структура экономии -->
    <section class="slide">
      <div class="eyebrow">Структура</div>
      <h2>Доля экономии в гипотетическом объеме работ</h2>
      <div class="grid-donut">
        <div class="card card--center">
%(donut)s
          <div class="legend" style="justify-content:center;margin:12px 0 0">
            <span><i style="background:%(teal)s"></i>Экономия</span>
            <span><i style="background:%(amber)s"></i>Фактически оплачено</span>
          </div>
        </div>
        <div class="card">
          <p class="h4">Разрез по конфигурациям</p>
          <table>
            <thead>
              <tr>
                <th>Конфигурация</th>
                <th class="n">Задач</th>
                <th class="n">Наши часы</th>
                <th class="n">Нормо-часы</th>
                <th class="n">Факт, тыс. &#8381;</th>
                <th class="n">Гипотеза, тыс. &#8381;</th>
                <th class="n">Экономия, тыс. &#8381;</th>
              </tr>
            </thead>
            <tbody>
%(comp_rows)s
            </tbody>
          </table>
          <div class="note" style="margin-top:12px">
            <strong>Где эффект максимален.</strong> В контурах ДУ и Финансы наша команда закрывает
            крупные задачи оптимизации, а вендору остается только интеграция &mdash; там и накоплена
            основная экономия. В ПИФ доля вендора выше: задачи мелкие, и его нормо-часы сопоставимы
            с нашими трудозатратами.
          </div>
        </div>
      </div>
      <div class="card" style="margin-top:14px">
%(components)s
      </div>
      <div class="src">
        Из гипотетического объема %(hypo_h)s &#8381; фактически оплачено вендору %(fact_h)s &#8381;
        (%(fact_share)s%%), сэкономлено %(saving_h)s &#8381; (%(saving_pct)s%%).
        Точные суммы: %(hypo)s / %(fact)s / %(saving)s &#8381;.
      </div>
    </section>

    <!-- 6. Динамика -->
    <section class="slide">
      <div class="eyebrow">Динамика</div>
      <h2>Накопленная экономия по месяцам</h2>
      <p class="lead" style="margin-bottom:12px">
        Экономия формируется неравномерно: основной вклад дают крупные задачи оптимизации,
        где объем нашей разработки многократно превышает интеграционные нормо-часы вендора.
      </p>
      <div class="card">
%(timeline)s
      </div>
      <div class="grid-3" style="margin-top:14px">
        <div class="card">
          <p class="h4">Источник часов команды</p>
          <table>
            <thead><tr><th>Файл учета времени</th><th class="n">Записей</th><th class="n">Часов</th></tr></thead>
            <tbody>
%(ts_rows)s
            </tbody>
          </table>
        </div>
        <div class="card">
          <p class="h4">Что в этом объеме</p>
          <ul class="facts">
            <li><span class="b">&#8226;</span><span>%(ts_hours)s ч учтенного времени по %(ts_tasks)d задачам всего</span></li>
            <li><span class="b">&#8226;</span><span>%(our_hours)s ч из них &mdash; по %(tasks_priced)d платным задачам вендора</span></li>
            <li><span class="b">&#8226;</span><span>%(av_hours)s нормо-часов &mdash; вклад вендора (интеграция)</span></li>
          </ul>
        </div>
        <div class="card">
          <p class="h4">Ключевой механизм</p>
          <p style="margin:0;font-size:13.5px;color:var(--ink-soft);line-height:1.55">
            Наша команда выполняет анализ, разработку и тестирование, вендору передается
            готовое расширение с планом внедрения. Вендор оплачивается только за проверку
            и включение доработки в свою поставку.
          </p>
        </div>
      </div>
    </section>

    <!-- 7. Выводы -->
    <section class="slide slide--dark">
      <div class="eyebrow">Выводы</div>
      <h2 class="serif" style="font-size:clamp(1.7rem,3.2vw,2.5rem)">Что это значит для компании</h2>
      <div class="grid-2" style="margin-top:8px">
        <div>
          <ul class="facts">
            <li><span class="b">1</span><span><strong>От %(saving_h)s до %(saving_max_h)s &#8381;
              не израсходовано</strong> на внешнюю разработку. Нижняя граница &mdash; только платные
              задачи без надбавок, верхняя &mdash; с бесплатными задачами и реальными накладными вендора.</span></li>
            <li><span class="b">2</span><span><strong>Полная разработка у вендора обошлась бы в
              %(ratio)s&ndash;%(ratio_max)s раза дороже</strong> фактически оплаченной
              интеграции (%(fact_h)s &#8381;).</span></li>
            <li><span class="b">3</span><span><strong>%(our_share)s%% объема работ</strong> в часах закрыто
              внутренней командой &mdash; вендор выступает только приемной стороной.</span></li>
            <li><span class="b">4</span><span><strong>Даже нижняя граница честная:</strong> ставка взята
              из смет вендора, гарантийные баги исключены, а половина бесплатных задач списана
              в его сопровождение.</span></li>
          </ul>
        </div>
        <div>
          <div class="card" style="background:rgba(255,255,255,.07);border-color:rgba(255,255,255,.16)">
            <p class="h4" style="color:rgba(226,234,244,.6)">Экономия по сценариям</p>
            <table class="sum">
              <tbody>
%(scen_sum_rows)s
                <tr><td class="lab">Фактически оплачено вендору</td>
                    <td class="v v-fact">%(fact_h)s &#8381;<span class="v-ex">%(fact)s &#8381;</span></td></tr>
                <tr><td class="lab">Работы нашей команды по всем %(tasks_total_used)d задачам</td>
                    <td class="v v-hypo">%(all_hours_r)s ч<span class="v-ex">%(our_hours)s + %(unpaid_hours)s ч</span></td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <div class="card card--glass" style="margin-top:18px">
%(split)s
      </div>
      <div class="improve">
        <span class="lbl2">Вид улучшения</span>
        <span class="badge">Снижение внешних затрат (cost avoidance)</span>
      </div>
      <div class="src">
        Расчет по выгрузкам Jira и отчетам учета времени на 17.09.2026. Ставка вендора и нормо-часы &mdash;
        из его собственных смет в задачах. Гипотетическая стоимость &mdash; расчетная величина;
        коэффициенты надбавки и сопровождения по каждому сценарию приведены на слайде 6.
      </div>
    </section>

  </div>

  <nav class="nav">
    <span class="deck-title">01 &middot; Экономика: стоимость доработок силами Аванкор</span>
    <div class="dots" id="dots"></div>
    <div class="nav-btns">
      <span class="counter" id="counter" style="margin-right:10px;align-self:center"></span>
      <button class="arrow" id="prev" aria-label="Назад">&#8592;</button>
      <button class="arrow" id="next" aria-label="Вперед">&#8594;</button>
    </div>
  </nav>
</div>

<script>
(function () {
  var slidesEl = document.getElementById('slides');
  var total = slidesEl.children.length;
  var current = 0;
  var dotsEl = document.getElementById('dots');
  var counterEl = document.getElementById('counter');

  for (var i = 0; i < total; i++) {
    var dot = document.createElement('button');
    dot.className = 'dot';
    dot.setAttribute('aria-label', 'Слайд ' + (i + 1));
    dot.dataset.index = i;
    dotsEl.appendChild(dot);
  }

  function render() {
    slidesEl.style.transform = 'translateX(-' + (current * 100) + '%%)';
    var dots = dotsEl.children;
    for (var i = 0; i < dots.length; i++) {
      dots[i].className = 'dot' + (i === current ? ' on' : '');
    }
    counterEl.textContent = (current + 1) + ' / ' + total;
  }

  function go(index) {
    current = Math.max(0, Math.min(total - 1, index));
    render();
  }

  document.getElementById('prev').addEventListener('click', function () { go(current - 1); });
  document.getElementById('next').addEventListener('click', function () { go(current + 1); });
  dotsEl.addEventListener('click', function (e) {
    if (e.target.dataset.index !== undefined) { go(parseInt(e.target.dataset.index, 10)); }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') { go(current + 1); }
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { go(current - 1); }
    else if (e.key === 'Home') { go(0); }
    else if (e.key === 'End') { go(total - 1); }
  });

  render();
})();
</script>
</body>
</html>
""" % {
        "muted": C_MUTED, "line": C_LINE, "navy": C_NAVY, "navy_mid": C_NAVY_MID,
        "teal": C_TEAL, "amber": C_AMBER,
        "kpi": kpi_html,
        "bars": svg_bars(tasks),
        "donut": svg_donut(s["fact_cost_total"], s["saving_total"]),
        # На титуле и в выводах показываем нижнюю границу - консервативный сценарий
        "split": svg_split(s["fact_cost_total"], s["saving_total"],
                           "  \u00b7  консервативный сценарий, только платные задачи"),
        "timeline": svg_timeline(payload["timeline"]),
        "components": svg_components(payload["by_component"]),
        "unpaid_bars": svg_unpaid(payload["unpaid_tasks"]),
        "scenarios_chart": svg_scenarios(payload["scenarios"]),
        "rows": table_rows(tasks),
        "comp_rows": comp_rows,
        "unpaid_type_rows": unpaid_type_rows,
        "scen_rows": scen_rows,
        "scen_sum_rows": scen_sum_rows,
        "ts_rows": ts_rows,
        "tasks_total": s["tasks_total"],
        "tasks_paid": s["tasks_paid"],
        "tasks_priced": s["tasks_priced"],
        "tasks_unpaid": s["tasks_unpaid"],
        "unpaid_hours": hrs(s["unpaid_hours"]),
        "unpaid_billable_hours": hrs(s["unpaid_billable_hours"]),
        "unpaid_warranty_hours": hrs(s["unpaid_warranty_hours"]),
        "unpaid_no_hours_tasks": s["unpaid_no_hours_tasks"],
        "our_hours": hrs(s["our_hours_priced"]),
        "our_hours_r": "%d" % round(s["our_hours_priced"]),
        "av_hours": hrs(s["avancor_norm_hours_priced"]),
        # Точные суммы - для таблиц-первоисточников и сносок
        "fact": rub(s["fact_cost_total"]),
        "hypo": rub(s["hypo_cost_total"]),
        "saving": rub(s["saving_total"]),
        # Округленные суммы - для заголовков и выводов
        "fact_h": money_head(s["fact_cost_total"]),
        "hypo_h": money_head(s["hypo_cost_total"]),
        "saving_h": money_head(s["saving_total"]),
        "saving_max_h": money_head(s["saving_max"]),
        "saving_pct": ("%.0f" % s["saving_pct"]),
        "fact_share": ("%.0f" % s["fact_share_pct"]),
        "ratio": ratio(s["cost_ratio"]),
        "ratio_max": ratio(sc_real["cost_ratio"]),
        "all_hours_r": "%d" % round(all_hours),
        "tasks_total_used": s["tasks_priced"] + s["tasks_unpaid"],
        "our_share": ("%.0f" % s["our_hours_share_pct"]),
        "base_rate": rub(s["base_rate"]),
        "rate_min": rub(s["rate_min"]),
        "rate_max": rub(s["rate_max"]),
        "ts_files": len(s["timesheet_files"]),
        "ts_hours": hrs(s["timesheet_hours_total"]),
        "ts_tasks": s["timesheet_tasks"],
    }
    return html


def main():
    with open(DATA, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    html = build(payload)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)

    safe_print("OK - presentation written: %s" % os.path.basename(OUT))
    safe_print("size = %.1f KB" % (len(html.encode("utf-8")) / 1024.0))


if __name__ == "__main__":
    sys.exit(main())
