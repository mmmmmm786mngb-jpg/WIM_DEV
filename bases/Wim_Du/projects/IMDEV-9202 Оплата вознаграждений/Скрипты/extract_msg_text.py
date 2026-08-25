#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract readable text from Outlook .msg (OLE) via utf-16 strings."""

import pathlib
import re
import sys

msg_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-9202 Оплата вознаграждений"
    r"\RE вопрос по поступлению на расчетный счет.msg"
)
raw = msg_path.read_bytes()
print("size", len(raw))

text = raw.decode("utf-16-le", errors="ignore")
chunks = re.findall(r"[\u0400-\u04FFA-Za-z0-9 \t\r\n.,;:!?\"'\-()/№%]{25,}", text)
keys = (
    "ЕБС", "ЕРС", "поступ", "выпис", "ВУК", "растор", "договор", "обработ",
    "Оплата", "Кукуш", "правильн", "исправ", "брокер", "Поручен", "Клиент",
    "зачисл", "РДУ", "КЗ",
)
print("chunks", len(chunks))
seen = set()
for c in chunks:
    c2 = " ".join(c.split())
    if len(c2) < 30:
        continue
    if not any(k.lower() in c2.lower() or k in c2 for k in keys):
        continue
    if c2 in seen:
        continue
    seen.add(c2)
    print("---")
    print(c2[:800])
