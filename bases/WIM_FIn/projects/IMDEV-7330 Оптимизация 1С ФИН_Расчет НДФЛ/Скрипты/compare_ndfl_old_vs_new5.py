#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sverka NDFL: etalon 27292 vs PoNovomu5 (Locks + NkdCoupon + NkdParam, IT 13 potokov).
Konsol - ASCII. HTML/JSON - UTF-8.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from decimal import Decimal
from html import escape

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import compare_ndfl_old_vs_new2 as c  # noqa: E402
import compare_ndfl_old_vs_new3 as n3  # noqa: E402

BASE = r"c:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects\IMDEV-7330 НовыеТесты"
DOC = r"c:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects\IMDEV-7330 Оптимизация 1С ФИН_Расчет НДФЛ\Документация"
OUT_HTML = os.path.join(DOC, "imdev7330_ndfl_old_vs_new5_diff.html")
OUT_JSON = os.path.join(DOC, "imdev7330_ndfl_old_vs_new5_diff.json")

FILES = {
    "uk_old": os.path.join(BASE, "НДФЛ_Управление_27292.xlsx"),
    "uk_n4": os.path.join(BASE, "НДФЛ_Управление_27292_ПоНовому5.xlsx"),
    "pf_old": os.path.join(BASE, "НДФЛ_Портфели_27292.xlsx"),
    "pf_n4": os.path.join(BASE, "НДФЛ_Портфели_27292_ПоНовому5.xlsx"),
    "msg_old": os.path.join(BASE, "Сообщения_поСтарому_Аванкор.txt"),
    "msg_n4": os.path.join(BASE, "Сообщения_поНовому5_Аванкор.txt"),
    "log_n4": os.path.join(BASE, "Лог формирования начисдений НДФЛ_ПоНовому5.xlsx"),
}

PLAT_NUM = n3.PLAT_NUM
NUM_UK = c.NUM_UK
NUM_PF = c.NUM_PF
EPS = c.EPS


def safe_print(text: str) -> None:
    c.safe_print(text)


def compare_docs_full(docs_old, docs_new, num_names):
    """All money diffs, not sliced. Also row-count / TCH diffs with equal money."""
    common = set(docs_old) & set(docs_new)
    only_old = sorted(set(docs_old) - set(docs_new))
    only_new = sorted(set(docs_new) - set(docs_old))
    money_diffs = []
    structure_diffs = []
    equal = 0
    for num in common:
        a = docs_old[num]
        b = docs_new[num]
        delta = {}
        money_changed = False
        for n in num_names:
            d = b["sums"][n] - a["sums"][n]
            if abs(d) >= EPS:
                money_changed = True
                delta[n] = str(d)
        parts_o = dict(a["parts"])
        parts_n = dict(b["parts"])
        struct = a["n"] != b["n"] or parts_o != parts_n
        item = {
            "num": num,
            "ref": b.get("ref") or a.get("ref") or "",
            "old_rows": a["n"],
            "new_rows": b["n"],
            "parts_old": parts_o,
            "parts_new": parts_n,
            "is_plat": num == PLAT_NUM
            or is_plat_ref(a.get("ref") or "")
            or is_plat_ref(b.get("ref") or ""),
        }
        if money_changed:
            item["delta"] = delta
            money_diffs.append(item)
        elif struct:
            structure_diffs.append(item)
        else:
            equal += 1
    money_diffs.sort(key=lambda x: -sum(abs(Decimal(v)) for v in x["delta"].values()))
    structure_diffs.sort(key=lambda x: abs(x["new_rows"] - x["old_rows"]), reverse=True)
    return {
        "common": len(common),
        "equal_sums_and_structure": equal,
        "diff_sums": len(money_diffs),
        "diff_structure_only": len(structure_diffs),
        "only_old": only_old,
        "only_new": only_new,
        "money_diffs": money_diffs,
        "structure_diffs": structure_diffs,
    }


def is_plat_ref(ref: str) -> bool:
    blob = ref or ""
    return any(m in blob for m in n3.PLAT_MARKERS) or PLAT_NUM in blob


def conv(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, Counter):
        return dict(obj)
    if isinstance(obj, tuple):
        return [conv(x) for x in obj]
    if isinstance(obj, list):
        return [conv(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): conv(v) for k, v in obj.items()}
    return obj


