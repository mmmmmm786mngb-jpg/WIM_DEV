#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Klassifikacija 61 UK-dokumenta old vs new4, i sverka teh zhe nomerov s new3.
Konsol - ASCII.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from decimal import Decimal

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import compare_ndfl_old_vs_new2 as c  # noqa: E402

BASE = r"c:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects\IMDEV-7330 НовыеТесты"
DOC = r"c:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects\IMDEV-7330 Оптимизация 1С ФИН_Расчет НДФЛ\Документация"
JSON4 = os.path.join(DOC, "imdev7330_ndfl_old_vs_new4_diff.json")
OUT = os.path.join(DOC, "imdev7330_ndfl_new4_uk_diff_clients.json")

NUM_UK = c.NUM_UK
EPS = Decimal("0.01")
PLAT = "000000000038432"


def safe_print(t: str) -> None:
    c.safe_print(t)


def classify(delta: dict) -> str:
    d = {k: Decimal(str(v)) for k, v in delta.items()}
    vy = d.get("СуммаВычета", Decimal("0"))
    tax = d.get("НалогооблагаемаяCумма", Decimal("0"))
    inc = d.get("СуммаДохода", Decimal("0"))
    ud = d.get("СуммаКУдержанию", Decimal("0"))
    fin = d.get("ФинансовыйРезультат", Decimal("0"))
    sm = d.get("Сумма", Decimal("0"))
    keys = set(d)
    if abs(inc) < EPS and abs(vy) >= EPS and abs(tax + vy) < EPS:
        return "invest_vychet_like_platonov"
    if abs(inc) < EPS and abs(vy) < EPS and abs(ud) >= EPS and keys <= {
        "СуммаКУдержанию",
        "НалогооблагаемаяCумма",
        "ФинансовыйРезультат",
        "Сумма",
        "Пропорция",
    }:
        return "withhold_only"
    if abs(inc) >= EPS:
        return "income_moved"
    return "other"


def load_docs(path):
    _, idx, rows = c.load_xlsx_rows(path)
    docs, _, _, _ = c.agg_docs(rows, idx, NUM_UK)
    by_num_pf = {}
    for row in rows:
        num = str(c.get(row, idx, "НомерДокумента") or "")
        pf = str(c.get(row, idx, "Портфель") or "")
        if not num:
            continue
        by_num_pf.setdefault(num, set())
        if pf:
            by_num_pf[num].add(pf)
    return docs, by_num_pf, idx, rows


