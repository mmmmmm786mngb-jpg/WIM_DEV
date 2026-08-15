#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экспорт HTML-презентации в PDF (16:9) через headless Edge под управлением Playwright.

Используется prefer_css_page_size, чтобы PDF получил размер страницы из CSS-правила
@page (338.7 x 190.5 мм = 16:9), а не Letter по умолчанию.
Проверка результата: количество страниц и размер страницы читаются из готового PDF.
"""

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent / "Документация" / "02_scha_rsa_group3"
HTML = BASE / "presentation_scha_rsa.html"
PDF = BASE / "presentation_scha_rsa.pdf"


def safe_print(text):
    """Безопасный вывод в консоль Windows - только ASCII."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def export():
    from playwright.sync_api import sync_playwright

    if not HTML.exists():
        safe_print("ERROR: source html not found: %s" % HTML)
        return 1

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page()
        page.goto(HTML.as_uri(), wait_until="load")
        page.wait_for_timeout(1200)
        page.emulate_media(media="print")
        page.pdf(
            path=str(PDF),
            prefer_css_page_size=True,
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        browser.close()

    return verify()


def verify():
    import fitz

    doc = fitz.open(str(PDF))
    w, h = doc[0].rect.width, doc[0].rect.height
    safe_print("PDF created: %s" % PDF.name)
    safe_print("pages: %d" % doc.page_count)
    safe_print("page size: %.1f x %.1f pt (ratio %.3f, target 1.778)" % (w, h, w / h))
    safe_print("size on disk: %.1f KB" % (PDF.stat().st_size / 1024))
    doc.close()
    return 0


if __name__ == "__main__":
    sys.exit(export())
