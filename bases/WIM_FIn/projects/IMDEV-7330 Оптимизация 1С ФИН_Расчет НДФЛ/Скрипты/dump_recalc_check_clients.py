#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dump TCH Nachisleniya for a few UK docs: old vs new4."""

from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent),
)
import compare_ndfl_old_vs_new2 as c  # noqa: E402

BASE = Path(r"c:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects\IMDEV-7330 НовыеТесты")
OUT = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects\IMDEV-7330 Оптимизация 1С ФИН_Расчет НДФЛ\Документация"
    r"\imdev7330_recalc_check_clients.txt"
)

DOCS = [
    ("000000000038432", "Platonov D.V. (FIFO)"),
    ("000000000025261", "Gladilov G.V. (FIFO like)"),
    ("000000000021692", "Babarykin P.N. (income moved)"),
    ("000000000032424", "Kubasov D.A. (income moved, small)"),
    ("000000000022005", "Baranikas L.I. (withhold only)"),
]

COLS = [
    "Портфель",
    "КодДохода",
    "КодВычета",
    "Ставка",
    "ТипДохода",
    "СуммаДохода",
    "СуммаВычета",
    "НалогооблагаемаяCумма",
]


def fmt(v):
    if v is None or v == "":
        return ""
    d = c.to_dec(v)
    if d == d.to_integral():
        return str(int(d))
    return str(d)


def load_nach(path, nums):
    _, idx, rows = c.load_xlsx_rows(str(path))
    out = {n: [] for n in nums}
    for row in rows:
        num = str(c.get(row, idx, "НомерДокумента") or "")
        if num not in out:
            continue
        part = str(c.get(row, idx, "ТабличнаяЧасть") or "")
        if part != "Начисления":
            continue
        rec = {col: c.get(row, idx, col) for col in COLS}
        rec["_num"] = num
        out[num].append(rec)
    return out


def main():
    nums = [d[0] for d in DOCS]
    c.safe_print("Load old...")
    old = load_nach(BASE / "НДФЛ_Управление_27292.xlsx", nums)
    c.safe_print("Load n3...")
    n3 = load_nach(BASE / "НДФЛ_Управление_27292_ПоНовому3.xlsx", nums)
    c.safe_print("Load n4...")
    n4 = load_nach(BASE / "НДФЛ_Управление_27292_ПоНовому4.xlsx", nums)

    lines = []
    for num, title in DOCS:
        lines.append("=" * 72)
        lines.append(title + "  UK " + num)
        lines.append("rows old/n3/n4 = %s/%s/%s" % (len(old[num]), len(n3[num]), len(n4[num])))
        for label, bag in (("OLD etalon", old[num]), ("NEW3", n3[num]), ("NEW4", n4[num])):
            lines.append("--- " + label + " ---")
            for rec in bag:
                lines.append(
                    "  pf=%s kod=%s vych=%s stavka=%s tip=%s doh=%s vychS=%s nalog=%s"
                    % (
                        rec.get("Портфель") or "",
                        rec.get("КодДохода") or "",
                        rec.get("КодВычета") or "",
                        rec.get("Ставка") or "",
                        rec.get("ТипДохода") or "",
                        fmt(rec.get("СуммаДохода")),
                        fmt(rec.get("СуммаВычета")),
                        fmt(rec.get("НалогооблагаемаяCумма")),
                    )
                )
        lines.append("")
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    c.safe_print("written " + str(OUT))
    # ASCII console summary
    for num, title in DOCS:
        c.safe_print(title + " old=" + str(len(old[num])) + " n3=" + str(len(n3[num])) + " n4=" + str(len(n4[num])))


if __name__ == "__main__":
    main()
