#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Рендер слайдов презентации в PNG при разрешении проектора (1600x900).

Проверяет верстку каждого слайда и попутно ищет проблемы:
переполнение по вертикали, нулевые размеры диаграмм.

Запуск:
  python shoot_slides.py 02_cursor_speedup.html p02
"""

import os
import sys

from playwright.sync_api import sync_playwright

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(SCRIPTS, "shots")
WIDTH, HEIGHT = 1600, 900


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def main():
    html_name = sys.argv[1] if len(sys.argv) > 1 else "01_avancor_economy.html"
    prefix = sys.argv[2] if len(sys.argv) > 2 else "p01"
    url = "http://localhost:8899/" + html_name

    os.makedirs(SHOTS, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        page.goto(url, wait_until="load")
        page.wait_for_timeout(700)

        total = page.locator(".slide").count()
        safe_print("file = %s ; slides = %d ; viewport = %dx%d" % (
            html_name, total, WIDTH, HEIGHT))

        report = page.evaluate("""() => {
            const out = [];
            document.querySelectorAll('.slide').forEach((s, i) => {
                const svgs = [...s.querySelectorAll('svg')].map(v => {
                    const r = v.getBoundingClientRect();
                    return Math.round(r.width) + 'x' + Math.round(r.height);
                });
                out.push({
                    i: i + 1,
                    scrollH: s.scrollHeight,
                    clientH: s.clientHeight,
                    overflow: s.scrollHeight - s.clientHeight,
                    svgs: svgs
                });
            });
            return out;
        }""")
        for r in report:
            flag = "OVERFLOW +%d" % r["overflow"] if r["overflow"] > 4 else "ok"
            safe_print("  slide %d: %-14s svg=%s" % (r["i"], flag, r["svgs"] or "-"))

        for idx in range(total):
            page.evaluate("i => { document.getElementById('slides')"
                          ".style.transform = 'translateX(-' + (i*100) + '%)'; }", idx)
            page.wait_for_timeout(520)
            path = os.path.join(SHOTS, "%s_s%d.png" % (prefix, idx + 1))
            page.screenshot(path=path)
            safe_print("  saved %s" % os.path.basename(path))

        browser.close()
    safe_print("OK done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