def money_rows_html(t_old, t_new):
    out = []
    keys = list(t_old.keys()) if isinstance(t_old, dict) else []
    for k in keys:
        a = Decimal(str(t_old.get(k) or 0))
        b = Decimal(str(t_new.get(k) or 0))
        d = b - a
        cls = "ok" if abs(d) < EPS else "bad"
        out.append(
            f"<tr class='{cls}'><td>{escape(k)}</td>"
            f"<td class='num'>{n3.fmt_dec(a)}</td>"
            f"<td class='num'>{n3.fmt_dec(b)}</td>"
            f"<td class='num'>{n3.fmt_dec(d)}</td></tr>"
        )
    return "".join(out)


def analyze():
    result = {"files": {}, "md5": {}}
    for k, p in FILES.items():
        result["files"][k] = {
            "name": os.path.basename(p),
            "bytes": os.path.getsize(p) if os.path.isfile(p) else 0,
            "exists": os.path.isfile(p),
        }
        if not os.path.isfile(p):
            raise FileNotFoundError(p)

    for k in ("uk_old", "uk_n4", "pf_old", "pf_n4"):
        safe_print("md5 " + os.path.basename(FILES[k]))
        result["md5"][k] = n3.file_md5(FILES[k])
    result["pf_identical"] = result["md5"]["pf_old"] == result["md5"]["pf_n4"]
    result["uk_identical"] = result["md5"]["uk_old"] == result["md5"]["uk_n4"]
    safe_print("pf identical=" + str(result["pf_identical"]))
    safe_print("uk identical=" + str(result["uk_identical"]))

    safe_print("Load UK old...")
    _, i_uk_o, r_uk_o = c.load_xlsx_rows(FILES["uk_old"])
    safe_print("Load UK new5...")
    _, i_uk_4, r_uk_4 = c.load_xlsx_rows(FILES["uk_n4"])
    docs_o, parts_o, pf_o, _ = c.agg_docs(r_uk_o, i_uk_o, NUM_UK)
    docs_4, parts_4, pf_4, _ = c.agg_docs(r_uk_4, i_uk_4, NUM_UK)
    uk_cmp = compare_docs_full(docs_o, docs_4, NUM_UK)
    bag_uk = c.bag_diff(r_uk_o, r_uk_4, c.line_key_uk, i_uk_o, i_uk_4)
    bag_uk["only_old_fmt"] = [(n, c.fmt_key_uk(k)) for n, k in bag_uk["only_old"][:40]]
    bag_uk["only_new_fmt"] = [(n, c.fmt_key_uk(k)) for n, k in bag_uk["only_new"][:40]]
    del bag_uk["only_old"]
    del bag_uk["only_new"]

    plat_o = {k: v for k, v in docs_o.items() if k == PLAT_NUM or is_plat_ref(v.get("ref") or "")}
    plat_4 = {k: v for k, v in docs_4.items() if k == PLAT_NUM or is_plat_ref(v.get("ref") or "")}
    plat_nums = set(plat_o) | set(plat_4) | {PLAT_NUM}
    docs_o_wo = {k: v for k, v in docs_o.items() if k not in plat_nums}
    docs_4_wo = {k: v for k, v in docs_4.items() if k not in plat_nums}
    uk_wo = compare_docs_full(docs_o_wo, docs_4_wo, NUM_UK)

    money_plat = [d for d in uk_cmp["money_diffs"] if d["num"] in plat_nums or d.get("is_plat")]
    money_other = [d for d in uk_cmp["money_diffs"] if d["num"] not in plat_nums and not d.get("is_plat")]

    result["uk"] = {
        "rows_old": len(r_uk_o),
        "rows_new": len(r_uk_4),
        "totals_old": c.totals(r_uk_o, i_uk_o, NUM_UK),
        "totals_new": c.totals(r_uk_4, i_uk_4, NUM_UK),
        "parts_old": dict(parts_o),
        "parts_new": dict(parts_4),
        "docs_old": len(docs_o),
        "docs_new": len(docs_4),
        "portfolios_old": len(pf_o),
        "portfolios_new": len(pf_4),
        "empty_old_n": len(n3.empty_uk_docs(docs_o)),
        "empty_new_n": len(n3.empty_uk_docs(docs_4)),
        "compare": uk_cmp,
        "compare_wo_plat": uk_wo,
        "line_bag": bag_uk,
        "by_portfolio": c.compare_pf_sums(
            c.sum_by_portfolio(r_uk_o, i_uk_o, NUM_UK),
            c.sum_by_portfolio(r_uk_4, i_uk_4, NUM_UK),
            NUM_UK,
        ),
        "plat_docs_old": {
            k: {
                "n": v["n"],
                "parts": dict(v["parts"]),
                "sums": {n: str(v["sums"][n]) for n in NUM_UK},
                "ref": v["ref"],
            }
            for k, v in plat_o.items()
        },
        "plat_docs_new": {
            k: {
                "n": v["n"],
                "parts": dict(v["parts"]),
                "sums": {n: str(v["sums"][n]) for n in NUM_UK},
                "ref": v["ref"],
            }
            for k, v in plat_4.items()
        },
        "plat_rows_old": n3.dump_plat_rows(r_uk_o, i_uk_o, NUM_UK),
        "plat_rows_new": n3.dump_plat_rows(r_uk_4, i_uk_4, NUM_UK),
        "money_plat_n": len(money_plat),
        "money_other_n": len(money_other),
        "money_other": money_other,
        "money_plat": money_plat,
        "surname_others_old": n3.docs_with_surname(docs_o),
        "surname_others_new": n3.docs_with_surname(docs_4),
    }
    del r_uk_o, r_uk_4, docs_o, docs_4

    if result["pf_identical"]:
        safe_print("Skip PF rows: MD5 identical")
        result["pf"] = {"skipped_full": True, "reason": "MD5 identical"}
        result["pf_plat"] = {"skipped": True}
    else:
        safe_print("Load PF old...")
        _, i_pf_o, r_pf_o = c.load_xlsx_rows(FILES["pf_old"])
        safe_print("Load PF new5...")
        _, i_pf_4, r_pf_4 = c.load_xlsx_rows(FILES["pf_n4"])
        docs_po, parts_po, pfset_o, _ = c.agg_docs(r_pf_o, i_pf_o, NUM_PF)
        docs_p4, parts_p4, pfset_4, _ = c.agg_docs(r_pf_4, i_pf_4, NUM_PF)
        pf_cmp = compare_docs_full(docs_po, docs_p4, NUM_PF)
        bag_pf = c.bag_diff(r_pf_o, r_pf_4, c.line_key_pf, i_pf_o, i_pf_4)
        bag_pf["only_old_fmt"] = [(n, c.fmt_key_pf(k)) for n, k in bag_pf["only_old"][:40]]
        bag_pf["only_new_fmt"] = [(n, c.fmt_key_pf(k)) for n, k in bag_pf["only_new"][:40]]
        del bag_pf["only_old"]
        del bag_pf["only_new"]
        result["pf"] = {
            "skipped_full": False,
            "rows_old": len(r_pf_o),
            "rows_new": len(r_pf_4),
            "totals_old": c.totals(r_pf_o, i_pf_o, NUM_PF),
            "totals_new": c.totals(r_pf_4, i_pf_4, NUM_PF),
            "parts_old": dict(parts_po),
            "parts_new": dict(parts_p4),
            "docs_old": len(docs_po),
            "docs_new": len(docs_p4),
            "portfolios_old": len(pfset_o),
            "portfolios_new": len(pfset_4),
            "compare": pf_cmp,
            "line_bag": bag_pf,
            "by_portfolio": c.compare_pf_sums(
                c.sum_by_portfolio(r_pf_o, i_pf_o, NUM_PF),
                c.sum_by_portfolio(r_pf_4, i_pf_4, NUM_PF),
                NUM_PF,
            ),
        }
        rows_plat_o = [rw for rw in r_pf_o if n3.is_plat_row(rw, i_pf_o)]
        rows_plat_4 = [rw for rw in r_pf_4 if n3.is_plat_row(rw, i_pf_4)]
        bagp = c.bag_diff(rows_plat_o, rows_plat_4, c.line_key_pf, i_pf_o, i_pf_4)
        bagp["only_old_fmt"] = [(n, c.fmt_key_pf(k)) for n, k in bagp["only_old"]]
        bagp["only_new_fmt"] = [(n, c.fmt_key_pf(k)) for n, k in bagp["only_new"]]
        del bagp["only_old"]
        del bagp["only_new"]
        result["pf_plat"] = {
            "rows_old": len(rows_plat_o),
            "rows_new": len(rows_plat_4),
            "totals_old": c.totals(rows_plat_o, i_pf_o, NUM_PF),
            "totals_new": c.totals(rows_plat_4, i_pf_4, NUM_PF),
            "bag": bagp,
        }
        del r_pf_o, r_pf_4

    safe_print("Parse messages...")
    msg_o = c.parse_messages(FILES["msg_old"])
    msg_4 = c.parse_messages(FILES["msg_n4"])
    sa, sb = msg_o["unique"], msg_4["unique"]
    cl_a, cl_b = set(msg_o["clients_rasp"]), set(msg_4["clients_rasp"])
    result["msg"] = {
        "kinds_a": dict(msg_o["kinds"]),
        "kinds_b": dict(msg_4["kinds"]),
        "nonempty_a": msg_o["nonempty"],
        "nonempty_b": msg_4["nonempty"],
        "only_a_n": len(sa - sb),
        "only_b_n": len(sb - sa),
        "common_n": len(sa & sb),
        "clients_rasp_a": len(cl_a),
        "clients_rasp_b": len(cl_b),
        "clients_only_a": sorted(cl_a - cl_b)[:50],
        "clients_only_b": sorted(cl_b - cl_a)[:50],
        "granica_a": len(msg_o["granica"]),
        "granica_b": len(msg_4["granica"]),
        "ne_prov_a": msg_o["ne_prov"],
        "ne_prov_b": msg_4["ne_prov"],
        "plat_msgs_a": [x for x in msg_o["clients_rasp"] if n3.PLAT_NAME in x],
        "plat_msgs_b": [x for x in msg_4["clients_rasp"] if n3.PLAT_NAME in x],
    }

    safe_print("Parse log new5 xlsx...")
    result["log_n4"] = n3.parse_log_xlsx(FILES["log_n4"])

    bp = result["uk"].get("by_portfolio") or {}
    if isinstance(bp.get("only_old"), list):
        bp["only_old_n"] = len(bp["only_old"])
        bp["only_old"] = bp["only_old"][:20]
    if isinstance(bp.get("only_new"), list):
        bp["only_new_n"] = len(bp["only_new"])
        bp["only_new"] = bp["only_new"][:20]
    if not result["pf"].get("skipped_full"):
        bp2 = result["pf"].get("by_portfolio") or {}
        if isinstance(bp2.get("only_old"), list):
            bp2["only_old_n"] = len(bp2["only_old"])
            bp2["only_old"] = bp2["only_old"][:20]
        if isinstance(bp2.get("only_new"), list):
            bp2["only_new_n"] = len(bp2["only_new"])
            bp2["only_new"] = bp2["only_new"][:20]

    slim_cmp_keys = []
    for block in (result["uk"]["compare"], result["uk"]["compare_wo_plat"]):
        slim_cmp_keys.append(block)
    if not result["pf"].get("skipped_full"):
        slim_cmp_keys.append(result["pf"]["compare"])
    for block in slim_cmp_keys:
        block["only_old_n"] = len(block.get("only_old") or [])
        block["only_new_n"] = len(block.get("only_new") or [])
        block["only_old_sample"] = (block.get("only_old") or [])[:40]
        block["only_new_sample"] = (block.get("only_new") or [])[:40]
        block.pop("only_old", None)
        block.pop("only_new", None)

    json_out = conv(result)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(json_out, f, ensure_ascii=False, indent=2)
    safe_print("JSON written")
    return result


