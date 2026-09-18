#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка презентации 04: скорость операционного учёта 1С.

Новый стиль относительно 01-03: тёмный плакат, крупно одно число,
коралл «было» / лайм «стало». Без navy-карточек портфеля.
"""

import json
import os
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)

from fmt import ratio

BASE = os.path.dirname(SCRIPTS)
DATA = os.path.join(SCRIPTS, "p04_dataset.json")
OUT = os.path.join(BASE, "04_perf_cases.html")

C_BG = "#090b0e"
C_PANEL = "#14171c"
C_LIME = "#c8ff3d"
C_CORAL = "#ff5a3c"
C_INK = "#f2f4ef"
C_DIM = "#8d9388"
C_LINE = "#2a2e36"


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def x_txt(value):
    return "x" + ratio(value)


def svg_pair(before_min, after_min, before_lbl, after_lbl, caption="", compact=False):
    """Два горизонтальных бара: было (коралл) и стало (лайм)."""
    width = 680 if compact else 1480
    height = 210 if compact else 260
    pad_l = 78 if compact else 168
    pad_r = 118 if compact else 210
    pad_t = 10 if compact else 36
    bar_h = 52 if compact else 48
    plot_w = width - pad_l - pad_r
    max_v = max(before_min, after_min, 1.0)
    bw = max(22.0, plot_w * before_min / max_v)
    aw = max(22.0, plot_w * after_min / max_v)
    y1 = pad_t
    y2 = pad_t + bar_h + 18
    parts = ['<svg viewBox="0 0 %d %d" class="chart" role="img" aria-label="%s">'
             % (width, height, esc(caption or "было и стало"))]
    if caption and not compact:
        parts.append('<text x="%d" y="22" class="d-cap">%s</text>' % (pad_l, esc(caption)))
        y1 = 40
        y2 = 40 + bar_h + 22
    parts.append('<text x="%d" y="%.1f" class="lbl" text-anchor="end">было</text>'
                 % (pad_l - 14, y1 + bar_h * 0.72))
    parts.append('<rect x="%d" y="%.1f" width="%.1f" height="%d" rx="6" fill="%s"/>'
                 % (pad_l, y1, bw, bar_h, C_CORAL))
    parts.append('<text x="%.1f" y="%.1f" class="val" fill="%s">%s</text>'
                 % (pad_l + bw + 10, y1 + bar_h * 0.72, C_CORAL, esc(before_lbl)))
    parts.append('<text x="%d" y="%.1f" class="lbl" text-anchor="end">стало</text>'
                 % (pad_l - 14, y2 + bar_h * 0.72))
    parts.append('<rect x="%d" y="%.1f" width="%.1f" height="%d" rx="6" fill="%s"/>'
                 % (pad_l, y2, aw, bar_h, C_LIME))
    parts.append('<text x="%.1f" y="%.1f" class="val" fill="%s">%s</text>'
                 % (pad_l + aw + 10, y2 + bar_h * 0.72, C_LIME, esc(after_lbl)))
    parts.append("</svg>")
    return "".join(parts)


def svg_x_bars(cases):
    """Кратности пяти кейсов."""
    width, height = 1480, 300
    pad_l, pad_t, pad_b, pad_r = 20, 16, 40, 20
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    max_x = max(c["x"] for c in cases)
    slot = plot_w / len(cases)
    bar_w = min(slot * 0.52, 120)
    parts = ['<svg viewBox="0 0 %d %d" class="chart chart--bars" role="img" '
             'aria-label="Кратность ускорения пяти операций">' % (width, height)]
    for i, c in enumerate(cases):
        h = plot_h * c["x"] / max_x
        x = pad_l + slot * i + (slot - bar_w) / 2
        y = pad_t + plot_h - h
        parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="8" fill="%s"/>'
                     % (x, y, bar_w, max(h, 8), C_LIME))
        ty = y + 28 if h > 48 else y - 10
        fill = "#111" if h > 48 else C_LIME
        parts.append('<text x="%.1f" y="%.1f" class="val-on" text-anchor="middle" fill="%s">%s</text>'
                     % (x + bar_w / 2, ty, fill, x_txt(c["x"])))
        parts.append('<text x="%.1f" y="%d" class="lbl" text-anchor="middle">%s</text>'
                     % (x + bar_w / 2, height - 22, esc(c["name"])))
        parts.append('<text x="%.1f" y="%d" class="d-cap" text-anchor="middle">%s</text>'
                     % (x + bar_w / 2, height - 6, esc(c["contour"])))
    parts.append("</svg>")
    return "".join(parts)


def saved_line(item):
    delta = item["before_min"] - item["after_min"]
    if item.get("norm"):
        return "минус %s мин на 1 000" % ratio(delta)
    if delta >= 60:
        return "минус %s ч с прогона" % ratio(delta / 60.0)
    return "минус %s мин с прогона" % ratio(delta)


def case_card(c):
    unit = "на 1 000" if c.get("norm") else esc(c["volume"])
    return (
        '<div class="xcard">'
        '<div class="xc-k">%s</div>'
        '<div class="xc-x">%s</div>'
        '<div class="xc-n">%s</div>'
        '<div class="xc-t"><span class="was">%s</span>'
        '<span class="arr"> -&gt; </span>'
        '<span class="now">%s</span></div>'
        '<div class="xc-v">%s</div>'
        '</div>'
        % (esc(c["contour"]), x_txt(c["x"]), esc(c["name"]),
           esc(c["before_short"]), esc(c["after_short"]), unit)
    )


def poster(c, extra="", bar=""):
    return (
        '<article class="poster">'
        '<div class="p-top"><span class="p-k">%s</span><span class="p-key">%s</span></div>'
        '<h3>%s</h3>'
        '<div class="p-x">%s</div>'
        '<div class="p-vs">'
        '<div class="was-box"><div class="tiny">было</div><div class="big">%s</div></div>'
        '<div class="now-box"><div class="tiny">стало</div><div class="big">%s</div></div>'
        '</div>'
        '%s'
        '<p class="p-saved">%s</p>'
        '<p class="p-meta">%s · %s</p>'
        '<p class="p-what">%s</p>'
        '%s'
        '</article>'
        % (esc(c["contour"]), esc(c["key"]), esc(c["name"]), x_txt(c["x"]),
           esc(c["before_label"]), esc(c["after_label"]), bar,
           esc(saved_line(c)),
           esc(c["volume"]), esc(c["env"]), esc(c["what"]), extra)
    )


def teaser_chip(c):
    return (
        '<div class="chip"><div class="cx">%s</div>'
        '<div class="cn">%s</div>'
        '<div class="ct">%s</div></div>'
        % (x_txt(c["x"]), esc(c["contour"]), esc(c["name"]))
    )


def build(payload):
    cases = payload["cases"]
    hero = payload["hero"]
    eve = payload["evening"]
    ai = payload["ai"]
    by_id = {c["id"]: c for c in cases}

    cards = "\n".join(case_card(c) for c in cases)
    teasers = "\n".join(teaser_chip(c) for c in cases)
    claims = "\n".join(
        '<div class="ai-card">'
        '<div class="ai-n">%s</div>'
        '<div class="ai-stat">%s</div>'
        '<h3>%s</h3>'
        '<p>%s</p>'
        '<p class="ai-map">%s</p>'
        '</div>'
        % (esc(c["src"]), esc(c["stat"]), esc(c["t"]), esc(c["d"]), esc(c["map"]))
        for c in ai["claims"]
    )
    src_rows = "\n".join(
        "<tr><td>%s</td><td>%s</td></tr>" % (esc(s["who"]), esc(s["what"]))
        for s in payload["sources"]
    )

    ndfl = by_id["ndfl"]
    fee = by_id["fee"]
    load = by_id["load"]
    exch = by_id["exchange"]
    t1 = by_id["t1"]

    html = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Презентация 04. Скорость операционного учёта 1С</title>
<style>
  :root {
    --bg: %(bg)s; --panel: %(panel)s; --lime: %(lime)s; --coral: %(coral)s;
    --ink: %(ink)s; --dim: %(dim)s; --line: %(line)s;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%%; margin: 0; }
  body {
    font-family: "Segoe UI", Arial, sans-serif;
    color: var(--ink); background: var(--bg); overflow: hidden;
  }
  .deck { position: relative; height: 100vh; overflow: hidden; }
  .slides { display: flex; height: 100%%; transition: transform .4s cubic-bezier(.4,0,.2,1); }
  .slide {
    flex: 0 0 100%%; height: 100%%; padding: 22px 40px 68px;
    background: var(--bg); overflow: hidden; display: flex; flex-direction: column;
  }
  .fill { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; gap: 12px; }
  .fill > .hero-row, .fill > .ai-grid, .fill > .posters, .fill > .conclusions,
  .fill > .chart--bars, .fill > .bar-slot { flex: 1 1 auto; min-height: 0; }
  .fill > .teaser, .fill > .xgrid, .fill > .contrast, .fill > .cite,
  .fill > .facts, .fill > table, .fill > .out { flex: 0 0 auto; }
  .eyebrow {
    font-size: 11px; font-weight: 700; letter-spacing: .18em; text-transform: uppercase;
    color: var(--lime); margin: 0 0 6px;
  }
  h1 { font-size: clamp(2.1rem, 4.2vw, 3.15rem); line-height: .95; margin: 0 0 8px; letter-spacing: -.03em; }
  h2 { font-size: clamp(1.55rem, 2.8vw, 2.15rem); line-height: 1.05; margin: 0 0 8px; letter-spacing: -.02em; }
  h3 { font-size: clamp(1.05rem, 1.6vw, 1.25rem); margin: 0 0 6px; font-weight: 700; }
  .lead { font-size: 17px; line-height: 1.35; color: var(--dim); margin: 0 0 12px; max-width: 58rem; }
  .hero-row {
    flex: 1 1 auto; min-height: 0;
    display: grid; grid-template-columns: minmax(380px, 1.05fr) 1fr;
    gap: 12px 36px; align-items: center;
  }
  .hero-x {
    font-size: clamp(8rem, 18vw, 13.2rem); font-weight: 800; line-height: .78;
    letter-spacing: -.08em; color: var(--lime); margin: 0;
  }
  .hero-side { display: flex; flex-direction: column; gap: 12px; height: 100%%; justify-content: center; }
  .hero-vs { display: flex; gap: 12px; }
  .hero-side .hero-vs { flex-direction: column; }
  .was-box, .now-box {
    flex: 1; border-radius: 16px; padding: 14px 18px 16px; min-height: 96px;
  }
  .teaser {
    display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px;
    flex: 0 0 auto; margin-top: 10px;
  }
  .chip {
    background: var(--panel); border: 1px solid var(--line); border-radius: 12px;
    padding: 10px 12px 11px;
  }
  .chip .cx { font-size: 1.7rem; font-weight: 800; color: var(--lime); letter-spacing: -.04em; line-height: 1; }
  .chip .cn { font-size: 11px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--dim); margin-top: 4px; }
  .chip .ct { font-size: 13px; margin-top: 2px; }
  .saved {
    margin-top: 8px; font-size: clamp(1.5rem, 2.6vw, 2rem); font-weight: 800;
    color: var(--lime); letter-spacing: -.03em;
  }
  .was-box { background: #2a1210; border: 1px solid #5a221c; }
  .now-box { background: #1a260c; border: 1px solid #4a6a18; }
  .tiny { font-size: 11px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }
  .was-box .tiny { color: var(--coral); }
  .now-box .tiny { color: var(--lime); }
  .big { font-size: clamp(1.8rem, 3.4vw, 2.6rem); font-weight: 800; letter-spacing: -.03em; margin-top: 4px; }
  .was-box .big { color: var(--coral); }
  .now-box .big { color: var(--lime); }
  .xgrid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; flex: 0 0 auto; }
  .xcard {
    background: var(--panel); border: 1px solid var(--line); border-radius: 14px;
    padding: 12px 12px 10px; display: flex; flex-direction: column;
  }
  .xc-k { font-size: 11px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: var(--dim); }
  .xc-x { font-size: clamp(2.4rem, 4.6vw, 3.2rem); font-weight: 800; color: var(--lime); letter-spacing: -.05em; line-height: .95; margin: 4px 0 2px; }
  .xc-n { font-size: 15px; font-weight: 700; line-height: 1.2; }
  .xc-t { margin-top: 8px; font-size: 14px; font-weight: 700; }
  .was { color: var(--coral); }
  .now { color: var(--lime); }
  .arr { color: var(--dim); font-weight: 600; }
  .xc-v { font-size: 12px; color: var(--dim); margin-top: 4px; }
  .ai-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; flex: 1; min-height: 0; }
  .ai-card {
    background: var(--panel); border-radius: 16px; padding: 14px 16px 12px;
    border: 1px solid var(--line); display: flex; flex-direction: column;
  }
  .ai-n { font-size: 11px; font-weight: 800; color: var(--lime); letter-spacing: .12em; text-transform: uppercase; }
  .ai-stat {
    font-size: clamp(2.2rem, 4vw, 3rem); font-weight: 800; color: var(--lime);
    letter-spacing: -.05em; line-height: .95; margin: 6px 0 4px;
  }
  .ai-card h3 { font-size: 1.15rem; margin: 2px 0 8px; }
  .ai-card p { margin: 0; font-size: 16.5px; line-height: 1.4; color: #c9cec4; }
  .ai-map { color: var(--lime) !important; font-size: 15px !important; font-weight: 700; margin-top: 12px !important; padding-top: 0; }
  .cite { margin: 8px 0 0; font-size: 12px; line-height: 1.35; color: var(--dim); }
  .contrast {
    margin-top: 12px; background: #1a260c; border-left: 4px solid var(--lime);
    border-radius: 0 12px 12px 0; padding: 12px 16px; font-size: 16px; line-height: 1.35;
  }
  .posters { display: grid; gap: 12px; flex: 1; min-height: 0; }
  .posters.two { grid-template-columns: 1fr 1fr; }
  .posters.three { grid-template-columns: 1fr 1fr 1fr; }
  .poster {
    background: var(--panel); border-radius: 16px; padding: 12px 14px 10px;
    border: 1px solid var(--line); display: flex; flex-direction: column; min-height: 0;
  }
  .p-top { display: flex; justify-content: space-between; gap: 8px; font-size: 11px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--dim); }
  .p-x {
    font-size: clamp(3.4rem, 7vw, 6.2rem); font-weight: 800; color: var(--lime);
    letter-spacing: -.07em; line-height: .85; margin: 4px 0 8px;
    flex: 1 1 auto; display: flex; align-items: center; min-height: 0;
  }
  .p-vs { display: flex; gap: 8px; }
  .poster .was-box, .poster .now-box { min-height: 72px; padding: 8px 10px; }
  .poster .big { font-size: clamp(1.0rem, 1.55vw, 1.28rem); }
  .p-saved { margin: 8px 0 0; font-size: 16px; font-weight: 800; color: var(--lime); }
  .p-meta, .p-what, .p-note { font-size: 15px; line-height: 1.32; margin: 6px 0 0; color: #c9cec4; }
  .p-note { color: var(--dim); }
  .facts { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 8px; flex: 0 0 auto; }
  .fact { background: var(--panel); border-radius: 12px; padding: 12px 14px; border: 1px solid var(--line); }
  .fact b { display: block; font-size: 1.35rem; margin-bottom: 4px; }
  .fact span { color: var(--dim); font-size: 14.5px; }
  .bar-slot { flex: 1 1 auto; min-height: 0; display: flex; }
  .bar-slot .chart { width: 100%%; height: 100%%; }
  .chart--bars { flex: 1 1 auto; min-height: 0; height: 100%%; }
  .d-cap { font-size: 13px; fill: %(dim)s; font-family: "Segoe UI", Arial, sans-serif; }
  .chart { width: 100%%; display: block; }
  .lbl { font-size: 14px; fill: %(dim)s; font-family: "Segoe UI", Arial, sans-serif; }
  .val { font-size: 18px; font-weight: 700; font-family: "Segoe UI", Arial, sans-serif; }
  .val-on { font-size: 16px; font-weight: 800; font-family: "Segoe UI", Arial, sans-serif; }
  table { width: 100%%; border-collapse: collapse; font-size: 15.5px; margin-top: 8px; }
  th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
  th { color: var(--dim); font-size: 11px; letter-spacing: .12em; text-transform: uppercase; }
  .out { font-size: 14px; color: var(--dim); margin-top: 8px; }
  .conclusions { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; flex: 1; }
  .conc {
    background: var(--panel); border-radius: 16px; padding: 18px 20px;
    border: 1px solid var(--line); display: flex; flex-direction: column; justify-content: center;
  }
  .conc .mark { font-size: 13px; font-weight: 800; color: var(--lime); letter-spacing: .12em; text-transform: uppercase; }
  .conc p { margin: 8px 0 0; font-size: 19px; line-height: 1.38; }
  nav.bar {
    position: absolute; left: 0; right: 0; bottom: 0; height: 56px;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 28px; background: linear-gradient(transparent, rgba(9,11,14,.96) 40%%);
  }
  .dots { display: flex; gap: 8px; }
  .dot { width: 9px; height: 9px; border-radius: 50%%; border: 0; background: #3a3f48; cursor: pointer; padding: 0; }
  .dot.on { background: var(--lime); }
  .counter { font-size: 12px; color: var(--dim); letter-spacing: .08em; }
  .arrows { display: flex; gap: 8px; }
  .arrow {
    width: 36px; height: 28px; border-radius: 8px; border: 1px solid var(--line);
    background: var(--panel); color: var(--ink); cursor: pointer; font-size: 16px;
  }
</style>
</head>
<body>
<div class="deck">
  <div class="slides" id="slides">

    <section class="slide" data-slide="1">
      <div class="eyebrow">Презентация 04 · скорость операционного учёта 1С</div>
      <h1>%(title)s</h1>
      <p class="lead">Не часы разработчика. Минуты и часы самой операции, пока растёт клиентская база.</p>
      <div class="fill">
        <div class="hero-row">
          <div class="hero-x">x%(hero_x)s</div>
          <div class="hero-side">
            <div class="hero-vs">
              <div class="was-box">
                <div class="tiny">было · %(hero_key)s</div>
                <div class="big">%(hero_before)s</div>
              </div>
              <div class="now-box">
                <div class="tiny">стало · %(hero_vol)s</div>
                <div class="big">%(hero_after)s</div>
              </div>
            </div>
            <div class="saved">%(hero_saved)s</div>
            <p class="lead" style="margin:0">%(hero_name)s. %(hero_what)s</p>
          </div>
        </div>
        <div class="teaser">%(teasers)s</div>
      </div>
    </section>

    <section class="slide" data-slide="2">
      <div class="eyebrow">Пять закрытых замеров · ФИН · ДУ · МО</div>
      <h2>Самые тяжёлые операции стали короче в разы</h2>
      <p class="lead">Сопоставимо: либо тот же объём, либо время на 1 000 объектов. Утренний регламент ФО в пятёрку не входит: нет закрытого «стало».</p>
      <div class="fill">
        <div class="xgrid">
          %(cards)s
        </div>
        %(xbars)s
      </div>
    </section>

    <section class="slide" data-slide="3">
      <div class="eyebrow">Почему ИИ здесь сильнее человека · внешние источники</div>
      <h2>Где ответ можно проверить, ИИ сильнее. Где нельзя - человек.</h2>
      <p class="lead">%(thesis)s</p>
      <div class="fill">
        <div class="ai-grid">%(claims)s</div>
        <div class="contrast">%(contrast)s</div>
        <p class="cite">%(cites)s</p>
      </div>
    </section>

    <section class="slide" data-slide="4">
      <div class="eyebrow">Самый тяжёлый кейс · ФИН</div>
      <h2>%(ndfl_name)s · %(ndfl_key)s</h2>
      <div class="fill">
        <div class="hero-vs" style="flex:0 0 auto">
          <div class="was-box">
            <div class="tiny">было · эталон 2.8.5.5</div>
            <div class="big">%(ndfl_before)s</div>
          </div>
          <div class="now-box">
            <div class="tiny">стало · чистый расчёт</div>
            <div class="big">%(ndfl_after)s</div>
          </div>
        </div>
        <div class="saved">%(ndfl_saved)s</div>
        <div class="bar-slot">%(ndfl_bar)s</div>
        <div class="facts">
          <div class="fact"><b>%(ndfl_x)s</b><span>кратность чистого расчёта</span></div>
          <div class="fact"><b>%(ndfl_vol)s</b><span>объём прогона</span></div>
          <div class="fact"><b>пакет, кэш, потоки</b><span>%(ndfl_what)s</span></div>
          <div class="fact"><b>стена 6 ч 40 мин</b><span>с паузами это x8,3. Среда: %(ndfl_env)s</span></div>
        </div>
      </div>
    </section>

    <section class="slide" data-slide="5">
      <div class="eyebrow">ДУ · ночное окно</div>
      <h2>Вознаграждение и вечерние регламенты</h2>
      <div class="fill">
        <div class="posters two">
          %(fee_poster)s
          <article class="poster">
            <div class="p-top"><span class="p-k">%(eve_k)s</span><span class="p-key">%(eve_key)s</span></div>
            <h3>%(eve_name)s</h3>
            <div class="p-x">%(eve_x)s</div>
            <div class="p-vs">
              <div class="was-box"><div class="tiny">было</div><div class="big">%(eve_before)s</div></div>
              <div class="now-box"><div class="tiny">стало</div><div class="big">%(eve_after)s</div></div>
            </div>
            %(eve_bar)s
            <p class="p-saved">%(eve_saved)s</p>
            <p class="p-meta">%(eve_vol)s · %(eve_env)s</p>
            <p class="p-what">%(eve_what)s</p>
            <p class="p-note">%(eve_alt)s</p>
          </article>
        </div>
      </div>
    </section>

    <section class="slide" data-slide="6">
      <div class="eyebrow">Сделки · обмен · проведение</div>
      <h2>База выросла. Время на 1 000 объектов упало.</h2>
      <div class="fill">
        <div class="posters three">
          %(load_poster)s
          %(exch_poster)s
          %(t1_poster)s
        </div>
      </div>
    </section>

    <section class="slide" data-slide="7">
      <div class="eyebrow">Выводы</div>
      <h2>Окно ночи не растягивается. Операции - да.</h2>
      <div class="fill">
        <div class="conclusions">
          <div class="conc">
            <div class="mark">Рост</div>
            <p>Клиентов и сделок больше. Ночное и утреннее окно те же. Без ускорения операций база упирается в часы.</p>
          </div>
          <div class="conc">
            <div class="mark">Замеры</div>
            <p>НДФЛ x10, вознаграждение x9, загрузка сделок x13, обмен x5, проведение Т-1 x5. Это закрытые протоколы, не оценка.</p>
          </div>
          <div class="conc">
            <div class="mark">Почему ИИ</div>
            <p>Harvard и BCG: на проверяемых задачах качество выше на 40%%+, без эталона ИИ чаще ошибается, чем человек. McKinsey: переписать существующий код - 20-30%% быстрее, придумать сложное с нуля - менее 10%%. Наши кейсы - существующая операция и замер, не новая система.</p>
          </div>
          <div class="conc">
            <div class="mark">Не складывать</div>
            <p>Деньги презентаций 01 и 02 сюда не входят. Часы оптимизации уже в 02. Здесь только длительность операции.</p>
          </div>
        </div>
        <table>
          <thead><tr><th>Источник</th><th>Что зафиксировано</th></tr></thead>
          <tbody>%(src_rows)s</tbody>
        </table>
        <p class="out">%(fo)s</p>
      </div>
    </section>

  </div>
  <nav class="bar">
    <div class="dots" id="dots"></div>
    <div class="counter" id="counter">1 / 7</div>
    <div class="arrows">
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
        "bg": C_BG, "panel": C_PANEL, "lime": C_LIME, "coral": C_CORAL,
        "ink": C_INK, "dim": C_DIM, "line": C_LINE,
        "title": esc(payload["title"]),
        "hero_x": hero["x_head"],
        "hero_key": esc(hero["key"]),
        "hero_before": esc(hero["before_label"]),
        "hero_after": esc(hero["after_label"]),
        "hero_vol": esc(hero["volume"]),
        "hero_name": esc(hero["name"]),
        "hero_what": esc(hero["what"]),
        "hero_saved": esc(saved_line(hero)),
        "teasers": teasers,
        "cards": cards,
        "xbars": svg_x_bars(cases),
        "thesis": esc(ai["thesis"]),
        "claims": claims,
        "contrast": esc(ai["contrast"]),
        "cites": esc(ai["cites"]),
        "ndfl_name": esc(ndfl["name"]),
        "ndfl_key": esc(ndfl["key"]),
        "ndfl_before": esc(ndfl["before_label"]),
        "ndfl_after": esc(ndfl["after_label"]),
        "ndfl_bar": svg_pair(ndfl["before_min"], ndfl["after_min"],
                             ndfl["before_label"], ndfl["after_label"],
                             "Чистый расчёт НДФЛ, минуты"),
        "ndfl_saved": esc(saved_line(ndfl)),
        "ndfl_x": x_txt(ndfl["x"]),
        "ndfl_vol": esc(ndfl["volume"]),
        "ndfl_env": esc(ndfl["env"]),
        "ndfl_what": esc(ndfl["what"]),
        "fee_poster": poster(
            fee, '<p class="p-note">%s</p>' % esc(fee["note"]),
            svg_pair(fee["before_min"], fee["after_min"],
                     fee["before_short"], fee["after_short"], compact=True)),
        "eve_k": esc(eve["contour"]),
        "eve_key": esc(eve["key"]),
        "eve_name": esc(eve["name"]),
        "eve_x": x_txt(eve["x"]),
        "eve_before": esc(eve["before_label"]),
        "eve_after": esc(eve["after_label"]),
        "eve_vol": esc(eve["volume"]),
        "eve_env": esc(eve["env"]),
        "eve_what": esc(eve["what"]),
        "eve_alt": esc(eve["alt"]),
        "eve_bar": svg_pair(eve["before_min"], eve["after_min"],
                            eve["before_label"], eve["after_label"], compact=True),
        "eve_saved": esc(saved_line(eve)),
        "load_poster": poster(
            load, '<p class="p-note">%s</p>' % esc(load["note"]),
            svg_pair(load["before_min"], load["after_min"],
                     load["before_short"], load["after_short"], compact=True)),
        "exch_poster": poster(
            exch, '<p class="p-note">%s</p>' % esc(exch["note"]),
            svg_pair(exch["before_min"], exch["after_min"],
                     exch["before_short"], exch["after_short"], compact=True)),
        "t1_poster": poster(
            t1, '<p class="p-note">%s</p>' % esc(t1["note"]),
            svg_pair(t1["before_min"], t1["after_min"],
                     t1["before_short"], t1["after_short"], compact=True)),
        "src_rows": src_rows,
        "fo": esc(payload["out_of_scope"]["fo"]),
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
    raise SystemExit(main())
