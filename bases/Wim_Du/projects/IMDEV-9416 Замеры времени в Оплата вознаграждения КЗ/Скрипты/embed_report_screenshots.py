#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Встраивает PNG скриншоты в HTML-отчет как data URI."""

import base64
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_PATH = os.path.join(BASE, "Документация", "imdev-9416_development_and_test_report.html")
IMG_DIR = os.path.join(BASE, "Документация", "it_test_screenshots")


def main():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    def repl(match):
        name = match.group(1)
        path = os.path.join(IMG_DIR, name)
        with open(path, "rb") as img:
            b64 = base64.b64encode(img.read()).decode("ascii")
        print("embedded", name, "bytes", os.path.getsize(path), "b64", len(b64))
        return 'src="data:image/png;base64,' + b64 + '"'

    html2, count = re.subn(r'src="it_test_screenshots/(image[1-5]\.png)"', repl, html)
    print("replacements", count)
    if count != 5:
        raise SystemExit("expected 5 replacements, got %s" % count)

    with open(HTML_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(html2)
    print("html_size", os.path.getsize(HTML_PATH))


if __name__ == "__main__":
    main()
