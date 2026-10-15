# -*- coding: utf-8 -*-
"""Собирает отчет тестирования 6.11/1.20: шаблон report_6_11_template.html, картинки @@<файл> -> data URI."""
import base64, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
TEST = os.path.normpath(os.path.join(HERE, ".."))
SHOTS = os.path.join(TEST, "Скриншоты")
OUT = os.path.join(TEST, "Отчет_тестирования_6_11_1_20.html")

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with open(os.path.join(HERE, "report_6_11_template.html"), encoding="utf-8-sig") as f:
        html = f.read()
    def repl(m):
        with open(os.path.join(SHOTS, m.group(1)), "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
    html, n = re.subn(r"@@([^\"]+\.png)", repl, html)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("картинок", n, "размер", os.path.getsize(OUT), OUT)

main()
