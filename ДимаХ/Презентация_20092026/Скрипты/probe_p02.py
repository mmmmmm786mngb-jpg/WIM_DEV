#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Разведка внутренних задач Jira для презентации 02 (эффект Cursor).
Консольный вывод - ASCII, подробности в probe_p02.txt.
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
OUT = os.path.join(SCRIPTS, "probe_p02.txt")

INTERNAL = os.path.join(BASE, "внутренние задачи VTB Capital - JIRA 2026-09-17T13_23_36+0300.xls")
AVANCOR = os.path.join(BASE, "задачиАванкору VTB Capital - JIRA 2026-09-17T13_22_34+0300.xls")
TS_DIR = os.path.join(BASE, "Reprot Time _Время задач")
CUTOFF = datetime(2025, 11, 1)


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


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
    per_task_dates = defaultdict(list)
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
            started = str(r.get("Started") or "").strip()
            if started and started.lower() != "nan":
                per_task_dates[key].append(started)
    return per_task, per_task_dates


def main():
    lines = []
    df = read_tables(INTERNAL)[1]
    av = read_tables(AVANCOR)[1]
    av_keys = set(av["Key"].astype(str).str.strip())
    ts, ts_dates = load_timesheets()

    lines.append("internal shape: %s" % (df.shape,))
    lines.append("columns filled:")
    for col in df.columns:
        n = df[col].notna().sum()
        if n == 0:
            continue
        uniq = df[col].dropna().astype(str).unique()[:8]
        lines.append("  %-40s filled=%3d uniq=%s" % (str(col)[:40], n, " | ".join(u[:50] for u in uniq)))

    lines.append("")
    lines.append("STATUS: %s" % dict(Counter(df["Status"].astype(str))))
    lines.append("ISSUE TYPE: %s" % dict(Counter(df["Issue Type"].astype(str))))
    if "Component/s" in df.columns:
        lines.append("COMPONENT: %s" % dict(Counter(df["Component/s"].fillna("").astype(str))))
    if "Labels" in df.columns:
        lines.append("LABELS sample: %s" % df["Labels"].dropna().astype(str).unique()[:15].tolist())
    if "Resolution" in df.columns:
        lines.append("RESOLUTION: %s" % dict(Counter(df["Resolution"].fillna("").astype(str))))

    overlap = set(df["Key"].astype(str).str.strip()) & av_keys
    lines.append("")
    lines.append("overlap with avancor export: %d" % len(overlap))
    for k in sorted(overlap)[:20]:
        lines.append("  overlap %s" % k)

    in_period = 0
    with_hours = 0
    hours_total = 0.0
    samples = []
    by_month = defaultdict(lambda: [0, 0.0])
    by_comp = defaultdict(lambda: [0, 0.0])
    no_hours = []

    for _, r in df.iterrows():
        key = str(r.get("Key")).strip()
        created = parse_jira_date(r.get("Created"))
        resolved = parse_jira_date(r.get("Resolved"))
        stamp = created
        if stamp is None or stamp < CUTOFF:
            continue
        if key in av_keys:
            continue
        in_period += 1
        hours = ts.get(key, 0.0)
        if hours <= 0:
            secs = r.get("Time Spent")
            if pd.notna(secs):
                hours = round(float(secs) / 3600.0, 2)
        if hours > 0:
            with_hours += 1
            hours_total += hours
        else:
            no_hours.append(key)
        month = stamp.strftime("%Y-%m")
        by_month[month][0] += 1
        by_month[month][1] += hours
        comp = str(r.get("Component/s") or "").strip() or "none"
        by_comp[comp][0] += 1
        by_comp[comp][1] += hours
        samples.append((hours, key, str(r.get("Summary") or "")[:80],
                        stamp.strftime("%Y-%m-%d"), str(r.get("Status")),
                        str(r.get("Issue Type")), hours))

    lines.append("")
    lines.append("after 2025-11-01, not in avancor export: %d" % in_period)
    lines.append("with hours: %d  hours_total=%.2f" % (with_hours, hours_total))
    lines.append("without hours: %d  examples=%s" % (len(no_hours), no_hours[:12]))
    lines.append("")
    lines.append("BY MONTH:")
    for m in sorted(by_month):
        lines.append("  %s  tasks=%d hours=%.1f" % (m, by_month[m][0], by_month[m][1]))
    lines.append("")
    lines.append("BY COMPONENT:")
    for c, v in sorted(by_comp.items(), key=lambda x: -x[1][1]):
        lines.append("  %-20s tasks=%d hours=%.1f" % (c[:20], v[0], v[1]))
    lines.append("")
    lines.append("TOP BY HOURS:")
    for item in sorted(samples, reverse=True)[:25]:
        lines.append("  %6.2f  %-14s %-10s %-12s %s" % (item[0], item[1], item[4][:10], item[5][:12], item[2]))

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    safe_print("OK probe written")
    safe_print("in_period=%d with_hours=%d total_h=%.1f overlap=%d" % (
        in_period, with_hours, hours_total, len(overlap)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
