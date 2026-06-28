#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robust regression compare for Regress2105 (and similar folders).
Compares by business multiset, not row order.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from compare_mxl import extract_hash_cells, parse_rows  # noqa: E402

REG_DIR = SCRIPT_DIR / "Регресс2105"
WIDTH = 33
DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
NUM_RE = re.compile(r"^\d+$")

# Vypiski: business key without row index N (order-independent)
VYPISKI_KEY = ("Data", "BankSchet", "Dogovor", "NomerScheta", "Zagruzhat", "Zagruzhena")

# PP: bank payment identity (stable across export)
PP_CORE = (
    "Дата",
    "Номер",
    "Сумма",
    "Плательщик счет",
    "Получатель счет",
    "Назначение платежа",
)

# PP: optional link to vypiska (may differ after reorder - report separately)
PP_LINK = "Ключ выписки"


def vypiski_business_key(row: dict) -> tuple:
    return (
        (row.get("Data") or "")[:10],
        row.get("BankSchet", ""),
        row.get("Dogovor", ""),
        row.get("NomerScheta", ""),
        row.get("Zagruzhat", ""),
        row.get("Zagruzhena", ""),
    )


def vypiski_alt_key(row: dict) -> tuple:
    """Without account number field (often empty in ERS rows)."""
    return (
        (row.get("Data") or "")[:10],
        row.get("BankSchet", ""),
        row.get("Dogovor", "") or "(empty)",
    )


ACCOUNT_RE = re.compile(r"^\d{15,25}$")


def is_valid_pp_chunk(chunk: list[str]) -> bool:
    if len(chunk) < 8:
        return False
    if not chunk[0].isdigit():
        return False
    if chunk[1] != "Платежное поручение":
        return False
    if not DATE_RE.match(chunk[2].strip()):
        return False
    if not NUM_RE.match(chunk[3].strip()):
        return False
    if not re.match(r"^[\d\s]+([.,]\d+)?$", chunk[4].strip()):
        return False
    if not DATE_RE.match(chunk[5].strip()):
        return False
    payer = chunk[6].strip().replace(" ", "")
    payee = chunk[7].strip().replace(" ", "")
    if not ACCOUNT_RE.match(payer) or not ACCOUNT_RE.match(payee):
        return False
    if len(chunk[8].strip()) < 10:
        return False
    return True


def parse_pp_robust(vals: list[str]) -> tuple[list[str], dict[tuple, dict]]:
    """
    Extract PP rows keyed by (Дата, Номер).
    Uses phase-locked WIDTH grid from first valid PP row to avoid shifted-window duplicates.
    """
    start = next(i for i, v in enumerate(vals) if v == "N" and vals[i + 1] == "Операция")
    columns = vals[start : start + WIDTH]
    by_key: dict[tuple, dict] = {}

    phase = None
    for i in range(start + WIDTH, len(vals) - WIDTH):
        chunk = vals[i : i + WIDTH]
        if not is_valid_pp_chunk(chunk):
            continue
        if phase is None:
            phase = i % WIDTH
        if i % WIDTH != phase:
            continue
        row = dict(zip(columns, chunk))
        key = (row.get("Дата", "").strip(), row.get("Номер", "").strip())
        by_key[key] = row

    return columns, by_key


def pp_core_key(row: dict) -> tuple:
    return tuple(row.get(c, "").strip() for c in PP_CORE)


def compare_multiset(cnt_bylo: Counter, cnt_stalo: Counter) -> dict:
    diff = (cnt_bylo - cnt_stalo) + (cnt_stalo - cnt_bylo)
    return {
        "identical": len(diff) == 0,
        "diff_types": len(diff),
        "only_bylo": sum((cnt_bylo - cnt_stalo).values()),
        "only_stalo": sum((cnt_stalo - cnt_bylo).values()),
        "shared_types": len(cnt_bylo & cnt_stalo),
        "top_diffs": [
            {"delta": delta, "key": key}
            for key, delta in sorted(diff.items(), key=lambda x: -abs(x[1]))[:20]
        ],
    }


