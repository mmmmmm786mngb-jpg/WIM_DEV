#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка автономности презентации: нет внешних ресурсов (CDN, шрифты),
все диаграммы встроены как inline SVG. Важно для показа на проекторе без сети.
"""

import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "01_avancor_economy.html"
    target = os.path.join(BASE, name)
    with open(target, "r", encoding="utf-8") as fh:
        text = fh.read()

    external = re.findall(r"""(?:src|href)\s*=\s*["'](https?://[^"']+)""", text)
    safe_print("file: %s" % os.path.basename(target))
    safe_print("size: %.1f KB" % (len(text.encode("utf-8")) / 1024.0))
    safe_print("slides: %d" % len(re.findall(r'class="slide[ "]', text)))
    safe_print("inline svg charts: %d" % text.count("<svg"))
    safe_print("tables: %d" % text.count("<table"))
    if external:
        safe_print("EXTERNAL RESOURCES (%d):" % len(external))
        for url in external:
            safe_print("  " + url)
    else:
        safe_print("external resources: NONE - file is fully self-contained")
    return 0


if __name__ == "__main__":
    sys.exit(main())
