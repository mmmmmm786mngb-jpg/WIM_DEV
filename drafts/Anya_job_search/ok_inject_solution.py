#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Write solution into a copy of the original test file (green plan columns)
and keep explanatory note as a front sheet.
"""

from pathlib import Path
from shutil import copy2

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

from ok_build_solution import (
    FILL_DEF,
    FILL_NOTE,
    FILL_OK,
    FILL_SOL,
    FILL_WARN,
    FONT_BOLD,
    FONT_NORM,
    FONT_TITLE,
    TARGETS_KG,
    allocate_sku_weekly,
    load_rows,
    scale_channels_to_targets,
    write_note,
)

SRC = Path(r"c:\Users\Acer\Downloads\OK_test_Demand") / "Тест_Деманд.xlsx"
OUT = Path(r"c:\Users\Acer\Downloads\OK_test_Demand") / "Тест_Деманд_РЕШЕНИЕ.xlsx"


def main():
    print("Compute plans...")
    rows = load_rows()
    raw_plans = []
    leftovers = []
    fc_months = []
    for r in rows:
        _, month, leftover = allocate_sku_weekly(r["stock"], r["prod_w"], r["fc_weeks"])
        fc_m = [sum(r["fc_weeks"][w][c] for w in range(5)) for c in range(8)]
        supply = r["stock"] + sum(r["prod_w"])
        demand = sum(fc_m)
        r["is_deficit"] = demand - supply > 1e-6
        raw_plans.append(month)
        leftovers.append(leftover)
        fc_months.append(fc_m)

    plans, leftovers = scale_channels_to_targets(
        raw_plans, leftovers, fc_months, [r["atype"] for r in rows]
    )
    by_excel = {r["excel_row"]: i for i, r in enumerate(rows)}

    print("Copy source...")
    if OUT.exists():
        OUT.unlink()
    copy2(SRC, OUT)

    print("Open copy and write...")
    wb = load_workbook(OUT)
    # insert note sheet first
    if "00_Пояснительная" in wb.sheetnames:
        del wb["00_Пояснительная"]
    ws_note = wb.create_sheet("00_Пояснительная", 0)
    write_note(ws_note)

    ws = wb["Массив"]
    # highlight instruction
    ws["A2"] = "РЕШЕНИЕ КАНДИДАТА: зеленые ячейки в блоке План мес (столбцы BO-BX / 67-76)"
    ws["A2"].fill = FILL_SOL
    ws["A2"].font = FONT_BOLD

    for excel_row, idx in by_excel.items():
        plan = plans[idx]
        # col 67 FS = empty / sum FS parts optional
        ws.cell(excel_row, 67).value = round(plan[0] + plan[1], 2)
        ws.cell(excel_row, 67).fill = FILL_SOL
        for c, val in enumerate(plan):
            cell = ws.cell(excel_row, 68 + c)
            cell.value = round(val, 2)
            cell.fill = FILL_SOL
        total = sum(plan)
        cell = ws.cell(excel_row, 76)
        cell.value = round(total, 2)
        cell.fill = FILL_SOL

    # mark deficit codes in column 2 area note via status in free col if any - use column 2
    for excel_row, idx in by_excel.items():
        r = rows[idx]
        if r["is_deficit"]:
            # light orange on code
            ws.cell(excel_row, 1).fill = FILL_DEF

    # channel totals check under targets row
    ws.cell(4, 67).value = "ПЛАН (решение), кг"
    ws.cell(4, 67).fill = FILL_NOTE
    ch_tot = [0.0] * 8
    for p in plans:
        for i in range(8):
            ch_tot[i] += p[i]
    for i in range(8):
        cell = ws.cell(4, 68 + i)
        cell.value = round(ch_tot[i], 2)
        cell.fill = FILL_SOL
    ws.cell(4, 76).value = round(sum(ch_tot), 2)
    ws.cell(4, 76).fill = FILL_SOL

    wb.save(OUT)
    print("Saved", OUT)
    print("Channel plan tons:", [round(x / 1000, 2) for x in ch_tot])
    print("Targets tons:", [round(x / 1000, 2) for x in TARGETS_KG])


if __name__ == "__main__":
    main()
