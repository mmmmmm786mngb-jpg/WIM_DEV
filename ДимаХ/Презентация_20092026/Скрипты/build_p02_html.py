#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка Презентации 02 "Эффект Cursor: экономия человеко-часов ИТ" в HTML.

Читает p02_dataset.json, встраивает CSS и SVG. Без CDN - работает офлайн.
"""

import json
import os
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)

from fmt import hrs, nice_max, pct, rub

BASE = os.path.dirname(SCRIPTS)
DATA = os.path.join(SCRIPTS, "p02_dataset.json")
OUT = os.path.join(BASE, "02_cursor_speedup.html")

C_NAVY = "#0b1f3a"
C_NAVY_MID = "#163a66"
C_TEAL = "#0e7c6b"
C_AMBER = "#c47a12"
C_LINE = "#d7dde8"
C_MUTED = "#6b7588"

TOP_BARS = 14
TOP_TABLE = 18


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def short_title(text, limit=52):
    text = str(text).strip()
    for prefix in ("[Оптимизировать] ", "[Вн.команда] ", "[для Аванкор] "):
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
    year, month = stamp.split("-")
    return "%s %s" % (MONTHS_RU.get(month, month), year[2:])


def date_ru(iso):
    year, month, day = iso.split("-")
    return "%d %s %s" % (int(day), MONTHS_RU.get(month, month), year)


def months_txt(value):
    return ("%.1f" % value).replace(".", ",")


def hrs_year(value):
    """Годовые часы для KPI: округление до десятков."""
    return hrs(int(round(value / 10.0) * 10))


def fte_share(value):
    txt = ("%.2f" % value).replace(".", ",")
    if txt.endswith("0"):
        txt = txt[:-1]
        if txt.endswith(","):
            txt = txt[:-1]
    return txt


def ru_tasks(n, adj=""):
    n10 = abs(n) % 10
    n100 = abs(n) % 100
    if 11 <= n100 <= 14:
        noun = "задач"
    elif n10 == 1:
        noun = "задача"
    elif 2 <= n10 <= 4:
        noun = "задачи"
    else:
        noun = "задач"
    if adj:
        return "%d %s %s" % (n, adj, noun)
    return "%d %s" % (n, noun)


def by_k(tasks, k):
    """Копия задач с гипотезой без Cursor по коэффициенту k."""
    out = []
    for t in tasks:
        without = t["our_hours"] * k
        out.append({
            "key": t["key"],
            "summary": t["summary"],
            "contour": t["contour"],
            "our_hours": t["our_hours"],
            "without_hours": round(without, 2),
            "saved_hours": round(without - t["our_hours"], 2),
        })
    return out


def svg_bars(tasks, k):
    """Парные горизонтальные столбцы: факт с Cursor vs прогноз без ИИ."""
    ranked = sorted(tasks, key=lambda t: -t["our_hours"])
    head = ranked[:TOP_BARS]
    rows = by_k(head, k)

    ticks = 5
    max_h = nice_max(max(r["without_hours"] for r in rows), ticks)
    label_w = 168
    plot_w = 900
    row_h = 28
    bar_h = 10
    gap = 2
    top = 44
    height = top + len(rows) * row_h + 34
    width = label_w + plot_w + 90

    parts = ['<svg viewBox="0 0 %d %d" class="chart" role="img" '
             'aria-label="Факт с Cursor против прогноза без ИИ">' % (width, height)]
    for i in range(ticks + 1):
        value = max_h * i / ticks
        x = label_w + plot_w * i / ticks
        parts.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="1"/>'
                     % (x, top - 12, x, height - 30, C_LINE))
        parts.append('<text x="%.1f" y="%d" class="ax" text-anchor="middle">%s</text>'
                     % (x, top - 20, hrs(value)))
    parts.append('<text x="%.1f" y="%d" class="ax-title" text-anchor="middle">'
                 'Человеко-часы</text>' % (label_w + plot_w / 2, height - 10))

    for idx, r in enumerate(rows):
        y = top + idx * row_h
        w_wo = plot_w * r["without_hours"] / max_h
        w_fact = plot_w * r["our_hours"] / max_h
        parts.append('<text x="%d" y="%.1f" class="lbl" text-anchor="end">%s</text>'
                     % (label_w - 10, y + 14, esc(r["key"])))
        parts.append('<rect x="%d" y="%.1f" width="%.1f" height="%d" rx="2" fill="%s" '
                     'fill-opacity="0.88"/>' % (label_w, y, w_wo, bar_h, C_NAVY_MID))
        parts.append('<rect x="%d" y="%.1f" width="%.1f" height="%d" rx="2" fill="%s"/>'
                     % (label_w, y + bar_h + gap, max(w_fact, 1.5), bar_h, C_TEAL))
        parts.append('<text x="%.1f" y="%.1f" class="val">%s</text>'
                     % (label_w + w_wo + 6, y + 9, hrs(round(r["without_hours"]))))
        parts.append('<text x="%.1f" y="%.1f" class="val val-dim">%s</text>'
                     % (label_w + max(w_fact, 1.5) + 6, y + bar_h + gap + 10, hrs(r["our_hours"])))
    parts.append("</svg>")
    return "".join(parts)


def svg_timeline(timeline, k):
    """Накопленная экономия часов по месяцам закрытия задач."""
    if not timeline:
        return ""
    points = []
    cum = 0.0
    for p in timeline:
        hours = p.get("hours") or p.get("fact_hours") or 0.0
        cum += hours * (k - 1.0)
        points.append({"month": p["month"], "cumulative_saved": cum})
    width, height = 1000, 220
    pad_l, pad_r, pad_t, pad_b = 62, 24, 28, 52
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    ticks = 4
    max_val = nice_max(max(p["cumulative_saved"] for p in points), ticks)
    step = plot_w / max(len(points) - 1, 1)

    def px(i):
        return pad_l + i * step

    def py(v):
        return pad_t + plot_h - plot_h * v / max_val

    parts = ['<svg viewBox="0 0 %d %d" class="chart" role="img" '
             'aria-label="Накопленная экономия часов">' % (width, height)]
    for i in range(ticks + 1):
        value = max_val * i / ticks
        y = py(value)
        parts.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1"/>'
                     % (pad_l, y, width - pad_r, y, C_LINE))
        parts.append('<text x="%d" y="%.1f" class="ax" text-anchor="end">%s</text>'
                     % (pad_l - 8, y + 4, hrs(value)))

    area = " ".join("%.1f,%.1f" % (px(i), py(p["cumulative_saved"])) for i, p in enumerate(points))
    parts.append('<polygon points="%.1f,%.1f %s %.1f,%.1f" fill="%s" fill-opacity="0.12"/>'
                 % (px(0), pad_t + plot_h, area, px(len(points) - 1), pad_t + plot_h, C_TEAL))
    path = " ".join("%.1f,%.1f" % (px(i), py(p["cumulative_saved"])) for i, p in enumerate(points))
    parts.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.5"/>' % (path, C_TEAL))
    for i, p in enumerate(points):
        x, y = px(i), py(p["cumulative_saved"])
        parts.append('<circle cx="%.1f" cy="%.1f" r="4.5" fill="#fff" stroke="%s" stroke-width="2"/>'
                     % (x, y, C_TEAL))
        parts.append('<text x="%.1f" y="%.1f" class="val" text-anchor="middle">%s</text>'
                     % (x, y - 12, hrs(round(p["cumulative_saved"]))))
        parts.append('<text x="%.1f" y="%d" class="ax" text-anchor="middle">%s</text>'
                     % (x, height - 32, month_label(p["month"])))
    parts.append('<text x="%.1f" y="%d" class="ax-title" text-anchor="middle">'
                 'Накопленная экономия часов: 25%% быстрее (McKinsey, рефакторинг)</text>'
                 % (pad_l + plot_w / 2, height - 8))
    parts.append("</svg>")
    return "".join(parts)


def svg_split(fact, saved, caption=""):
    """Полоса: потраченные часы vs не потраченные (экономия)."""
    total = fact + saved
    width, height = 1000, 128
    x0, bar_w = 4, width - 8
    bar_y, bar_h = 40, 44
    fact_w = bar_w * fact / total
    save_w = bar_w - fact_w
    parts = ['<svg viewBox="0 0 %d %d" class="chart chart--flat" role="img" '
             'aria-label="Факт и экономия часов">' % (width, height)]
    parts.append('<text x="%d" y="20" class="d-cap">Объем без Cursor: %s ч%s</text>'
                 % (x0, hrs(total), esc(caption)))
    parts.append('<rect x="%d" y="%d" width="%.1f" height="%d" rx="4" fill="%s"/>'
                 % (x0, bar_y, fact_w, bar_h, C_AMBER))
    parts.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="4" fill="%s"/>'
                 % (x0 + fact_w, bar_y, save_w, bar_h, C_TEAL))
    parts.append('<text x="%.1f" y="%d" class="d-val" text-anchor="middle">%s ч</text>'
                 % (x0 + fact_w / 2, bar_y + 28, hrs(fact)))
    parts.append('<text x="%.1f" y="%d" class="d-val" text-anchor="middle">%s ч</text>'
                 % (x0 + fact_w + save_w / 2, bar_y + 28, hrs(saved)))
    parts.append('<text x="%.1f" y="%d" class="d-lbl" text-anchor="middle">'
                 'Факт с Cursor &#183; %.0f%%</text>'
                 % (x0 + fact_w / 2, bar_y + bar_h + 22, 100.0 * fact / total))
    parts.append('<text x="%.1f" y="%d" class="d-lbl" text-anchor="middle">'
                 'Не потрачено &#183; %.0f%%</text>'
                 % (x0 + fact_w + save_w / 2, bar_y + bar_h + 22, 100.0 * saved / total))
    parts.append("</svg>")
    return "".join(parts)


def svg_fit(chosen_pct):
    """Шкала исследований: какой процент ускорения к нашему типу задач."""
    width, height = 700, 390
    pad_l, pad_r, pad_t, pad_b = 28, 28, 48, 56
    plot_w = width - pad_l - pad_r
    axis_y = 168
    max_pct = 60.0

    def px(pct):
        return pad_l + plot_w * pct / max_pct

    marks = [
        (21, "Google, поле", "21%", "support"),
        (chosen_pct, "наш коэффициент", "25%", "chosen"),
        (40, "McKinsey, новый код", "40%", "reject"),
        (55.8, "GitHub, лаборатория JS", "56%", "reject"),
    ]
    parts = ['<svg viewBox="0 0 %d %d" class="chart" role="img" '
             'aria-label="Выбор коэффициента ускорения">' % (width, height)]
    parts.append('<text x="%d" y="24" class="ax-title">Ускорение, %% времени задачи. '
                 'Подходит только то, что измеряли на похожей работе</text>' % pad_l)
    parts.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="3"/>'
                 % (pad_l, axis_y, width - pad_r, axis_y, C_LINE))
    for tick in (0, 10, 20, 30, 40, 50, 60):
        x = px(tick)
        parts.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="1"/>'
                     % (x, axis_y - 6, x, axis_y + 6, C_MUTED))
        parts.append('<text x="%.1f" y="%d" class="ax" text-anchor="middle">%d</text>'
                     % (x, axis_y + 22, tick))
    # полоса McKinsey рефакторинг 20-30
    x0, x1 = px(20), px(30)
    parts.append('<rect x="%.1f" y="%d" width="%.1f" height="18" rx="4" fill="%s" fill-opacity="0.22"/>'
                 % (x0, axis_y - 9, x1 - x0, C_TEAL))
    parts.append('<text x="%.1f" y="%d" class="ax-title" text-anchor="middle">'
                 'McKinsey, рефакторинг 20-30%%</text>' % ((x0 + x1) / 2, axis_y - 18))
    y_off = {"chosen": -78, "support": 58, "reject": -78}
    used = {}
    for pct, name, label, kind in marks:
        x = px(pct)
        fill = C_TEAL if kind == "chosen" else (C_NAVY_MID if kind == "support" else C_MUTED)
        r = 9 if kind == "chosen" else 6
        parts.append('<circle cx="%.1f" cy="%d" r="%d" fill="%s"/>' % (x, axis_y, r, fill))
        dy = y_off[kind]
        if kind == "reject" and used.get("reject"):
            dy = 78
        used[kind] = True
        parts.append('<text x="%.1f" y="%.1f" class="lbl" text-anchor="middle" fill="%s">%s</text>'
                     % (x, axis_y + dy, fill, esc(name)))
        parts.append('<text x="%.1f" y="%.1f" class="val-big" text-anchor="middle" fill="%s">%s</text>'
                     % (x, axis_y + dy + 16, fill, label))
    parts.append('<text x="%.1f" y="%d" class="ax-title" text-anchor="middle">'
                 'Не берём справа от полосы: это другой тип задач</text>'
                 % (pad_l + plot_w / 2, height - 14))
    parts.append("</svg>")
    return "".join(parts)


def svg_contours(contours):
    """Столбцы фактических часов по контурам."""
    rows = [c for c in contours if c["hours"] > 0]
    width, height = 1000, 168
    pad_l, pad_b, pad_t = 54, 48, 28
    plot_w = width - pad_l - 20
    plot_h = height - pad_t - pad_b
    ticks = 3
    max_val = nice_max(max(c["hours"] for c in rows), ticks)
    slot = plot_w / len(rows)
    bar_w = min(slot * 0.42, 110)
    palette = [C_NAVY_MID, C_TEAL, C_AMBER, "#4b6fa8", "#7a8da6", "#9aa7b8"]

    parts = ['<svg viewBox="0 0 %d %d" class="chart chart--flat" role="img" '
             'aria-label="Часы по контурам">' % (width, height)]
    for i in range(ticks + 1):
        value = max_val * i / ticks
        y = pad_t + plot_h - plot_h * value / max_val
        parts.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1"/>'
                     % (pad_l, y, width - 20, y, C_LINE))
        parts.append('<text x="%d" y="%.1f" class="ax" text-anchor="end">%s</text>'
                     % (pad_l - 8, y + 4, hrs(value)))
    for i, c in enumerate(rows):
        x = pad_l + slot * i + (slot - bar_w) / 2
        h = plot_h * c["hours"] / max_val
        y = pad_t + plot_h - h
        parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3" fill="%s"/>'
                     % (x, y, bar_w, h, palette[i % len(palette)]))
        parts.append('<text x="%.1f" y="%.1f" class="val val-big" text-anchor="middle">%s ч</text>'
                     % (x + bar_w / 2, y - 8, hrs(c["hours"])))
        parts.append('<text x="%.1f" y="%d" class="lbl" text-anchor="middle">%s</text>'
                     % (x + bar_w / 2, height - 30, esc(c["contour"])))
        parts.append('<text x="%.1f" y="%d" class="ax ax-dim" text-anchor="middle">%d задач</text>'
                     % (x + bar_w / 2, height - 16, c["tasks"]))
    parts.append("</svg>")
    return "".join(parts)


def table_rows(tasks, k):
    ranked = sorted(tasks, key=lambda t: -t["our_hours"])
    head = by_k(ranked[:TOP_TABLE], k)
    rest = ranked[TOP_TABLE:]
    out = []
    for t in head:
        pct = 100.0 * t["saved_hours"] / t["without_hours"] if t["without_hours"] else 0
        out.append(
            "<tr>"
            '<td class="k">%s</td>'
            '<td class="t">%s</td>'
            '<td class="c">%s</td>'
            '<td class="n">%s</td>'
            '<td class="n hypo">%s</td>'
            '<td class="n save">%s</td>'
            '<td class="n">%.0f%%</td>'
            "</tr>"
            % (esc(t["key"]), esc(short_title(t["summary"])), esc(t["contour"]),
               hrs(t["our_hours"]), hrs(round(t["without_hours"])),
               hrs(round(t["saved_hours"])), pct)
        )
    if rest:
        fact = sum(t["our_hours"] for t in rest)
        without = fact * k
        saved = without - fact
        out.append(
            "<tr>"
            '<td class="k">прочие</td>'
            '<td class="t">ещё %s с меньшим объемом</td>'
            '<td class="c">-</td>'
            '<td class="n">%s</td>'
            '<td class="n hypo">%s</td>'
            '<td class="n save">%s</td>'
            '<td class="n">%.0f%%</td>'
            "</tr>"
            % (ru_tasks(len(rest)), hrs(round(fact)), hrs(round(without)), hrs(round(saved)),
               100.0 * (k - 1.0) / k)
        )
    return "\n".join(out)


def normalize(payload):
    """Приводит поля датасета к единым именам, которыми пользуется верстка."""
    s = payload["summary"]
    for sc in payload["scenarios"]:
        overhead = sc.get("overhead")
        if "k" not in sc:
            sc["k"] = 1.0 + float(overhead)
        sc["add_pct"] = sc.get("overhead_pct") or int(round((sc["k"] - 1.0) * 100))
        sc["time_reduction_pct"] = sc.get("faster_pct") or sc.get("time_reduction_pct")
        sc["saved_cost"] = sc.get("saved_money", sc.get("saved_cost", 0))
        sc["saved_fte_months"] = sc.get("person_months", sc.get("saved_fte_months", 0))
        sc["capacity_x"] = sc["k"]
        sc["source"] = sc.get("anchor") or sc.get("source") or ""
    months = float(s.get("period_months") or 1.0)
    s["period_months"] = months
    for sc in payload["scenarios"]:
        if "saved_hours_month" not in sc:
            sc["saved_hours_month"] = round(sc["saved_hours"] / months, 1)
        if "saved_hours_year" not in sc:
            sc["saved_hours_year"] = round(sc["saved_hours"] / months * 12.0, 0)
        if "saved_money_month" not in sc:
            sc["saved_money_month"] = int(round(sc["saved_cost"] / months))
        if "saved_money_year" not in sc:
            sc["saved_money_year"] = int(round(sc["saved_cost"] / months * 12.0))
        if "fte_ongoing" not in sc:
            sc["fte_ongoing"] = round(sc["saved_hours_month"] / s.get("month_hours", 168.0), 2)
    s["saved_cost_min"] = s.get("saved_money_min", s.get("saved_cost_min", 0))
    s["saved_cost_max"] = s.get("saved_money_max", s.get("saved_cost_max", 0))
    s["fte_month_hours"] = s.get("month_hours", s.get("fte_month_hours", 168.0))
    sc_min = payload["scenarios"][0]
    sc_real = payload["scenarios"][-1]
    s.setdefault("saved_hours_month_min", sc_min["saved_hours_month"])
    s.setdefault("saved_hours_month_max", sc_real["saved_hours_month"])
    s.setdefault("saved_hours_year_min", sc_min["saved_hours_year"])
    s.setdefault("saved_hours_year_max", sc_real["saved_hours_year"])
    s.setdefault("saved_money_year_min", sc_min["saved_money_year"])
    s.setdefault("saved_money_year_max", sc_real["saved_money_year"])
    s.setdefault("fte_ongoing_min", sc_min["fte_ongoing"])
    s.setdefault("fte_ongoing_max", sc_real["fte_ongoing"])
    if "saved_hours_base" not in s:
        base = next((x for x in payload["scenarios"] if x["id"] == "base"), payload["scenarios"][0])
        s["saved_hours_base"] = base["saved_hours"]
    for t in payload["tasks"]:
        t["contour"] = t.get("contour") or t.get("component") or "прочее"
    if "by_contour" not in payload and "by_component" in payload:
        payload["by_contour"] = []
        for c in payload["by_component"]:
            payload["by_contour"].append({
                "contour": c.get("component") or c.get("contour"),
                "tasks": c["tasks"],
                "hours": c["hours"],
                "saved": c.get("saved", c.get("saved_min", 0)),
            })
    return payload


def build(payload):
    payload = normalize(payload)
    s = payload["summary"]
    tasks = payload["tasks"]
    coeff = payload.get("coeff") or payload["scenarios"][0]
    k_show = float(coeff.get("k") or s.get("k"))
    saved = s.get("saved_hours", coeff["saved_hours"])
    without = s.get("without_hours", coeff["without_hours"])
    money = s.get("saved_money", coeff["saved_money"])
    h_mo = s.get("saved_hours_month", coeff["saved_hours_month"])
    h_y = s.get("saved_hours_year", coeff["saved_hours_year"])
    fte = s.get("fte_ongoing", coeff["fte_ongoing"])
    faster = s.get("faster_pct", coeff["faster_pct"])
    rate = s["rate"]

    cr_share = s.get("cr_share")
    if cr_share is None:
        cr_h = next((t["hours"] for t in payload["by_type"]
                     if t["issue_type"] == "Change Request"), 0.0)
        cr_share = 100.0 * cr_h / s["fact_hours"] if s["fact_hours"] else 0.0

    period_from = date_ru(s["period_from"])
    period_to = date_ru(s["period_to"])
    period_mo = months_txt(s["period_months"])
    period_mo_int = str(int(round(s["period_months"])))
    k_dec = ("%.2f" % k_show).replace(".", ",")
    saved_h = hrs(round(saved))
    h_mo_txt = hrs(h_mo)
    h_y_txt = hrs(round(h_y))
    money_year_tied = int(round(h_y) * rate)

    kpis = [
        (saved_h, "ч", "За %s месяцев" % period_mo_int,
         "%s - %s, %s, факт %s ч" % (
             period_from, period_to, ru_tasks(s["tasks_selected"]), hrs(s["fact_hours"]))),
        (h_mo_txt, "ч/мес", "Средний темп экономии",
         "период уже включает и тихие месяцы, и пик лета 2026"),
        (h_y_txt, "ч/год", "Оценка на год",
         "средний темп x 12, %s ставки ИТ постоянно" % fte_share(fte)),
        (rub(money), "руб", "Эквивалент внешней разработки",
         "%s ч x %s руб/ч, ставка Аванкор" % (saved_h, rub(rate))),
    ]
    kpi_html = "\n".join(
        '<div class="kpi"><div class="kpi-num">%s<span class="kpi-unit">%s</span></div>'
        '<div class="kpi-lbl">%s</div><div class="kpi-sub">%s</div></div>'
        % (esc(num), esc(unit), esc(label), esc(sub)) for num, unit, label, sub in kpis
    )

    sum_rows = (
        '<tr><td class="lab">Высвобождено за период'
        '<span class="sub sub--dark">%s - %s</span></td>'
        '<td class="v v-save">%s ч<span class="v-ex">%s ч/мес / %s ч/год</span></td></tr>'
        '<tr><td class="lab">В рублях по ставке Аванкор'
        '<span class="sub sub--dark">%s руб/ч из смет вендора</span></td>'
        '<td class="v v-save">%s &#8381;<span class="v-ex">%s ч x %s руб = %s руб</span></td></tr>'
        '<tr><td class="lab">На год при том же темпе</td>'
        '<td class="v v-hypo">%s &#8381;/год<span class="v-ex">%s ч x %s руб</span></td></tr>'
        % (period_from, period_to,
           saved_h, h_mo_txt, h_y_txt,
           rub(rate), rub(money),
           saved_h, rub(rate), rub(money),
           rub(money_year_tied), h_y_txt, rub(rate))
    )

    contour_rows = "\n".join(
        "<tr><td>%s</td><td class=\"n\">%d</td><td class=\"n\">%s</td>"
        "<td class=\"n save\">%s</td></tr>"
        % (esc(c["contour"]), c["tasks"], hrs(c["hours"]),
           hrs(c.get("saved", 0)))
        for c in payload["by_contour"]
    )

    fit_lbl = {
        "chosen": ("берём", "flag-ok"),
        "support": ("опора", "flag-ok"),
        "reject": ("не берём", "flag-no"),
        "context": ("контекст", "flag"),
    }
    src_rows = "\n".join(
        '<tr%s><td><span class="%s">%s</span></td><td><strong>%s</strong></td><td>%s</td></tr>'
        % (' class="row-hi"' if src.get("fit") == "chosen" else "",
           fit_lbl.get(src.get("fit"), ("", "flag"))[1],
           fit_lbl.get(src.get("fit"), (src.get("fit") or "", "flag"))[0],
           esc(src.get("who") or src.get("id")),
           esc(src.get("what") or ""))
        for src in payload["sources"]
    )

    html = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Презентация 02. Эффект Cursor: экономия человеко-часов ИТ</title>
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
    flex: 0 0 100%%; height: 100%%; padding: 22px 4vw 64px;
    background: var(--slide-bg); overflow: hidden; display: flex; flex-direction: column;
  }
  .fill {
    flex: 1 1 auto; min-height: 0;
    display: flex; flex-direction: column; gap: 12px;
  }
  .fill > .grid-2,
  .fill > .grid-3,
  .fill > .grid-4,
  .fill > .grid-scen,
  .fill > .table-wrap,
  .fill > .kpi-row,
  .fill > .card--glass {
    flex: 1 1 auto; min-height: 0;
  }
  .fill > .card { flex: 0 1 auto; min-height: 0; }
  .fill > .card:has(.chart) { flex: 1 1 auto; min-height: 0; }
  .fill .facts { flex: 1; align-content: space-between; }
  .fill .formula { flex: 1; }
  .slide--title {
    background:
      radial-gradient(900px 420px at 88%% 6%%, rgba(14,124,107,.35), transparent 60%%),
      linear-gradient(135deg, #0b1f3a 0%%, #163a66 52%%, #0e5f57 100%%);
    color: #f4f7fb; justify-content: flex-start;
  }
  .slide--dark { background: linear-gradient(150deg, #0f1d33 0%%, #1c3a5e 100%%); color: #e6edf6; }
  .eyebrow {
    font-size: 11px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase;
    color: var(--teal); margin-bottom: 10px;
  }
  .slide--title .eyebrow, .slide--dark .eyebrow { color: #6fdcc6; }
  h1 { font-size: clamp(2.05rem, 4.2vw, 3.15rem); line-height: 1.08; margin: 0 0 10px; letter-spacing: -.01em; }
  h2 { font-size: clamp(1.5rem, 2.8vw, 2.2rem); line-height: 1.12; margin: 0 0 8px; letter-spacing: -.01em; }
  .lead { font-size: clamp(1.02rem, 1.55vw, 1.14rem); color: var(--muted); margin: 0 0 12px; max-width: 64rem; }
  .slide--title .lead, .slide--dark .lead { color: rgba(226,234,244,.86); }
  .kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-top: 12px; }
  .kpi {
    background: rgba(255,255,255,.09); border: 1px solid rgba(255,255,255,.16);
    border-radius: 16px; padding: 18px 16px 16px; backdrop-filter: blur(6px);
    display: flex; flex-direction: column; justify-content: center;
  }
  .kpi-num {
    font-size: clamp(1.55rem, 2.9vw, 2.5rem); font-weight: 800; letter-spacing: -.025em;
    color: #fff; line-height: 1.05; white-space: nowrap;
  }
  .kpi-unit { font-size: .48em; font-weight: 700; margin-left: 5px; color: rgba(244,247,251,.72); }
  .kpi-lbl { font-size: 13px; font-weight: 700; margin-top: 8px; color: rgba(244,247,251,.94); }
  .kpi-sub { font-size: 11.5px; margin-top: 5px; color: rgba(226,234,244,.62); line-height: 1.4; }
  .card {
    background: var(--paper); border: 1px solid var(--line); border-radius: 16px;
    padding: 16px 18px; box-shadow: 0 10px 30px rgba(11,31,58,.06);
    display: flex; flex-direction: column;
  }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: stretch; }
  .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; align-items: stretch; }
  .grid-scen { display: grid; grid-template-columns: 1.15fr 1fr; gap: 16px; align-items: stretch; }
  .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; align-items: stretch; }
  .card--glass {
    background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.16);
    box-shadow: none; margin-top: 0; border-radius: 16px; padding: 10px 16px 6px;
  }
  table { width: 100%%; border-collapse: collapse; font-size: 15px; }
  th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
  th {
    background: var(--navy); color: #eef3f9; font-size: 10.5px; font-weight: 700;
    letter-spacing: .06em; text-transform: uppercase; position: sticky; top: 0;
  }
  td.n, th.n { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
  td.k { font-weight: 700; color: var(--navy-mid); white-space: nowrap; }
  td.c { color: var(--muted); white-space: nowrap; font-size: 12px; }
  td.hypo { color: var(--navy-mid); font-weight: 700; }
  td.save { color: #0a5c50; font-weight: 800; background: #f0faf7; }
  table:not(.sum) tbody tr:nth-child(even) td { background: #fafbfd; }
  table:not(.sum) tbody tr:nth-child(even) td.save { background: #e9f6f2; }
  tr.total td {
    background: var(--navy) !important; color: #fff; font-weight: 800; font-size: 13px;
    border-bottom: 0; position: sticky; bottom: 0;
  }
  tr.row-hi td { background: #eef7f4 !important; }
  tr.row-hi td.save { background: #ddf1eb !important; }
  td .sub { display: block; font-size: 10.5px; font-weight: 600; color: var(--muted); margin-top: 1px; }
  td .sub--dark { color: rgba(226,234,244,.5); }
  .table-wrap { overflow: auto; flex: 1; min-height: 0; border: 1px solid var(--line); border-radius: 12px; background: #fff; }
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
  .v-ex { display: block; font-size: 10.5px; font-weight: 600; color: rgba(226,234,244,.45); margin-top: 1px; }
  .legend { display: flex; gap: 18px; flex-wrap: wrap; margin: 2px 0 10px; font-size: 12.5px; color: var(--ink-soft); }
  .legend span { display: inline-flex; align-items: center; gap: 7px; font-weight: 600; }
  .legend i { width: 13px; height: 13px; border-radius: 3px; display: inline-block; }
  .chart { width: 100%%; height: 100%%; max-height: none; display: block; flex: 1; min-height: 0; }
  .chart--flat { max-height: none; height: auto; flex: 0 0 auto; }
  .chart text { font-family: "Manrope", "Segoe UI", Arial, sans-serif; }
  .ax { font-size: 11px; fill: %(muted)s; }
  .ax-dim { font-size: 10px; fill: #94a0b3; }
  .ax-title { font-size: 11.5px; fill: %(muted)s; font-weight: 700; }
  .lbl { font-size: 11.5px; fill: #2c3a4f; font-weight: 700; }
  .val { font-size: 10.5px; fill: #2c3a4f; font-weight: 700; }
  .val-dim { fill: #0a5c50; }
  .val-big { font-size: 14px; fill: #142a44; font-weight: 800; }
  .d-cap { font-size: 13px; fill: rgba(226,234,244,.72); font-weight: 700; }
  .d-val { font-size: 17px; fill: #0d2036; font-weight: 800; }
  .d-lbl { font-size: 12.5px; fill: rgba(226,234,244,.85); font-weight: 700; }
  .facts { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }
  .facts li { display: flex; gap: 11px; align-items: flex-start; font-size: 17px; color: var(--ink-soft); line-height: 1.42; }
  .facts .b {
    flex: 0 0 auto; width: 22px; height: 22px; border-radius: 7px; background: var(--teal);
    color: #fff; font-size: 11.5px; font-weight: 800; display: grid; place-items: center; margin-top: 1px;
  }
  .facts strong { color: var(--ink); }
  .slide--dark .facts li { color: rgba(226,234,244,.9); }
  .slide--dark .facts strong { color: #fff; }
  .formula {
    background: var(--sky); border: 1px solid #cfdff2; border-radius: 12px;
    padding: 16px 16px; font-size: 16px; color: #14314f; line-height: 1.55;
  }
  .formula code {
    font-family: ui-monospace, Consolas, monospace; font-size: 14.5px; background: #fff;
    padding: 2px 6px; border-radius: 5px; border: 1px solid #cfdff2;
  }
  .note {
    background: var(--amber-soft); border: 1px solid #edd9b0; border-radius: 12px;
    padding: 14px 16px; font-size: 14.5px; color: #6f4a10; line-height: 1.5;
  }
  .h4 {
    font-size: 11px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase;
    color: var(--muted); margin: 0 0 9px;
  }
  .impact {
    background: var(--paper); border: 1px solid var(--line); border-radius: 14px; padding: 20px 18px 18px;
    display: flex; flex-direction: column; justify-content: space-between; height: 100%%;
  }
  .impact .n {
    font-size: clamp(2.05rem, 3.6vw, 2.85rem); font-weight: 800; color: var(--navy); letter-spacing: -.02em; line-height: 1.05;
  }
  .impact p { margin: 8px 0 0; font-size: 16px; color: var(--ink-soft); line-height: 1.4; }
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
  .flag {
    display: inline-block; padding: 2px 8px; border-radius: 999px;
    font-size: 10px; font-weight: 800; letter-spacing: .04em; text-transform: uppercase;
    background: #e8eef6; color: #3a4d66; white-space: nowrap;
  }
  .flag-ok { background: #ddf1eb; color: #0a5c50; }
  .flag-no { background: #f3e6e6; color: #8a3a3a; }
  .slide--dark .src, .slide--title .src { color: rgba(226,234,244,.6); }
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
    .kpi-row, .grid-2, .grid-4 { grid-template-columns: 1fr 1fr; }
    .grid-scen { grid-template-columns: 1fr; }
  }
  @media print {
    body, .deck { height: auto; overflow: visible; background: #fff; }
    .slides { display: block; transform: none !important; }
    .slide { height: auto; page-break-after: always; overflow: visible; }
    .nav { display: none; }
  }
</style>
</head>
<body>
<div class="deck">
  <div class="slides" id="slides">

    <section class="slide slide--title">
      <div class="eyebrow">Презентация 02 &middot; Пакет 20.09.2026</div>
      <h1 class="serif">Cursor высвобождает человеко-часы ИТ<br>без расширения штата</h1>
      <p class="lead">
        За %(period_mo_int)s месяцев (%(period_from)s &mdash; %(period_to)s) внутренние задачи
        (не Аванкор) ведутся с Cursor. %(tasks_phrase)s закрыты за %(fact)s ч.
        Без ИИ тот же объем занял бы %(without)s ч: коэффициент 25%% быстрее
        подобран под наш тип работы (рефакторинг существующей 1С).
        Разница &mdash; %(saved)s ч за период: %(h_mo)s ч каждый месяц, или %(h_y)s ч в год.
        В рублях: %(saved)s ч &times; %(rate)s &#8381;/ч = %(money_exact)s &#8381;.
      </p>
      <div class="fill">
      <div class="kpi-row">
%(kpi)s
      </div>
      <div class="card--glass">
%(split)s
      </div>
      </div>
      <div class="improve">
        <span class="lbl2">Вид улучшения</span>
        <span class="badge">Экономия ресурсов ИТ / рост capacity</span>
      </div>
      <div class="src">
        Выборка: внутренние задачи Jira, созданные с 01.11.2025, без пересечения
        с выгрузкой Аванкор, с учтенным временем. Горизонт факта &mdash;
        %(period_from)s &mdash; %(period_to)s (%(period_mo)s мес.).
        Ставка &mdash; %(rate)s &#8381;/ч из смет Аванкор (презентация 01). Один коэффициент, без диапазона.
      </div>
    </section>

    <section class="slide">
      <div class="eyebrow">Методика</div>
      <h2>Факт из учета, один коэффициент &mdash; из исследования под наш тип задач</h2>
      <div class="fill">
      <div class="grid-2">
        <div class="card">
          <p class="h4">Что берем из учетных систем</p>
          <ul class="facts">
            <li><span class="b">1</span><span><strong>Факт часов</strong> &mdash; Time Sheet по каждой задаче,
              иначе Time Spent из Jira. По выборке это %(fact)s ч.</span></li>
            <li><span class="b">2</span><span><strong>Граница Cursor.</strong> В расчет входят задачи,
              созданные 01.11.2025 и позже. Более ранние не смешиваем: часть работы могла идти без ИИ.</span></li>
            <li><span class="b">3</span><span><strong>Не Аванкор.</strong> Пересечение с выгрузкой вендора
              исключено (0 задач). Дубли и отмены тоже.</span></li>
            <li><span class="b">4</span><span><strong>Деньги &mdash; не зарплата.</strong>
              Экономия часов &times; ставка Аванкор %(rate)s &#8381;/ч.
              Это ровно %(money_exact)s &#8381; за период, без вилки ставок.</span></li>
          </ul>
        </div>
        <div>
          <div class="card">
            <p class="h4">Формула (один коэффициент)</p>
            <div class="formula">
              <div><strong>Факт</strong> = <code>часы Time Sheet</code> = %(fact)s ч</div>
              <div style="margin-top:10px"><strong>Без Cursor</strong> =
                <code>факт &times; 4/3</code> = %(without)s ч<br>
                <span style="color:#4a6280">k = 4/3 &asymp; %(k_dec)s. «На 25%% быстрее»
                значит задача занимает 75%% времени, а не «+25%% к факту».</span></div>
              <div style="margin-top:10px"><strong>Экономия часов</strong> =
                <code>без Cursor &minus; факт</code> = %(saved)s ч</div>
              <div style="margin-top:10px"><strong>В рублях</strong> =
                <code>%(saved)s &times; %(rate)s</code> = <strong>%(money_exact)s &#8381;</strong></div>
            </div>
            <div class="note" style="margin-top:12px">
              <strong>Два языка процентов.</strong>
              «На 25%% быстрее» = задача занимает 75%% времени, k = 4/3, надбавка к факту +33%%.
              Это не «+25%% к факту». Год &mdash; средний темп за %(period_mo)s мес. &times; 12.
            </div>
          </div>
        </div>
      </div>
      <div class="grid-3">
        <div class="impact">
          <p class="h4">Берём</p>
          <div class="n">25%%</div>
          <p>McKinsey, рефакторинг 20&ndash;30%%. Середина полосы. Совпадает с нашими Change Request
            (%(cr_share)s%% часов выборки).</p>
        </div>
        <div class="impact">
          <p class="h4">Опора</p>
          <div class="n">~21%%</div>
          <p>Google, полевой корпоративный RCT. Подтверждает: 25%% не лабораторный потолок.</p>
        </div>
        <div class="impact">
          <p class="h4">Не берём</p>
          <div class="n">40%% / 56%%</div>
          <p>Новый код McKinsey и лаборатория GitHub (JS HTTP). Другой тип задач, не наша 1С.</p>
        </div>
      </div>
      </div>
    </section>

    <section class="slide">
      <div class="eyebrow">Сравнение по задачам</div>
      <h2>Факт с Cursor против прогноза без ИИ</h2>
      <div class="legend">
        <span><i style="background:%(navy_mid)s"></i>Прогноз без Cursor (25%% быстрее, k = 4/3)</span>
        <span><i style="background:%(teal)s"></i>Факт с Cursor</span>
      </div>
      <div class="fill">
      <div class="card">
%(bars)s
      </div>
      </div>
      <div class="src">
        Показаны %(top_bars)d крупнейших задач (около двух третей объема).
        Диаграмма &mdash; один коэффициент: 25%% быстрее, McKinsey по рефакторингу.
      </div>
    </section>

    <section class="slide">
      <div class="eyebrow">Детализация</div>
      <h2>Крупнейшие задачи: часы, прогноз, экономия</h2>
      <div class="fill">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Задача</th>
              <th>Наименование</th>
              <th>Контур</th>
              <th class="n">Факт, ч</th>
              <th class="n">Без Cursor, ч</th>
              <th class="n">Экономия, ч</th>
              <th class="n">Доля</th>
            </tr>
          </thead>
          <tbody>
%(rows)s
            <tr class="total">
              <td colspan="3">ИТОГО по %(tasks)d задачам</td>
              <td class="n">%(fact)s</td>
              <td class="n">%(without)s</td>
              <td class="n">%(saved)s</td>
              <td class="n">%(pct_save)s%%</td>
            </tr>
          </tbody>
        </table>
      </div>
      </div>
      <div class="src">
        «Без Cursor» = факт &times; 4/3. Доля экономии в гипотетическом объеме постоянна
        (%(pct_save)s%%) &mdash; коэффициент общий. Различается абсолют: чем больше задача,
        тем больше часов возвращается.
      </div>
    </section>

    <section class="slide">
      <div class="eyebrow">Динамика и контуры</div>
      <h2>Экономия копится неровно: пик &mdash; лето 2026, ядро &mdash; МО и ДУ</h2>
      <div class="fill">
      <div class="card">
%(timeline)s
      </div>
      <div class="grid-2">
        <div class="card">
%(contours)s
        </div>
        <div class="card">
          <p class="h4">Разрез по контурам</p>
          <table>
            <thead>
              <tr>
                <th>Контур</th><th class="n">Задач</th><th class="n">Факт, ч</th>
                <th class="n">Экономия, ч</th>
              </tr>
            </thead>
            <tbody>
%(contour_rows)s
            </tbody>
          </table>
          <div class="note" style="margin-top:12px">
            <strong>Где эффект для бизнеса.</strong> Большая часть часов &mdash; оптимизация оперативного
            учета МО и ДУ при росте клиентской базы. Средний темп
            %(h_mo)s ч/мес уже учитывает и зиму, и пик лета 2026:
            годовая оценка = этот средний &times; 12, а не пиковый август.
          </div>
        </div>
      </div>
      </div>
    </section>

    <section class="slide">
      <div class="eyebrow">Почему этот коэффициент</div>
      <h2>Берём исследование, которое измеряло похожую работу</h2>
      <p class="lead">
        %(cr_share)s%% часов выборки &mdash; Change Request на существующих конфигурациях
        Аванкор МО и ДУ. Это рефакторинг, не greenfield. McKinsey для рефакторинга:
        20&ndash;30%% меньше времени. Середина &mdash; <strong>25%% быстрее</strong>.
      </p>
      <div class="fill">
      <div class="grid-scen">
        <div class="card">
%(fit_chart)s
        </div>
        <div class="card">
          <p class="h4">Источники: что берём и что отбрасываем</p>
          <table>
            <thead>
              <tr><th>Решение</th><th>Источник</th><th>Что показали</th></tr>
            </thead>
            <tbody>
%(src_rows)s
            </tbody>
          </table>
          <div class="note" style="margin-top:12px">
            <strong>Итог для расчета.</strong> k = 4/3. Без Cursor = факт &times; 4/3.
            Экономия = %(saved)s ч. Рубли = %(saved)s &times; %(rate)s =
            %(money_exact)s &#8381;. Других коэффициентов в этой презентации нет.
          </div>
        </div>
      </div>
      </div>
      <div class="src">
        McKinsey, Unleashing developer productivity with generative AI, июнь 2023
        (refactoring 20&ndash;30%% less time). Google DORA / enterprise RCT, 2024 (~21%%).
        GitHub Copilot, Peng et al., 2022&ndash;2023 (лабораторный HTTP-сервер на JS, 55,8%%) &mdash;
        в расчет не входит.
      </div>
    </section>

    <section class="slide">
      <div class="eyebrow">На что влияет</div>
      <h2>Высвобожденные часы &mdash; это не «экономия на бумаге», а capacity компании</h2>
      <p class="lead">
        IBM и McKinsey описывают ценность gen AI в разработке так: не сокращение штата,
        а тот же состав делает больше &mdash; без найма и без подрядчика.
      </p>
      <div class="fill">
      <div class="grid-4">
        <div class="impact">
          <p class="h4">Capacity без найма</p>
          <div class="n">&times;%(k_dec)s</div>
          <p>Та же команда закрывает объем работ в %(k_dec)s раза больше за тот же календарный срок.</p>
        </div>
        <div class="impact">
          <p class="h4">Темп без найма</p>
          <div class="n">%(h_mo)s ч/мес</div>
          <p>%(fte)s ставки ИТ постоянно. Штат не растет,
            подрядчик не вызывается, тот же состав закрывает больший объем.</p>
        </div>
        <div class="impact">
          <p class="h4">Оценка на год</p>
          <div class="n">%(h_y)s ч</div>
          <p>%(h_y)s ч &times; %(rate)s &#8381; = %(money_year)s &#8381;/год
            по ставке Аванкор. Пик лета уже внутри среднего темпа.</p>
        </div>
        <div class="impact">
          <p class="h4">Приоритеты бизнеса</p>
          <div class="n">%(cr_share)s%%</div>
          <p>фактических часов &mdash; Change Request (оптимизация учета), а не разбор мелочи.
            Высвобождение идет в ту же работу, за которую спрашивает бизнес.</p>
        </div>
      </div>
      <div class="card">
        <p class="h4">Как это стыкуется с презентацией 01</p>
        <p style="margin:0;font-size:16px;color:var(--ink-soft);line-height:1.5">
          Там экономия &mdash; счета вендора, которых не выставили. Здесь &mdash; часы самой команды,
          которых не пришлось тратить. Складывать эти суммы нельзя: это разные контуры.
          Вместе они показывают, что Cursor работает и наружу, и внутрь.
        </p>
      </div>
      </div>
      <div class="src">
        Формулировка «value = capacity + cost avoidance» &mdash; McKinsey / IBM, 2024.
        Человеко-месяц принят как 168 ч. Темп &mdash; экономия за %(period_mo)s мес., деленная
        на длительность. Денежный эквивалент &mdash; ставка Аванкор %(rate)s &#8381;/ч,
        без диапазона ставок.
      </div>
    </section>

    <section class="slide slide--dark">
      <div class="eyebrow">Выводы</div>
      <h2 class="serif" style="font-size:clamp(1.7rem,3.2vw,2.5rem)">Что это значит для компании</h2>
      <div class="fill">
      <div class="grid-2">
        <div>
          <ul class="facts">
            <li><span class="b">1</span><span><strong>За %(period_mo_int)s месяцев высвобождено
              %(saved)s ч ИТ</strong> на внутренних задачах
              (%(period_from)s &mdash; %(period_to)s). Cursor сокращает цикл, а не качество.</span></li>
            <li><span class="b">2</span><span><strong>Это %(h_mo)s ч каждый месяц
              и %(h_y)s ч в год</strong> &mdash; %(fte)s ставки
              без найма. Штат не растет, подрядчик не вызывается, бэклог идет быстрее.</span></li>
            <li><span class="b">3</span><span><strong>Коэффициент честный под нашу работу:</strong>
              25%% быстрее (k = 4/3) &mdash; середина McKinsey по рефакторингу.
              %(cr_share)s%% часов выборки как раз такого типа.</span></li>
            <li><span class="b">4</span><span><strong>Рубли привязаны к ставке Аванкор:</strong>
              %(saved)s ч &times; %(rate)s &#8381; = %(money_exact)s &#8381; за период.
              На год: %(h_y)s ч &times; %(rate)s = %(money_year)s &#8381;.</span></li>
          </ul>
        </div>
        <div>
          <div class="card" style="background:rgba(255,255,255,.07);border-color:rgba(255,255,255,.16)">
            <p class="h4" style="color:rgba(226,234,244,.6)">Экономия часов и рублей</p>
            <table class="sum">
              <tbody>
%(sum_rows)s
                <tr><td class="lab">Факт с Cursor</td>
                    <td class="v v-fact">%(fact)s ч<span class="v-ex">%(tasks_phrase)s</span></td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <div class="card--glass">
%(split)s
      </div>
      </div>
      <div class="improve">
        <span class="lbl2">Вид улучшения</span>
        <span class="badge">Экономия ресурсов ИТ / рост capacity</span>
      </div>
      <div class="src">
        Расчет по выгрузке внутренних задач Jira и Time Sheet на 17.09.2026,
        горизонт %(period_from)s &mdash; %(period_to)s (%(period_mo)s мес.).
        Коэффициент &mdash; McKinsey, июнь 2023, рефакторинг, середина 20&ndash;30%%.
        Гипотетическое время без Cursor &mdash; расчетная величина. Год &mdash; средний темп &times; 12.
        Ставка &mdash; %(rate)s &#8381;/ч из смет Аванкор.
      </div>
    </section>

  </div>
  <nav class="nav">
    <span class="deck-title">02 &middot; Эффект Cursor: экономия человеко-часов ИТ</span>
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
        "split": svg_split(s["fact_hours"], saved,
                           "  -  25% быстрее, McKinsey рефакторинг"),
        "bars": svg_bars(tasks, k_show),
        "rows": table_rows(tasks, k_show),
        "timeline": svg_timeline(payload["timeline"], k_show),
        "contours": svg_contours(payload["by_contour"]),
        "contour_rows": contour_rows,
        "fit_chart": svg_fit(faster),
        "src_rows": src_rows,
        "sum_rows": sum_rows,
        "tasks": s["tasks_selected"],
        "tasks_phrase": ru_tasks(s["tasks_selected"]),
        "fact": hrs(s["fact_hours"]),
        "without": hrs(round(without)),
        "saved": saved_h,
        "pct_save": "%.0f" % (100.0 * saved / without if without else 0),
        "rate": rub(rate),
        "top_bars": TOP_BARS,
        "k_dec": k_dec,
        "fte": fte_share(fte),
        "period_from": period_from,
        "period_to": period_to,
        "period_mo": period_mo,
        "period_mo_int": period_mo_int,
        "h_mo": h_mo_txt,
        "h_y": h_y_txt,
        "money_exact": rub(money),
        "money_year": rub(money_year_tied),
        "cr_share": pct(cr_share),
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