def compare_vypiski(path_bylo: Path, path_stalo: Path) -> dict:
    rows_b = parse_rows(extract_hash_cells(path_bylo))
    rows_s = parse_rows(extract_hash_cells(path_stalo))

    biz_b = Counter(vypiski_business_key(r) for r in rows_b)
    biz_s = Counter(vypiski_business_key(r) for r in rows_s)
    alt_b = Counter(vypiski_alt_key(r) for r in rows_b)
    alt_s = Counter(vypiski_alt_key(r) for r in rows_s)

    # balances multiset (optional detail)
    bal_key = lambda r: (
        (r.get("Data") or "")[:10],
        r.get("BankSchet", ""),
        r.get("Dogovor", "") or "(empty)",
        tuple(r.get("balances", [])),
    )
    bal_b = Counter(bal_key(r) for r in rows_b)
    bal_s = Counter(bal_key(r) for r in rows_s)

    return {
        "rows": (len(rows_b), len(rows_s)),
        "business": compare_multiset(biz_b, biz_s),
        "alt_dogovor": compare_multiset(alt_b, alt_s),
        "balances": compare_multiset(bal_b, bal_s),
    }


def compare_pp(path_bylo: Path, path_stalo: Path) -> dict:
    _, map_b = parse_pp_robust(extract_hash_cells(path_bylo))
    _, map_s = parse_pp_robust(extract_hash_cells(path_stalo))

    keys_b = set(map_b)
    keys_s = set(map_s)
    only_keys_b = keys_b - keys_s
    only_keys_s = keys_s - keys_b
    shared = keys_b & keys_s

    core_b = Counter(pp_core_key(map_b[k]) for k in keys_b)
    core_s = Counter(pp_core_key(map_s[k]) for k in keys_s)
    core_cmp = compare_multiset(core_b, core_s)

    # same (date, number) but different core fields
    core_field_diffs = []
    link_diffs = []
    loaded_diffs = []
    for key in sorted(shared):
        rb, rs = map_b[key], map_s[key]
        if pp_core_key(rb) != pp_core_key(rs):
            core_field_diffs.append(
                {
                    "key": key,
                    "bylo": {c: rb.get(c, "")[:100] for c in PP_CORE},
                    "stalo": {c: rs.get(c, "")[:100] for c in PP_CORE},
                }
            )
        if rb.get(PP_LINK, "").strip() != rs.get(PP_LINK, "").strip():
            link_diffs.append(
                {
                    "key": key,
                    "bylo": rb.get(PP_LINK, "")[:120],
                    "stalo": rs.get(PP_LINK, "")[:120],
                }
            )
        if rb.get("Загружен", "").strip() != rs.get("Загружен", "").strip():
            loaded_diffs.append(
                {
                    "key": key,
                    "bylo": rb.get("Загружен", ""),
                    "stalo": rs.get("Загружен", ""),
                }
            )

    return {
        "payments_by_dn": (len(map_b), len(map_s)),
        "only_bylo_keys": sorted(only_keys_b)[:30],
        "only_stalo_keys": sorted(only_keys_s)[:30],
        "only_bylo_count": len(only_keys_b),
        "only_stalo_count": len(only_keys_s),
        "shared_count": len(shared),
        "core_multiset": core_cmp,
        "same_dn_core_diff_count": len(core_field_diffs),
        "same_dn_core_diff_samples": core_field_diffs[:10],
        "same_dn_link_diff_count": len(link_diffs),
        "same_dn_link_diff_samples": link_diffs[:10],
        "same_dn_loaded_diff_count": len(loaded_diffs),
        "probe_485038": {
            "in_bylo": ("21.05.2026", "485038") in map_b,
            "in_stalo": ("21.05.2026", "485038") in map_s,
            "core_equal": (
                pp_core_key(map_b[("21.05.2026", "485038")])
                == pp_core_key(map_s[("21.05.2026", "485038")])
                if ("21.05.2026", "485038") in map_b and ("21.05.2026", "485038") in map_s
                else None
            ),
            "link_equal": (
                map_b[("21.05.2026", "485038")].get(PP_LINK)
                == map_s[("21.05.2026", "485038")].get(PP_LINK)
                if ("21.05.2026", "485038") in map_b and ("21.05.2026", "485038") in map_s
                else None
            ),
        },
    }


def safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def main() -> int:
    v_bylo = REG_DIR / "2105_2105_ВЫПИСКИ_было.mxl"
    v_stalo = REG_DIR / "2105_2105_ВЫПИСКИ_стало.mxl"
    p_bylo = REG_DIR / "2105_2105_ПП_было.mxl"
    p_stalo = REG_DIR / "2105_2105_ПП_стало.mxl"

    report = {
        "vypiski": compare_vypiski(v_bylo, v_stalo),
        "pp": compare_pp(p_bylo, p_stalo),
    }
    out = REG_DIR / "2105_robust_compare_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    safe_print("=== REGRESS2105 ROBUST COMPARE (no row order) ===")
    safe_print("")
    safe_print("1. VYPISKI")
    v = report["vypiski"]
    safe_print(f"   Rows: {v['rows'][0]} / {v['rows'][1]}")
    b = v["business"]
    safe_print(
        f"   Business multiset (Data,Bank,Dogovor,Schet,Zagruzhat,Zagruzhena): "
        f"identical={b['identical']} diff_types={b['diff_types']} "
        f"only_b={b['only_bylo']} only_s={b['only_stalo']}"
    )
    a = v["alt_dogovor"]
    safe_print(
        f"   Alt multiset (Data,Bank,Dogovor): "
        f"identical={a['identical']} diff_types={a['diff_types']}"
    )
    bal = v["balances"]
    safe_print(
        f"   Balances multiset: identical={bal['identical']} diff_types={bal['diff_types']}"
    )
    if a["top_diffs"]:
        safe_print("   Alt diffs:")
        for d in a["top_diffs"][:10]:
            safe_print(f"     delta={d['delta']:+d} {d['key']}")
    safe_print("")

    safe_print("2. PP (key = Date + Number, deduped robust parse)")
    p = report["pp"]
    safe_print(f"   Payments (Date,Number): {p['payments_by_dn'][0]} / {p['payments_by_dn'][1]}")
    safe_print(f"   Only BYLO keys: {p['only_bylo_count']}")
    safe_print(f"   Only STALO keys: {p['only_stalo_count']}")
    safe_print(f"   Shared keys: {p['shared_count']}")
    c = p["core_multiset"]
    safe_print(
        f"   Core multiset identical: {c['identical']} "
        f"(diff_types={c['diff_types']} only_b={c['only_bylo']} only_s={c['only_stalo']})"
    )
    safe_print(f"   Same (Date,Number) but different core fields: {p['same_dn_core_diff_count']}")
    safe_print(f"   Same (Date,Number) but different Klyuch vypiski: {p['same_dn_link_diff_count']}")
    safe_print(f"   Same (Date,Number) but different Zагружен: {p['same_dn_loaded_diff_count']}")
    safe_print(f"   Probe 485038: {p['probe_485038']}")
    if p["only_bylo_keys"]:
        safe_print(f"   Sample only BYLO: {p['only_bylo_keys'][:8]}")
    if p["only_stalo_keys"]:
        safe_print(f"   Sample only STALO: {p['only_stalo_keys'][:8]}")
    if p["same_dn_core_diff_samples"]:
        safe_print("   Sample same-DN core diffs:")
        for s in p["same_dn_core_diff_samples"][:3]:
            safe_print(f"     {s['key']}")
    safe_print("")
    safe_print(f"Saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
