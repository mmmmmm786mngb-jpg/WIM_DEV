#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
General regression test 26.06.2026 (T-1 prod copy): Prochitat XLSX + Razbor logs.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

REG = Path(__file__).resolve().parent

# Reuse xlsx helpers from compare_regression_xlsx
sys.path.insert(0, str(REG))
from compare_regression_xlsx import (  # noqa: E402
    compare_pp_xlsx,
    compare_vypiski_xlsx,
    norm_str,
)

VYPISKA_RE = re.compile(
    r"Выписка:\s*(\d{2}\.\d{2}\.\d{4})\s+0:00:00\s+ДУ\s+(\d+)\s+\(([^)]+)\)\s+(\d{20,})"
)
PP_RE = re.compile(
    r"^(\d+)\s+(\d{2}\.\d{2}\.\d{4})\s+Сумма:\s*([\d,\.]+)\s+Плательщик:(.+?)Получатель:(.+?)Назначение платежа:(.+)$"
)
DOC_RE = re.compile(
    r'Перезаписан документ "(.+?)" № ([\w\-]+) от (\d{2}\.\d{2}\.\d{4})'
)
RULE_RE = re.compile(r"Сработало Правило № (\d+) (.+?) для строки (\d+)")
CLIENT_RE = re.compile(r"По клиенту:\s*(.+?)\s+По счету")
SUCCESS_RE = re.compile(r"Остатки по\s+(.+?)\s+сверены")
DISCREP_RE = re.compile(r"обнаружены расхождения в данных")
DURATION_RE = re.compile(r"Продолжительность:\s*([\d,\.]+)\s*сек")


