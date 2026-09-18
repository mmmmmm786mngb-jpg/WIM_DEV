#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка презентации 05.

Цепочка: первая идея -> что замерили -> три альтернативы -> как замеряли -> что выбрали и почему.
"""

import json
import os
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)

BASE = os.path.dirname(SCRIPTS)
DATA = os.path.join(SCRIPTS, "p05_dataset.json")
OUT = os.path.join(BASE, "05_cursor_decisions.html")

C_PAPER = "#fbf6ee"
C_CARD = "#fffdf8"
C_INK = "#2a241c"
C_MUTED = "#7a7166"
C_LINE = "#eadfce"
C_SAGE = "#4f7d5c"
C_SAGE_SOFT = "#e7f2ea"
C_PEACH = "#c4785b"
C_PEACH_SOFT = "#fbeee6"
C_GOLD = "#c4a36a"


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def steps5_html():
    items = [
        ("1", "s1", "Первая идея",
         "Что хотели сделать сразу. Править общий код базы. Нарастить потоки. Сделать две волны обмена."),
        ("2", "s2", "Что показали цифры",
         "Сколько заняло и где узкое место. 4 часа СЧА. 3 часа 36 минут проведения. Документ Сделка ещё не в пакетах, как БП СделкиTn."),
        ("3", "s3", "Три варианта",
         "Три реальных хода, и первая идея среди них. Её не прячем и не выбираем до цифр."),
        ("4", "s4", "Как проверяли",
         "Повтор на том же объёме. Сверка с контрольными цифрами. Разбор текущего кода обработки."),
        ("5", "s5", "Что взяли",
         "Что ушло в работу или в ТЗ. И одной фразой: почему два других варианта не взяли."),
    ]
    parts = ['<div class="steps5">']
    for n, cls, title, text in items:
        parts.append(
            '<div class="step5 %s"><div class="n">%s</div>'
            '<div class="body"><div class="t">%s</div><p>%s</p></div></div>'
            % (cls, n, esc(title), esc(text))
        )
    parts.append("</div>")
    return "".join(parts)


def alts_html(alts, big=False):
    cls = "alts alts-lg" if big else "alts"
    parts = ['<div class="%s">' % cls]
    for i, a in enumerate(alts, 1):
        mark = '<span class="first-tag">первая идея</span>' if a.get("first") else ""
        extra = "<p>%s</p>" % esc(a["d"]) if big else ""
        parts.append(
            '<div class="alt%s">'
            '<div class="alt-top"><span class="an">%d</span><b>%s</b>%s</div>'
            "%s</div>"
            % (" is-first" if a.get("first") else "", i, esc(a["t"]), mark, extra)
        )
    parts.append("</div>")
    return "".join(parts)


def teaser(c):
    alts = " / ".join(a["t"] for a in c["alts"])
    rows = [
        ("1", "Первая идея", c.get("first_idea_short") or c["first_idea"]),
        ("2", "Что показали цифры", c["measured_short"]),
        ("3", "Три варианта", alts),
        ("4", "Как проверяли", c.get("how_short") or (c["how"].split(". ")[0] + ".")),
        ("5", "Что взяли", c.get("chose_short") or c["chose"]),
    ]
    lines = []
    for n, lab, text in rows:
        lines.append(
            '<div class="line l%s"><span class="ln">%s</span>'
            '<div><div class="k">%s</div><p>%s</p></div></div>'
            % (n, n, esc(lab), esc(text))
        )
    return (
        '<div class="chip">'
        '<div class="cx">%s · %s</div>'
        '<div class="ct">%s</div>'
        '%s</div>'
        % (esc(c["contour"]), esc(c["key"]), esc(c["name"]), "".join(lines))
    )


def case_block(c):
    return """
        <p class="lead">%(problem)s</p>
        <div class="chain">
          <div class="row two">
            <article class="box b1">
              <div class="num">1</div>
              <div class="k">Первая идея</div>
              <p>%(first)s</p>
            </article>
            <article class="box b2">
              <div class="num">2</div>
              <div class="k">Что показали цифры</div>
              <p>%(measured)s</p>
            </article>
          </div>
          <article class="box b3">
            <div class="num">3</div>
            <div class="k">Три варианта</div>
            %(alts)s
          </article>
          <article class="box b4">
            <div class="num">4</div>
            <div class="k">Как проверяли</div>
            <p>%(how)s</p>
          </article>
          <article class="box b5">
            <div class="num">5</div>
            <div class="k">Что выбрали и почему</div>
            <p class="chose">%(chose)s</p>
            <p>%(why)s</p>
          </article>
        </div>
        <div class="result">%(result)s</div>
