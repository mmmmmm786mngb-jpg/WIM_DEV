#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from collections import Counter
from pathlib import Path

REG = Path(__file__).resolve().parent

def read(p):
    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return p.read_text(encoding="utf-8", errors="replace")

for label in ("было", "стало"):
    t = read(REG / f"СообщенияЗагрузкиВыписок_0906_{label}.txt")
    keys = [
        "ИТОГИ ПО КЛИЕНТУ",
        "пришли к успеху",
        "обнаружены расхождения",
        "Перезаписан документ",
        "Перепроведен документ",
        "Сработало Правило",
        "время выполнения",
        "Не найдено платежное поручение",
        "Не найден документ задолженности",
        "Пытаюсь создать, валюта по умолчанию",
        "Начисление",
    ]
    print(label, {k: t.count(k) for k in keys})

b = read(REG / "СообщенияЗагрузкиВыписок_0906_было.txt")
s = read(REG / "СообщенияЗагрузкиВыписок_0906_стало.txt")
from collections import Counter
cb = Counter(x.strip() for x in b.splitlines() if x.strip())
cs = Counter(x.strip() for x in s.splitlines() if x.strip())
print("msg line multiset equal:", cb == cs)
