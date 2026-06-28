#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compare 09.06.2026 RazobratOtmeennye regression: load logs + message window logs.
"""

import json
import re
from collections import Counter
from pathlib import Path

REG = Path(__file__).resolve().parent

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
            current_vyp = {
                "date": m.group(1),
                "du_num": m.group(2),
                "du_name": m.group(3),
                "account": m.group(4),
                "key": (m.group(1), m.group(2), m.group(4)),
            }
            vypiski.append(current_vyp)
            continue
        m = PP_RE.match(line)
        if m:
            pp = {
                "number": m.group(1),
                "date": m.group(2),
                "sum": norm_amount(m.group(3)),
                "payer": m.group(4).strip()[:80],
                "recipient": m.group(5).strip()[:80],
                "purpose": m.group(6).strip()[:120],
                "vypiska": current_vyp["key"] if current_vyp else None,
            }
            pp_list.append(pp)

    pp_core = Counter(
        (p["date"], p["number"], p["sum"], p["purpose"][:80]) for p in pp_list
    )
    vyp_keys = Counter(v["key"] for v in vypiski)

    return {
        "vypiski_count": len(vypiski),
        "vypiski_unique": len(vyp_keys),
        "pp_count": len(pp_list),
        "pp_core_types": len(pp_core),
        "vypiski_keys": vyp_keys,
        "pp_core": pp_core,
        "vypiski": vypiski,
        "pp_list": pp_list,
    }


def parse_messages(text: str) -> dict:
    rules = Counter()
    docs = Counter()
    clients_success = []
    clients_discrep = []
    warnings = Counter()

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = RULE_RE.search(line)
        if m:
            rules[(m.group(1), m.group(2).strip())] += 1
            continue
        m = DOC_RE.search(line)
        if m:
            docs[(m.group(1), m.group(2), m.group(3))] += 1
            continue
        m = CLIENT_RE.search(line)
        if m and DISCREP_RE.search(line):
            clients_discrep.append(m.group(1).strip())
            continue
        m = SUCCESS_RE.search(line)
        if m:
            clients_success.append(m.group(1).strip())
            continue
        if "Не найдено платежное поручение" in line:
            warnings["Не найдено платежное поручение"] += 1
        elif "Не найден документ задолженности" in line:
            warnings["Не найден документ задолженности"] += 1
        elif "Пытаюсь создать, валюта по умолчанию" in line:
            warnings["Создание счета RUB по умолчанию"] += 1
        elif line.startswith("Начисление"):
            warnings["Начисление (задолженность/вознаграждение)"] += 1
        elif "Ошибка" in line or "ошибк" in line.lower():
            warnings[f"ERROR: {line[:100]}"] += 1

    return {
        "rules": rules,
        "docs": docs,
        "clients_success": clients_success,
        "clients_discrep": clients_discrep,
        "warnings": warnings,
        "rules_total": sum(rules.values()),
        "docs_total": sum(docs.values()),
        "client_blocks": len(clients_success) + len(clients_discrep),
    }


def compare_counter(a: Counter, b: Counter) -> dict:
    diff = (a - b) + (b - a)
    return {
        "identical": len(diff) == 0,
        "diff_types": len(diff),
        "only_a": sum((a - b).values()),
        "only_b": sum((b - a).values()),
        "top_diffs": [
            {"key": k, "delta_a": (a - b).get(k, 0), "delta_b": (b - a).get(k, 0)}
            for k in sorted(diff, key=lambda x: -abs(diff[x]))[:20]
        ],
    }


def compare_multiset(ca: Counter, cb: Counter) -> dict:
    return compare_counter(ca, cb)


def main() -> int:
    paths = {
        "log_bylo": REG / "ЛогЗагрузкиВыписок_0906_было.txt",
        "log_stalo": REG / "ЛогЗагрузкиВыписок_0906_стало.txt",
        "msg_bylo": REG / "СообщенияЗагрузкиВыписок_0906_было.txt",
        "msg_stalo": REG / "СообщенияЗагрузкиВыписок_0906_стало.txt",
    }

    log_b = parse_load_log(read_text(paths["log_bylo"]))
    log_s = parse_load_log(read_text(paths["log_stalo"]))
    msg_b = parse_messages(read_text(paths["msg_bylo"]))
    msg_s = parse_messages(read_text(paths["msg_stalo"]))

    # vypiski by DU number multiset
    du_b = Counter(v["du_num"] for v in log_b["vypiski"])
    du_s = Counter(v["du_num"] for v in log_s["vypiski"])

    report = {
        "date": "09.06.2026",
        "command": "РазобратьОтмеченные",
        "timing": {
            "bylo_min": 23,
            "stalo_min": 10,
            "speedup": round(23 / 10, 2),
        },
        "load_log": {
            "bylo": {k: log_b[k] for k in ("vypiski_count", "vypiski_unique", "pp_count", "pp_core_types")},
            "stalo": {k: log_s[k] for k in ("vypiski_count", "vypiski_unique", "pp_count", "pp_core_types")},
            "vypiski_du": compare_multiset(du_b, du_s),
            "pp_core": compare_multiset(log_b["pp_core"], log_s["pp_core"]),
        },
        "messages": {
            "bylo": {
                "rules_total": msg_b["rules_total"],
                "docs_total": msg_b["docs_total"],
                "client_success": len(msg_b["clients_success"]),
                "client_discrep": len(msg_b["clients_discrep"]),
                "warnings": dict(msg_b["warnings"]),
            },
            "stalo": {
                "rules_total": msg_s["rules_total"],
                "docs_total": msg_s["docs_total"],
                "client_success": len(msg_s["clients_success"]),
                "client_discrep": len(msg_s["clients_discrep"]),
                "warnings": dict(msg_s["warnings"]),
            },
            "rules": compare_multiset(msg_b["rules"], msg_s["rules"]),
            "docs": compare_multiset(msg_b["docs"], msg_s["docs"]),
            "warnings": compare_multiset(msg_b["warnings"], msg_s["warnings"]),
        },
    }

    # docs only in one side
    only_docs_b = set(msg_b["docs"]) - set(msg_s["docs"])
    only_docs_s = set(msg_s["docs"]) - set(msg_b["docs"])
    report["messages"]["only_docs_bylo"] = [list(x) for x in sorted(only_docs_b)[:15]]
    report["messages"]["only_docs_stalo"] = [list(x) for x in sorted(only_docs_s)[:15]]

    # PP only in one side
    only_pp_b = log_b["pp_core"] - log_s["pp_core"]
    only_pp_s = log_s["pp_core"] - log_b["pp_core"]
    report["load_log"]["only_pp_bylo"] = [{"key": k, "count": v} for k, v in only_pp_b.most_common(10)]
    report["load_log"]["only_pp_stalo"] = [{"key": k, "count": v} for k, v in only_pp_s.most_common(10)]

    # rule diffs detail
    rule_diff = msg_b["rules"] - msg_s["rules"]
    rule_diff_s = msg_s["rules"] - msg_b["rules"]
    report["messages"]["rules_only_bylo"] = [
        {"rule": k, "count": v} for k, v in rule_diff.most_common(15)
    ]
    report["messages"]["rules_only_stalo"] = [
        {"rule": k, "count": v} for k, v in rule_diff_s.most_common(15)
    ]

    out = REG / "0906_razobrat_regression_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def sp(t):
        try:
            print(t)
        except UnicodeEncodeError:
            print(t.encode("ascii", errors="replace").decode("ascii"))

    sp("=== 09.06 RAZOBRAT REGRESSION ===")
    sp(f"Time: bylo 23 min -> stalo 10 min (x{report['timing']['speedup']})")
    sp("")
    sp("LOAD LOG:")
    sp(f"  Vypiski: {log_b['vypiski_count']}/{log_s['vypiski_count']} unique DU: {log_b['vypiski_unique']}/{log_s['vypiski_unique']}")
    sp(f"  PP: {log_b['pp_count']}/{log_s['pp_count']} core types: {log_b['pp_core_types']}/{log_s['pp_core_types']}")
    sp(f"  PP core identical: {report['load_log']['pp_core']['identical']}")
    sp(f"  DU multiset identical: {report['load_log']['vypiski_du']['identical']}")
    if report["load_log"]["only_pp_bylo"]:
        sp(f"  Only BYLO PP: {len(only_pp_b)} types")
    if report["load_log"]["only_pp_stalo"]:
        sp(f"  Only STALO PP: {len(only_pp_s)} types")
    sp("")
    sp("MESSAGES:")
    sp(f"  Docs rewritten: {msg_b['docs_total']}/{msg_s['docs_total']} identical={report['messages']['docs']['identical']}")
    sp(f"  Rules fired: {msg_b['rules_total']}/{msg_s['rules_total']} identical={report['messages']['rules']['identical']}")
    sp(f"  Client success: {len(msg_b['clients_success'])}/{len(msg_s['clients_success'])}")
    sp(f"  Client discrep: {len(msg_b['clients_discrep'])}/{len(msg_s['clients_discrep'])}")
    sp(f"  Warnings BYLO: {dict(msg_b['warnings'])}")
    sp(f"  Warnings STALO: {dict(msg_s['warnings'])}")
    if report["messages"]["rules_only_bylo"]:
        sp("  Rules only BYLO (top 5):")
        for r in report["messages"]["rules_only_bylo"][:5]:
            sp(f"    {r}")
    if report["messages"]["rules_only_stalo"]:
        sp("  Rules only STALO (top 5):")
        for r in report["messages"]["rules_only_stalo"][:5]:
            sp(f"    {r}")
    if only_docs_b:
        sp(f"  Docs only BYLO: {len(only_docs_b)}")
        for d in list(only_docs_b)[:3]:
            sp(f"    {d}")
    if only_docs_s:
        sp(f"  Docs only STALO: {len(only_docs_s)}")
        for d in list(only_docs_s)[:3]:
            sp(f"    {d}")
    sp(f"\nSaved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