""" % {
        "problem": esc(c["problem"]),
        "first": esc(c["first_idea"]),
        "measured": esc(c["measured"]),
        "alts": alts_html(c["alts"], big=True),
        "how": esc(c["how"]),
        "chose": esc(c["chose"]),
        "why": esc(c["why_chose"]),
        "result": esc(c["result"]),
    }


def close_html(cases):
    parts = ['<div class="verdict">']
    for c in cases:
        parts.append(
            '<article class="vcard">'
            '<div class="cx">%s · %s</div>'
            '<h3>%s</h3>'
            '<div class="v-first"><div class="k">Первая идея</div>'
            '<p>%s</p><span>%s</span></div>'
            '<div class="v-took"><div class="k">Что взяли</div>'
            '<p>%s</p></div>'
            '<div class="v-res">%s</div>'
            '</article>'
            % (
                esc(c["contour"]), esc(c["key"]), esc(c["close_title"]),
                esc(c["close_first"]), esc(c["close_why"]),
                esc(c["close_took"]), esc(c["close_result"]),
            )
        )
    parts.append("</div>")
    return "".join(parts)


def case_slides_html(cases):
    parts = []
    for c in cases:
        parts.append("""
    <section class="slide">
      <div class="eyebrow">%s · %s</div>
      <h2>%s</h2>
      <div class="fill">%s
        <div class="foot">%s</div>
      </div>
    </section>