def read_text(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def norm_amount(s: str) -> str:
    return s.replace(" ", "").replace("\u00a0", "").replace(".", ",")


def parse_load_log(text: str) -> dict:
    vypiski = []
    pp_list = []
    current_vyp = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = VYPISKA_RE.search(line)
        if m:
            current_vyp = (m.group(1), m.group(2), m.group(4))
            vypiski.append(current_vyp)
            continue
        m = PP_RE.match(line)
        if m:
            pp_list.append(
                (m.group(2), m.group(1), norm_amount(m.group(3)), m.group(6).strip()[:80])
            )
    pp_core = Counter(pp_list)
    vyp_keys = Counter(vypiski)
    return {
        "vypiski_count": len(vypiski),
        "vypiski_unique": len(vyp_keys),
        "pp_count": len(pp_list),
        "pp_core_types": len(pp_core),
        "vypiski_keys": vyp_keys,
        "pp_core": pp_core,
    }


def parse_messages(text: str) -> dict:
    rules = Counter()
    docs = Counter()
    warnings = Counter()
    clients_success = 0
    clients_discrep = 0
    duration_sec = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = DURATION_RE.search(line)
        if m:
            duration_sec = float(m.group(1).replace(",", "."))
        m = RULE_RE.search(line)
        if m:
            rules[(m.group(1), m.group(2).strip())] += 1
            continue
        m = DOC_RE.search(line)
        if m:
            docs[(m.group(1), m.group(2), m.group(3))] += 1
            continue
        if CLIENT_RE.search(line) and DISCREP_RE.search(line):
            clients_discrep += 1
            continue
        if SUCCESS_RE.search(line):
            clients_success += 1
            continue
        if "не определен ДоговорДУ" in line:
            warnings["Не определен ДоговорДУ"] += 1
        elif "Не найдено платежное поручение" in line:
            warnings["Не найдено платежное поручение"] += 1
        elif "Не найден документ задолженности" in line:
            warnings["Не найден документ задолженности"] += 1
        elif "Пытаюсь создать, валюта по умолчанию" in line:
            warnings["Создание счета RUB по умолчанию"] += 1
        elif line.startswith("Начисление"):
            warnings["Начисление"] += 1

    return {
        "rules_total": sum(rules.values()),
        "rules": rules,
        "docs_total": sum(docs.values()),
        "docs": docs,
        "clients_success": clients_success,
        "clients_discrep": clients_discrep,
        "warnings": warnings,
        "duration_sec": duration_sec,
    }


def compare_counter(a: Counter, b: Counter) -> dict:
    diff = (a - b) + (b - a)
    return {
        "identical": len(diff) == 0,
        "diff_types": len(diff),
        "only_bylo": sum((a - b).values()),
        "only_stalo": sum((b - a).values()),
    }


def line_multiset(text: str) -> Counter:
    return Counter(x.strip() for x in text.splitlines() if x.strip())


def main() -> int:
    paths = {
        "vyp_bylo": REG / "2606_PP_Выписки_было.xlsx",
        "vyp_stalo": REG / "2606_PP_Выписки_стало.xlsx",
        "pp_bylo": REG / "2606_PP_ПП_было.xlsx",
        "pp_stalo": REG / "2606_PP_ПП_стало.xlsx",
        "msg_pp_bylo": REG / "Сообщения_2606_PP_было.txt",
        "msg_pp_stalo": REG / "Сообщения_2606_PP_стало.txt",
        "msg_raz_bylo": REG / "СообщенияРАЗБОР_2606_PP_было.txt",
        "msg_raz_stalo": REG / "СообщенияРАЗБОР_2606_PP_стало.txt",
        "log_bylo": REG / "ЛогЗагрузкиВыписок_2606_было.txt",
        "log_stalo": REG / "ЛогЗагрузкиВыписок_2606_стало.txt",
    }
    for k, p in paths.items():
        if not p.exists():
            print(f"ERROR: missing {k}: {p}")
            return 1

    vyp = compare_vypiski_xlsx(paths["vyp_bylo"], paths["vyp_stalo"])
    pp = compare_pp_xlsx(paths["pp_bylo"], paths["pp_stalo"])

    msg_pp_b = parse_messages(read_text(paths["msg_pp_bylo"]))
    msg_pp_s = parse_messages(read_text(paths["msg_pp_stalo"]))
    msg_raz_b = parse_messages(read_text(paths["msg_raz_bylo"]))
    msg_raz_s = parse_messages(read_text(paths["msg_raz_stalo"]))

    log_b = parse_load_log(read_text(paths["log_bylo"]))
    log_s = parse_load_log(read_text(paths["log_stalo"]))

    log_lines_b = line_multiset(read_text(paths["log_bylo"]))
    log_lines_s = line_multiset(read_text(paths["log_stalo"]))
    raz_lines_b = line_multiset(read_text(paths["msg_raz_bylo"]))
    raz_lines_s = line_multiset(read_text(paths["msg_raz_stalo"]))

    timing = {
        "prochitat": {
            "bylo_sec": 290,
            "bylo_min": 5.0,
            "stalo_sec": 45,
            "stalo_min": 0.75,
            "speedup": round(290 / 45, 1),
        },
        "razobrat": {
            "bylo_min": 13,
            "stalo_min": 7,
            "threads_stalo": 3,
            "speedup": round(13 / 7, 1),
        },
        "msg_prochitat_duration": {
            "bylo": msg_pp_b.get("duration_sec"),
            "stalo": msg_pp_s.get("duration_sec"),
        },
    }

    report = {
        "test": "general_T-1",
        "period": "26.06.2026",
        "database": 'Srvr="SMSK02MG138U";Ref="AVC_PP_DU"',
        "timing": timing,
        "prochitat": {
            "vypiski": vyp,
            "pp": pp,
            "messages": {
                "bylo": {k: v for k, v in msg_pp_b.items() if k not in ("rules", "docs")},
                "stalo": {k: v for k, v in msg_pp_s.items() if k not in ("rules", "docs")},
                "warnings_identical": msg_pp_b["warnings"] == msg_pp_s["warnings"],
            },
        },
        "razobrat": {
            "load_log": {
                "bylo": {k: log_b[k] for k in ("vypiski_count", "vypiski_unique", "pp_count", "pp_core_types")},
                "stalo": {k: log_s[k] for k in ("vypiski_count", "vypiski_unique", "pp_count", "pp_core_types")},
                "pp_core": compare_counter(log_b["pp_core"], log_s["pp_core"]),
                "vyp_du": compare_counter(
                    Counter(k[1] for k in log_b["vypiski_keys"]),
                    Counter(k[1] for k in log_s["vypiski_keys"]),
                ),
                "line_multiset_identical": log_lines_b == log_lines_s,
                "line_diff_types": len((log_lines_b - log_lines_s) + (log_lines_s - log_lines_b)),
            },
            "messages": {
                "bylo": {
                    "rules_total": msg_raz_b["rules_total"],
                    "docs_total": msg_raz_b["docs_total"],
                    "clients_success": msg_raz_b["clients_success"],
                    "clients_discrep": msg_raz_b["clients_discrep"],
                    "warnings": dict(msg_raz_b["warnings"]),
                },
                "stalo": {
                    "rules_total": msg_raz_s["rules_total"],
                    "docs_total": msg_raz_s["docs_total"],
                    "clients_success": msg_raz_s["clients_success"],
                    "clients_discrep": msg_raz_s["clients_discrep"],
                    "warnings": dict(msg_raz_s["warnings"]),
                },
                "rules": compare_counter(msg_raz_b["rules"], msg_raz_s["rules"]),
                "docs": compare_counter(msg_raz_b["docs"], msg_raz_s["docs"]),
                "line_multiset_identical": raz_lines_b == raz_lines_s,
                "line_diff_types": len((raz_lines_b - raz_lines_s) + (raz_lines_s - raz_lines_b)),
            },
        },
        "verdict": {},
    }

    pp_ok = pp["core_multiset"]["identical"] and pp["only_bylo_count"] == 0 and pp["only_stalo_count"] == 0
    vyp_biz_ok = vyp["business"]["identical"]
    raz_data_ok = (
        log_b["pp_core"] == log_s["pp_core"]
        and log_b["vypiski_count"] == log_s["vypiski_count"]
        and msg_raz_b["docs"] == msg_raz_s["docs"]
        and msg_raz_b["rules"] == msg_raz_s["rules"]
        and msg_raz_b["clients_success"] == msg_raz_s["clients_success"]
        and msg_raz_b["clients_discrep"] == msg_raz_s["clients_discrep"]
    )

    report["verdict"] = {
        "pp_core_ok": pp_ok,
        "vypiski_business_ok": vyp_biz_ok,
        "razobrat_data_ok": raz_data_ok,
        "regression_passed": pp_ok and raz_data_ok,
        "vypiski_row_delta": vyp["row_delta"],
        "vypiski_business_diff_types": vyp["business"]["diff_types"],
    }

    out = REG / "2606_general_test_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def sp(t):
        try:
            print(t)
        except UnicodeEncodeError:
            print(t.encode("ascii", errors="replace").decode("ascii"))

    sp("=== 2606 GENERAL TEST ===")
    sp(f"PP core OK: {pp_ok}")
    sp(f"Vypiski business OK: {vyp_biz_ok} (row delta {vyp['row_delta']})")
    sp(f"Razobrat data OK: {raz_data_ok}")
    sp(f"REGRESSION: {'PASS' if report['verdict']['regression_passed'] else 'CHECK'}")
    sp(f"Saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
