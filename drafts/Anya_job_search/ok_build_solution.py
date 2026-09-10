#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build solution workbook for OK Demand test (Obedinennye Konditery).
Creates colored plan + explanatory note.
"""

from copy import copy
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

SRC = Path(r"c:\Users\Acer\Downloads\OK_test_Demand") / "Тест_Деманд.xlsx"
OUT = Path(r"c:\Users\Acer\Downloads\OK_test_Demand") / "Reshenie_Test_Demand.xlsx"

# Channel order as in weekly forecast blocks (cols 13-20, ...)
CH_NAMES = [
    "FS promo",
    "FS reg",
    "RDC",
    "FT",
    "EK",
    "KPi",
    "E-commerce",
    "RKP",
]
CH_NAMES_RU = [
    "FS promo",
    "FS reg",
    "RDC",
    "FT",
    "EK",
    "KPi",
    "E-commerce",
    "RKP",
]

# Fill deficit first in this order (business priority)
PRIORITY = [0, 1, 2, 7, 4, 3, 5, 6]

# Targets from row 5 of Massiv, tons -> kg
TARGETS_TONS = [7358.0, 1582.0, 5373.0, 586.0, 1300.0, 748.0, 530.0, 2686.5]
TARGETS_KG = [t * 1000.0 for t in TARGETS_TONS]

WEEK_STARTS = [13, 22, 31, 40, 49]

FILL_SOL = PatternFill("solid", fgColor="C6EFCE")  # green solution
FILL_NOTE = PatternFill("solid", fgColor="FFF2CC")  # yellow note
FILL_HEAD = PatternFill("solid", fgColor="305496")
FILL_DEF = PatternFill("solid", fgColor="F4B183")  # orange deficit
FILL_OK = PatternFill("solid", fgColor="DDEBF7")  # blue info
FILL_WARN = PatternFill("solid", fgColor="FCE4D6")
FONT_HEAD = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
FONT_BOLD = Font(bold=True, name="Calibri", size=11)
FONT_TITLE = Font(bold=True, name="Calibri", size=14, color="1F4E79")
FONT_NORM = Font(name="Calibri", size=11)
THIN = Border(
    left=Side(style="thin", color="B0B0B0"),
    right=Side(style="thin", color="B0B0B0"),
    top=Side(style="thin", color="B0B0B0"),
    bottom=Side(style="thin", color="B0B0B0"),
)


def fnum(v):
    try:
        if v is None:
            return 0.0
        return float(v)
    except Exception:
        return 0.0


def load_rows():
    wb = load_workbook(SRC, data_only=True, read_only=True)
    names = {}
    if "Цены" in wb.sheetnames:
        for row in wb["Цены"].iter_rows(min_row=5, max_col=2, values_only=True):
            code, name = row[0], row[1]
            if code and name and str(code) not in names:
                names[str(code)] = str(name)

    ws = wb["Массив"]
    rows = []
    for idx, row in enumerate(ws.iter_rows(min_row=8, max_row=435, max_col=76, values_only=True), start=8):
        code = row[0]
        if not code:
            continue
        code = str(code)
        stock = fnum(row[5])
        prod_m = fnum(row[6])
        prod_w = [fnum(row[c - 1]) for c in range(8, 13)]
        cat = row[3]
        atype = row[4]
        fc_weeks = []
        for ws_ in WEEK_STARTS:
            ch = [fnum(row[ws_ + i - 1]) for i in range(8)]
            fc_weeks.append(ch)
        rows.append(
            {
                "excel_row": idx,
                "code": code,
                "name": names.get(code, ""),
                "cat": cat or "",
                "atype": atype or "",
                "stock": stock,
                "prod_m": prod_m,
                "prod_w": prod_w,
                "fc_weeks": fc_weeks,
            }
        )
    wb.close()
    return rows


def allocate_sku_weekly(stock, prod_w, fc_weeks):
    """Priority allocation by week with carry-over stock."""
    carry = stock
    week_alloc = []
    for w in range(5):
        avail = carry + prod_w[w]
        demand = fc_weeks[w]
        remaining = avail
        alloc = [0.0] * 8
        for ch in PRIORITY:
            take = min(demand[ch], remaining)
            alloc[ch] = take
            remaining -= take
        week_alloc.append(alloc)
        carry = remaining
    month = [sum(week_alloc[w][c] for w in range(5)) for c in range(8)]
    leftover = carry
    return week_alloc, month, leftover


def scale_channels_to_targets(plans, leftovers, fc_months, atypes):
    """
    plans: list of 8-length month plans
    Cap channels over target; push surplus stock into under-target channels.
    """
    n = len(plans)
    plans = [list(p) for p in plans]
    leftovers = list(leftovers)

    # Cap over-target channels (cut lowest priority first within each SKU)
    reverse_priority = list(reversed(PRIORITY))
    for ch in range(8):
        total = sum(p[ch] for p in plans)
        if total <= TARGETS_KG[ch] + 1e-6:
            continue
        need_cut = total - TARGETS_KG[ch]
        # cut proportionally but prefer cutting non-federal / low priority SKUs
        weights = []
        for i, p in enumerate(plans):
            w = p[ch]
            if w <= 0:
                weights.append(0.0)
                continue
            # higher weight = cut more
            factor = 1.0
            if str(atypes[i]).lower().startswith("лок"):
                factor *= 1.35
            weights.append(w * factor)
        wsum = sum(weights)
        if wsum <= 0:
            continue
        for i in range(n):
            if weights[i] <= 0:
                continue
            cut = need_cut * (weights[i] / wsum)
            cut = min(cut, plans[i][ch])
            plans[i][ch] -= cut
            leftovers[i] += cut

    # Fill under-target channels from leftovers, proportional to residual forecast
    for _pass in range(3):
        for ch in range(8):
            total = sum(p[ch] for p in plans)
            gap = TARGETS_KG[ch] - total
            if gap <= 1e-6:
                continue
            candidates = []
            for i in range(n):
                if leftovers[i] <= 1e-9:
                    continue
                # residual unconstrained demand not yet in plan
                residual = max(0.0, fc_months[i][ch] - plans[i][ch])
                # allow some surplus push even without residual (up to leftover)
                score = residual if residual > 0 else leftovers[i] * 0.05
                if str(atypes[i]).lower().startswith("фед"):
                    score *= 1.25
                if score > 0 and leftovers[i] > 0:
                    candidates.append((i, score))
            ssum = sum(s for _, s in candidates)
            if ssum <= 0:
                continue
            for i, score in candidates:
                add = min(leftovers[i], gap * (score / ssum))
                if add <= 0:
                    continue
                plans[i][ch] += add
                leftovers[i] -= add
                gap -= add
                if gap <= 1e-6:
                    break

    # Final hard cap (tiny float fixes)
    for ch in range(8):
        total = sum(p[ch] for p in plans)
        if total > TARGETS_KG[ch] + 1e-3:
            factor = TARGETS_KG[ch] / total
            for i in range(n):
                freed = plans[i][ch] * (1 - factor)
                plans[i][ch] *= factor
                leftovers[i] += freed

    return plans, leftovers


def style_header(ws, row, cols):
    for c in range(1, cols + 1):
        cell = ws.cell(row, c)
        cell.fill = FILL_HEAD
        cell.font = FONT_HEAD
        cell.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
        cell.border = THIN


def autosize(ws, max_width=42):
    for col in ws.columns:
        letter = get_column_letter(col[0].column)
        width = 10
        for cell in col[:80]:
            if cell.value is not None:
                width = max(width, min(max_width, len(str(cell.value)) + 2))
        ws.column_dimensions[letter].width = width


def write_note(ws):
    ws.sheet_view.showGridLines = False
    lines = [
        ("Поjasnitelnaya zapiska k resheniju testa", True, FILL_NOTE),
        ("Vakansija: Specialist po prognozirovaniju sprosa / OOO Obedinennye konditery", False, FILL_NOTE),
        ("", False, None),
        ("1. Spisok deficitnyh pozicij", True, FILL_DEF),
        (
            "Deficitnymi schitayutsya SKU, gde dostupnyj ostatok na nachalo + plan proizvodstva "
            "po nedelyam menshe summy neogranichennogo prognoza sprosa po kanalam. "
            "Polnyj spisok — na liste 02_Deficitnye_pozicii (oranževaya podsvetka).",
            False,
            FILL_DEF,
        ),
        ("", False, None),
        ("2. Pochemu deficit raspredelen imenno tak", True, FILL_NOTE),
        (
            "Prioritet kanalov pri nehvatke tovara (ot vysshego k nizshemu): "
            "1) FS promo (obyazatelstva / promo federalnyh setej), "
            "2) FS reg (regulyar federalnyh setej), "
            "3) RDC (regionalnye DC, servis regionov), "
            "4) RKP (roznichnaya set kompanii), "
            "5) EK (eksport, kontraktnye obyazatelstva), "
            "6) FT (firmennaya torgovlya), "
            "7) KPi (korporativnye prodazhi), "
            "8) E-commerce (bolee gibkij kanal).",
            False,
            FILL_NOTE,
        ),
        (
            "Raschet po nedelyam: ostаток_nachala + vypusk_nedeli -> otgruzka po prioritetu -> "
            "perehodyashchij ostatok na sleduyushchuyu nedelyu. Plan proizvodstva ne uvelichivalsya.",
            False,
            FILL_NOTE,
        ),
        (
            "Pri obrezke sverh plana kanala v pervuyu ochered snizhalis lokalnye SKU "
            "(tip assortimenta Lokalnyj), federalnye sohranyalis po vozmozhnosti.",
            False,
            FILL_NOTE,
        ),
        ("", False, None),
        ("3. Riski pri obrazovanii deficita", True, FILL_WARN),
        (
            "- Nedopostavka v federalnye seti: shtrafy, cut-off promo, poterya polki / ranking.",
            False,
            FILL_WARN,
        ),
        (
            "- Prosadka OTIF i urovnya servisa RDC: deficity v regionah, rost out-of-stock.",
            False,
            FILL_WARN,
        ),
        (
            "- Iskazhenie signalov sprosa: esli rezat' bez prioriteta, otdel prodazh usilit "
            "overforecasting v sleduyushchem cikle.",
            False,
            FILL_WARN,
        ),
        (
            "- Perenos sprosa na analogi / konkurentov; risk cannibalizacii i poteri dolo rynka.",
            False,
            FILL_WARN,
        ),
        (
            "- Izbytochnye ostatki po proficitnym SKU pri odnovremennom deficite po hitam: "
            "zamorozka oborotnogo kapitala.",
            False,
            FILL_WARN,
        ),
        ("", False, None),
        ("4. Dejstviya po deficitnym poziciyam", True, FILL_OK),
        (
            "1) Zafiksirovat' short-list deficita i soglasovat' s Sales / Marketing prioritet kanalov "
            "na tekushchij S&OP-cikl (FS promo / klyuchevye seti — zashchita v pervuyu ochered).",
            False,
            FILL_OK,
        ),
        (
            "2) Zaprosit' u Production vozmozhnost' perebroski moshchnostej / syrya na deficitnye "
            "SKU vnutri utverzhdennogo plana vypuska (bez uvelicheniya obshchego limila, esli nelzya).",
            False,
            FILL_OK,
        ),
        (
            "3) Po poziciyam s ustojchivym deficitom: sokratit' promo / ne podtverzhdat' extra-zakazy; "
            "predlozhit' substituty iz proficitnogo assortimenta.",
            False,
            FILL_OK,
        ),
        (
            "4) Proficitnye ob'yomy napravit' v kanaly s nedoborom do celevogo plana kanala "
            "(v predelah sumмарного plana kanala v tonnah), predpochitaya federalnyj assortiment.",
            False,
            FILL_OK,
        ),
        (
            "5) Zavesti kontrol' weekly: fact otgruzok vs plan, early-warning po otrical'nym "
            "prognoznym ostatkam na 1-2 nedeli vpered.",
            False,
            FILL_OK,
        ),
        (
            "6) Eskalaciya na S&OP: esli deficit > X% po klyuchevym SKU — decision log "
            "(accept OOS / cut channel / replan production).",
            False,
            FILL_OK,
        ),
        ("", False, None),
        ("Metodika i edinicy", True, FILL_SOL),
        (
            "Ishodnye ob'yomy v liste Massiv — v kg (ili edinicah 1:1000 k tonne). "
            "Celi kanalov nad tablicej — v tonnah; v reshenii limity = tonny * 1000. "
            "Itogovyj plan prodazh — listy 01/03 (zelenaya podsvetka = reshenie kandidata).",
            False,
            FILL_SOL,
        ),
        (
            "Plan vypuska / plan proizvodstva ne menyalsya. Celevoj ostatok ne ispol'zovalsya. "
            "Prognoz sprosa rassmatrivalsya kak neogranichennoe videnie prodazh, ne kak zakaz.",
            False,
            FILL_SOL,
        ),
    ]

    # Use proper Russian text instead of translit - rewrite note in Russian via unicode
    ru_lines = [
        ("Пояснительная записка к решению теста", True, FILL_NOTE),
        ("Вакансия: Специалист по прогнозированию спроса / ООО «Объединенные кондитеры»", False, FILL_NOTE),
        ("", False, None),
        ("1. Список дефицитных позиций", True, FILL_DEF),
        (
            "Дефицитными считаются SKU, где доступный остаток на начало + план производства "
            "по неделям меньше суммы неограниченного прогноза спроса по каналам. "
            "Полный список — на листе «02_Дефицитные_позиции» (оранжевая подсветка).",
            False,
            FILL_DEF,
        ),
        ("", False, None),
        ("2. Почему дефицит распределен именно так", True, FILL_NOTE),
        (
            "Приоритет каналов при нехватке товара (от высшего к низшему): "
            "1) ФС промо (обязательства / промо федеральных сетей), "
            "2) ФС рег (регуляр федеральных сетей), "
            "3) РДЦ (региональные РЦ, сервис регионов), "
            "4) РКП (розничная сеть компании), "
            "5) ЭК (экспорт, контрактные обязательства), "
            "6) ФТ (фирменная торговля), "
            "7) КПи (корпоративные продажи), "
            "8) E-commerce (более гибкий канал).",
            False,
            FILL_NOTE,
        ),
        (
            "Расчет по неделям: остаток начала + выпуск недели -> отгрузка по приоритету -> "
            "переходящий остаток на следующую неделю. План производства не увеличивался.",
            False,
            FILL_NOTE,
        ),
        (
            "При обрезке сверх плана канала в первую очередь снижались локальные SKU "
            "(тип ассортимента «Локальный»), федеральные сохранялись по возможности.",
            False,
            FILL_NOTE,
        ),
        ("", False, None),
        ("3. Риски при образовании дефицита", True, FILL_WARN),
        (
            "- Недопоставка в федеральные сети: штрафы, cut-off промо, потеря полки / ranking.",
            False,
            FILL_WARN,
        ),
        (
            "- Просадка OTIF и уровня сервиса РДЦ: дефициты в регионах, рост out-of-stock.",
            False,
            FILL_WARN,
        ),
        (
            "- Искажение сигналов спроса: если резать без приоритета, отдел продаж усилит "
            "overforecasting в следующем цикле.",
            False,
            FILL_WARN,
        ),
        (
            "- Перенос спроса на аналоги / конкурентов; риск каннибализации и потери доли рынка.",
            False,
            FILL_WARN,
        ),
        (
            "- Избыточные остатки по профицитным SKU при одновременном дефиците по хитам: "
            "заморозка оборотного капитала.",
            False,
            FILL_WARN,
        ),
        ("", False, None),
        ("4. Действия по дефицитным позициям", True, FILL_OK),
        (
            "1) Зафиксировать short-list дефицита и согласовать с Sales / Marketing приоритет каналов "
            "на текущий S&OP-цикл (ФС промо / ключевые сети — защита в первую очередь).",
            False,
            FILL_OK,
        ),
        (
            "2) Запросить у Production возможность переброски мощностей / сырья на дефицитные "
            "SKU внутри утвержденного плана выпуска (без увеличения общего лимита, если нельзя).",
            False,
            FILL_OK,
        ),
        (
            "3) По позициям с устойчивым дефицитом: сократить промо / не подтверждать extra-заказы; "
            "предложить субституты из профицитного ассортимента.",
            False,
            FILL_OK,
        ),
        (
            "4) Профицитные объемы направить в каналы с недобором до целевого плана канала "
            "(в пределах суммарного плана канала в тоннах), предпочитая федеральный ассортимент.",
            False,
            FILL_OK,
        ),
        (
            "5) Завести контроль weekly: факт отгрузок vs план, early-warning по отрицательным "
            "прогнозным остаткам на 1-2 недели вперед.",
            False,
            FILL_OK,
        ),
        (
            "6) Эскалация на S&OP: если дефицит критичен по ключевым SKU — decision log "
            "(accept OOS / cut channel / replan production).",
            False,
            FILL_OK,
        ),
        ("", False, None),
        ("Методика и единицы", True, FILL_SOL),
        (
            "Исходные объемы в листе «Массив» — в кг (соотношение к тонне 1000:1). "
            "Цели каналов над таблицей — в тоннах; в решении лимиты = тонны * 1000. "
            "Итоговый план продаж — листы 01 и 03 (зеленая подсветка = решение кандидата).",
            False,
            FILL_SOL,
        ),
        (
            "План выпуска / план производства не менялся. Целевой остаток не использовался. "
            "Прогноз спроса рассматривался как неограниченное видение продаж, не как заказ.",
            False,
            FILL_SOL,
        ),
    ]

    ws["A1"] = "РЕШЕНИЕ ТЕСТА / ПОЯСНИТЕЛЬНАЯ ЗАПИСКА"
    ws["A1"].font = FONT_TITLE
    ws["A1"].fill = FILL_NOTE
    ws.merge_cells("A1:B1")

    r = 3
    for text, is_head, fill in ru_lines:
        ws.cell(r, 1).value = text
        ws.cell(r, 1).font = FONT_BOLD if is_head else FONT_NORM
        ws.cell(r, 1).alignment = Alignment(wrap_text=True, vertical="top")
        if fill:
            ws.cell(r, 1).fill = fill
            ws.cell(r, 2).fill = fill
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
        ws.row_dimensions[r].height = 36 if not is_head and text else 18
        r += 1

    ws.column_dimensions["A"].width = 100
    ws.column_dimensions["B"].width = 20
    ws.freeze_panes = "A3"


def main():
    print("Loading...")
    rows = load_rows()
    print("SKU rows:", len(rows))

    raw_plans = []
    leftovers = []
    fc_months = []
    deficits = []

    for r in rows:
        week_alloc, month, leftover = allocate_sku_weekly(r["stock"], r["prod_w"], r["fc_weeks"])
        fc_m = [sum(r["fc_weeks"][w][c] for w in range(5)) for c in range(8)]
        supply = r["stock"] + sum(r["prod_w"])
        demand = sum(fc_m)
        gap = demand - supply
        r["week_alloc0"] = week_alloc
        r["fc_m"] = fc_m
        r["supply"] = supply
        r["demand"] = demand
        r["is_deficit"] = gap > 1e-6
        if r["is_deficit"]:
            deficits.append(
                {
                    "excel_row": r["excel_row"],
                    "code": r["code"],
                    "name": r["name"],
                    "cat": r["cat"],
                    "atype": r["atype"],
                    "supply": supply,
                    "demand": demand,
                    "gap": gap,
                    "gap_pct": (gap / demand * 100.0) if demand else 0.0,
                }
            )
        raw_plans.append(month)
        leftovers.append(leftover)
        fc_months.append(fc_m)

    atypes = [r["atype"] for r in rows]
    plans, leftovers = scale_channels_to_targets(raw_plans, leftovers, fc_months, atypes)

    for i, r in enumerate(rows):
        r["plan"] = plans[i]
        r["plan_total"] = sum(plans[i])
        r["leftover"] = leftovers[i]
        r["fill_rate"] = (r["plan_total"] / r["demand"] * 100.0) if r["demand"] else 100.0

    # Workbook
    wb = Workbook()

    # --- Note ---
    ws_note = wb.active
    ws_note.title = "00_Poyasnitelnaya_zapiska"
    write_note(ws_note)

    # --- Summary ---
    ws_sum = wb.create_sheet("01_Svodka_kanalov")
    headers = [
        "Kanal",
        "Cel_tonn",
        "Cel_kg",
        "Plan_kg",
        "Plan_tonn",
        "Otklonenie_kg",
        "Otklonenie_%",
        "Prognoz_kg",
    ]
    for c, h in enumerate(headers, 1):
        ws_sum.cell(1, c, h)
    style_header(ws_sum, 1, len(headers))

    # Russian headers overwrite
    ru_h = [
        "Канал",
        "Цель, т",
        "Цель, кг",
        "План, кг",
        "План, т",
        "Отклонение, кг",
        "Отклонение, %",
        "Прогноз (неогран.), кг",
    ]
    for c, h in enumerate(ru_h, 1):
        ws_sum.cell(1, c, h)
        ws_sum.cell(1, c).fill = FILL_HEAD
        ws_sum.cell(1, c).font = FONT_HEAD

    ch_plan = [sum(p[c] for p in plans) for c in range(8)]
    ch_fc = [sum(fc[c] for fc in fc_months) for c in range(8)]
    for i, name in enumerate(CH_NAMES_RU):
        row = i + 2
        plan_kg = ch_plan[i]
        tgt = TARGETS_KG[i]
        vals = [
            name,
            TARGETS_TONS[i],
            tgt,
            round(plan_kg, 2),
            round(plan_kg / 1000.0, 3),
            round(plan_kg - tgt, 2),
            round((plan_kg / tgt - 1) * 100.0, 2) if tgt else None,
            round(ch_fc[i], 2),
        ]
        for c, v in enumerate(vals, 1):
            cell = ws_sum.cell(row, c, v)
            cell.fill = FILL_SOL
            cell.border = THIN
            cell.font = FONT_NORM

    # totals
    tr = 10
    ws_sum.cell(tr, 1, "ИТОГО").font = FONT_BOLD
    ws_sum.cell(tr, 2, sum(TARGETS_TONS))
    ws_sum.cell(tr, 3, sum(TARGETS_KG))
    ws_sum.cell(tr, 4, round(sum(ch_plan), 2))
    ws_sum.cell(tr, 5, round(sum(ch_plan) / 1000.0, 3))
    ws_sum.cell(tr, 6, round(sum(ch_plan) - sum(TARGETS_KG), 2))
    ws_sum.cell(tr, 8, round(sum(ch_fc), 2))
    for c in range(1, 9):
        ws_sum.cell(tr, c).fill = FILL_NOTE
        ws_sum.cell(tr, c).font = FONT_BOLD
        ws_sum.cell(tr, c).border = THIN

    ws_sum.cell(12, 1, "Зеленая заливка = итоговое решение по каналам (не превышает целевой план канала).")
    ws_sum.cell(12, 1).fill = FILL_SOL
    ws_sum.merge_cells("A12:H12")
    ws_sum.cell(13, 1, "Желтая заливка = контрольный итог.")
    ws_sum.cell(13, 1).fill = FILL_NOTE
    autosize(ws_sum)

    # --- Deficit list ---
    ws_def = wb.create_sheet("02_Deficitnye_pozicii")
    def_h = [
        "Короткий код",
        "Наименование",
        "Категория",
        "Тип ассортимента",
        "Доступно (остаток+выпуск), кг",
        "Прогноз спроса, кг",
        "Дефицит, кг",
        "Дефицит, %",
        "План после приоритезации, кг",
        "Fill rate, %",
    ]
    for c, h in enumerate(def_h, 1):
        ws_def.cell(1, c, h)
    style_header(ws_def, 1, len(def_h))

    deficits_sorted = sorted(deficits, key=lambda x: -x["gap"])
    by_row = {r["excel_row"]: r for r in rows}
    r_i = 2
    for d in deficits_sorted:
        match = by_row[d["excel_row"]]
        vals = [
            d["code"],
            d["name"],
            d["cat"],
            d["atype"],
            round(d["supply"], 2),
            round(d["demand"], 2),
            round(d["gap"], 2),
            round(d["gap_pct"], 2),
            round(match["plan_total"], 2),
            round(match["fill_rate"], 2),
        ]
        for c, v in enumerate(vals, 1):
            cell = ws_def.cell(r_i, c, v)
            cell.fill = FILL_DEF
            cell.border = THIN
        r_i += 1

    ws_def.cell(r_i + 1, 1, f"Всего дефицитных позиций: {len(deficits_sorted)}")
    ws_def.cell(r_i + 1, 1).fill = FILL_NOTE
    ws_def.cell(r_i + 1, 1).font = FONT_BOLD
    autosize(ws_def)

    # --- Full plan ---
    ws_plan = wb.create_sheet("03_Plan_prodazh")
    plan_h = [
        "Строка_в_Массиве",
        "Короткий код",
        "Наименование",
        "Категория",
        "Тип",
        "Остаток нач., кг",
        "Выпуск мес., кг",
        "Доступно, кг",
        "Прогноз, кг",
        "Статус",
        "ФС промо",
        "ФС рег",
        "РДЦ",
        "ФТ",
        "ЭК",
        "КПи",
        "E-commerce",
        "РКП",
        "ИТОГО ПЛАН",
        "Остаток после плана",
        "Fill rate %",
    ]
    for c, h in enumerate(plan_h, 1):
        ws_plan.cell(1, c, h)
    style_header(ws_plan, 1, len(plan_h))
    ws_plan.row_dimensions[1].height = 30

    for i, r in enumerate(rows):
        row = i + 2
        status = "ДЕФИЦИТ" if r["is_deficit"] else ("ПРОФИЦИТ" if r["leftover"] > 1 else "БАЛАНС")
        vals = [
            r["excel_row"],
            r["code"],
            r["name"],
            r["cat"],
            r["atype"],
            round(r["stock"], 2),
            round(sum(r["prod_w"]), 2),
            round(r["supply"], 2),
            round(r["demand"], 2),
            status,
        ] + [round(x, 2) for x in r["plan"]] + [
            round(r["plan_total"], 2),
            round(r["leftover"], 2),
            round(r["fill_rate"], 2),
        ]
        for c, v in enumerate(vals, 1):
            cell = ws_plan.cell(row, c, v)
            cell.border = THIN
            cell.font = FONT_NORM
            # solution columns 11-19 green
            if 11 <= c <= 19:
                cell.fill = FILL_SOL
            elif c == 10:
                cell.fill = FILL_DEF if status == "ДЕФИЦИТ" else (FILL_OK if status == "ПРОФИЦИТ" else FILL_NOTE)

    ws_plan.freeze_panes = "C2"
    ws_plan.auto_filter.ref = f"A1:U{len(rows)+1}"
    # note row
    note_row = len(rows) + 3
    ws_plan.cell(note_row, 1, "Зеленые столбцы (ФС промо ... ИТОГО ПЛАН) — решение кандидата для вставки в блок «План мес» файла ТЗ.")
    ws_plan.cell(note_row, 1).fill = FILL_SOL
    ws_plan.merge_cells(start_row=note_row, start_column=1, end_row=note_row, end_column=12)
    autosize(ws_plan, max_width=28)

    # --- Legend ---
    ws_leg = wb.create_sheet("04_Legenda_cveta")
    legend = [
        ("Цвет", "Значение"),
        ("Зеленый", "Итоговое решение (план продаж / ответ кандидата)"),
        ("Желтый", "Пояснительная записка и контрольные итоги"),
        ("Оранжевый", "Дефицитные позиции и риски"),
        ("Голубой", "Рекомендуемые действия"),
        ("Синий заголовок", "Шапка таблиц"),
    ]
    for r, (a, b) in enumerate(legend, 1):
        ws_leg.cell(r, 1, a)
        ws_leg.cell(r, 2, b)
        ws_leg.cell(r, 1).font = FONT_BOLD if r == 1 else FONT_NORM
        ws_leg.cell(r, 2).font = FONT_BOLD if r == 1 else FONT_NORM
    ws_leg["A2"].fill = FILL_SOL
    ws_leg["A3"].fill = FILL_NOTE
    ws_leg["A4"].fill = FILL_DEF
    ws_leg["A5"].fill = FILL_OK
    ws_leg["A6"].fill = FILL_HEAD
    ws_leg["A6"].font = FONT_HEAD
    autosize(ws_leg)

    # Rename sheets to Russian-friendly short ASCII-safe already set;
    # Add Cyrillic titles via second pass rename where Excel allows
    ws_note.title = "00_Пояснительная"
    ws_sum.title = "01_Сводка_каналов"
    ws_def.title = "02_Дефицит"
    ws_plan.title = "03_План_продаж"
    ws_leg.title = "04_Легенда"

    print("Saving", OUT)
    wb.save(OUT)
    print("OK")
    print("Deficit SKUs:", len(deficits_sorted))
    print("Channel plan tons:", [round(x / 1000, 2) for x in ch_plan])
    print("Targets tons:", TARGETS_TONS)


if __name__ == "__main__":
    main()
