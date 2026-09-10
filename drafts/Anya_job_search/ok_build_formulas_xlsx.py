#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create Excel workbook with LIVE FORMULAS for OK Demand test.
Inputs are values; all calculations are Excel formulas.
"""

from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side, Protection
from openpyxl.formatting.rule import FormulaRule
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName

SRC = Path(r"c:\Users\Acer\Downloads\OK_test_Demand") / "Тест_Деманд.xlsx"
OUT = Path(r"c:\Users\Acer\Downloads\OK_test_Demand") / "Тест_Деманд_ФОРМУЛЫ.xlsx"

CH = ["FS_promo", "FS_reg", "RDC", "FT", "EK", "KPi", "Ecom", "RKP"]
CH_RU = ["ФС промо", "ФС рег", "РДЦ", "ФТ", "ЭК", "КПи", "E-commerce", "РКП"]
# Priority order (index into CH): promo, reg, RDC, RKP, EK, FT, KPi, Ecom
PRIORITY = [0, 1, 2, 7, 4, 3, 5, 6]
TARGETS_TONS = [7358.0, 1582.0, 5373.0, 586.0, 1300.0, 748.0, 530.0, 2686.5]
WEEK_STARTS = [13, 22, 31, 40, 49]

FILL_IN = PatternFill("solid", fgColor="DDEBF7")      # input
FILL_F = PatternFill("solid", fgColor="C6EFCE")       # formula / solution
FILL_Y = PatternFill("solid", fgColor="FFF2CC")
FILL_O = PatternFill("solid", fgColor="F4B183")
FILL_H = PatternFill("solid", fgColor="305496")
FILL_G = PatternFill("solid", fgColor="E2EFDA")
FONT_H = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
FONT_B = Font(bold=True, name="Calibri", size=11)
FONT_N = Font(name="Calibri", size=10)
FONT_T = Font(bold=True, name="Calibri", size=14, color="1F4E79")
THIN = Border(
    left=Side(style="thin", color="B0B0B0"),
    right=Side(style="thin", color="B0B0B0"),
    top=Side(style="thin", color="B0B0B0"),
    bottom=Side(style="thin", color="B0B0B0"),
)


def fnum(v):
    try:
        return float(v or 0)
    except Exception:
        return 0.0


def load_input_rows():
    wb = load_workbook(SRC, data_only=True, read_only=True)
    names = {}
    if "Цены" in wb.sheetnames:
        for row in wb["Цены"].iter_rows(min_row=5, max_col=2, values_only=True):
            if row[0] and row[1] and str(row[0]) not in names:
                names[str(row[0])] = str(row[1])
    ws = wb["Массив"]
    rows = []
    for idx, row in enumerate(ws.iter_rows(min_row=8, max_row=435, max_col=76, values_only=True), start=8):
        if not row[0]:
            continue
        code = str(row[0])
        stock = fnum(row[5])
        prod_w = [fnum(row[c - 1]) for c in range(8, 13)]
        fc = []
        for ws_ in WEEK_STARTS:
            fc.append([fnum(row[ws_ + i - 1]) for i in range(8)])
        rows.append(
            {
                "src_row": idx,
                "code": code,
                "name": names.get(code, ""),
                "cat": row[3] or "",
                "atype": row[4] or "",
                "stock": stock,
                "prod_w": prod_w,
                "fc": fc,
            }
        )
    wb.close()
    return rows


def style_header_row(ws, row, n_cols):
    for c in range(1, n_cols + 1):
        cell = ws.cell(row, c)
        cell.fill = FILL_H
        cell.font = FONT_H
        cell.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
        cell.border = THIN
    ws.row_dimensions[row].height = 36


def main():
    print("Load inputs...")
    rows = load_input_rows()
    n = len(rows)
    print("rows", n)

    wb = Workbook()

    # ========== 00 README ==========
    ws0 = wb.active
    ws0.title = "00_Как_читать"
    readme = [
        "ЭТОТ ФАЙЛ — С ФОРМУЛАМИ (не с забитыми ответами)",
        "",
        "Синие ячейки = исходные данные (значения из ТЗ, их не надо выдумывать).",
        "Зелёные ячейки = ФОРМУЛЫ Excel. Кликни ячейку и смотри строку формул.",
        "Жёлтые = пояснения / нормативы.",
        "Оранжевые = дефицит (статус считается формулой).",
        "",
        "Листы:",
        "01_Нормативы — цели каналов в тоннах и кг (для ссылок в формулах).",
        "02_Данные — вход: остаток, выпуск по неделям, прогноз по каналам/неделям.",
        "03_Расчёт — вся логика формулами: доступно, приоритет каналов, недельный перенос, план мес, урезка до лимита канала.",
        "04_Сводка — СУММ планов vs цели (формулы).",
        "05_Дефицит — список через формулы/фильтр (статус на листе 03).",
        "06_Пояснительная — текст для HR (4 пункта ТЗ).",
        "07_Мини_пример — 1 SKU вручную, чтобы показать понимание на собеседовании.",
        "",
        "Приоритет каналов при дефиците:",
        "ФС промо -> ФС рег -> РДЦ -> РКП -> ЭК -> ФТ -> КПи -> E-commerce",
        "",
        "Важно: план производства не меняется. Прогноз = видение продаж, не заказ.",
        "Лимит канала (кг) = тонны * 1000 из листа 01_Нормативы.",
    ]
    ws0["A1"] = "ТЕСТ DEMAND — РАБОЧАЯ ТЕТРАДЬ С ФОРМУЛАМИ"
    ws0["A1"].font = FONT_T
    ws0["A1"].fill = FILL_Y
    for i, line in enumerate(readme, start=3):
        ws0.cell(i, 1, line).font = FONT_B if line and not line.startswith(" ") and i < 5 else FONT_N
        if "Зелёные" in line or "формул" in line.lower():
            ws0.cell(i, 1).fill = FILL_F
        if "Синие" in line:
            ws0.cell(i, 1).fill = FILL_IN
        if "Оранжевые" in line:
            ws0.cell(i, 1).fill = FILL_O
        if "Жёлтые" in line:
            ws0.cell(i, 1).fill = FILL_Y
    ws0.column_dimensions["A"].width = 110

    # ========== 01 NORMS ==========
    ws1 = wb.create_sheet("01_Нормативы")
    ws1["A1"] = "Целевые планы каналов (из шапки ТЗ)"
    ws1["A1"].font = FONT_T
    ws1["A1"].fill = FILL_Y
    headers = ["Канал", "Цель_тонн", "Цель_кг", "Имя_ячейки_кг"]
    for c, h in enumerate(headers, 1):
        ws1.cell(3, c, h)
    style_header_row(ws1, 3, 4)
    for i, (name, tons) in enumerate(zip(CH_RU, TARGETS_TONS)):
        r = 4 + i
        ws1.cell(r, 1, name).fill = FILL_IN
        ws1.cell(r, 2, tons).fill = FILL_IN
        ws1.cell(r, 3, f"=B{r}*1000")
        ws1.cell(r, 3).fill = FILL_F
        ws1.cell(r, 4, f"Цель_{CH[i]}").fill = FILL_Y
        for c in range(1, 5):
            ws1.cell(r, c).border = THIN
            ws1.cell(r, c).font = FONT_N
    ws1.cell(12, 1, "ИТОГО")
    ws1.cell(12, 2, "=SUM(B4:B11)")
    ws1.cell(12, 3, "=SUM(C4:C11)")
    for c in range(1, 4):
        ws1.cell(12, c).fill = FILL_Y
        ws1.cell(12, c).font = FONT_B
    ws1.cell(14, 1, "Приоритет (порядок раздачи при дефиците) — номер меньше = важнее")
    ws1.cell(14, 1).fill = FILL_Y
    for i, p in enumerate(PRIORITY):
        ws1.cell(15 + i, 1, i + 1)
        ws1.cell(15 + i, 2, CH_RU[p])
        ws1.cell(15 + i, 1).fill = FILL_F
        ws1.cell(15 + i, 2).fill = FILL_F
    ws1.column_dimensions["A"].width = 18
    ws1.column_dimensions["B"].width = 12
    ws1.column_dimensions["C"].width = 14
    ws1.column_dimensions["D"].width = 16

    # Defined names for targets C4:C11
    for i, ch in enumerate(CH):
        wb.defined_names.add(DefinedName(f"TGT_{ch}", attr_text=f"'01_Нормативы'!$C${4+i}"))

    # ========== 02 DATA ==========
    ws2 = wb.create_sheet("02_Данные")
    # Column map:
    # A src_row, B code, C name, D cat, E atype, F stock,
    # G-K prod w1-5,
    # then weeks: for w in 0..4: 8 channels starting col 12
    # L=12 ... 
    h2 = [
        "Строка_ТЗ",
        "Код",
        "Наименование",
        "Категория",
        "Тип",
        "Остаток_нач",
        "Выпуск_н1",
        "Выпуск_н2",
        "Выпуск_н3",
        "Выпуск_н4",
        "Выпуск_н5",
    ]
    for w in range(1, 6):
        for name in CH_RU:
            h2.append(f"Прг_н{w}_{name}")
    for c, h in enumerate(h2, 1):
        ws2.cell(1, c, h)
    style_header_row(ws2, 1, len(h2))

    for i, r in enumerate(rows):
        rr = i + 2
        vals = [r["src_row"], r["code"], r["name"], r["cat"], r["atype"], r["stock"]] + r["prod_w"]
        for w in range(5):
            vals.extend(r["fc"][w])
        for c, v in enumerate(vals, 1):
            cell = ws2.cell(rr, c, v)
            cell.fill = FILL_IN
            cell.font = FONT_N
            cell.border = THIN
    ws2.freeze_panes = "C2"
    ws2.auto_filter.ref = f"A1:{get_column_letter(len(h2))}{n+1}"
    ws2.column_dimensions["B"].width = 12
    ws2.column_dimensions["C"].width = 28

    last_data = n + 1  # row number

    # ========== 03 CALC ==========
    # Layout:
    # A = link code from data
    # B status formula
    # C supply = stock+sum prod
    # D demand = sum all fc
    # E deficit = max(0, D-C)
    # Then for each week 1..5:
    #   Avail, then for each channel in PRIORITY order we need cascade...
    # Better store plans in fixed channel column order (0..7), built with nested MIN using priority chain.
    #
    # For formulas with priority order P0..P7:
    # Avail_w
    # Plan[P0] = MIN(Fc[P0], Avail)
    # Rem1 = Avail - Plan[P0]
    # Plan[P1] = MIN(Fc[P1], Rem1)
    # ...
    #
    # Column plan:
    # A Kod
    # B Tip
    # C Dostupno_vsego  =F+sum prod from data
    # D Spros_vsego
    # E Deficit
    # F Status
    # --- Week blocks starting col 7 ---
    # For week w: Avail, Rem after each priority step could be hidden; output 8 plan cols in CH order + EndStock
    #
    # To keep file usable, one week block =
    # Avail | P_FS_promo | P_FS_reg | P_RDC | P_FT | P_EK | P_KPi | P_Ecom | P_RKP | End
    # where P_* use cascade formulas with LET if Excel 365 - but for compatibility use helper Rem columns.
    #
    # Compact cascade without extra Rem columns using nested expressions is huge.
    # Use helper columns: Avail, R0,P0,R1,P1,... but P in priority order then map - messy for summary.
    #
    # Practical structure per week (cols):
    # Avail,
    # R_after_promo, Plan_promo,
    # R_after_reg, Plan_reg,
    # ... following PRIORITY order for Plan, with running remain.
    # Then "pack" month sums by channel with SUM of plan cols.
    #
    # PRIORITY plans columns named by channel; remain helpers between them.

    ws3 = wb.create_sheet("03_Расчёт")

    # Build header
    h3 = [
        "Код",
        "Тип",
        "Доступно_всего",
        "Спрос_всего",
        "Дефицит_кг",
        "Статус",
    ]
    # Month RAW plans (before cap) - will be formulas summing weeks
    for name in CH_RU:
        h3.append(f"Сырой_{name}")
    h3.append("Сырой_Итого")
    # Cap factors are on summary; Final plans
    for name in CH_RU:
        h3.append(f"План_{name}")
    h3.append("План_Итого")
    h3.append("Остаток_после")
    h3.append("Fill_rate_%")

    # Weekly detail starts after that - for transparency
    # Base cols: 1-6 meta, 7-14 raw ch, 15 raw tot, 16-23 plan ch, 24 plan tot, 25 leftover, 26 fill
    # Weekly from col 27

    week_start_col = 27
    # each week: Avail + 8 pairs (Remain_before isn't needed if we do: Plan, Remain_after) 
    # Avail, Plan_p0, Rem1, Plan_p1, Rem2, ... Plan_p7, Rem8(=End)
    # That's 1 + 8*2 = 17 cols per week, ×5 = 85 cols. Heavy but OK.

    for w in range(1, 6):
        h3.append(f"Н{w}_Доступно")
        for pi, ch_i in enumerate(PRIORITY):
            h3.append(f"Н{w}_План_{CH_RU[ch_i]}")
            h3.append(f"Н{w}_Ост_после_{pi+1}")

    for c, h in enumerate(h3, 1):
        ws3.cell(1, c, h)
    style_header_row(ws3, 1, len(h3))

    # Data column letters on sheet 02
    # F=6 stock, G-K=7-11 prod, L=12 start forecasts
    # fc week w channel c -> col 12 + w*8 + c

    def data_cell(col_idx, row):
        return f"'02_Данные'!{get_column_letter(col_idx)}{row}"

    def fc_col(week0, ch0):
        return 12 + week0 * 8 + ch0

    for i in range(n):
        r = i + 2  # row on calc and data
        # A code, B type
        ws3.cell(r, 1, f"={data_cell(2, r)}")
        ws3.cell(r, 2, f"={data_cell(5, r)}")
        # C supply
        ws3.cell(r, 3, f"={data_cell(6, r)}+{data_cell(7, r)}+{data_cell(8, r)}+{data_cell(9, r)}+{data_cell(10, r)}+{data_cell(11, r)}")
        # D demand - sum all forecast cols L to (12+40-1)=51
        ws3.cell(r, 4, f"=SUM({data_cell(12, r)}:{data_cell(51, r)})")
        # E deficit
        ws3.cell(r, 5, f"=MAX(0,D{r}-C{r})")
        # F status
        ws3.cell(r, 6, f'=IF(E{r}>0.0001,"ДЕФИЦИТ",IF(C{r}-Y{r}>0.0001,"ПРОФИЦИТ","БАЛАНС"))')
        # Note: Y will be plan total col 24 - careful with column letters!

        # Weekly blocks starting col 27
        # Track column index
        col = week_start_col
        week_plan_cols = {ch: [] for ch in range(8)}  # excel col numbers for each channel's weekly plans

        for w in range(5):
            # Avail
            if w == 0:
                # stock + prod1
                avail_f = f"={data_cell(6, r)}+{data_cell(7, r)}"
            else:
                # previous week end remain is last col of previous week block
                # each week uses 1 + 16 = 17 columns
                prev_end_col = week_start_col + (w - 1) * 17 + 16  # Rem after 8th plan
                prod_col = 7 + w  # G=7 is w1, so w2 prod = 8, etc. data col 7+w
                avail_f = f"={get_column_letter(prev_end_col)}{r}+{data_cell(7 + w, r)}"
            ws3.cell(r, col, avail_f)
            avail_col = col
            col += 1
            remain_col = avail_col
            for step, ch_i in enumerate(PRIORITY):
                fc = data_cell(fc_col(w, ch_i), r)
                # Plan = MIN(forecast, current remain)
                plan_f = f"=MIN({fc},{get_column_letter(remain_col)}{r})"
                ws3.cell(r, col, plan_f)
                week_plan_cols[ch_i].append(col)
                plan_col = col
                col += 1
                # Remain after = remain_before - plan
                rem_f = f"={get_column_letter(remain_col)}{r}-{get_column_letter(plan_col)}{r}"
                ws3.cell(r, col, rem_f)
                remain_col = col
                col += 1

        # Raw month plans cols 7-14 (channel order 0..7)
        for ch_i in range(8):
            parts = "+".join(f"{get_column_letter(c)}{r}" for c in week_plan_cols[ch_i])
            ws3.cell(r, 7 + ch_i, f"={parts}")
        ws3.cell(r, 15, f"=SUM(G{r}:N{r})")

        # Final plans with cap: Plan = Raw * MIN(1, Target / SumRawColumn)
        # IFERROR: if channel raw total is 0 (no forecast), avoid #DIV/0!
        for ch_i in range(8):
            raw_letter = get_column_letter(7 + ch_i)
            tgt_cell = f"'01_Нормативы'!$C${4 + ch_i}"
            ws3.cell(
                r,
                16 + ch_i,
                f"=IFERROR({raw_letter}{r}*MIN(1,{tgt_cell}/SUM({raw_letter}$2:{raw_letter}${last_data})),0)",
            )
        ws3.cell(r, 24, f"=SUM(P{r}:W{r})")
        # leftover after raw weekly (end of week 5 remain) — last remain col of week 5
        # week 5 starts at week_start_col + 4*17, end rem at +16
        end5 = week_start_col + 4 * 17 + 16
        # After cap, leftover approx = supply - plan_total (not exact vs weekly but OK for status)
        ws3.cell(r, 25, f"=MAX(0,C{r}-X{r})")
        ws3.cell(r, 26, f'=IF(D{r}=0,100,X{r}/D{r}*100)')

        # Fix status formula: use X for plan total, Y was wrong
        ws3.cell(r, 6, f'=IF(E{r}>0.0001,"ДЕФИЦИТ",IF(Y{r}>0.0001,"ПРОФИЦИТ","БАЛАНС"))')

        # styles
        for c in range(1, 27):
            cell = ws3.cell(r, c)
            cell.font = FONT_N
            cell.border = THIN
            if c <= 2:
                cell.fill = FILL_IN
            elif c == 6:
                pass  # conditional later
            else:
                cell.fill = FILL_F
        # weekly formula cols also green
        for c in range(week_start_col, week_start_col + 5 * 17):
            cell = ws3.cell(r, c)
            cell.fill = FILL_F
            cell.font = FONT_N
            cell.border = THIN

    # conditional status colors
    ws3.conditional_formatting.add(
        f"F2:F{last_data}",
        FormulaRule(formula=['$F2="ДЕФИЦИТ"'], fill=FILL_O),
    )
    ws3.conditional_formatting.add(
        f"F2:F{last_data}",
        FormulaRule(formula=['$F2="ПРОФИЦИТ"'], fill=PatternFill("solid", fgColor="DDEBF7")),
    )
    ws3.conditional_formatting.add(
        f"F2:F{last_data}",
        FormulaRule(formula=['$F2="БАЛАНС"'], fill=FILL_Y),
    )

    ws3.freeze_panes = "C2"
    ws3.auto_filter.ref = f"A1:Z{last_data}"
    ws3.column_dimensions["A"].width = 12
    ws3.column_dimensions["F"].width = 12

    # Note row
    note_r = last_data + 2
    ws3.cell(note_r, 1, "Зелёные ячейки = формулы. Столбцы P-W = итоговый план после урезки до лимита канала (ТЗ). Сырой G-N = до урезки.")
    ws3.cell(note_r, 1).fill = FILL_Y
    ws3.merge_cells(start_row=note_r, start_column=1, end_row=note_r, end_column=10)

    # ========== 04 SUMMARY ==========
    ws4 = wb.create_sheet("04_Сводка")
    ws4["A1"] = "Сводка по каналам (всё формулами)"
    ws4["A1"].font = FONT_T
    ws4["A1"].fill = FILL_Y
    sh = ["Канал", "Цель_т", "Цель_кг", "Сырой_план_кг", "Итоговый_план_кг", "Итоговый_план_т", "Отклонение_кг", "Отклонение_%"]
    for c, h in enumerate(sh, 1):
        ws4.cell(3, c, h)
    style_header_row(ws4, 3, len(sh))
    for i, name in enumerate(CH_RU):
        r = 4 + i
        raw_letter = get_column_letter(7 + i)   # G..N on calc
        plan_letter = get_column_letter(16 + i)  # P..W
        ws4.cell(r, 1, name).fill = FILL_IN
        ws4.cell(r, 2, f"='01_Нормативы'!B{4+i}").fill = FILL_F
        ws4.cell(r, 3, f"='01_Нормативы'!C{4+i}").fill = FILL_F
        ws4.cell(r, 4, f"=SUM('03_Расчёт'!{raw_letter}2:{raw_letter}{last_data})").fill = FILL_F
        ws4.cell(r, 5, f"=SUM('03_Расчёт'!{plan_letter}2:{plan_letter}{last_data})").fill = FILL_F
        ws4.cell(r, 6, f"=E{r}/1000").fill = FILL_F
        ws4.cell(r, 7, f"=E{r}-C{r}").fill = FILL_F
        ws4.cell(r, 8, f"=IF(C{r}=0,0,(E{r}/C{r}-1)*100)").fill = FILL_F
        for c in range(1, 9):
            ws4.cell(r, c).border = THIN
            ws4.cell(r, c).font = FONT_N
    ws4.cell(12, 1, "ИТОГО").font = FONT_B
    ws4.cell(12, 2, "=SUM(B4:B11)")
    ws4.cell(12, 3, "=SUM(C4:C11)")
    ws4.cell(12, 4, "=SUM(D4:D11)")
    ws4.cell(12, 5, "=SUM(E4:E11)")
    ws4.cell(12, 6, "=SUM(F4:F11)")
    ws4.cell(12, 7, "=SUM(G4:G11)")
    for c in range(1, 8):
        ws4.cell(12, c).fill = FILL_Y
        ws4.cell(12, c).font = FONT_B
        ws4.cell(12, c).border = THIN
    ws4.cell(14, 1, "Проверка: итоговый план канала не должен превышать Цель_кг (отклонение <= 0 с учётом округления).")
    ws4.cell(14, 1).fill = FILL_G
    ws4.cell(15, 1, "Число дефицитных SKU:")
    ws4.cell(15, 2, f'=COUNTIF(\'03_Расчёт\'!F2:F{last_data},"ДЕФИЦИТ")')
    ws4.cell(15, 2).fill = FILL_F
    ws4.cell(16, 1, "Число профицитных SKU:")
    ws4.cell(16, 2, f'=COUNTIF(\'03_Расчёт\'!F2:F{last_data},"ПРОФИЦИТ")')
    ws4.cell(16, 2).fill = FILL_F
    for col in ws4.columns:
        ws4.column_dimensions[get_column_letter(col[0].column)].width = 16
    ws4.column_dimensions["A"].width = 14

    # ========== 05 DEFICIT VIEW ==========
    ws5 = wb.create_sheet("05_Дефицит")
    ws5["A1"] = "Как пользоваться: на листе 03_Расчёт включи Автофильтр по столбцу «Статус» = ДЕФИЦИТ."
    ws5["A1"].fill = FILL_O
    ws5["A1"].font = FONT_B
    ws5.merge_cells("A1:F1")
    ws5["A3"] = "Ниже — формулы, которые подтягивают топ строк с дефицитом (по убыванию). Для сдачи достаточно фильтра на 03."
    ws5["A3"].fill = FILL_Y
    hs = ["Код", "Тип", "Доступно", "Спрос", "Дефицит", "План_итого", "Fill_%"]
    for c, h in enumerate(hs, 1):
        ws5.cell(5, c, h)
    style_header_row(ws5, 5, len(hs))
    # Pull all rows with IF - heavy. Simpler: direct references sorted manually note + link formulas for same rows where deficit
    # Just mirror key columns with formulas for ALL rows and tell to filter - duplicate of 03.
    ws5["A6"] = "Смотри лист 03_Расчёт, столбцы A-F и P-X. Отфильтруй Статус=ДЕФИЦИТ и скопируй видимые строки на лист «К сдаче» при необходимости."
    ws5["A6"].fill = FILL_IN
    ws5.merge_cells("A6:G6")
    ws5["A8"] = "Количество дефицитных:"
    ws5["B8"] = f"=COUNTIF('03_Расчёт'!F:F,\"ДЕФИЦИТ\")"
    ws5["B8"].fill = FILL_F
    ws5["A9"] = "Сумма дефицита, кг:"
    ws5["B9"] = f"=SUMIF('03_Расчёт'!F:F,\"ДЕФИЦИТ\",'03_Расчёт'!E:E)"
    ws5["B9"].fill = FILL_F

    # ========== 06 NOTE ==========
    ws6 = wb.create_sheet("06_Пояснительная")
    note_lines = [
        "ПОЯСНИТЕЛЬНАЯ ЗАПИСКА (перепиши своими словами перед отправкой)",
        "",
        "1. Список дефицитных позиций",
        "Дефицит = позиции, где остаток на начало + выпуск по неделям < суммы прогноза каналов.",
        "Список: лист 03_Расчёт, фильтр Статус=ДЕФИЦИТ (оранжевый). Количество и сумма — на листе 04/05 (формулы COUNTIF/SUMIF).",
        "",
        "2. Почему распределение именно такое",
        "При нехватке товара действует приоритет каналов: ФС промо → ФС рег → РДЦ → РКП → ЭК → ФТ → КПи → E-commerce.",
        "Расчёт понедельный: доступно = переходящий остаток + выпуск недели; остаток переносится на следующую неделю.",
        "После сборки сырого плана сумма по каналу ограничивается целевым планом канала (тонны×1000) пропорциональным коэффициентом.",
        "План производства не увеличивался. Целевой остаток не использовался.",
        "",
        "3. Риски при дефиците",
        "- Штрафы / cut-off промо и потеря полки в федеральных сетях",
        "- Снижение OTIF и рост OOS в регионах (РДЦ)",
        "- Искажение сигнала спроса (overforecast в следующем цикле)",
        "- Уход спроса к аналогам и конкурентам",
        "- Заморозка капитала в профицитных остатках при дефиците хитов",
        "",
        "4. Действия",
        "1) Short-list дефицита на S&OP с Sales/Marketing",
        "2) Запрос Production на переброску внутри лимита выпуска",
        "3) Сокращение промо/extra по хроническому дефициту, субституты из профицита",
        "4) Weekly контроль остатка на 1–2 недели вперёд",
        "5) Эскалация: accept OOS / cut channel / replan — с фиксацией решения",
    ]
    for i, line in enumerate(note_lines, 1):
        ws6.cell(i, 1, line)
        ws6.cell(i, 1).font = FONT_B if line.startswith(("ПОЯСН", "1.", "2.", "3.", "4.")) else FONT_N
        ws6.cell(i, 1).fill = FILL_Y
        ws6.cell(i, 1).alignment = Alignment(wrap_text=True)
    ws6.column_dimensions["A"].width = 110

    # ========== 07 MINI EXAMPLE ==========
    ws7 = wb.create_sheet("07_Мини_пример")
    ws7["A1"] = "Мини-пример на 1 SKU (чтобы устно объяснить логику)"
    ws7["A1"].font = FONT_T
    ws7["A1"].fill = FILL_Y
    ws7["A3"] = "Вход (синий) — можно менять и смотреть, как пересчитывается зелёное"
    demo = {
        "stock": 8000,
        "prod": [0, 1000, 0, 0, 0],
        # forecasts week1: promo 3000, reg 2000, rdc 2000, others 0
        "fc": [
            [3000, 2000, 2000, 0, 0, 0, 0, 0],
            [2000, 2000, 1000, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
        ],
    }
    ws7["A5"] = "Остаток нач"
    ws7["B5"] = demo["stock"]
    ws7["B5"].fill = FILL_IN
    for w in range(5):
        ws7.cell(6, 1 + w, f"Выпуск н{w+1}")
        ws7.cell(7, 1 + w, demo["prod"][w]).fill = FILL_IN
    ws7["A9"] = "Прогноз н1 ФС промо / ФС рег / РДЦ"
    ws7["A10"] = demo["fc"][0][0]
    ws7["B10"] = demo["fc"][0][1]
    ws7["C10"] = demo["fc"][0][2]
    for c in range(1, 4):
        ws7.cell(10, c).fill = FILL_IN
    ws7["A12"] = "Неделя 1 доступно"
    ws7["B12"] = "=B5+A7"
    ws7["B12"].fill = FILL_F
    ws7["A13"] = "План ФС промо н1"
    ws7["B13"] = "=MIN(A10,B12)"
    ws7["B13"].fill = FILL_F
    ws7["A14"] = "Остаток после промо"
    ws7["B14"] = "=B12-B13"
    ws7["B14"].fill = FILL_F
    ws7["A15"] = "План ФС рег н1"
    ws7["B15"] = "=MIN(B10,B14)"
    ws7["B15"].fill = FILL_F
    ws7["A16"] = "Остаток после рег"
    ws7["B16"] = "=B14-B15"
    ws7["B16"].fill = FILL_F
    ws7["A17"] = "План РДЦ н1"
    ws7["B17"] = "=MIN(C10,B16)"
    ws7["B17"].fill = FILL_F
    ws7["A18"] = "Остаток конец н1"
    ws7["B18"] = "=B16-B17"
    ws7["B18"].fill = FILL_F
    ws7["A20"] = "Неделя 2 доступно (= остаток н1 + выпуск н2)"
    ws7["B20"] = "=B18+B7"
    ws7["B20"].fill = FILL_F
    ws7["A21"] = "Прогноз н2 (промо/рег/рдц)"
    ws7["A22"] = demo["fc"][1][0]
    ws7["B22"] = demo["fc"][1][1]
    ws7["C22"] = demo["fc"][1][2]
    for c in range(1, 4):
        ws7.cell(22, c).fill = FILL_IN
    ws7["A23"] = "План ФС промо н2"
    ws7["B23"] = "=MIN(A22,B20)"
    ws7["B23"].fill = FILL_F
    ws7["A24"] = "Ост после промо н2"
    ws7["B24"] = "=B20-B23"
    ws7["B24"].fill = FILL_F
    ws7["A25"] = "План ФС рег н2"
    ws7["B25"] = "=MIN(B22,B24)"
    ws7["B25"].fill = FILL_F
    ws7["A26"] = "Ост после рег н2"
    ws7["B26"] = "=B24-B25"
    ws7["B26"].fill = FILL_F
    ws7["A27"] = "План РДЦ н2"
    ws7["B27"] = "=MIN(C22,B26)"
    ws7["B27"].fill = FILL_F
    ws7["A28"] = "Остаток конец н2"
    ws7["B28"] = "=B26-B27"
    ws7["B28"].fill = FILL_F
    ws7["A30"] = "Вывод: на н2 товара меньше спроса — режется младший канал (РДЦ), старшие закрываются раньше."
    ws7["A30"].fill = FILL_O
    ws7.merge_cells("A30:D30")
    ws7.column_dimensions["A"].width = 42
    ws7.column_dimensions["B"].width = 14

    # ========== 08 LEGEND ==========
    ws8 = wb.create_sheet("08_Легенда")
    ws8["A1"] = "Легенда цветов"
    ws8["A2"] = "Синий — ввод (данные ТЗ)"
    ws8["A2"].fill = FILL_IN
    ws8["A3"] = "Зелёный — формула / решение"
    ws8["A3"].fill = FILL_F
    ws8["A4"] = "Жёлтый — нормативы и текст"
    ws8["A4"].fill = FILL_Y
    ws8["A5"] = "Оранжевый — дефицит"
    ws8["A5"].fill = FILL_O
    ws8.column_dimensions["A"].width = 40

    print("Saving", OUT)
    wb.save(OUT)
    print("OK, rows", n)


if __name__ == "__main__":
    main()
