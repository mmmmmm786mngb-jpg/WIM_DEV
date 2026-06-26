#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare two MOXCEL (.mxl) regression exports - IMDEV-9096 Запрос1."""

import re
import sys
from collections import Counter
from pathlib import Path

DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}")
ACCOUNT_RE = re.compile(r"^407\d{17}$")
N_RE = re.compile(r"^\d+$")
CONTRACT_RE = re.compile(r"^(ДУ \d+|УК ВТБ)")


def extract_hash_cells(path: Path) -> list[str]:
    text = path.read_bytes().decode("utf-8", errors="replace")
    return re.findall(r'\{"#","((?:[^"\\]|\\.)*)"\}', text)


def is_date(value: str) -> bool:
    return bool(DATE_RE.match(value))


def is_account(value: str) -> bool:
    return bool(ACCOUNT_RE.match(value.replace(" ", "")))


def is_contract(value: str) -> bool:
    return bool(CONTRACT_RE.match(value))


def is_row_start(vals: list[str], i: int) -> bool:
    if i >= len(vals):
        return False
    v = vals[i]
    if N_RE.match(v):
        window = vals[i : min(i + 5, len(vals))]
        if any(is_date(x) for x in window[1:]):
            return True
        if any(x in ("Да", "Нет") for x in window[1:3]):
            return True
    if is_date(v):
        window = vals[i : min(i + 6, len(vals))]
        if any(is_account(x.replace(" ", "")) for x in window):
            return True
    return False


def normalize_row(chunk: list[str]) -> dict:
    row = {
        "N": "",
        "Zagruzhat": "",
        "Zagruzhena": "",
        "Data": "",
        "Dogovor": "",
        "BankSchet": "",
        "NomerScheta": "",
        "balances": [],
        "raw": chunk,
    }

    for v in chunk:
        if not row["N"] and N_RE.match(v) and v not in ("Да", "Нет"):
            row["N"] = v
        elif v in ("Да", "Нет") and not row["Zagruzhat"]:
            row["Zagruzhat"] = v
        elif v in ("Да", "Нет") and row["Zagruzhat"] and not row["Zagruzhena"]:
            row["Zagruzhena"] = v
        elif is_date(v) and not row["Data"]:
            row["Data"] = v
        elif is_contract(v) and not row["Dogovor"]:
            row["Dogovor"] = v
        elif v.startswith("р/с_") and not row["BankSchet"]:
            row["BankSchet"] = v
        elif is_account(v.replace(" ", "")) and not row["NomerScheta"]:
            row["NomerScheta"] = v.replace(" ", "")
        elif re.match(r"^[\d\s,\.]+$", v) and "," in v:
            row["balances"].append(v)

    # Contract may appear after other fields in ERS split rows
    for v in chunk:
        if is_contract(v):
            row["Dogovor"] = v
            break

    for v in chunk:
        if is_date(v):
            row["Data"] = v

    return row


def parse_rows(vals: list[str]) -> list[dict]:
    # skip header block (first 11 labels)
    start = 0
    for i, v in enumerate(vals):
        if v == "N" and i + 4 < len(vals) and vals[i + 4] == "Договор ДУ":
            start = i + 11
            break

    rows = []
    i = start
    while i < len(vals):
        if not is_row_start(vals, i):
            i += 1
            continue

        row_start = i
        i += 1
        while i < len(vals) and not is_row_start(vals, i):
            i += 1

        chunk = vals[row_start:i]
        if len(chunk) >= 3:
            rows.append(normalize_row(chunk))

    return rows


def row_signature(row: dict) -> tuple:
    return (
        row.get("Data", ""),
        row.get("NomerScheta", ""),
        row.get("Dogovor", ""),
        row.get("BankSchet", ""),
        row.get("N", ""),
    )


def main() -> int:
    base = Path(__file__).parent
    path_bylo = base / "Запрос1_было.mxl"
    path_stalo = base / "Запрос1_стало.mxl"

    vals_bylo = extract_hash_cells(path_bylo)
    vals_stalo = extract_hash_cells(path_stalo)

    rows_bylo = parse_rows(vals_bylo)
    rows_stalo = parse_rows(vals_stalo)

    print("=== SRAVNENIE: Zапрос1_было.mxl vs Zапрос1_стало.mxl ===")
    print(f"Razmer fayla: {path_bylo.stat().st_size} bayt (odinakovo)")
    print(f"Strok raspoznano: {len(rows_bylo)} / {len(rows_stalo)}")
    print()

    cnt_b = Counter(row_signature(r) for r in rows_bylo)
    cnt_s = Counter(row_signature(r) for r in rows_stalo)
    diff = (cnt_b - cnt_s) + (cnt_s - cnt_b)

    print(f"Multiset po (Data, NomerScheta, Dogovor, Bank, N): {len(diff)} razlichiy")
    only_b = sum(1 for d in (cnt_b - cnt_s).values() if d > 0)
    only_s = sum(1 for d in (cnt_s - cnt_b).values() if d > 0)
    print(f"  tolko v bylo: {only_b} tipov zapisey")
    print(f"  tolko v stalo: {only_s} tipov zapisey")
    print()

    if diff:
        print("--- Razlichiya (delta, Data, Schet, Dogovor) ---")
        for key, delta in sorted(diff.items(), key=lambda x: -abs(x[1]))[:30]:
            data, schet, dog, bank, n = key
            print(f"  delta={delta:+d} | {data[:19]} | {schet} | {dog[:50]} | N={n}")
        print()

    # Positional compare on same NomerScheta+Data+Bank block for RUR ERS
    target_schet = "40701810000030000413"
    b_block = [r for r in rows_bylo if r.get("NomerScheta") == target_schet]
    s_block = [r for r in rows_stalo if r.get("NomerScheta") == target_schet]

    print(f"--- Blok RUR ERS schet {target_schet} ---")
    print(f"  strok bylo: {len(b_block)}, stalo: {len(s_block)}")
    print("  Poryadok dogovorov BYLO:")
    for r in b_block:
        print(f"    N={r.get('N','?'):>3} | {r.get('Dogovor','')[:45]}")
    print("  Poryadok dogovorov STALO:")
    for r in s_block:
        print(f"    N={r.get('N','?'):>3} | {r.get('Dogovor','')[:45]}")
    print()

    contracts_b = [r.get("Dogovor", "") for r in b_block if r.get("Dogovor")]
    contracts_s = [r.get("Dogovor", "") for r in s_block if r.get("Dogovor")]
    set_b, set_s = set(contracts_b), set(contracts_s)
    print(f"  Mnozhestvo dogovorov: bylo={len(set_b)} stalo={len(set_s)}")
    print(f"  Tolko v bylo: {sorted(set_b - set_s)}")
    print(f"  Tolko v stalo: {sorted(set_s - set_b)}")
    print(f"  Odinakovoe mnozhestvo: {set_b == set_s}")
    print(f"  Odinakovyy poryadok: {contracts_b == contracts_s}")

    # Positional diffs all rows
    pos = 0
    for i, (rb, rs) in enumerate(zip(rows_bylo, rows_stalo)):
        if row_signature(rb) != row_signature(rs):
            pos += 1
    extra = abs(len(rows_bylo) - len(rows_stalo))
    print()
    print(f"Pozitsionnye otlichiya (index 1..min): {pos} iz {min(len(rows_bylo), len(rows_stalo))}")
    print(f"Raznica v chisle strok: {extra}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