""" % (esc(c["contour"]), esc(c["key"]), esc(c["name"]),
           case_block(c), esc(c["source"])))
    return "".join(parts)


def build(payload):
    cases = payload["cases"]
    teasers = "\n".join(teaser(c) for c in cases)
    roles = "\n".join(
        '<div class="role"><div class="k">%s</div><ul>%s</ul></div>'
        % (esc(r["who"]), "".join("<li>%s</li>" % esc(x) for x in r["items"]))
        for r in payload["roles"]
    )

    html = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Презентация 05. Cursor помогает выбрать решение</title>
<style>
  :root {
    --paper: %(paper)s; --card: %(card)s; --ink: %(ink)s; --muted: %(muted)s;
    --line: %(line)s; --sage: %(sage)s; --sage-soft: %(sage_soft)s;
    --peach: %(peach)s; --peach-soft: %(peach_soft)s; --gold: %(gold)s;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%%; margin: 0; }
  body {
    font-family: "Segoe UI", Arial, sans-serif; color: var(--ink);
    background:
      radial-gradient(1200px 500px at 8%% -10%%, #fff8e8 0%%, transparent 55%%),
      radial-gradient(900px 420px at 110%% 10%%, #eef6ef 0%%, transparent 50%%),
      var(--paper);
    overflow: hidden;
  }
  .deck { position: relative; height: 100vh; overflow: hidden; }
  .slides { display: flex; height: 100%%; transition: transform .4s cubic-bezier(.4,0,.2,1); }
  .slide {
    flex: 0 0 100%%; height: 100%%; padding: 16px 32px 56px;
    overflow: hidden; display: flex; flex-direction: column;
  }
  .fill { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; gap: 10px; }
  .fill > .teaser, .fill > .steps5, .fill > .roles,
  .fill > .verdict, .fill > .chain { flex: 1 1 auto; min-height: 0; }
  .fill > .lead, .fill > .note, .fill > .result, .fill > .foot, .fill > .punch { flex: 0 0 auto; }
  .eyebrow {
    font-size: 15px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
    color: var(--peach); margin: 0 0 6px;
  }
  h1 { font-family: Georgia, "Times New Roman", serif; font-size: clamp(2.1rem, 3.6vw, 2.8rem);
       line-height: 1.06; margin: 0 0 8px; letter-spacing: -.02em; }
  h2 { font-family: Georgia, "Times New Roman", serif; font-size: clamp(1.7rem, 2.8vw, 2.3rem);
       line-height: 1.1; margin: 0 0 6px; }
  .lead { font-size: 22px; line-height: 1.32; color: var(--muted); margin: 0 0 8px; max-width: 70rem; }
  .teaser { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
  .chip {
    background: var(--card); border: 1px solid var(--line); border-radius: 18px;
    padding: 14px 16px; display: flex; flex-direction: column; gap: 0;
    justify-content: space-between;
    box-shadow: 0 8px 24px rgba(90, 70, 40, .05);
  }
  .chip .cx { font-size: 15px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; color: var(--sage); }
  .chip .ct { font-family: Georgia, serif; font-size: 24px; line-height: 1.18; margin: 8px 0 12px; }
  .line { display: flex; gap: 10px; align-items: flex-start; }
  .ln {
    flex: 0 0 30px; width: 30px; height: 30px; border-radius: 50%%; background: var(--peach);
    color: #fffdf8; font-size: 15px; font-weight: 800; display: inline-flex;
    align-items: center; justify-content: center; margin-top: 2px;
  }
  .l2 .ln, .l4 .ln { background: var(--gold); }
  .l5 .ln { background: var(--sage); }
  .k { font-size: 14px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
  .line p { margin: 2px 0 0; font-size: 19px; line-height: 1.3; }
  .chain { display: flex; flex-direction: column; gap: 10px; min-height: 0; }
  .row.two { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; flex: 1.1 1 0; min-height: 0; }
  .b3, .b4, .b5 { flex: 1 1 0; min-height: 0; display: flex; flex-direction: column; }
  .b5 { flex: 1.35 1 0; }
  .box {
    background: var(--card); border: 1px solid var(--line); border-radius: 16px;
    padding: 12px 16px; position: relative; min-height: 0;
    display: flex; flex-direction: column; justify-content: center;
  }
  .b1 { background: var(--peach-soft); border-color: #f0d2c0; }
  .b2, .b4 { background: #fff7ea; border-color: #ecd9b0; }
  .b5 { background: var(--sage-soft); border-color: #cfe0d3; }
  .num {
    position: absolute; right: 12px; top: 8px; font-family: Georgia, serif;
    font-size: 42px; font-weight: 800; color: rgba(42,36,28,.16); line-height: 1;
  }
  .box .k { margin-bottom: 4px; font-size: 13px; }
  .box p { margin: 0; font-size: 19px; line-height: 1.34; }
  .box p.chose { font-size: 22px; font-weight: 800; margin-bottom: 6px; }
  .alts { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 8px; flex: 1; }
  .alt {
    background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: 12px 14px;
    display: flex; flex-direction: column; justify-content: center;
  }
  .alt.is-first { border-color: var(--peach); background: #fffdf8; }
  .alt-top { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .an {
    flex: 0 0 24px; width: 24px; height: 24px; border-radius: 50%%; background: var(--ink);
    color: #fff; font-size: 13px; font-weight: 800; display: inline-flex;
    align-items: center; justify-content: center;
  }
  .alt b { font-size: 18px; }
  .alt p { margin: 6px 0 0; font-size: 17px; line-height: 1.32; color: var(--ink); }
  .first-tag { font-size: 12px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase;
           color: var(--peach); background: var(--peach-soft); border-radius: 8px; padding: 3px 7px; }
  .result {
    background: var(--sage); color: #f6fff8; border-radius: 14px;
    padding: 12px 16px; font-size: 20px; font-weight: 700; line-height: 1.3;
  }
  .note {
    background: var(--sage-soft); border-radius: 14px; padding: 12px 16px;
    font-size: 18px; line-height: 1.35; color: #355743;
  }
  .steps5 { display: grid; grid-template-rows: repeat(5, 1fr); gap: 8px; }
  .step5 {
    border-radius: 16px; border: 1px solid var(--line); padding: 8px 22px;
    display: flex; flex-direction: row; align-items: center; gap: 22px; min-height: 0;
  }
  .step5.s1 { background: var(--peach-soft); border-color: #f0d2c0; }
  .step5.s2, .step5.s4 { background: #fff7ea; border-color: #ecd9b0; }
  .step5.s3 { background: var(--card); }
  .step5.s5 { background: var(--sage-soft); border-color: #cfe0d3; }
  .step5 .n { font-family: Georgia, serif; font-size: 4rem; line-height: .9; font-weight: 800; color: var(--peach); flex: 0 0 64px; }
  .step5.s2 .n, .step5.s4 .n { color: var(--gold); }
  .step5.s5 .n { color: var(--sage); }
  .step5 .body { min-width: 0; }
  .step5 .t { font-family: Georgia, serif; font-size: 28px; font-weight: 700; margin: 0 0 2px; line-height: 1.1; }
  .step5 p { margin: 0; font-size: 22px; line-height: 1.3; }
  .roles { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .role {
    background: var(--card); border: 1px solid var(--line); border-radius: 18px;
    padding: 18px 28px 20px; display: flex; flex-direction: column;
  }
  .role .k { color: var(--sage); font-size: 18px; margin: 0 0 4px; flex: 0 0 auto; }
  .role ul {
    margin: 0; padding: 0 0 0 28px; font-size: 25px; line-height: 1.32;
    flex: 1; display: flex; flex-direction: column; justify-content: space-evenly;
  }
  .role li { margin: 0; }
  .verdict { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
  .vcard {
    background: var(--card); border: 1px solid var(--line); border-radius: 18px;
    padding: 16px 18px; display: flex; flex-direction: column; gap: 12px; min-height: 0;
    box-shadow: 0 8px 24px rgba(90, 70, 40, .05);
  }
  .vcard .cx { font-size: 15px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; color: var(--sage); }
  .vcard h3 { font-family: Georgia, serif; font-size: 32px; line-height: 1.12; margin: 0; }
  .v-first, .v-took {
    border-radius: 14px; padding: 14px 16px; flex: 1 1 0; min-height: 0;
    display: flex; flex-direction: column; justify-content: center;
  }
  .v-first { background: var(--peach-soft); border: 1px solid #f0d2c0; }
  .v-took { background: var(--sage-soft); border: 1px solid #cfe0d3; }
  .v-first .k { color: var(--peach); }
  .v-took .k { color: var(--sage); }
  .v-first p, .v-took p { margin: 6px 0 0; font-size: 26px; font-weight: 800; line-height: 1.22; }
  .v-first span { display: block; margin-top: 8px; font-size: 20px; line-height: 1.3; font-weight: 400; color: var(--ink); }
  .v-res {
    background: var(--sage); color: #f6fff8; border-radius: 14px;
    padding: 14px 16px; font-size: 22px; font-weight: 800; line-height: 1.25;
  }
  .punch {
    background: var(--ink); color: #fbf6ee; border-radius: 14px;
    padding: 16px 22px; font-size: 24px; font-weight: 700; line-height: 1.3;
  }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
  th { color: var(--muted); font-size: 13px; letter-spacing: .12em; text-transform: uppercase; }
  .out { font-size: 17px; color: var(--muted); margin: 4px 0 0; }
  .foot { font-size: 13px; color: var(--muted); }
  nav.bar {
    position: absolute; left: 0; right: 0; bottom: 0; height: 48px;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 24px; background: linear-gradient(transparent, rgba(251,246,238,.97) 40%%);
  }
  .dots { display: flex; gap: 8px; }
  .dot { width: 9px; height: 9px; border-radius: 50%%; border: 0; background: #ddd2c2; cursor: pointer; padding: 0; }
  .dot.on { background: var(--sage); }
  .counter { font-size: 12px; color: var(--muted); letter-spacing: .08em; }
  .arrows { display: flex; gap: 8px; }
  .arrow {
    width: 36px; height: 28px; border-radius: 8px; border: 1px solid var(--line);
    background: var(--card); color: var(--ink); cursor: pointer; font-size: 16px;
  }
</style>
</head>
<body>
<div class="deck">
  <div class="slides" id="slides">

    <section class="slide">
      <div class="eyebrow">Презентация 05 · Cursor как помощник в выборе решений</div>
      <h1>%(title)s</h1>
      <p class="lead">%(lead)s</p>
      <div class="fill">
        <div class="teaser">%(teasers)s</div>
        <div class="note">%(hook_note)s</div>
      </div>
    </section>

    <section class="slide">
      <div class="eyebrow">Как смотрим каждую задачу</div>
      <h2>Один и тот же порядок на три задачи.</h2>
      <p class="lead">
        Не берём первый ответ и не спорим без цифр.
        В каждой задаче один и тот же порядок.
      </p>
      <div class="fill">
        %(flow)s
        <div class="note">
          Первая идея, которая приходит в голову, часто не работает.
          ИИ даёт выбор и помогает взять эффективную.
        </div>
      </div>
    </section>

%(case_slides)s
    <section class="slide">
      <div class="eyebrow">Кто что делает</div>
      <h2>Человек выбирает. ИИ помогает проверить.</h2>
      <p class="lead">
        Ответ ИИ сам в работу не идёт. Сначала цифры, потом решение.
        Человек выбирает. ИИ помогает сравнить варианты.
      </p>
      <div class="fill">
        <div class="roles">%(roles)s</div>
      </div>
    </section>

    <section class="slide">
      <div class="eyebrow">Выводы</div>
      <h2>Первая идея не работает. ИИ помогает выбрать эффективную.</h2>
      <p class="lead">
        Три раза мысль, которая пришла первой, не прошла проверку.
        ИИ положил рядом варианты. В работу ушла другая идея.
      </p>
      <div class="fill">
        %(close)s
        <div class="punch">
          ИИ не ставит в работу первую мысль. ИИ даёт выбор и помогает взять эффективную. Решает человек.
        </div>
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
        "paper": C_PAPER, "card": C_CARD, "ink": C_INK, "muted": C_MUTED,
        "line": C_LINE, "sage": C_SAGE, "sage_soft": C_SAGE_SOFT,
        "peach": C_PEACH, "peach_soft": C_PEACH_SOFT, "gold": C_GOLD,
        "title": esc(payload["title"]),
        "lead": esc(payload["lead"]),
        "hook_note": esc(payload["hook_note"]),
        "teasers": teasers,
        "flow": steps5_html(),
        "case_slides": case_slides_html(cases),
        "roles": roles,
        "close": close_html(cases),
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)
    safe_print("OK - presentation written: %s" % os.path.basename(OUT))
    safe_print("size = %.1f KB" % (os.path.getsize(OUT) / 1024.0))
    return 0


def main():
    with open(DATA, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    return build(payload)


if __name__ == "__main__":
    raise SystemExit(main())