def write_html(r):
    uk = r["uk"]
    pf = r["pf"]
    log4 = r["log_n4"]
    msg = r["msg"]
    cmpu = uk["compare"]
    cmpw = uk["compare_wo_plat"]

    st = n3.parse_dt((log4.get("header") or {}).get("start") or "")
    en = n3.parse_dt((log4.get("header") or {}).get("end") or "")
    job_dur = n3.dur_hms(st, en) if st and en else "?"

    pf_ok = False
    if pf.get("skipped_full"):
        pf_ok = True
        pf_note = "файлы портфелей совпали по MD5"
    else:
        bag = pf.get("line_bag") or {}
        pfc = pf.get("compare") or {}
        pf_ok = (
            bag.get("only_old_n", 1) == 0
            and bag.get("only_new_n", 1) == 0
            and pfc.get("diff_sums", 1) == 0
            and pfc.get("only_old_n", 1) == 0
            and pfc.get("only_new_n", 1) == 0
        )
        pf_note = "строки и суммы портфелей"

    plat_ok = uk.get("money_plat_n", 1) == 0
    money_others_ok = cmpw.get("diff_sums", 1) == 0 and uk.get("money_other_n", 1) == 0
    missing_docs = cmpw.get("only_old_n", 1)
    extra_docs = cmpw.get("only_new_n", 0)
    others_ok = money_others_ok and missing_docs == 0 and extra_docs == 0
    struct_wo = cmpw.get("diff_structure_only", 0)

    if pf_ok and plat_ok and money_others_ok and missing_docs == 0 and extra_docs == 0 and struct_wo == 0:
        verdict = (
            "Полное совпадение с эталоном 27292: портфели, документ Платонова и все остальные УК."
        )
        vcls = "in"
    elif pf_ok and plat_ok and money_others_ok and missing_docs == 0:
        verdict = (
            "Все денежные поля совпали с эталоном 27292 (портфели, Платонов и остальные УК). "
            "Не денежные отличия: лишние пустые документы УК в новой выгрузке и/или "
            "лишние строки ТЧ Выводы/ОбщиеРасходы при тех же суммах."
        )
        vcls = "in"
    elif pf_ok and plat_ok and others_ok:
        verdict = (
            "Суммы всех УК (включая Платонова) совпали. Есть только структурные отличия "
            "(число строк ТЧ при тех же суммах)."
        )
        vcls = "warn"
    elif pf_ok and others_ok and not plat_ok:
        verdict = "Портфели и УК кроме Платонова совпали. Расхождение только по Платонову."
        vcls = "warn"
    elif pf_ok and plat_ok and not money_others_ok:
        verdict = "Платонов совпал, но есть денежные расхождения по другим УК."
        vcls = "out"
    else:
        verdict = "Есть расхождения. См. таблицы ниже."
        vcls = "out"

    def fname(key):
        return ((r.get("files") or {}).get(key) or {}).get("name") or key

    def fbytes(key):
        return n3.fmt_int(((r.get("files") or {}).get(key) or {}).get("bytes") or 0)

    labels = {
        "raspredelenie": "Невозможно распределить НДФЛ",
        "granica": "Граница актуальности сдвинута",
        "ne_proveden": "Документ не проведен",
        "oshibka": "Ошибка",
        "other": "Прочее",
        "empty": "Пустые",
    }
    kind_rows = []
    for k in sorted(set(msg["kinds_a"]) | set(msg["kinds_b"])):
        a = msg["kinds_a"].get(k, 0)
        b = msg["kinds_b"].get(k, 0)
        cls = "ok" if a == b else "warn"
        kind_rows.append(
            f"<tr class='{cls}'><td>{escape(labels.get(k, k))}</td>"
            f"<td class='num'>{a}</td><td class='num'>{b}</td><td class='num'>{b - a}</td></tr>"
        )

    def doc_rows(items, limit=80):
        out = []
        for d in items[:limit]:
            deltas = "; ".join(f"{k}={v}" for k, v in (d.get("delta") or {}).items())
            cls = "warn" if d.get("num") == PLAT_NUM else "bad"
            out.append(
                f"<tr class='{cls}'><td class='sig'>{escape(d.get('num') or '')}</td>"
                f"<td>{n3.mask_esc(d.get('ref') or '')}</td>"
                f"<td class='sig'>{escape(deltas)}</td>"
                f"<td class='num'>{d.get('old_rows')}</td>"
                f"<td class='num'>{d.get('new_rows')}</td></tr>"
            )
        if len(items) > limit:
            out.append(
                f"<tr><td colspan='5'>... ещё {len(items) - limit} документов</td></tr>"
            )
        return "".join(out) or "<tr class='ok'><td colspan='5'>Нет</td></tr>"

    plat_sum_html = ""
    po = uk.get("plat_docs_old") or {}
    pn = uk.get("plat_docs_new") or {}
    if PLAT_NUM in po and PLAT_NUM in pn:
        plat_sum_html = money_rows_html(po[PLAT_NUM]["sums"], pn[PLAT_NUM]["sums"])

    plat_lines = n3.plat_table(uk.get("plat_rows_old") or [], uk.get("plat_rows_new") or [], NUM_UK)

    pf_totals_html = ""
    if not pf.get("skipped_full"):
        pf_totals_html = money_rows_html(pf["totals_old"], pf["totals_new"])

    lock_lis = "".join(
        f"<li><code>{n3.mask_esc(a)}</code> - {n3.mask_esc(b)}</li>"
        for a, b in log4.get("lock_sample") or []
    ) or "<p class='small'>Сообщений про блокировки / повтор / 1222 в логе нет.</p>"

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>IMDEV-7330. Сверка эталон vs ПоНовому5</title>
<style>
    body {{ font-family: "Segoe UI", Arial, sans-serif; line-height: 1.55; color: #212529; background: #f5f6f8; margin: 0; padding: 0 0 60px 0; }}
    .wrap {{ max-width: 1180px; margin: 0 auto; padding: 0 24px; }}
    header {{ background: #1f2d3d; color: #fff; padding: 28px 0 22px 0; margin-bottom: 28px; }}
    header h1 {{ margin: 0 0 8px 0; font-size: 24px; }}
    header .sub {{ color: #b8c4d0; font-size: 14px; }}
    h2 {{ font-size: 20px; margin: 32px 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid #17a2b8; }}
    p {{ margin: 10px 0; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; margin: 12px 0; font-size: 13.5px; }}
    th {{ background: #1f2d3d; color: #fff; text-align: left; padding: 8px 10px; }}
    td {{ padding: 7px 10px; border-bottom: 1px solid #e3e6ea; vertical-align: top; }}
    tbody tr:nth-child(even) {{ background: #fafbfc; }}
    tr.ok td {{ background: #eefaf1; }}
    tr.bad td {{ background: #fdf0f1; }}
    tr.warn td {{ background: #fff9e6; }}
    .num {{ text-align: right; font-family: Consolas, monospace; white-space: nowrap; }}
    .sig {{ font-family: Consolas, "Courier New", monospace; font-size: 12px; }}
    .box {{ padding: 14px 18px; border-radius: 5px; margin: 14px 0; border-left: 5px solid; }}
    .in {{ background: #eefaf1; border-color: #28a745; }}
    .out {{ background: #fdf0f1; border-color: #dc3545; }}
    .warn {{ background: #fff9e6; border-color: #f0ad4e; }}
    .info {{ background: #eaf7fa; border-color: #17a2b8; }}
    .small {{ font-size: 13px; color: #6c757d; }}
    footer {{ margin-top: 36px; padding-top: 12px; border-top: 1px solid #dee2e6; font-size: 13px; color: #6c757d; }}
</style>
</head>
<body>
<header>
<div class="wrap">
    <h1>IMDEV-7330. Сверка эталон 27292 vs ПоНовому5</h1>
    <div class="sub">
        Три расширения: IMDEV7330_Locks + IMDEV7330_NkdCoupon + IMDEV7330_NkdParam.
        Эталон: НДФЛ_Портфели_27292.xlsx и НДФЛ_Управление_27292.xlsx.
        ФИО в таблицах скрыты.
    </div>
</div>
</header>
<div class="wrap">

<div class="box {vcls}"><b>Вывод</b>{escape(verdict)}</div>

<div class="box info">
<b>Прогон</b>
Лог: {escape(str((log4.get("header") or {}).get("start")))} — {escape(str((log4.get("header") or {}).get("end")))}
({escape(job_dur)}). Ошибок в шапке лога: {escape(str((log4.get("header") or {}).get("errors")))}.
Проведено по портфелям: {n3.fmt_int(log4.get("proveden_pf_n") or 0)},
по клиентам УК: {n3.fmt_int(log4.get("proveden_uk_n") or 0)}.
Блокировок в логе: {n3.fmt_int(log4.get("lock_n") or 0)}.
Портфели: {escape(pf_note)}.
</div>

<h2>1. Файлы</h2>
<table>
<thead><tr><th>Роль</th><th>Файл</th><th>Байт</th><th>MD5</th></tr></thead>
<tbody>
<tr><td>УК эталон</td><td>{escape(fname("uk_old"))}</td><td class="num">{fbytes("uk_old")}</td><td class="sig">{escape(r["md5"].get("uk_old",""))}</td></tr>
<tr><td>УК новое5</td><td>{escape(fname("uk_n4"))}</td><td class="num">{fbytes("uk_n4")}</td><td class="sig">{escape(r["md5"].get("uk_n4",""))}</td></tr>
<tr><td>Портфели эталон</td><td>{escape(fname("pf_old"))}</td><td class="num">{fbytes("pf_old")}</td><td class="sig">{escape(r["md5"].get("pf_old",""))}</td></tr>
<tr><td>Портфели новое5</td><td>{escape(fname("pf_n4"))}</td><td class="num">{fbytes("pf_n4")}</td><td class="sig">{escape(r["md5"].get("pf_n4",""))}</td></tr>
</tbody>
</table>

<h2>2. Портфели</h2>
<p>Идентичны по MD5: <b>{"да" if r.get("pf_identical") else "нет"}</b>.</p>
{"<p>Построчное сравнение не запускалось.</p>" if pf.get("skipped_full") else f'''
<table>
<thead><tr><th>Показатель</th><th>Эталон</th><th>Новое5</th><th>Дельта</th></tr></thead>
<tbody>
<tr><td>Строк</td><td class="num">{n3.fmt_int(pf.get("rows_old") or 0)}</td><td class="num">{n3.fmt_int(pf.get("rows_new") or 0)}</td><td class="num">{n3.fmt_int((pf.get("rows_new") or 0)-(pf.get("rows_old") or 0))}</td></tr>
<tr><td>Документов</td><td class="num">{n3.fmt_int(pf.get("docs_old") or 0)}</td><td class="num">{n3.fmt_int(pf.get("docs_new") or 0)}</td><td></td></tr>
<tr><td>Денежных расхождений документов</td><td colspan="3">{n3.fmt_int((pf.get("compare") or {}).get("diff_sums") or 0)}</td></tr>
<tr><td>Строк только в эталоне / только в новом</td><td class="num">{n3.fmt_int((pf.get("line_bag") or {}).get("only_old_n") or 0)}</td><td class="num">{n3.fmt_int((pf.get("line_bag") or {}).get("only_new_n") or 0)}</td><td></td></tr>
</tbody></table>
<table><thead><tr><th>Поле</th><th>Эталон</th><th>Новое5</th><th>Дельта</th></tr></thead><tbody>{pf_totals_html}</tbody></table>
'''}

<h2>3. УК: итог по всем клиентам</h2>
<table>
<thead><tr><th>Показатель</th><th>Эталон</th><th>Новое5</th></tr></thead>
<tbody>
<tr><td>Строк выгрузки</td><td class="num">{n3.fmt_int(uk["rows_old"])}</td><td class="num">{n3.fmt_int(uk["rows_new"])}</td></tr>
<tr><td>Документов</td><td class="num">{n3.fmt_int(uk["docs_old"])}</td><td class="num">{n3.fmt_int(uk["docs_new"])}</td></tr>
<tr><td>Пустых документов</td><td class="num">{n3.fmt_int(uk["empty_old_n"])}</td><td class="num">{n3.fmt_int(uk["empty_new_n"])}</td></tr>
<tr class="{"ok" if cmpu["diff_sums"]==0 else "bad"}"><td>Документов с денежным расхождением</td><td colspan="2" class="num">{n3.fmt_int(cmpu["diff_sums"])}</td></tr>
<tr class="{"ok" if uk["money_other_n"]==0 else "bad"}"><td>из них не Платонов</td><td colspan="2" class="num">{n3.fmt_int(uk["money_other_n"])}</td></tr>
<tr class="{"ok" if uk["money_plat_n"]==0 else "warn"}"><td>из них Платонов</td><td colspan="2" class="num">{n3.fmt_int(uk["money_plat_n"])}</td></tr>
<tr><td>Только структура (суммы те же)</td><td colspan="2" class="num">{n3.fmt_int(cmpu.get("diff_structure_only") or 0)}</td></tr>
<tr><td>Только в эталоне / только в новом (номера)</td><td class="num">{n3.fmt_int(cmpu.get("only_old_n") or 0)}</td><td class="num">{n3.fmt_int(cmpu.get("only_new_n") or 0)}</td></tr>
<tr><td>Строки bag только эталон / только новое</td><td class="num">{n3.fmt_int(uk["line_bag"].get("only_old_n") or 0)}</td><td class="num">{n3.fmt_int(uk["line_bag"].get("only_new_n") or 0)}</td></tr>
</tbody>
</table>
<table>
<thead><tr><th>Поле</th><th>Эталон</th><th>Новое5</th><th>Дельта</th></tr></thead>
<tbody>{money_rows_html(uk["totals_old"], uk["totals_new"])}</tbody>
</table>

<h2>4. Платонов (УК {escape(PLAT_NUM)})</h2>
<table>
<thead><tr><th>Поле</th><th>Эталон</th><th>Новое5</th><th>Дельта</th></tr></thead>
<tbody>{plat_sum_html or "<tr><td colspan='4'>Документ не найден</td></tr>"}</tbody>
</table>
{plat_lines}

<h2>5. Другие УК с денежным расхождением</h2>
<table>
<thead><tr><th>Номер</th><th>Ссылка</th><th>Дельта</th><th>Строк эталон</th><th>Строк новое</th></tr></thead>
<tbody>{doc_rows(uk.get("money_other") or [])}</tbody>
</table>

<h2>6. Сообщения</h2>
<table>
<thead><tr><th>Тип</th><th>Эталон</th><th>Новое5</th><th>Дельта</th></tr></thead>
<tbody>{"".join(kind_rows)}</tbody>
</table>
<p>Клиентов «невозможно распределить»: эталон {msg["clients_rasp_a"]}, новое5 {msg["clients_rasp_b"]}.</p>
<p>Уникальных строк только в эталоне: {msg["only_a_n"]}, только в новом: {msg["only_b_n"]}.</p>

<h2>7. Блокировки в логе</h2>
{lock_lis}

<footer>Скрипт compare_ndfl_old_vs_new5.py. JSON рядом с этим HTML.</footer>
</div>
</body>
</html>
"""
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    safe_print("HTML written")


def print_summary(r):
    uk = r["uk"]
    cmpu = uk["compare"]
    cmpw = uk["compare_wo_plat"]
    safe_print("==== SUMMARY old vs new5 ====")
    safe_print("pf_identical=" + str(r.get("pf_identical")))
    safe_print("uk_identical=" + str(r.get("uk_identical")))
    safe_print(
        "UK rows old/new="
        + str(uk["rows_old"])
        + "/"
        + str(uk["rows_new"])
        + " docs="
        + str(uk["docs_old"])
        + "/"
        + str(uk["docs_new"])
    )
    safe_print(
        "UK money_diffs="
        + str(cmpu["diff_sums"])
        + " plat="
        + str(uk["money_plat_n"])
        + " other="
        + str(uk["money_other_n"])
        + " structure_only="
        + str(cmpu.get("diff_structure_only"))
        + " only_old="
        + str(cmpu.get("only_old_n"))
        + " only_new="
        + str(cmpu.get("only_new_n"))
    )
    safe_print(
        "UK without Platonov money_diffs="
        + str(cmpw["diff_sums"])
        + " structure="
        + str(cmpw.get("diff_structure_only"))
    )
    bag = uk["line_bag"]
    safe_print(
        "UK bag only_old/only_new=" + str(bag.get("only_old_n")) + "/" + str(bag.get("only_new_n"))
    )
    if uk["money_plat"]:
        for d in uk["money_plat"]:
            safe_print("PLAT delta " + d["num"] + " " + str(d.get("delta")))
    else:
        safe_print("PLAT money: MATCH")
    if uk["money_other"]:
        safe_print("OTHER money docs: " + str(len(uk["money_other"])))
        for d in uk["money_other"][:30]:
            ref = (d.get("ref") or "")[:80]
            safe_print("  " + d["num"] + " " + ref + " " + str(d.get("delta")))
    else:
        safe_print("OTHER UK money: MATCH")
    pf = r["pf"]
    if pf.get("skipped_full"):
        safe_print("PF: skipped MD5 identical")
    else:
        pfc = pf["compare"]
        safe_print(
            "PF money_diffs="
            + str(pfc["diff_sums"])
            + " bag "
            + str(pf["line_bag"].get("only_old_n"))
            + "/"
            + str(pf["line_bag"].get("only_new_n"))
        )
    plat_pf = r.get("pf_plat") or {}
    if plat_pf.get("bag"):
        safe_print(
            "PF Platonov bag "
            + str(plat_pf["bag"].get("only_old_n"))
            + "/"
            + str(plat_pf["bag"].get("only_new_n"))
        )


def main():
    r = analyze()
    write_html(r)
    print_summary(r)
    safe_print("HTML " + OUT_HTML)
    safe_print("JSON " + OUT_JSON)


if __name__ == "__main__":
    main()
