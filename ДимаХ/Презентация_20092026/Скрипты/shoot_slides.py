#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Рендер слайдов презентации в PNG при разрешении проектора (1600x900).

Проверяет верстку каждого слайда и попутно ищет проблемы:
переполнение по вертикали, нулевые размеры диаграмм.
"""

import os
import sys

from playwright.sync_api import sync_playwright

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(SCRIPTS, "shots")
URL = "http://localhost:8899/01_avancor_economy.html"
WIDTH, HEIGHT = 1600, 900


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def main():
    os.makedirs(SHOTS, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        page.goto(URL, wait_until="load")
        page.wait_for_timeout(700)

        total = page.locator(".slide").count()
        safe_print("slides = %d ; viewport = %dx%d" % (total, WIDTH, HEIGHT))

        # Диагностика: переполнение контента и размеры диаграмм
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
            path = os.path.join(SHOTS, "p01_s%d.png" % (idx + 1))
            page.screenshot(path=path)
            safe_print("  saved %s" % os.path.basename(path))

        browser.close()
    safe_print("OK done")


if __name__ == "__main__":
    sys.exit(main())
