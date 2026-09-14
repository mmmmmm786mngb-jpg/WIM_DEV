#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка автономной версии презентации: картинки встраиваются в HTML как data:URI.
Результат - один файл, который можно переслать письмом или открыть без папки images.

Запуск:
    python build_standalone.py
"""

import base64
import io
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE_DIR, "index.html")
DST = os.path.join(BASE_DIR, "cursor_for_1c_standalone.html")

MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
}


def safe_print(text):
    """Консольный вывод только ASCII - защита от проблем с кодировкой."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def inline_image(match):
    """Заменяет src="images/..." на data:URI с содержимым файла."""
    rel_path = match.group(1)
    abs_path = os.path.join(BASE_DIR, rel_path.replace("/", os.sep))

    if not os.path.isfile(abs_path):
        safe_print("SKIP (not found): " + rel_path)
        return match.group(0)

    ext = os.path.splitext(abs_path)[1].lower()
    mime = MIME_BY_EXT.get(ext)
    if mime is None:
        safe_print("SKIP (unknown type): " + rel_path)
        return match.group(0)

    with open(abs_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("ascii")

    safe_print("INLINE: " + rel_path + " -> " + str(len(encoded)) + " base64 chars")
    return 'src="data:' + mime + ";base64," + encoded + '"'


def main():
    if not os.path.isfile(SRC):
        safe_print("ERROR: index.html not found")
        return 1

    html = io.open(SRC, encoding="utf-8").read()
    result = re.sub(r'src="(images/[^"]+)"', inline_image, html)

    with io.open(DST, "w", encoding="utf-8") as out_file:
        out_file.write(result)

    size_kb = os.path.getsize(DST) // 1024
    safe_print("OK: cursor_for_1c_standalone.html (" + str(size_kb) + " KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
