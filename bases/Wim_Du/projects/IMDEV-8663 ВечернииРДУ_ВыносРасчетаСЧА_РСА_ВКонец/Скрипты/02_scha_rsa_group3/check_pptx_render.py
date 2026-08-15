#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка верстки PPTX: экспорт всех слайдов в PNG через PowerPoint (COM)
и сборка обзорного листа 4 x 4 для быстрого поиска наложений и переполнений.

Результат: <temp>/deck_pptx_check/contact_sheet.png и отдельные PNG по слайдам.
"""

import shutil
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent.parent / "Документация" / "02_scha_rsa_group3" / "presentation_scha_rsa.pptx"
OUT = Path(tempfile.gettempdir()) / "deck_pptx_check"
CELL = (480, 270)
COLS = 4


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def export_slides():
    import pythoncom
    import win32com.client

    if OUT.exists():
        shutil.rmtree(OUT)
    pythoncom.CoInitialize()
    app = win32com.client.Dispatch("PowerPoint.Application")
    pres = app.Presentations.Open(str(SRC), ReadOnly=True, WithWindow=False)
    pres.Export(str(OUT), "PNG", 1280, 720)
    count = pres.Slides.Count
    pres.Close()
    app.Quit()
    pythoncom.CoUninitialize()
    return count


def contact_sheet(count):
    from PIL import Image

    files = []
    for i in range(1, count + 1):
        for pattern in ("Слайд%d.PNG", "Slide%d.PNG", "Слайд%d.png", "Slide%d.png"):
            f = OUT / (pattern % i)
            if f.exists():
                files.append(f)
                break

    rows = (len(files) + COLS - 1) // COLS
    sheet = Image.new("RGB", (CELL[0] * COLS, CELL[1] * rows), "white")
    for idx, f in enumerate(files):
        im = Image.open(f).convert("RGB").resize(CELL, Image.LANCZOS)
        sheet.paste(im, ((idx % COLS) * CELL[0], (idx // COLS) * CELL[1]))
    target = OUT / "contact_sheet.png"
    sheet.save(target)
    return target, len(files)


if __name__ == "__main__":
    n = export_slides()
    sheet, used = contact_sheet(n)
    safe_print("slides exported: %d" % n)
    safe_print("contact sheet: %s (%d cells)" % (sheet, used))
    sys.exit(0)
