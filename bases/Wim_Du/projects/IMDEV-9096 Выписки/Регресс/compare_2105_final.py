#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final robust PP compare: stream parse + lookup by (Date, Number)."""

import json
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REG = SCRIPT_DIR / "Регресс2105"
sys.path.insert(0, str(SCRIPT_DIR))

from compare_mxl import extract_hash_cells, parse_rows  # noqa: E402
from compare_2105_robust import (  # noqa: E402
    compare_vypiski,
    is_valid_pp_chunk,
    pp_core_key,
    PP_CORE,
    PP_LINK,
    vypiski_alt_key,
    vypiski_business_key,
)

WIDTH = 33


def parse_pp_stream(vals: list[str]) -> dict[tuple, dict]:
    start = next(i for i, v in enumerate(vals) if v == "N" and vals[i + 1] == "Операция")
    cols = vals[start : start + WIDTH]
    by_key: dict[tuple, dict] = {}
    i = start + WIDTH
    while i + WIDTH <= len(vals):
        if vals[i].isdigit() and vals[i + 1] == "Платежное поручение":
            chunk = vals[i : i + WIDTH]
            if is_valid_pp_chunk(chunk):
                row = dict(zip(cols, chunk))
                key = (row["Дата"].strip(), row["Номер"].strip())
                by_key[key] = row
            i += WIDTH
        else:
            i += 1
    return by_key


def find_pp_by_number(vals: list[str], date: str, number: str) -> dict | None:
    """Find PP row by scanning raw cells for Nomer, validate PP structure."""
    start = next(i for i, v in enumerate(vals) if v == "N" and vals[i + 1] == "Операция")
    cols = vals[start : start + WIDTH]
    for idx, cell in enumerate(vals):
        if cell != number:
            continue
        for row_start in range(max(0, idx - 5), idx + 1):
            if row_start + WIDTH > len(vals):
                continue
            chunk = vals[row_start : row_start + WIDTH]
            if len(chunk) <= 3:
                continue
            if chunk[3].strip() != number:
                continue
            if not is_valid_pp_chunk(chunk):
                continue
            row = dict(zip(cols, chunk))
            if row.get("Дата", "").strip().startswith(date[:10]):
                return row
    return None


def merge_maps(stream: dict, vals: list[str], other_stream: dict) -> dict:
    """Union stream keys; fill gaps via raw lookup."""
    merged = dict(stream)
    all_keys = set(stream) | set(other_stream)
    for key in all_keys:
        if key in merged and pp_core_key(merged[key]):
            continue
        found = find_pp_by_number(vals, key[0], key[1])
        if found:
            merged[key] = found
    return merged


def compare_pp_final(path_bylo: Path, path_stalo: Path) -> dict:
    vb = extract_hash_cells(path_bylo)
    vs = extract_hash_cells(path_stalo)
    sb = parse_pp_stream(vb)
    ss = parse_pp_stream(vs)
    mb = merge_maps(sb, vb, ss)
    ms = merge_maps(ss, vs, sb)

    keys_b, keys_s = set(mb), set(ms)
    only_b = sorted(keys_b - keys_s)
    only_s = sorted(keys_s - keys_b)
    shared = keys_b & keys_s

    core_diffs = []
    link_diffs = []
    loaded_diffs = []
    for key in sorted(shared):
        rb, rs = mb[key], ms[key]
        if pp_core_key(rb) != pp_core_key(rs):
            core_diffs.append({"key": list(key), "bylo": {c: rb.get(c, "")[:80] for c in PP_CORE}, "stalo": {c: rs.get(c, "")[:80] for c in PP_CORE}})
        lb, ls = rb.get(PP_LINK, "").strip(), rs.get(PP_LINK, "").strip()
        if lb != ls and lb not in ("Да", "Нет", "833", "834") and ls not in ("Да", "Нет", "833", "834"):
            # ignore obvious column-shift garbage (short numeric)
            if len(lb) > 10 or len(ls) > 10:
                link_diffs.append({"key": list(key), "bylo": lb[:120], "stalo": ls[:120]})
        elif lb != ls and (len(lb) > 10 or len(ls) > 10):
            link_diffs.append({"key": list(key), "bylo": lb[:120], "stalo": ls[:120]})
        if rb.get("Загружен", "").strip() != rs.get("Загружен", "").strip():
            zb, zs = rb.get("Загружен", "").strip(), rs.get("Загружен", "").strip()
            # ignore if looks like shifted column (contains comma sum pattern in wrong field)
            if re.match(r"^(Да|Нет)$", zb) or re.match(r"^(Да|Нет)$", zs):
                loaded_diffs.append({"key": list(key), "bylo": zb, "stalo": zs})

    probe = ("21.05.2026", "485038")
    pb = find_pp_by_number(vb, *probe) or mb.get(probe)
    ps = find_pp_by_number(vs, *probe) or ms.get(probe)

    return {
        "stream_count": (len(sb), len(ss)),
        "merged_count": (len(mb), len(ms)),
        "only_bylo_count": len(only_b),
        "only_stalo_count": len(only_s),
        "only_bylo": only_b[:20],
        "only_stalo": only_s[:20],
        "shared_count": len(shared),
        "core_diff_count": len(core_diffs),
        "core_diff_samples": core_diffs[:10],
        "link_diff_count": len(link_diffs),
        "link_diff_samples": link_diffs[:10],
        "loaded_diff_count": len(loaded_diffs),
        "loaded_diff_samples": loaded_diffs[:10],
        "probe_485038": {
            "in_bylo": pb is not None,
            "in_stalo": ps is not None,
            "core_equal": pp_core_key(pb) == pp_core_key(ps) if pb and ps else None,
            "link_bylo": (pb or {}).get(PP_LINK, "")[:80],
            "link_stalo": (ps or {}).get(PP_LINK, "")[:80],
        },
    }


def main() -> int:
    v = compare_vypiski(REG / "2105_2105_ВЫПИСКИ_было.mxl", REG / "2105_2105_ВЫПИСКИ_стало.mxl")
    p = compare_pp_final(REG / "2105_2105_ПП_было.mxl", REG / "2105_2105_ПП_стало.mxl")
    report = {"vypiski": v, "pp": p}
    out = REG / "2105_robust_compare_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== VYPISKI (multiset, no order) ===")
    print(f"rows {v['rows']}")
    print(f"business identical: {v['business']['identical']}")
    print(f"alt (Data,Bank,Dogovor) identical: {v['alt_dogovor']['identical']}")
    print(f"balances identical: {v['balances']['identical']}")
    print()
    print("=== PP (Date+Number, stream+lookup) ===")
    print(f"stream parsed: {p['stream_count']}, merged: {p['merged_count']}")
    print(f"only BYLO: {p['only_bylo_count']}, only STALO: {p['only_stalo_count']}, shared: {p['shared_count']}")
    print(f"core field diffs (same DN): {p['core_diff_count']}")
    print(f"link diffs (real): {p['link_diff_count']}")
    print(f"Zagruzhen Da/Net diffs: {p['loaded_diff_count']}")
    print(f"485038: {p['probe_485038']}")
    if p["only_bylo"]:
        print("only BYLO sample:", p["only_bylo"][:5])
    if p["only_stalo"]:
        print("only STALO sample:", p["only_stalo"][:5])
    if p["core_diff_samples"]:
        print("core diff sample:", p["core_diff_samples"][0])
    if p["link_diff_samples"]:
        print("link diff sample:", p["link_diff_samples"][0])
    print("saved", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
