#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze LogRabotyServisa.txt from vнVygruzkaOstatkovMO_FO."""

import os
import re
from collections import Counter

LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "ЛогРаботыСервиса.txt",
)


def main():
    size = os.path.getsize(LOG_PATH)
    markers = {
        "position_set": "--------- Position set ------------",
        "packet_open": "<Пакет xmlns",
        "packet_response": "<ПакетОтвет xmlns",
        "error_export": "Ошибка выгрузки позиции по:",
        "http_413": "HTTP Status 413",
        "success_portfolio": " - успех!",
        "virtual_sub": "Ошибки создания виртуальных субпортфелей",
        "block_error": "Ошибка выгрузки блокировки",
    }

    counts = Counter()
    error_lines = []
    dates = []
    packet_line_starts = []
    line_num = 0

    with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line_num += 1
            for key, m in markers.items():
                if m in line:
                    counts[key] += 1
            if "Ошибка выгрузки позиции по:" in line:
                error_lines.append((line_num, line.strip()[:240]))
            if "<ДатаВыполнения>" in line and "<ДатаВыполненияЗапроса>" not in line:
                dates.append(line.strip())
            if line.startswith("<Пакет xmlns") or line.startswith("<ПакетОтвет xmlns"):
                packet_line_starts.append((line_num, line.strip()[:140]))

    ami_codes = set()
    fact_pos = 0
    scha_rsa = 0
    other_errors = []

    with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "<ВнешнийКод>АМИ" in line:
                m = re.search(r"<ВнешнийКод>(АМИ[^<]+)</ВнешнийКод>", line)
                if m:
                    ami_codes.add(m.group(1))
            if "<ФактическаяПозиция>" in line:
                fact_pos += 1
            if "<СтоимостьЧистыхАктивов>" in line:
                scha_rsa += 1
            if "Ошибка" in line and "Ошибка выгрузки позиции" not in line:
                if "ОшибкиЗагрузки" not in line and "HTTP Error" not in line:
                    other_errors.append(line.strip()[:200])

    ranges = []
    for i, (start, _) in enumerate(packet_line_starts):
        end = packet_line_starts[i + 1][0] - 1 if i + 1 < len(packet_line_starts) else line_num
        ranges.append((start, end, end - start + 1))

    print("=== FILE ===")
    print("size_mb:", round(size / 1024 / 1024, 2))
    print("total_lines:", line_num)
    print()
    print("=== MARKERS ===")
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"{k}: {v}")
    print()
    print("=== DATES (unique, first 10) ===")
    seen = set()
    for d in dates:
        if d not in seen:
            seen.add(d)
            print(d)
        if len(seen) >= 10:
            break
    print()
    print("=== PACKET XML BLOCKS ===")
    for start, end, nlines in ranges:
        frag = ""
        for s, hdr in packet_line_starts:
            if s == start:
                frag = hdr
                break
        print(f"lines {start}-{end}: {nlines} lines | {frag[:100]}")
    print()
    print("=== UNIQUE AMI portfolio codes:", len(ami_codes))
    print("=== СтоимостьЧистыхАктивов blocks:", scha_rsa)
    print("=== ФактическаяПозиция openings:", fact_pos)
    print()
    print("=== POSITION EXPORT ERRORS ===")
    for ln, txt in error_lines:
        print(f"L{ln}: {txt}")
    print()
    print("=== OTHER ERROR-LIKE LINES (max 20) ===")
    for x in other_errors[:20]:
        print(x)
    print("other_error_lines:", len(other_errors))


if __name__ == "__main__":
    main()
