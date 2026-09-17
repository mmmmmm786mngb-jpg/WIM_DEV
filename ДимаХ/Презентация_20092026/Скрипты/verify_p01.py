#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка качества разбора датасета Презентации 01.
Печатает построчную сверку смет Аванкор с расчетными значениями в файл UTF-8.
"""

import json
import os
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(SCRIPTS, "p01_dataset.json")
OUT = os.path.join(SCRIPTS, "verify_p01.txt")


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def main():
    with open(DATA, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    lines = []
    s = payload["summary"]
    lines.append("SUMMARY")
    for k, v in s.items():
        if k != "timesheet_files":
            lines.append("  %-28s %s" % (k, v))
    lines.append("")
    lines.append("TIMESHEET FILES")
    for f in s["timesheet_files"]:
        lines.append("  %-28s rows=%-4d hours=%s" % (f["file"], f["rows"], f["hours"]))
    lines.append("")

    lines.append("=" * 130)
    lines.append("PAID TASKS (paid=yes)")
    lines.append("=" * 130)
    paid = [t for t in payload["tasks"] if t["paid"] == "yes"]
    paid.sort(key=lambda t: -t["saving"])
    for t in paid:
        lines.append("-" * 130)
        lines.append("%s | %s" % (t["key"], t["summary"][:100]))
        lines.append("  component=%s | dept=%s | status=%s | src=%s" % (
            t["component"], t["department"], t["status"], t["hours_source"]))
        lines.append("  EXT RAW: %s" % t["ext_estimate_raw"][:200])
        lines.append("  parsed: norm_hours=%s cost=%s rate=%s" % (
            t["avancor_norm_hours"], t["avancor_cost"], t["rate_used"]))
        lines.append("  hours: ts=%s jira=%s our=%s (entries=%s)" % (
            t["ts_hours"], t["jira_hours"], t["our_hours"], t["ts_entries"]))
        lines.append("  cost: fact=%s hypo=%s (hypo_hours=%s) saving=%s" % (
            t["fact_cost"], t["hypo_cost"], t["hypo_hours"], t["saving"]))
        lines.append("  dates: created=%s resolved=%s" % (t["created_iso"], t["resolved_iso"]))

    lines.append("")
    lines.append("=" * 130)
    lines.append("NOT PAID (paid=no) - для контекста")
    lines.append("=" * 130)
    for t in payload["tasks"]:
        if t["paid"] != "yes":
            lines.append("%-14s our_hours=%-7s ext=%s" % (
                t["key"], t["our_hours"], (t["ext_estimate_raw"] or "-")[:70]))

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    safe_print("OK verify written: %d lines" % len(lines))


if __name__ == "__main__":
    sys.exit(main())