def main():
    with open(JSON4, encoding="utf-8") as f:
        j4 = json.load(f)
    diffs = j4["uk"]["compare"]["money_diffs"]
    nums = [d["num"] for d in diffs]
    safe_print("money docs=" + str(len(nums)))

    safe_print("Load UK old")
    docs_o, pf_o, _, _ = load_docs(os.path.join(BASE, "НДФЛ_Управление_27292.xlsx"))
    safe_print("Load UK n3")
    docs_3, pf_3, _, _ = load_docs(os.path.join(BASE, "НДФЛ_Управление_27292_ПоНовому3.xlsx"))
    safe_print("Load UK n4")
    docs_4, pf_4, _, _ = load_docs(os.path.join(BASE, "НДФЛ_Управление_27292_ПоНовому4.xlsx"))

    kinds = Counter()
    rows_out = []
    n3_match = 0
    n3_diff = 0
    n3_missing = 0
    n4_eq_n3 = 0
    n4_ne_n3 = 0

    for d in diffs:
        num = d["num"]
        kind = classify(d["delta"])
        kinds[kind] += 1
        pfs = sorted(pf_4.get(num) or pf_o.get(num) or [])
        clients = []
        for p in pfs:
            if "(" in p and p.endswith(")"):
                clients.append(p[p.find("(") + 1 : -1])
        so = docs_o.get(num)
        s3 = docs_3.get(num)
        s4 = docs_4.get(num)

        def sums(doc):
            if not doc:
                return None
            return {n: str(doc["sums"][n]) for n in NUM_UK}

        delta_n3 = {}
        if so and s3:
            for n in NUM_UK:
                dd = s3["sums"][n] - so["sums"][n]
                if abs(dd) >= EPS:
                    delta_n3[n] = str(dd)
            if delta_n3:
                n3_diff += 1
            else:
                n3_match += 1
        elif not s3:
            n3_missing += 1

        delta_n4_n3 = {}
        if s3 and s4:
            for n in NUM_UK:
                dd = s4["sums"][n] - s3["sums"][n]
                if abs(dd) >= EPS:
                    delta_n4_n3[n] = str(dd)
            if delta_n4_n3:
                n4_ne_n3 += 1
            else:
                n4_eq_n3 += 1

        rows_out.append(
            {
                "num": num,
                "kind": kind,
                "is_plat": num == PLAT,
                "clients": sorted(set(clients)),
                "portfolios": pfs,
                "old_rows": so["n"] if so else 0,
                "n3_rows": s3["n"] if s3 else 0,
                "n4_rows": s4["n"] if s4 else 0,
                "parts_old": dict(so["parts"]) if so else {},
                "parts_n3": dict(s3["parts"]) if s3 else {},
                "parts_n4": dict(s4["parts"]) if s4 else {},
                "delta_n4_vs_old": d["delta"],
                "delta_n3_vs_old": delta_n3,
                "delta_n4_vs_n3": delta_n4_n3,
                "n3_matched_old": bool(so and s3 and not delta_n3),
            }
        )

    # also: among ALL common docs, how many n4!=n3
    safe_print("Scan all docs n3 vs n4 vs old...")
    common = set(docs_o) & set(docs_4)
    n4_old_money = 0
    n3_old_money = 0
    n4_n3_money = 0
    n4_old_not_n3 = 0
    n3_old_fixed_in_n4 = 0
    for num in common:
        a = docs_o[num]["sums"]
        b = docs_4[num]["sums"]
        ch4 = any(abs(b[n] - a[n]) >= EPS for n in NUM_UK)
        if ch4:
            n4_old_money += 1
        if num in docs_3:
            c3 = docs_3[num]["sums"]
            ch3 = any(abs(c3[n] - a[n]) >= EPS for n in NUM_UK)
            ch43 = any(abs(b[n] - c3[n]) >= EPS for n in NUM_UK)
            if ch3:
                n3_old_money += 1
            if ch43:
                n4_n3_money += 1
            if ch4 and not ch3:
                n4_old_not_n3 += 1
            if ch3 and not ch4:
                n3_old_fixed_in_n4 += 1

    summary = {
        "kinds": dict(kinds),
        "n3_vs_old_on_61": {"match": n3_match, "diff": n3_diff, "missing": n3_missing},
        "n4_vs_n3_on_61": {"equal": n4_eq_n3, "diff": n4_ne_n3},
        "all_common": {
            "common_old_n4": len(common),
            "n4_vs_old_money": n4_old_money,
            "n3_vs_old_money": n3_old_money,
            "n4_vs_n3_money": n4_n3_money,
            "n4_broke_vs_old_but_n3_ok": n4_old_not_n3,
            "n4_fixed_n3_vs_old": n3_old_fixed_in_n4,
        },
        "docs": rows_out,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    safe_print("kinds=" + str(dict(kinds)))
    safe_print("on 61: n3_match_old=" + str(n3_match) + " n3_diff_old=" + str(n3_diff))
    safe_print("on 61: n4_eq_n3=" + str(n4_eq_n3) + " n4_ne_n3=" + str(n4_ne_n3))
    safe_print("ALL n4_vs_old=" + str(n4_old_money) + " n3_vs_old=" + str(n3_old_money))
    safe_print("ALL n4_vs_n3=" + str(n4_n3_money))
    safe_print("broke_in_n4=" + str(n4_old_not_n3) + " fixed_in_n4=" + str(n3_old_fixed_in_n4))
    for row in rows_out:
        cl = ",".join(row["clients"][:3]) or "?"
        safe_print(
            row["kind"][:18].ljust(18)
            + " "
            + row["num"]
            + " n3ok="
            + str(row["n3_matched_old"])
            + " "
            + cl
        )
    safe_print("JSON " + OUT)


if __name__ == "__main__":
    main()
