#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Доп. разведка: статусы, оценки Jira vs факт, пересечения с Аванкор по ссылкам.
"""

import io
import os
import re
import sys
import warnings
from collections import Counter, defaultdict
from datetime import datetime

import pandas as pd

warnings.filterwarnings("ignore")

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(SCRIPTS)
OUT = os.path.join(SCRIPTS, "probe_p02b.txt")
INTERNAL = os.path.join(BASE, "внутренние задачи VTB Capital - JIRA 2026-09-17T13_23_36+0300.xls")
AVANCOR = os.path.join(BASE, "задачиАванкору VTB Capital - JIRA 2026-09-17T13_22_34+0300.xls")
TS_DIR = os.path.join(BASE, "Reprot Time _Время задач")
CUTOFF = datetime(2025, 11, 1)


def read_tables(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return pd.read_html(io.StringIO(fh.read()))


def parse_jira_date(text):
    if not text or str(text).lower() == "nan":
        return None
    match = re.match(r"(\d{2})/([A-Za-z]{3})/(\d{2})", str(text))
    if not match:
        return None
    try:
        return datetime.strptime("%s/%s/%s" % match.groups(), "%d/%b/%y")
    except ValueError:
        return None


def load_timesheets():
    per_task = defaultdict(float)
    for name in sorted(os.listdir(TS_DIR)):
        if not name.lower().endswith(".xls"):
            continue
        df = read_tables(os.path.join(TS_DIR, name))[1]
        header = df.iloc[0].tolist()
        body = df.iloc[1:].copy()
        body.columns = [str(h).strip() for h in header]
        body = body[body["Project"].astype(str).str.lower() != "total"]
        for _, r in body.iterrows():
            key = str(r.get("Key") or "").strip()
            if not key or key.lower() == "nan":
                continue
            try:
                hours = float(str(r.get("Time Spent (Hours)")).replace(",", "."))
            except (TypeError, ValueError):
                continue
            per_task[key] += hours
    return per_task


def main():
    lines = []
    df = read_tables(INTERNAL)[1]
    av = read_tables(AVANCOR)[1]
    av_keys = set(av["Key"].astype(str).str.strip())
    ts = load_timesheets()

    done = {"closed", "resolved", "done"}
    skip_res = {"duplicate", "request cancelled"}
    skip_st = {"cancelled"}

    rows = []
    for _, r in df.iterrows():
        key = str(r.get("Key")).strip()
        created = parse_jira_date(r.get("Created"))
        if created is None or created < CUTOFF:
            continue
        if key in av_keys:
            continue
        status = str(r.get("Status") or "").strip()
        resol = str(r.get("Resolution") or "").strip()
        hours = ts.get(key, 0.0)
        if hours <= 0:
            secs = r.get("Time Spent")
            if pd.notna(secs):
                hours = round(float(secs) / 3600.0, 2)
        orig = r.get("Original Estimate")
        orig_h = round(float(orig) / 3600.0, 2) if pd.notna(orig) and float(orig) > 0 else None
        rows.append({
            "key": key,
            "status": status,
            "resolution": resol,
            "hours": hours,
            "orig": orig_h,
            "type": str(r.get("Issue Type") or ""),
            "component": str(r.get("Component/s") or ""),
            "summary": str(r.get("Summary") or "")[:70],
        })

    lines.append("in period not avancor: %d" % len(rows))
    lines.append("STATUS: %s" % dict(Counter(r["status"] for r in rows)))
    lines.append("RESOLUTION: %s" % dict(Counter(r["resolution"] for r in rows)))
    lines.append("TYPE: %s" % dict(Counter(r["type"] for r in rows)))

    completed = [r for r in rows
                 if r["status"].lower() not in skip_st
                 and r["resolution"].lower() not in skip_res
                 and r["hours"] > 0]
    lines.append("")
    lines.append("completed with hours: %d  hours=%.2f" % (
        len(completed), sum(r["hours"] for r in completed)))

    with_est = [r for r in completed if r["orig"]]
    lines.append("with original estimate: %d" % len(with_est))
    if with_est:
        sum_orig = sum(r["orig"] for r in with_est)
        sum_act = sum(r["hours"] for r in with_est)
        lines.append("  orig_h=%.1f act_h=%.1f  act/orig=%.2f  saved_vs_est=%.1f" % (
            sum_orig, sum_act, sum_act / sum_orig, sum_orig - sum_act))
        faster = [r for r in with_est if r["hours"] < r["orig"]]
        slower = [r for r in with_est if r["hours"] > r["orig"]]
        lines.append("  faster_than_est=%d slower=%d" % (len(faster), len(slower)))
        lines.append("  EST vs ACT samples:")
        for r in sorted(with_est, key=lambda x: -x["hours"])[:20]:
            ratio = r["hours"] / r["orig"] if r["orig"] else 0
            lines.append("    %-14s orig=%6.1f act=%6.1f ratio=%.2f  %s" % (
                r["key"], r["orig"], r["hours"], ratio, r["summary"]))

    lines.append("")
    lines.append("EXCLUDED cancelled/dup/no hours:")
    for r in rows:
        if r not in completed:
            lines.append("  %-14s st=%-12s res=%-18s h=%5.1f %s" % (
                r["key"], r["status"][:12], r["resolution"][:18], r["hours"], r["summary"]))

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("OK")
    print("completed=%d hours=%.1f with_est=%d" % (
        len(completed), sum(r["hours"] for r in completed), len(with_est)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
