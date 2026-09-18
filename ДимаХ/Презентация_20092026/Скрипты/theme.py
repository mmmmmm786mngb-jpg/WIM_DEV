#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Единый оптимистичный стиль пакета презентаций 20.09.2026.

Опора: cream/sage company profile (Claymoon Endeavour), beige minimalist pitch,
Duarte Glance Test - заголовок читается за 3 секунды.
Без CDN. Segoe UI + Georgia. 1600x900.
"""

# Cream / sage / peach. Светлая, тёплая, без тёмно-синего.
PAPER = "#fbf6ee"
CARD = "#fffdf8"
INK = "#2a241c"
MUTED = "#7a7166"
LINE = "#eadfce"
SAGE = "#4f7d5c"
SAGE_SOFT = "#e7f2ea"
PEACH = "#c4785b"
PEACH_SOFT = "#fbeee6"
GOLD = "#c4a36a"


def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def rank_html(rows):
    parts = ['<div class="rank">']
    for key, name, value in rows:
        parts.append(
            '<div class="rank-row"><div><div class="rank-k">%s</div>'
            '<div class="rank-n">%s</div></div><div class="rank-v">%s</div></div>'
            % (esc(key), esc(name), esc(value))
        )
    parts.append("</div>")
    return "".join(parts)


def css():
    return """
  :root {
    --paper: %(paper)s; --card: %(card)s; --ink: %(ink)s; --muted: %(muted)s;
    --line: %(line)s; --sage: %(sage)s; --sage-soft: %(sage_soft)s;
    --peach: %(peach)s; --peach-soft: %(peach_soft)s; --gold: %(gold)s;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%%; margin: 0; }
  body {
    font-family: "Segoe UI", Arial, sans-serif;
    color: var(--ink);
    background:
      radial-gradient(1100px 480px at 6%% -12%%, #fff8e8 0%%, transparent 55%%),
      radial-gradient(800px 380px at 108%% 8%%, #eef6ef 0%%, transparent 52%%),
      var(--paper);
    overflow: hidden;
  }
  .deck { position: relative; height: 100vh; overflow: hidden; }
  .slides { display: flex; height: 100%%; transition: transform .4s cubic-bezier(.4,0,.2,1); }
  .slide {
    flex: 0 0 100%%; height: 100%%; padding: 22px 40px 62px;
    overflow: hidden; display: flex; flex-direction: column;
  }
  .fill { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; gap: 12px; }
  .fill > .grid-2, .fill > .grid-3, .fill > .grid-4,
  .fill > .teaser, .fill > .ai-grid, .fill > .pair,
  .fill > .hero-vs, .fill > .case-top, .fill > .chart { flex: 1 1 auto; min-height: 0; }
  .fill > .kpi-row, .fill > .hero-row, .fill > .legend, .fill > .card { flex: 0 0 auto; }
  .fill > .xgrid { flex: 1 1 auto; min-height: 0; }
  .fill > .card.grow { flex: 1 1 auto; min-height: 0; }
  .card.grow .chart { height: 100%%; }
  .fill > .note { margin-top: auto; }
  .fill > .note, .fill > .how, .fill > .result, .fill > .foot, .fill > .src,
  .fill > table, .fill > .out, .fill > .cite, .fill > .contrast { flex: 0 0 auto; }
  .eyebrow {
    font-size: 15px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
    color: var(--peach); margin: 0 0 8px;
  }
  h1, h2, .serif {
    font-family: Georgia, "Times New Roman", serif; font-weight: 400; letter-spacing: -.02em;
  }
  h1 { font-size: clamp(2.55rem, 4.4vw, 3.35rem); line-height: 1.06; margin: 0 0 10px; }
  h2 { font-size: clamp(2.15rem, 3.6vw, 2.85rem); line-height: 1.1; margin: 0 0 10px; }
  .lead { font-size: 22px; line-height: 1.32; color: var(--muted); margin: 0 0 12px; max-width: 68rem; }
  .kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
  .kpi-row.three { grid-template-columns: 1fr 1fr 1fr; }
  .kpi {
    background: var(--card); border: 1px solid var(--line); border-radius: 18px;
    padding: 14px 16px; display: flex; flex-direction: column; justify-content: center;
    box-shadow: 0 8px 22px rgba(90, 70, 40, .05);
  }
  .kpi-num {
    font-family: Georgia, "Times New Roman", serif;
    font-size: clamp(2.3rem, 3.8vw, 3.05rem); line-height: .92; color: var(--ink);
  }
  .kpi-unit { font-size: .42em; margin-left: 4px; color: var(--muted); }
  .kpi-lbl { font-size: 18px; font-weight: 700; margin-top: 8px; }
  .kpi-sub { font-size: 16px; color: var(--muted); margin-top: 4px; line-height: 1.25; }
  .card {
    background: var(--card); border: 1px solid var(--line); border-radius: 18px;
    padding: 16px 18px; display: flex; flex-direction: column; min-height: 0;
    box-shadow: 0 8px 22px rgba(90, 70, 40, .04);
  }
  .card.num, .ai-card { justify-content: center; }
  .stat {
    font-family: Georgia, "Times New Roman", serif;
    font-size: clamp(2.8rem, 5.6vw, 4rem); line-height: .9; margin: 8px 0 10px;
  }
  .h4 { font-size: 15px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase;
        color: var(--sage); margin: 0 0 8px; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
  .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
  .grid-5 { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
  .note {
    background: var(--sage-soft); border-radius: 14px; padding: 14px 18px;
    font-size: 20px; line-height: 1.32; color: #355743;
  }
  .note.warn { background: var(--peach-soft); color: #6a3b2c; }
  .formula { font-size: 20px; line-height: 1.35; }
  .formula code { font-family: "Segoe UI", Arial, sans-serif; font-weight: 700; color: var(--sage); }
  .legend { display: flex; gap: 18px; flex-wrap: wrap; margin: 0 0 8px; font-size: 18px; color: var(--muted); }
  .legend span { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; }
  .legend i { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
  table { width: 100%%; border-collapse: collapse; font-size: 15px; }
  th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
  th { color: var(--muted); font-size: 11px; letter-spacing: .1em; text-transform: uppercase; }
  td.n, th.n { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
  td.save { color: var(--sage); font-weight: 800; }
  tr.total td { font-weight: 800; background: var(--sage-soft); border-bottom: 0; }
  .src, .foot, .out, .cite { font-size: 16px; color: var(--muted); line-height: 1.3; }
  .chart { width: 100%%; height: auto; max-height: 100%%; display: block; }
  .chart text { font-family: "Segoe UI", Arial, sans-serif; }
  .ax, .ax-title { font-size: 15px; fill: %(muted)s; }
  .lbl { font-size: 16px; fill: %(ink)s; font-weight: 700; }
  .val { font-size: 15px; fill: %(ink)s; font-weight: 700; }
  .val-big { font-size: 17px; fill: %(ink)s; font-weight: 800; }
  .val-on { font-size: 20px; font-weight: 800; }
  .d-cap { font-size: 18px; fill: %(muted)s; font-weight: 700; }
  .d-val { font-size: 28px; fill: #fffdf8; font-weight: 800; }
  .d-lbl { font-size: 16px; fill: %(muted)s; }
  .donut-num { font-size: 28px; font-weight: 800; fill: %(ink)s; font-family: Georgia, serif; }
  .donut-cap, .donut-sum { font-size: 12px; fill: %(muted)s; }
  .facts { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
  .facts li { display: flex; gap: 10px; font-size: 16px; line-height: 1.38; }
  .facts .b {
    flex: 0 0 22px; height: 22px; border-radius: 50%%; background: var(--peach); color: #fffdf8;
    font-size: 12px; font-weight: 800; display: inline-flex; align-items: center; justify-content: center;
  }
  .was-box, .now-box {
    flex: 1; border-radius: 16px; padding: 18px 20px;
    display: flex; flex-direction: column; justify-content: center;
  }
  .was-box { background: var(--peach-soft); border: 1px solid #f0d2c0; }
  .now-box { background: var(--sage-soft); border: 1px solid #cfe0d3; }
  .tiny { font-size: 15px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
  .was-box .tiny { color: var(--peach); }
  .now-box .tiny { color: var(--sage); }
  .big { font-family: Georgia, serif; font-size: clamp(2.4rem, 5.5vw, 4.2rem); margin-top: 6px; line-height: .95; }
  .was-box .big { color: var(--peach); }
  .now-box .big { color: var(--sage); }
  .hero-x {
    font-family: Georgia, serif; font-size: clamp(6.5rem, 14vw, 10rem);
    line-height: .82; color: var(--sage); letter-spacing: -.06em; margin: 0;
  }
  .hero-row { display: grid; grid-template-columns: .9fr 1.1fr; gap: 20px; align-items: center; }
  .fill > .hero-row.tall { flex: 1 1 auto; min-height: 0; }
  .stack { display: flex; flex-direction: column; gap: 12px; min-height: 0; }
  .stack > .card { flex: 1 1 auto; }
  .hero-vs { min-height: 0; }
  .hero-side { display: flex; flex-direction: column; gap: 12px; justify-content: center; }
  .hero-vs { display: flex; gap: 10px; }
  .saved { font-size: 26px; font-weight: 800; color: var(--sage); }
  .teaser { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
  .xgrid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
  .chip, .xcard {
    background: var(--card); border: 1px solid var(--line); border-radius: 16px;
    padding: 12px 14px; display: flex; flex-direction: column;
    box-shadow: 0 8px 22px rgba(90, 70, 40, .04);
  }
  .xcard { justify-content: center; gap: 6px; }
  .chip { justify-content: space-between; }
  .chip .cx { font-size: 14px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; color: var(--sage); }
  .chip .ct { font-family: Georgia, "Times New Roman", serif; font-size: 1.45rem; line-height: 1.2; margin: 8px 0 6px; }
  .xcard .xc-x, .chip .xc-x { font-family: Georgia, serif; font-size: 2.2rem; color: var(--sage); line-height: 1; }
  .chip .cn, .xc-k { font-size: 14px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
  .xc-t { margin-top: 8px; font-size: 18px; font-weight: 700; }
  .xc-v { font-size: 16px; color: var(--muted); margin-top: 4px; }
  .essence { font-size: 18px; line-height: 1.3; margin: 4px 0 0; }
  .chip-top, .chip-mid { flex: 0 0 auto; }
  .was { color: var(--peach); font-weight: 700; }
  .now { color: var(--sage); font-weight: 700; }
  .arr { color: var(--gold); font-weight: 700; }
  .ai-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
  .ai-card {
    background: var(--card); border: 1px solid var(--line); border-radius: 16px;
    padding: 14px 16px; display: flex; flex-direction: column;
  }
  .ai-n { font-size: 14px; font-weight: 800; color: var(--sage); letter-spacing: .12em; text-transform: uppercase; }
  .ai-stat { font-family: Georgia, serif; font-size: clamp(2.4rem, 3.8vw, 3.1rem); color: var(--sage); line-height: .95; margin: 8px 0 12px; }
  .ai-card h3 { font-size: 1.35rem; margin: 0 0 8px; }
  .ai-card p { margin: 0; font-size: 18px; line-height: 1.32; }
  .ai-map { color: var(--sage) !important; font-weight: 700; margin-top: 10px !important; font-size: 18px !important; }
  .contrast {
    background: var(--sage-soft); border-left: 4px solid var(--sage);
    border-radius: 0 12px 12px 0; padding: 14px 18px; font-size: 20px; line-height: 1.32;
  }
  .path p { margin: 0; font-size: 18px; line-height: 1.32; }
  .path .n { font-family: Georgia, serif; font-size: clamp(2.3rem, 4vw, 3rem); margin: 4px 0; line-height: .95; }
  .fit { font-size: 15px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
  .spoiler p { margin: 0; font-family: Georgia, serif; font-size: 20px; line-height: 1.28; }
  .spoiler .k, .k {
    font-size: 14px; font-weight: 800; letter-spacing: .1em;
    text-transform: uppercase; color: var(--muted);
  }
  .spoiler .k { color: var(--sage); margin: 0 0 6px; }
  .forks { margin: 6px 0 0; padding: 0; list-style: none; font-size: 18px; }
  .box p { margin: 6px 0 0; font-size: 18px; line-height: 1.32; }
  .pair-sm .box p { font-size: 18px; }
  .result { font-size: 22px; padding: 14px 18px; }
  .how { font-size: 18px; }
  .hero-n { font-family: Georgia, serif; font-size: clamp(2.6rem, 4.4vw, 3.5rem); line-height: .9; }
  .hero-u { font-size: 18px; font-weight: 700; color: var(--peach); margin-top: 6px; }
  .hero-h { font-size: 16px; color: var(--muted); margin-top: 4px; }
  .fact b { font-family: Georgia, serif; font-size: clamp(1.9rem, 2.8vw, 2.5rem); line-height: 1; }
  .fact span { color: var(--muted); font-size: 16px; margin-top: 6px; }
  .clk-big { font-size: 28px; fill: #fffdf8; font-weight: 800; font-family: Georgia, serif; }
  .clk-n { font-size: 18px; font-weight: 800; }
  .clk-sub { font-size: 14px; fill: #fffdf8; }
  .strip-n { font-size: 18px; font-weight: 800; }
  .strip-l { font-size: 13px; }
  .strip-ev { font-size: 14px; fill: %(muted)s; font-weight: 700; }
  .rank { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 14px; }
  .fill > .rank { flex: 1 1 auto; min-height: 0; }
  .rank-row {
    display: flex; justify-content: space-between; align-items: center; gap: 12px;
    background: var(--card); border: 1px solid var(--line); border-radius: 14px;
    padding: 10px 16px;
  }
  .rank-k { font-size: 18px; font-weight: 800; }
  .rank-n { font-size: 16px; color: var(--muted); margin-top: 2px; }
  .rank-v { font-family: Georgia, serif; font-size: 1.7rem; color: var(--sage); white-space: nowrap; }
  .roles { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .fill > .roles { flex: 1 1 auto; min-height: 0; }
  .role { padding: 18px 20px; }
  .role ul { margin: 8px 0 0; padding-left: 1.2em; }
  .role li { font-size: 24px; line-height: 1.4; margin: 16px 0; }
  .steps { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
  .fill > .steps { flex: 1 1 auto; }
  .step {
    background: var(--card); border: 1px solid var(--line); border-radius: 16px;
    padding: 28px 16px; display: flex; flex-direction: column; justify-content: flex-start;
  }
  .step .n { font-family: Georgia, serif; font-size: 4.2rem; color: var(--sage); line-height: 1; }
  .step .t { font-size: 24px; font-weight: 700; margin-top: 16px; }
  .card.role { justify-content: center; }
  table { width: 100%%; border-collapse: collapse; font-size: 18px; }
  th { color: var(--muted); font-size: 14px; letter-spacing: .08em; text-transform: uppercase; }
  th, td { text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
  .path {
    background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 16px 18px;
    display: flex; flex-direction: column; justify-content: space-between; min-height: 0; gap: 8px;
  }
  .path-ok { background: var(--sage-soft); border-color: #cfe0d3; }
  .path-bad { background: var(--peach-soft); border-color: #f0d2c0; }
  .path-ok .n { color: var(--sage); }
  .path-bad .n { color: var(--peach); }
  .spoiler {
    background: var(--sage-soft); border: 1px solid #cfe0d3; border-radius: 14px;
    padding: 12px 14px; color: #2d4a36;
  }
  .forks li { display: flex; gap: 8px; margin: 8px 0; }
  .fn {
    flex: 0 0 26px; height: 26px; border-radius: 50%%; background: var(--peach); color: #fffdf8;
    font-size: 14px; font-weight: 800; display: inline-flex; align-items: center; justify-content: center;
  }
  .box { background: var(--card); border-radius: 16px; padding: 14px 16px; border: 1px solid var(--line); }
  .box-hyp { background: var(--peach-soft); border-color: #f0d2c0; }
  .box-ok { background: var(--sage-soft); border-color: #cfe0d3; }
  .box-chk { background: #fff7ea; border-color: #ecd9b0; }
  .pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .result {
    background: var(--sage); color: #f6fff8; border-radius: 14px;
    padding: 14px 18px; font-size: 22px; font-weight: 700; line-height: 1.32;
  }
  .how {
    background: var(--card); border: 1px dashed var(--gold); border-radius: 14px;
    padding: 12px 16px; font-size: 18px; line-height: 1.35;
  }
  .hero-card {
    background: var(--card); border: 1px solid var(--line); border-radius: 18px;
    padding: 12px 16px; display: flex; flex-direction: column; justify-content: center;
  }
  .case-top { display: grid; grid-template-columns: 260px 1fr; gap: 12px; }
  .facts-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
  .fact {
    background: var(--card); border: 1px solid var(--line); border-radius: 16px;
    padding: 10px 14px; display: flex; flex-direction: column; justify-content: center;
  }
  nav.bar {
    position: absolute; left: 0; right: 0; bottom: 0; height: 52px;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 28px; background: linear-gradient(transparent, rgba(251,246,238,.97) 40%%);
  }
  .dots { display: flex; gap: 8px; }
  .dot { width: 9px; height: 9px; border-radius: 50%%; border: 0; background: #ddd2c2; cursor: pointer; padding: 0; }
  .dot.on { background: var(--sage); }
  .counter { font-size: 14px; color: var(--muted); letter-spacing: .08em; }
  .arrows { display: flex; gap: 8px; }
  .arrow {
    width: 36px; height: 28px; border-radius: 8px; border: 1px solid var(--line);
    background: var(--card); color: var(--ink); cursor: pointer; font-size: 16px;
  }
  .deck-title { font-size: 14px; color: var(--muted); letter-spacing: .06em; }
""" % {
        "paper": PAPER, "card": CARD, "ink": INK, "muted": MUTED, "line": LINE,
        "sage": SAGE, "sage_soft": SAGE_SOFT, "peach": PEACH, "peach_soft": PEACH_SOFT,
        "gold": GOLD,
    }


def nav(label):
    return """
  <nav class="bar">
    <span class="deck-title">%s</span>
    <div class="dots" id="dots"></div>
    <div class="counter" id="counter">1 / 1</div>
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
""" % esc(label)


def wrap(page_title, deck_label, slides_html):
    return (
        "<!DOCTYPE html>\n<html lang=\"ru\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>%s</title>\n<style>%s</style>\n</head>\n<body>\n"
        "<div class=\"deck\">\n  <div class=\"slides\" id=\"slides\">\n%s\n  </div>\n"
        % (esc(page_title), css(), slides_html)
        + nav(deck_label)
    )
