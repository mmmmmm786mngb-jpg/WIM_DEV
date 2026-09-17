#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка Презентации 03: vibe-coding под дедлайн регулятора.

Формат другой, чем у 01/02: не портфель часов и денег, а один кейс
против окна сдачи в Банк России. Без CDN, inline SVG.
"""

import json
import math
import os
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)

from fmt import num_int

BASE = os.path.dirname(SCRIPTS)
DATA = os.path.join(SCRIPTS, "p03_dataset.json")
OUT = os.path.join(BASE, "03_vibe_deadline.html")

C_NAVY = "#0b1f3a"
C_NAVY_MID = "#163a66"
C_TEAL = "#0e7c6b"
C_AMBER = "#c47a12"
C_LINE = "#d7dde8"
C_MUTED = "#6b7588"
C_RISK = "#b42318"


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def svg_clock(window):
    """Кольцо из 10 рабочих дней окна сдачи."""
    cx, cy, r_out, r_in = 170, 170, 148, 94
    n = len(window["days"])
    parts = ['<svg viewBox="0 0 340 340" class="chart" role="img" '
             'aria-label="Окно сдачи 10 рабочих дней">']
    for i, day in enumerate(window["days"]):
        a0 = math.radians(-90.0 + 360.0 * i / n + 1.4)
        a1 = math.radians(-90.0 + 360.0 * (i + 1) / n - 1.4)
        x0o = cx + r_out * math.cos(a0)
        y0o = cy + r_out * math.sin(a0)
        x1o = cx + r_out * math.cos(a1)
        y1o = cy + r_out * math.sin(a1)
        x0i = cx + r_in * math.cos(a1)
        y0i = cy + r_in * math.sin(a1)
        x1i = cx + r_in * math.cos(a0)
        y1i = cy + r_in * math.sin(a0)
        if day.get("event") == "дедлайн ЦБ":
            fill = C_AMBER
        elif day.get("event") == "задача закрыта":
            fill = C_TEAL
        elif day["n"] < window["closed_day"]:
            fill = C_NAVY_MID
        else:
            fill = "#d7dde8"
        d = ("M %.1f %.1f A %d %d 0 0 1 %.1f %.1f "
             "L %.1f %.1f A %d %d 0 0 0 %.1f %.1f Z" % (
                 x0o, y0o, r_out, r_out, x1o, y1o,
                 x0i, y0i, r_in, r_in, x1i, y1i))
        parts.append('<path d="%s" fill="%s"/>' % (d, fill))
        mid = (a0 + a1) / 2.0
        lx = cx + ((r_out + r_in) / 2.0) * math.cos(mid)
        ly = cy + ((r_out + r_in) / 2.0) * math.sin(mid)
        color = "#fff" if fill != "#d7dde8" else "#5a6578"
        parts.append('<text x="%.1f" y="%.1f" text-anchor="middle" class="clk-n" fill="%s">%d</text>'
                     % (lx, ly + 4, color, day["n"]))
    parts.append('<circle cx="%d" cy="%d" r="%d" fill="#0b1f3a"/>' % (cx, cy, r_in - 10))
    parts.append('<text x="%d" y="%d" text-anchor="middle" class="clk-big">день %d</text>'
                 % (cx, cy - 8, window["closed_day"]))
    parts.append('<text x="%d" y="%d" text-anchor="middle" class="clk-sub">из %d рабочих</text>'
                 % (cx, cy + 16, window["working_days"]))
    parts.append("</svg>")
    return "".join(parts)


def svg_window_strip(window):
    """Лента 10 рабочих дней июля 2026."""
    width, height = 1180, 118
    pad = 16
    slot = (width - pad * 2) / len(window["days"])
    box_w = slot - 8
    parts = ['<svg viewBox="0 0 %d %d" class="chart chart--flat" role="img" '
             'aria-label="Лента окна сдачи июля 2026">' % (width, height)]
    parts.append('<text x="%d" y="18" class="d-cap">Окно сдачи XBRL за июль 2026 · 10 рабочих дней</text>'
                 % pad)
    for i, day in enumerate(window["days"]):
        x = pad + i * slot
        if day.get("event") == "дедлайн ЦБ":
            fill, fg = C_AMBER, "#fff"
        elif day.get("event") == "задача закрыта":
            fill, fg = C_TEAL, "#fff"
        else:
            fill, fg = "#e8edf5", C_NAVY
        parts.append('<rect x="%.1f" y="28" width="%.1f" height="52" rx="8" fill="%s"/>'
                     % (x, box_w, fill))
        parts.append('<text x="%.1f" y="50" text-anchor="middle" fill="%s" class="strip-n">%d</text>'
                     % (x + box_w / 2, fg, day["n"]))
        parts.append('<text x="%.1f" y="68" text-anchor="middle" fill="%s" class="strip-l">%s</text>'
                     % (x + box_w / 2, fg, esc(day["label"])))
        if day.get("event"):
            parts.append('<text x="%.1f" y="102" text-anchor="middle" class="strip-ev">%s</text>'
                         % (x + box_w / 2, esc(day["event"])))
    parts.append("</svg>")
    return "".join(parts)


def svg_paths(paths):
    """Сравнение путей: помещается ли визуализация в рабочий день."""
    visual = [p for p in paths if p["id"] != "vendor"]
    width, height = 1100, 320
    pad_l, pad_t = 268, 36
    plot_w, row_h = 760, 78
    parts = ['<svg viewBox="0 0 %d %d" class="chart" role="img" '
             'aria-label="Пути визуализации XBRL">' % (width, height)]
    parts.append('<text x="%d" y="22" class="ax-title">Время, чтобы увидеть пакет (не разработка)</text>'
                 % pad_l)
    max_h = 8.0
    for i, p in enumerate(visual):
        y = pad_t + 10 + i * row_h
        w = max(22, plot_w * min(p["hours"], max_h) / max_h)
        fill = C_TEAL if p["fits"] else (C_AMBER if p["id"] == "portal" else C_NAVY_MID)
        parts.append('<text x="%d" y="%.1f" class="lbl" text-anchor="end">%s</text>'
                     % (pad_l - 14, y + 22, esc(p["name"])))
        parts.append('<rect x="%d" y="%.1f" width="%.1f" height="34" rx="7" fill="%s"/>'
                     % (pad_l, y, w, fill))
        parts.append('<text x="%.1f" y="%.1f" class="val-big" fill="%s">%s</text>'
                     % (pad_l + w + 12, y + 24, fill, esc(p["time"])))
    parts.append("</svg>")
    return "".join(parts)


def svg_volume(forms, total_rows):
    """Строки июньского пакета по формам. 0420431 доминирует — это и есть проблема."""
    rows = [f for f in forms if f["rows"] > 0]
    width, height = 1100, 250
    pad_l, pad_t, pad_b = 90, 32, 44
    plot_w = width - pad_l - 24
    plot_h = height - pad_t - pad_b
    max_v = max(f["rows"] for f in rows)
    slot = plot_w / len(rows)
    bar_w = min(slot * 0.55, 90)
    parts = ['<svg viewBox="0 0 %d %d" class="chart" role="img" '
             'aria-label="Строки пакета по формам">' % (width, height)]
    parts.append('<text x="%d" y="20" class="ax-title">Строки данных в Excel, июнь 2026 · всего %s</text>'
                 % (pad_l, num_int(total_rows)))
    for i, f in enumerate(rows):
        h = plot_h * f["rows"] / max_v
        x = pad_l + slot * i + (slot - bar_w) / 2
        y = pad_t + plot_h - h
        fill = C_AMBER if f["form"] == "0420431" else C_NAVY_MID
        parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="4" fill="%s"/>'
                     % (x, y, bar_w, max(h, 2), fill))
        label = num_int(f["rows"]) if f["rows"] >= 100 else str(f["rows"])
        if h > 48:
            parts.append('<text x="%.1f" y="%.1f" class="val-big" text-anchor="middle" fill="#fff">%s</text>'
                         % (x + bar_w / 2, y + 22, label))
        else:
            parts.append('<text x="%.1f" y="%.1f" class="val-big" text-anchor="middle">%s</text>'
                         % (x + bar_w / 2, y - 8, label))
        parts.append('<text x="%.1f" y="%d" class="lbl" text-anchor="middle">%s</text>'
                     % (x + bar_w / 2, height - 28, esc(f["form"])))
        parts.append('<text x="%.1f" y="%d" class="ax ax-dim" text-anchor="middle">%d л.</text>'
                     % (x + bar_w / 2, height - 14, f["sheets"]))
    parts.append("</svg>")
    return "".join(parts)


def build(payload):
    s = payload["summary"]
    w = payload["window"]
    v = payload["volume"]
    risk = payload["risk"]

    acc = payload["acceptance"]
    conv = payload["conversion"]
    kpis = [
        ("14", "ч", "Разработка с vibe-coding",
         "Time Sheet IMDEV-9182 · закрыто 12.08"),
        (num_int(s["bsl_lines"]), "строк", "Код обработки в 1С",
         "модуль объекта, таксономия 7.1, весь пакет"),
        (conv["june_label"].replace(" мин", ""), "мин", "XBRL в Excel, весь пакет",
         "эталон июня: %s. Было: конвертер >1 ч, портал >8 ч" % conv["june_exact"]),
        ("Done", "", "Приёмка заказчиком",
         "%s · Closed 12.08 · приоритет High" % acc["reporter"]),
    ]
    kpi_html = "\n".join(
        '<div class="kpi"><div class="kpi-num">%s%s</div>'
        '<div class="kpi-lbl">%s</div><div class="kpi-sub">%s</div></div>'
        % (esc(num),
           ('<span class="kpi-unit">%s</span>' % esc(unit) if unit else ""),
           esc(label), esc(sub)) for num, unit, label, sub in kpis
    )

    quotes_html = "\n".join(
        '<blockquote class="q"><span class="q-tag">%s</span>«%s»</blockquote>'
        % (esc(q["tag"]), esc(q["text"]))
        for q in payload["quotes"]
    )

    path_cards = "\n".join(
        '<div class="path %s"><p class="h4">%s</p>'
        '<div class="n">%s</div><p>%s</p>'
        '<span class="fit">%s</span></div>'
        % ("path-ok" if p["fits"] else "path-bad",
           esc(p["name"]), esc(p["time"]), esc(p["note"]),
           "в окне" if p["fits"] else "не в окне")
        for p in payload["paths"]
    )

    src_rows = "\n".join(
        "<tr><td><strong>%s</strong></td><td>%s</td></tr>"
        % (esc(src["who"]), esc(src["what"]))
        for src in payload["sources"]
    )

    form_rows = []
    for f in v["by_form"]:
        if f["rows"] <= 0:
            continue
        share = 100.0 * f["rows"] / v["rows_total"] if v["rows_total"] else 0
        if share >= 1:
            share_s = "%.0f%%" % share
        elif share > 0:
            share_s = "<1%"
        else:
            share_s = "—"
        form_rows.append(
            "<tr%s><td>%s</td><td class=\"n\">%d</td><td class=\"n\">%s</td>"
            "<td class=\"n\">%s</td></tr>"
            % (' class="row-hi"' if f["form"] == "0420431" else "",
               esc(f["form"]), f["sheets"], num_int(f["rows"]), share_s)
        )
    form_rows = "\n".join(form_rows)

    html = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Презентация 03. Vibe-coding под дедлайн регулятора</title>
<style>
  :root {
    --ink: #0c1524; --ink-soft: #3a4558; --muted: %(muted)s; --line: %(line)s;
    --paper: #ffffff; --navy: %(navy)s; --navy-mid: %(navy_mid)s;
    --teal: %(teal)s; --amber: %(amber)s; --amber-soft: #f8ecd8;
    --risk: %(risk)s; --slide-bg: #f5f7fb;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%%; margin: 0; }
  body {
    font-family: "Manrope", "Segoe UI", Arial, sans-serif;
    color: var(--ink); background: #0a1220; overflow: hidden;
  }
  .serif { font-family: "Instrument Serif", Georgia, "Times New Roman", serif; font-weight: 400; }
  .deck { position: relative; height: 100vh; overflow: hidden; }
  .slides { display: flex; height: 100%%; transition: transform .45s cubic-bezier(.4,0,.2,1); }
  .slide {
    flex: 0 0 100%%; height: 100%%; padding: 34px 5vw 78px;
    background: var(--slide-bg); overflow-y: auto; display: flex; flex-direction: column;
  }
  .slide--title {
    background:
      radial-gradient(880px 420px at 90%% 0%%, rgba(196,122,18,.42), transparent 58%%),
      linear-gradient(135deg, #0b1f3a 0%%, #1a2e4c 48%%, #7a4a10 100%%);
    color: #f4f7fb; justify-content: flex-start; padding-top: 28px;
  }
  .slide--dark { background: linear-gradient(150deg, #0f1d33 0%%, #3a2a14 100%%); color: #e6edf6; }
  .eyebrow {
    font-size: 11px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase;
    color: var(--amber); margin-bottom: 10px;
  }
  .slide--title .eyebrow, .slide--dark .eyebrow { color: #f3c98a; }
  h1 { font-size: clamp(1.7rem, 3.4vw, 2.55rem); line-height: 1.1; margin: 0 0 10px; }
  h2 { font-size: clamp(1.35rem, 2.5vw, 2rem); line-height: 1.15; margin: 0 0 8px; }
  .lead { font-size: clamp(.94rem, 1.45vw, 1.06rem); color: var(--muted); margin: 0 0 12px; max-width: 64rem; }
  .slide--title .lead, .slide--dark .lead { color: rgba(226,234,244,.88); }
  .q-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin: 4px 0 8px; }
  .q {
    margin: 0; background: rgba(255,255,255,.08); border-left: 3px solid #f3c98a;
    border-radius: 0 10px 10px 0; padding: 10px 12px 11px;
    font-size: 12.5px; line-height: 1.4; color: rgba(244,247,251,.94);
  }
  .q-tag {
    display: block; font-size: 10px; font-weight: 800; letter-spacing: .12em;
    text-transform: uppercase; color: #f3c98a; margin-bottom: 5px;
  }
  .q-who {
    margin: 0 0 2px; font-size: 11px; font-weight: 700; color: rgba(243,201,138,.85);
  }
  .kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 10px; }
  .kpi {
    background: rgba(255,255,255,.09); border: 1px solid rgba(255,255,255,.16);
    border-radius: 14px; padding: 12px 12px 11px;
  }
  .kpi-num {
    font-size: clamp(1.4rem, 2.6vw, 2.25rem); font-weight: 800; letter-spacing: -.025em;
    color: #fff; line-height: 1.05; white-space: nowrap;
  }
  .kpi-unit { font-size: .46em; font-weight: 700; margin-left: 5px; color: rgba(244,247,251,.72); }
  .kpi-lbl { font-size: 13px; font-weight: 700; margin-top: 8px; color: rgba(244,247,251,.94); }
  .kpi-sub { font-size: 11.5px; margin-top: 5px; color: rgba(226,234,244,.62); line-height: 1.4; }
  .card {
    background: var(--paper); border: 1px solid var(--line); border-radius: 16px;
    padding: 16px 18px; box-shadow: 0 10px 30px rgba(11,31,58,.06);
  }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
  .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
  .grid-clock { display: grid; grid-template-columns: 340px 1fr; gap: 20px; align-items: center; }
  .card--glass {
    background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.16);
    box-shadow: none; margin-top: 12px; border-radius: 16px; padding: 6px 12px 2px;
  }
  table { width: 100%%; border-collapse: collapse; font-size: 12.5px; }
  th, td { text-align: left; padding: 5px 9px; border-bottom: 1px solid var(--line); vertical-align: top; }
  th {
    background: var(--navy); color: #eef3f9; font-size: 10.5px; font-weight: 700;
    letter-spacing: .06em; text-transform: uppercase;
  }
  td.n, th.n { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
  table:not(.sum) tbody tr:nth-child(even) td { background: #fafbfd; }
  tr.row-hi td { background: #f8ecd8 !important; font-weight: 700; }
  tr.total td { background: var(--navy) !important; color: #fff; font-weight: 800; border-bottom: 0; }
  .sum { width: 100%%; border-collapse: collapse; font-size: 14px; }
  .sum td { padding: 9px 2px; border-bottom: 1px solid rgba(255,255,255,.13); background: transparent; }
  .sum tr:last-child td { border-bottom: 0; }
  .sum td.lab { color: rgba(226,234,244,.82); }
  .sum td.v {
    text-align: right; font-weight: 800; font-size: 17px; font-variant-numeric: tabular-nums;
    letter-spacing: -.01em; color: #fff;
  }
  .sum td.v-fact { color: #f3c98a; }
  .sum td.v-save { color: #6fdcc6; }
  .v-ex { display: block; font-size: 10.5px; font-weight: 600; color: rgba(226,234,244,.45); margin-top: 1px; }
  .h4 {
    font-size: 11px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase;
    color: var(--muted); margin: 0 0 8px;
  }
  .effect {
    background: var(--paper); border: 1px solid var(--line); border-radius: 16px; padding: 16px 16px 14px;
  }
  .effect .n { font-size: 1.15rem; font-weight: 800; color: var(--navy); margin: 0 0 8px; }
  .effect p { margin: 0; font-size: 13px; color: var(--ink-soft); line-height: 1.45; }
  .effect--here { border-color: var(--amber); box-shadow: 0 0 0 3px rgba(196,122,18,.15); }
  .effect--here .n { color: var(--amber); }
  .path {
    background: var(--paper); border: 1px solid var(--line); border-radius: 14px; padding: 14px;
    display: flex; flex-direction: column; gap: 6px;
  }
  .path .n { font-size: 1.45rem; font-weight: 800; color: var(--navy); }
  .path p { margin: 0; font-size: 12.5px; color: var(--ink-soft); line-height: 1.45; }
  .path .fit {
    margin-top: auto; align-self: flex-start; font-size: 11px; font-weight: 800;
    letter-spacing: .08em; text-transform: uppercase; padding: 4px 8px; border-radius: 999px;
  }
  .path-bad .fit { background: #fde8e6; color: var(--risk); }
  .path-ok .fit { background: #d8f3ee; color: var(--teal); }
  .path-ok { border-color: #9ad9ce; }
  .quote {
    background: var(--amber-soft); border-left: 4px solid var(--amber);
    border-radius: 0 12px 12px 0; padding: 14px 16px; font-size: 15px; line-height: 1.45;
    color: #5a3a0a; margin: 0;
  }
  .quote .who { display: block; margin-top: 8px; font-size: 12px; font-weight: 700; color: #8a6a2a; }
  .risk {
    background: #fff6f4; border: 1px solid #f0c4be; border-radius: 14px; padding: 14px;
  }
  .risk .n { font-size: 1.3rem; font-weight: 800; color: var(--risk); }
  .risk p { margin: 6px 0 0; font-size: 12.5px; color: var(--ink-soft); line-height: 1.45; }
  .note {
    background: var(--amber-soft); border: 1px solid #edd9b0; border-radius: 12px;
    padding: 12px 14px; font-size: 12.5px; color: #6f4a10; line-height: 1.55;
  }
  .facts { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
  .facts li { display: flex; gap: 11px; align-items: flex-start; font-size: 14px; color: var(--ink-soft); }
  .facts .b {
    flex: 0 0 auto; width: 22px; height: 22px; border-radius: 7px; background: var(--amber);
    color: #fff; font-size: 11.5px; font-weight: 800; display: grid; place-items: center; margin-top: 1px;
  }
  .facts strong { color: var(--ink); }
  .slide--dark .facts li { color: rgba(226,234,244,.9); }
  .slide--dark .facts strong { color: #fff; }
  .improve {
    margin-top: auto; padding-top: 14px; display: flex; align-items: center; gap: 12px;
    flex-wrap: wrap; border-top: 1px dashed rgba(255,255,255,.25);
  }
  .improve .lbl2 { font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: rgba(226,234,244,.6); }
  .improve .badge {
    display: inline-flex; align-items: center; gap: 8px; padding: 8px 14px; border-radius: 999px;
    font-size: 13px; font-weight: 800; background: rgba(196,122,18,.28); color: #f8d9a0;
    border: 1px solid rgba(243,201,138,.45);
  }
  .improve .badge::before { content: ""; width: 8px; height: 8px; border-radius: 50%%; background: #f3c98a; }
  .src { margin-top: 12px; font-size: 11.5px; color: var(--muted); line-height: 1.5; }
  .slide--dark .src, .slide--title .src { color: rgba(226,234,244,.6); }
  .chart { width: 100%%; height: auto; max-height: 58vh; display: block; }
  .chart--flat { max-height: 22vh; }
  .chart--vol { max-height: 28vh; }
  .chart text { font-family: "Manrope", "Segoe UI", Arial, sans-serif; }
  .ax { font-size: 11px; fill: %(muted)s; }
  .ax-dim { font-size: 10px; fill: #94a0b3; }
  .ax-title { font-size: 12px; fill: %(muted)s; font-weight: 700; }
  .lbl { font-size: 12px; fill: #2c3a4f; font-weight: 700; }
  .val-big { font-size: 13px; fill: #142a44; font-weight: 800; }
  .d-cap { font-size: 12px; fill: rgba(226,234,244,.78); font-weight: 700; }
  .clk-n { font-size: 13px; font-weight: 800; }
  .clk-big { font-size: 22px; font-weight: 800; fill: #fff; }
  .clk-sub { font-size: 12px; fill: rgba(226,234,244,.7); font-weight: 700; }
  .strip-n { font-size: 14px; font-weight: 800; }
  .strip-l { font-size: 10px; font-weight: 700; }
  .strip-ev { font-size: 10.5px; font-weight: 800; fill: %(amber)s; }
  .legend { display: flex; gap: 16px; flex-wrap: wrap; margin: 4px 0 8px; font-size: 12.5px; color: var(--ink-soft); }
  .legend span { display: inline-flex; align-items: center; gap: 7px; font-weight: 600; }
  .legend i { width: 13px; height: 13px; border-radius: 3px; display: inline-block; }
  .nav {
    position: fixed; left: 0; right: 0; bottom: 0; height: 56px; display: flex;
    align-items: center; justify-content: space-between; padding: 0 5vw;
    background: rgba(10,18,32,.9); color: #cbd6e6; font-size: 12.5px; z-index: 20;
  }
  .dots { display: flex; gap: 7px; }
  .dot {
    width: 9px; height: 9px; border-radius: 50%%; background: #3d4c63; border: 0;
    cursor: pointer; padding: 0;
  }
  .dot.on { background: #f3c98a; transform: scale(1.35); }
  .nav-btns { display: flex; gap: 8px; }
  .nav button.arrow {
    background: #1c2b44; color: #dbe5f2; border: 1px solid #35486a; border-radius: 8px;
    width: 34px; height: 30px; font-size: 14px; cursor: pointer;
  }
  .counter { font-variant-numeric: tabular-nums; font-weight: 700; }
  .deck-title { font-weight: 700; opacity: .75; }
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
      <div class="eyebrow">Презентация 03 &middot; Пакет 20.09.2026 &middot; кейс %(key)s</div>
      <h1 class="serif">Не экономия часов.<br>Срок, который нельзя сорвать</h1>
      <p class="lead">
        Back-Office Settle просил увидеть XBRL в Excel до сдачи в Банк России.
        Классика &mdash; часы и сбои. С vibe-coding обработка собрана за 14 часов:
        весь пакет виден за 4 минуты. Задача закрыта 12 августа, за 2 рабочих дня до дедлайна июля.
      </p>
      <p class="q-who">Из заявки Карасевой Ольги, IM Back-Office Settle, 17.07.2026, приоритет High</p>
      <div class="q-row">
%(quotes)s
      </div>
      <div class="kpi-row">
%(kpi)s
      </div>
      <div class="card--glass">
%(strip)s
      </div>
      <div class="improve">
        <span class="lbl2">Вид улучшения</span>
        <span class="badge">Снижение регуляторного риска / дедлайн</span>
      </div>
      <div class="src">
        Это не презентация 01 (счета вендора) и не 02 (часы команды). Здесь цена вопроса &mdash;
        окно сдачи и качество пакета. 14 ч этой задачи уже внутри выборки 02, повторно не считаем.
      </div>
    </section>

    <section class="slide">
      <div class="eyebrow">Другой эффект &mdash; другой формат</div>
      <h2>Три презентации считают разные вещи. Складывать их нельзя</h2>
      <p class="lead">
        01 и 02 отвечают «сколько сэкономили». 03 отвечает «успели ли в срок, который нельзя сдвинуть».
        Поэтому здесь нет портфеля задач, сценариев +40/+80%% и млн рублей в год.
      </p>
      <div class="grid-3">
        <div class="effect">
          <p class="h4">Презентация 01</p>
          <div class="n">Деньги вендора</div>
          <p>Счета, которых не выставили. Гипотеза полной разработки Аванкор vs факт интеграции.</p>
        </div>
        <div class="effect">
          <p class="h4">Презентация 02</p>
          <div class="n">Часы команды</div>
          <p>Capacity без найма. 14 часов этой задачи уже внутри тех 1 065 ч. Повторно не считаем.</p>
        </div>
        <div class="effect effect--here">
          <p class="h4">Презентация 03</p>
          <div class="n">Дедлайн регулятора</div>
          <p>Одна оперативная задача. Если не успеть увидеть пакет &mdash; риск штрафа, отклонения и срыва сдачи.</p>
        </div>
      </div>
      <div class="grid-3" style="margin-top:16px">
        <div class="card">
          <p class="h4">Что смотрим вместо млн ₽</p>
          <p style="margin:0;font-size:13.5px;color:var(--ink-soft);line-height:1.5">
            Цитаты постановки, ленту из 10 рабочих дней, карточку штрафа как <em>риска</em>
            и сравнение путей: портал / конвертер / вендор / vibe.
          </p>
        </div>
        <div class="card">
          <p class="h4">Один кейс, не портфель</p>
          <p style="margin:0;font-size:13.5px;color:var(--ink-soft);line-height:1.5">
            IMDEV-9182, контур ДУ, таксономия 7.1. Разработка 14 ч, код %(bsl)s строк.
            XBRL в Excel: 4 мин на эталоне июня. Следующий месяц &mdash; то же окно.
          </p>
        </div>
        <div class="card">
          <p class="h4">Приёмка заказчиком</p>
          <p style="margin:0;font-size:13.5px;color:var(--ink-soft);line-height:1.5">
            Постановщик &mdash; Карасева Ольга (IM Back-Office Settle), приоритет High.
            Задача Closed, резолюция Done 12.08.2026. Отдельного текста комментария приёмки
            в выгрузке Jira нет: зафиксированы постановщик и закрытие Done.
          </p>
        </div>
      </div>
      <div class="src">
        14 ч IMDEV-9182 входят в выборку презентации 02. Денежный эквивалент этих часов туда же.
        Здесь &mdash; только срок и риск. McKinsey CIB: code assistants сжимают time-to-market;
        McKinsey / Merck: gen AI сжимает цикл регуляторной сдачи, где цена &mdash; сорванное окно.
      </div>
    </section>

    <section class="slide">
      <div class="eyebrow">Регуляторные часы</div>
      <h2>10 рабочих дней &mdash; это не метафора, а точка входа XBRL</h2>
      <div class="grid-clock">
        <div class="card">%(clock)s</div>
        <div>
          <div class="card">
            <p class="h4">Что тикает</p>
            <ul class="facts">
              <li><span class="b">1</span><span><strong>НСО ПУРЦБ, таксономия 7.1.</strong>
                Точка входа <code>%(entry)s</code>: пакет в Банк России в течение 10 рабочих дней
                после отчетной даты. Окно повторяется каждый месяц.</span></li>
              <li><span class="b">2</span><span><strong>Июль 2026:</strong> отчетная дата 31 июля,
                дедлайн 14 августа. Задача закрыта 12 августа &mdash; 8-й рабочий день окна,
                2 дня запаса на сдачу и правки.</span></li>
              <li><span class="b">3</span><span><strong>Заявка 17 июля</strong> пришла уже после
                июньского дедлайна (14 июля). Инструмент нужен был к июльскому окну, не «когда-нибудь в бэклоге».</span></li>
            </ul>
          </div>
          <div class="grid-2" style="margin-top:12px">
            <div class="risk">
              <p class="h4">Юридическое лицо</p>
              <div class="n">500–700 тыс. ₽</div>
              <p>%(article)s: непредставление, просрочка или недостоверность информации в Банк России.</p>
            </div>
            <div class="risk">
              <p class="h4">Должностное лицо</p>
              <div class="n">20–30 тыс. ₽</div>
              <p>или дисквалификация %(disq)s. Плюс отклонение пакета на техническом контроле и повтор в том же окне.</p>
            </div>
          </div>
        </div>
      </div>
      <div class="src">
        Штраф &mdash; мера риска, не утверждение, что его выписали бы. Бизнес просил инструмент контроля качества,
        без которого сдавать пакет вслепую нельзя.
      </div>
    </section>

    <section class="slide">
      <div class="eyebrow">Постановка бизнеса</div>
      <h2>Бэк-офис не просил «написать парсер». Просил увидеть данные до сдачи</h2>
      <blockquote class="quote">
        «%(quote)s»
        <span class="who">%(quote_who)s</span>
      </blockquote>
      <div class="grid-4" style="margin-top:16px">
%(path_cards)s
      </div>
      <div class="note" style="margin-top:16px">
        <strong>Почему классика не в окне.</strong> Портал Аванкор съедает больше рабочего дня на одну загрузку
        и не дает Excel. Конвертер режет форму 431 на части, идет больше часа и сбоит &mdash; чужое ПО.
        Вендор на парсер таксономии 7.1 и 77 таблиц не встанет в 10 дней. Vibe-coding собрал обработку 1С,
        которая выгружает <em>весь</em> пакет одним запуском.
      </div>
      <div class="src">
        Исходная заявка просила форму 0420431. Сделали весь пакет (78 листов): иначе контроль качества
        снова остался бы «частями». Скорость на эталоне июня: 4 мин 3 с vs конвертер &gt;1 ч и портал &gt;8 ч.
      </div>
    </section>

    <section class="slide">
      <div class="eyebrow">Объём, из-за которого ломается классика</div>
      <h2>Один пакет: 78 листов, %(rows)s строк. Почти всё &mdash; форма 431</h2>
      <div class="legend">
        <span><i style="background:%(amber)s"></i>0420431, тяжёлая форма</span>
        <span><i style="background:%(navy_mid)s"></i>прочие формы пакета</span>
      </div>
      <div class="card">%(volume)s</div>
      <div class="grid-2" style="margin-top:12px">
        <div class="card">
          <table>
            <thead><tr><th>Форма</th><th class="n">Листов</th><th class="n">Строк</th><th class="n">Доля</th></tr></thead>
            <tbody>
%(form_rows)s
              <tr class="total"><td>Итого таблицы пакета (июнь 2026)</td>
                <td class="n">%(sheets)d</td><td class="n">%(rows)s</td><td class="n">100%%</td></tr>
            </tbody>
          </table>
        </div>
        <div class="card">
          <p class="h4">Что это значит для дедлайна</p>
          <ul class="facts">
            <li><span class="b">1</span><span><strong>%(max_rows)s строк в одном листе 431.</strong>
              Именно это бизнес назвал причиной сбоев конвертера.</span></li>
            <li><span class="b">2</span><span><strong>Пакеты «уже ~500 МБ»</strong> в постановке.
              Июньский тестовый ZIP &mdash; эталон состава: 77 таблиц + оглавление.</span></li>
            <li><span class="b">3</span><span><strong>Скорость:</strong> эталон июня &mdash; весь пакет за 4 мин 3 с
              (v1.4.10, режим таксономии). Январский меньший пакет &mdash; 29 с. Было: конвертер &gt;1 ч частями,
              портал &gt;8 ч.</span></li>
          </ul>
        </div>
      </div>
    </section>

    <section class="slide">
      <div class="eyebrow">Как закрыли</div>
      <h2>Vibe-coding: 14 часов учёта, %(bsl)s строк, живой файл июля</h2>
      <p class="lead">
        Не «магия ИИ», а сжатый цикл: сгенерировать разбор таксономии 7.1, прогнать на эталоне ЦБ,
        поймать сбой, поправить, повторить. Классикой этот цикл не влезает в окно сдачи.
      </p>
      <div class="grid-2">
        <div class="card">%(paths_chart)s</div>
        <div class="card">
          <p class="h4">Цикл, который поместился</p>
          <ul class="facts">
            <li><span class="b">1</span><span><strong>17 июля</strong> &mdash; заявка Back-Office Settle.
              Нужен Excel для контроля качества, не замена сдачи в ЦБ.</span></li>
            <li><span class="b">2</span><span><strong>Итерации на живых пакетах</strong> (январь, апрель, июнь, июль).
              Версия обработки 1.4.10 &mdash; это не «написал и забыл», а дожим до устойчивого прогона.</span></li>
            <li><span class="b">3</span><span><strong>12 августа, 14 ч Time Sheet.</strong>
              Обработка в 1С: %(bsl)s строк, только платформа, весь пакет одним запуском.
              Постановщик Карасева: Closed / Done.</span></li>
            <li><span class="b">4</span><span><strong>14 августа</strong> &mdash; дедлайн июля.
              2 рабочих дня остаются на сдачу и правки, а не на изобретение конвертера.</span></li>
          </ul>
        </div>
      </div>
      <div class="src">
        %(bsl)s строк модуля объекта &mdash; парсер instance + таксономия 7.1 + XLSX.
        Разработка отмечена в коде как выполненная с Cursor. 14 ч &mdash; факт учёта.
        Конвертация эталона июня: 4 мин 3 с на весь пакет.
      </div>
    </section>

    <section class="slide slide--dark">
      <div class="eyebrow">Выводы</div>
      <h2 class="serif" style="font-size:clamp(1.7rem,3.2vw,2.5rem)">Что это значит для компании</h2>
      <div class="grid-2" style="margin-top:8px">
        <ul class="facts">
          <li><span class="b">1</span><span><strong>Окно не сдвинуть.</strong> 10 рабочих дней повторяются
            каждый месяц. Инструмент остаётся: следующий пакет не ждёт новую разработку.</span></li>
          <li><span class="b">2</span><span><strong>Снят операционный риск контроля качества.</strong>
            Бэк-офис видит весь пакет, включая 431-ю, а не «части» конвертера и не 8 часов портала.</span></li>
          <li><span class="b">3</span><span><strong>Штраф 500–700 тыс. ₽</strong> и дисквалификация &mdash;
            цена срыва срока или недостоверности, не «экономия ИТ». Мы не утверждаем, что штраф был бы выписан;
            утверждаем, что без визуализации сдавать было нельзя, а визуализации не было.</span></li>
          <li><span class="b">4</span><span><strong>Паттерн, не разовый трюк.</strong> Vibe-coding имеет смысл
            там, где бизнес-задача критична по дате, а классический контур (вендор, чужое ПО, долгий портал)
            в дату не помещается.</span></li>
        </ul>
        <div class="card" style="background:rgba(255,255,255,.07);border-color:rgba(255,255,255,.16)">
          <p class="h4" style="color:rgba(226,234,244,.6)">Кейс одной строкой</p>
          <table class="sum">
            <tbody>
              <tr><td class="lab">Задача</td><td class="v">%(key)s</td></tr>
              <tr><td class="lab">Окно июля</td><td class="v">31.07 &rarr; 14.08</td></tr>
              <tr><td class="lab">Закрыто</td><td class="v v-save">12.08 · день 8 из 10</td></tr>
              <tr><td class="lab">Факт часов</td><td class="v v-fact">14 ч · %(bsl)s строк</td></tr>
              <tr><td class="lab">XBRL в Excel</td>
                  <td class="v v-save">4 мин<span class="v-ex">эталон июня · 78 листов · %(rows)s строк</span></td></tr>
              <tr><td class="lab">Приёмка</td>
                  <td class="v">Карасева · Done<span class="v-ex">постановщик, Closed 12.08, приоритет High</span></td></tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="improve">
        <span class="lbl2">Вид улучшения</span>
        <span class="badge">Снижение регуляторного риска / дедлайн</span>
      </div>
      <div class="src">
        Источники: постановка IMDEV-9182 (Карасева), Time Sheet, эталон июня 2026 (4 мин 3 с),
        разъяснения ЦБ по точкам входа НСО ПУРЦБ, ст. 19.7.3 КоАП РФ, McKinsey CIB / regulatory submissions.
        Гипотетическое время вендора в окно не входит и в млн рублей презентаций 01–02 не добавляется.
      </div>
    </section>

  </div>
  <nav class="nav">
    <span class="deck-title">03 &middot; Vibe-coding под дедлайн регулятора</span>
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
    var dot = document.getElementById ? document.createElement('button') : null;
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
        "teal": C_TEAL, "amber": C_AMBER, "risk": C_RISK,
        "kpi": kpi_html,
        "quotes": quotes_html,
        "strip": svg_window_strip(w),
        "clock": svg_clock(w),
        "path_cards": path_cards,
        "volume": svg_volume(v["by_form"], v["rows_total"]),
        "paths_chart": svg_paths(payload["paths"]),
        "form_rows": form_rows,
        "src_rows": src_rows,
        "key": s["key"],
        "entry": esc(w["entry_point"]),
        "article": esc(risk["article"]),
        "disq": esc(risk["disqualification"]),
        "quote": esc(payload["quote"]),
        "quote_who": esc(payload["quote_who"]),
        "rows": num_int(v["rows_total"]),
        "sheets": v["sheets_data"],
        "max_rows": num_int(v["max_rows_one_sheet"]),
        "bsl": num_int(s["bsl_lines"]),
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
