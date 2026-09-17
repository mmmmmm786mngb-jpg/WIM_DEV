#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Датасет презентации 02: эффект Cursor на внутренних задачах (не Аванкор).

Выборка: задачи из выгрузки «внутренние задачи», созданные с 01.11.2025,
отсутствующие в выгрузке задач вендора, с ненулевыми часами, без отмен и дублей.

Часы: Time Sheet (приоритет), иначе Jira Time Spent.
Ставка для денежной оценки: преобладающая ставка Аванкор из презентации 01
(документированный рыночный эквивалент часа разработки 1С).

Сценарии задают надбавку к фактическому времени («сколько заняло бы без ИИ»):
  min  +40%  — нижняя граница, ТЗ и полевые замеры enterprise
  base +50%  — консервативная оценка из ТЗ
  real +80%  — ближе к кодогенерации по McKinsey, всё ещё ниже лабораторных 55,8%
"""

import io
import json
import os
import re
import sys
import warnings
from collections import defaultdict
from datetime import datetime

import pandas as pd

warnings.filterwarnings("ignore")

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(SCRIPTS)
OUT = os.path.join(SCRIPTS, "p02_dataset.json")

INTERNAL_XLS = os.path.join(BASE, "внутренние задачи VTB Capital - JIRA 2026-09-17T13_23_36+0300.xls")
AVANCOR_XLS = os.path.join(BASE, "задачиАванкору VTB Capital - JIRA 2026-09-17T13_22_34+0300.xls")
P01_DATA = os.path.join(SCRIPTS, "p01_dataset.json")
TS_DIR = os.path.join(BASE, "Reprot Time _Время задач")

CUTOFF = datetime(2025, 11, 1)
MONTH_HOURS = 168.0  # 21 раб. день x 8 ч
SKIP_STATUS = {"cancelled"}
SKIP_RESOLUTION = {"duplicate", "request cancelled"}

COMPONENT_SHORT = {
    "AvancoreDU": "ДУ",
    "AvancoreMO": "МО",
    "AvancoreFinance": "ФИН",
    "AvancorePIF": "ПИФ",
    "1C-InvestmentCentre": "IC",
    "1C-Custody": "Депозитарий",
    "XBRL": "XBRL",
}

# time_without = fact * (1 + overhead)
# faster_pct = 1 - 1/(1+overhead)  — на сколько процентов быстрее с ИИ
SCENARIOS = [
    {
        "id": "min",
        "name": "Консервативный",
        "tag": "нижняя граница",
        "overhead": 0.40,
        "note": "Без Cursor задача заняла бы на 40% больше времени. "
                "Это 29% ускорения — чуть выше полевого RCT Google (~21%) "
                "и внутри диапазона McKinsey по рефакторингу (20-30%).",
        "anchor": "Google enterprise RCT, 2024: ~21% быстрее; McKinsey, 2023: рефакторинг 20-30%.",
    },
    {
        "id": "base",
        "name": "Базовый",
        "tag": "оценка по ТЗ",
        "overhead": 0.50,
        "note": "Надбавка +50% к факту — верхняя консервативная граница из постановки. "
                "Ускорение 33%, нижняя половина диапазона IBM 30-40%.",
        "anchor": "Постановка презентации: +40-50% к фактическому времени. IBM Software: +30-40% производительности.",
    },
    {
        "id": "real",
        "name": "Реалистичный",
        "tag": "ближе к практике Cursor",
        "overhead": 0.80,
        "note": "Надбавка +80%: без ИИ ушло бы почти вдвое больше времени. "
                "Ускорение 44% — уровень McKinsey по написанию кода (35-45%), "
                "всё ещё ниже лабораторных 55,8% GitHub Copilot.",
        "anchor": "McKinsey, 2023: кодогенерация 35-45% меньше времени. GitHub Copilot lab, 2022: 55,8% быстрее (не берём).",
    },
]


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


def iso(dt):
    return dt.strftime("%Y-%m-%d") if dt else None


def short_component(raw):
    text = str(raw or "").strip()
    if not text or text.lower() == "nan":
        return "Прочее"
    parts = [p.strip() for p in text.split(",") if p.strip()]
    mapped = []
    for part in parts:
        mapped.append(COMPONENT_SHORT.get(part, part.replace("Avancore", "")))
    # уникальные, порядок сохранён
    seen = []
    for item in mapped:
        if item not in seen:
            seen.append(item)
    return "+".join(seen) if seen else "Прочее"


def load_avancor_keys():
    df = read_tables(AVANCOR_XLS)[1]
    return set(df["Key"].astype(str).str.strip())


def load_timesheets():
    per_task = defaultdict(float)
    per_month = defaultdict(float)
    users = defaultdict(float)
    files = []
    for name in sorted(os.listdir(TS_DIR)):
        if not name.lower().endswith(".xls"):
            continue
        path = os.path.join(TS_DIR, name)
        df = read_tables(path)[1]
        header = df.iloc[0].tolist()
        body = df.iloc[1:].copy()
        body.columns = [str(h).strip() for h in header]
        body = body[body["Project"].astype(str).str.lower() != "total"]
        file_hours = 0.0
        for _, r in body.iterrows():
            key = str(r.get("Key") or "").strip()
            if not key or key.lower() == "nan":
                continue
            try:
                hours = float(str(r.get("Time Spent (Hours)")).replace(",", "."))
            except (TypeError, ValueError):
                continue
            per_task[key] += hours
            file_hours += hours
            started = parse_jira_date(r.get("Started"))
            if started and started >= CUTOFF:
                per_month[started.strftime("%Y-%m")] += hours
            user = str(r.get("Username") or "").strip()
            if user and user.lower() != "nan":
                users[user] += hours
        files.append({"file": name, "rows": int(len(body)), "hours": round(file_hours, 2)})
    return {
        "per_task": {k: round(v, 2) for k, v in per_task.items()},
        "per_month": {k: round(v, 2) for k, v in per_month.items()},
        "users": {k: round(v, 2) for k, v in users.items()},
        "files": files,
    }


def load_internal():
    df = read_tables(INTERNAL_XLS)[1]
    rows = []
    for _, r in df.iterrows():
        jira_secs = r.get("Time Spent")
        jira_hours = round(float(jira_secs) / 3600.0, 2) if pd.notna(jira_secs) else 0.0
        orig = r.get("Original Estimate")
        orig_h = round(float(orig) / 3600.0, 2) if pd.notna(orig) and float(orig) > 0 else None
        rows.append({
            "key": str(r.get("Key")).strip(),
            "summary": str(r.get("Summary") or "").strip(),
            "status": str(r.get("Status") or "").strip(),
            "resolution": str(r.get("Resolution") or "").strip(),
            "issue_type": str(r.get("Issue Type") or "").strip(),
            "component_raw": str(r.get("Component/s") or "").strip(),
            "component": short_component(r.get("Component/s")),
            "department": str(r.get("IM Department") or "").strip(),
            "assignee": str(r.get("Assignee") or "").strip(),
            "epic": str(r.get("Epic Link") or "").strip(),
            "labels": str(r.get("Labels") or "").strip(),
            "created": str(r.get("Created") or "").strip(),
            "resolved": str(r.get("Resolved") or "").strip(),
            "created_iso": iso(parse_jira_date(r.get("Created"))),
            "resolved_iso": iso(parse_jira_date(r.get("Resolved"))),
            "jira_hours": jira_hours,
            "orig_hours": orig_h,
        })
    return rows


def vendor_rate():
    if os.path.exists(P01_DATA):
        with open(P01_DATA, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        return float(payload["summary"]["base_rate"])
    return 3900.0


def compute_scenario(sc, fact_hours, rate, period_months):
    without = fact_hours * (1.0 + sc["overhead"])
    saved = without - fact_hours
    money = int(round(saved * rate))
    faster = 100.0 * sc["overhead"] / (1.0 + sc["overhead"])
    months = period_months if period_months else 1.0
    hours_month = saved / months
    hours_year = hours_month * 12.0
    return {
        "id": sc["id"],
        "name": sc["name"],
        "tag": sc["tag"],
        "note": sc["note"],
        "anchor": sc["anchor"],
        "overhead": sc["overhead"],
        "overhead_pct": int(round(sc["overhead"] * 100)),
        "faster_pct": round(faster, 1),
        "fact_hours": round(fact_hours, 2),
        "without_hours": round(without, 2),
        "saved_hours": round(saved, 2),
        "saved_money": money,
        "person_months": round(saved / MONTH_HOURS, 2),
        "saved_hours_month": round(hours_month, 1),
        "saved_hours_year": round(hours_year, 0),
        "saved_money_month": int(round(money / months)),
        "saved_money_year": int(round(money / months * 12.0)),
        "fte_ongoing": round(hours_month / MONTH_HOURS, 2),
    }


def main():
    avancor_keys = load_avancor_keys()
    ts = load_timesheets()
    internal = load_internal()
    rate = vendor_rate()

    selected = []
    excluded = {"before_cutoff": 0, "avancor": 0, "cancelled": 0, "no_hours": 0}
    for row in internal:
        created = parse_jira_date(row["created"])
        if created is None or created < CUTOFF:
            excluded["before_cutoff"] += 1
            continue
        if row["key"] in avancor_keys:
            excluded["avancor"] += 1
            continue
        if row["status"].strip().lower() in SKIP_STATUS:
            excluded["cancelled"] += 1
            continue
        if row["resolution"].strip().lower() in SKIP_RESOLUTION:
            excluded["cancelled"] += 1
            continue
        hours = ts["per_task"].get(row["key"], 0.0)
        source = "timesheet"
        if hours <= 0:
            hours = row["jira_hours"]
            source = "jira" if hours > 0 else "none"
        if hours <= 0:
            excluded["no_hours"] += 1
            continue
        row["our_hours"] = round(hours, 2)
        row["hours_source"] = source
        selected.append(row)

    fact_hours = round(sum(r["our_hours"] for r in selected), 2)

    first = min(r["created_iso"] for r in selected if r["created_iso"])
    last = max((r["resolved_iso"] or r["created_iso"]) for r in selected)
    start_dt = datetime.strptime(first, "%Y-%m-%d")
    end_dt = datetime.strptime(last, "%Y-%m-%d")
    period_days = (end_dt - start_dt).days
    period_months = round(period_days / 30.44, 1)

    scenarios = [compute_scenario(sc, fact_hours, rate, period_months) for sc in SCENARIOS]

    # Позадачный расчёт для базового сценария (+50%) — основной ряд диаграммы
    base_k = 1.50
    for row in selected:
        row["without_min"] = round(row["our_hours"] * 1.40, 2)
        row["without_base"] = round(row["our_hours"] * base_k, 2)
        row["without_real"] = round(row["our_hours"] * 1.80, 2)
        row["saved_min"] = round(row["without_min"] - row["our_hours"], 2)
        row["saved_base"] = round(row["without_base"] - row["our_hours"], 2)
        row["saved_real"] = round(row["without_real"] - row["our_hours"], 2)

    by_component = {}
    for r in selected:
        agg = by_component.setdefault(r["component"], {
            "component": r["component"], "tasks": 0, "hours": 0.0,
        })
        agg["tasks"] += 1
        agg["hours"] += r["our_hours"]
    for agg in by_component.values():
        agg["hours"] = round(agg["hours"], 2)
        agg["saved_min"] = round(agg["hours"] * 0.40, 2)
        agg["saved_base"] = round(agg["hours"] * 0.50, 2)
        agg["saved_real"] = round(agg["hours"] * 0.80, 2)

    by_type = {}
    for r in selected:
        kind = r["issue_type"] or "Прочее"
        agg = by_type.setdefault(kind, {"issue_type": kind, "tasks": 0, "hours": 0.0})
        agg["tasks"] += 1
        agg["hours"] += r["our_hours"]
    for agg in by_type.values():
        agg["hours"] = round(agg["hours"], 2)

    # Накопленная экономия по месяцу закрытия (базовый сценарий)
    monthly = defaultdict(lambda: {"tasks": 0, "hours": 0.0})
    for r in selected:
        stamp = r["resolved_iso"] or r["created_iso"]
        if not stamp:
            continue
        month = stamp[:7]
        monthly[month]["tasks"] += 1
        monthly[month]["hours"] += r["our_hours"]
    timeline = []
    cum_h = cum_s = 0.0
    for month in sorted(monthly):
        hours = round(monthly[month]["hours"], 2)
        saved = round(hours * 0.50, 2)
        cum_h += hours
        cum_s += saved
        timeline.append({
            "month": month,
            "tasks": monthly[month]["tasks"],
            "hours": hours,
            "saved_base": saved,
            "cumulative_hours": round(cum_h, 2),
            "cumulative_saved": round(cum_s, 2),
        })

    sc_min = scenarios[0]
    sc_real = scenarios[2]
    summary = {
        "cutoff": "2025-11-01",
        "tasks_in_export": len(internal),
        "tasks_selected": len(selected),
        "excluded": excluded,
        "fact_hours": fact_hours,
        "rate": rate,
        "month_hours": MONTH_HOURS,
        "period_from": first,
        "period_to": last,
        "period_days": period_days,
        "period_months": period_months,
        "saved_hours_min": sc_min["saved_hours"],
        "saved_hours_max": sc_real["saved_hours"],
        "saved_hours_month_min": sc_min["saved_hours_month"],
        "saved_hours_month_max": sc_real["saved_hours_month"],
        "saved_hours_year_min": sc_min["saved_hours_year"],
        "saved_hours_year_max": sc_real["saved_hours_year"],
        "saved_money_min": sc_min["saved_money"],
        "saved_money_max": sc_real["saved_money"],
        "saved_money_month_min": sc_min["saved_money_month"],
        "saved_money_month_max": sc_real["saved_money_month"],
        "saved_money_year_min": sc_min["saved_money_year"],
        "saved_money_year_max": sc_real["saved_money_year"],
        "person_months_min": sc_min["person_months"],
        "person_months_max": sc_real["person_months"],
        "fte_ongoing_min": sc_min["fte_ongoing"],
        "fte_ongoing_max": sc_real["fte_ongoing"],
        "without_min": sc_min["without_hours"],
        "without_max": sc_real["without_hours"],
        "timesheet_files": ts["files"],
        "timesheet_hours_total": round(sum(f["hours"] for f in ts["files"]), 2),
        "assignees": sorted({r["assignee"] for r in selected if r["assignee"]}),
    }

    payload = {
        "summary": summary,
        "scenarios": scenarios,
        "tasks": sorted(selected, key=lambda r: -r["our_hours"]),
        "by_component": sorted(by_component.values(), key=lambda a: -a["hours"]),
        "by_type": sorted(by_type.values(), key=lambda a: -a["hours"]),
        "timeline": timeline,
        "sources": [
            {
                "id": "github",
                "who": "GitHub Copilot / Peng et al., 2022-2023",
                "what": "Контролируемый эксперимент: задача HTTP-сервера на JavaScript. "
                        "С Copilot на 55,8% быстрее (71 мин против 161 мин). 95% ДИ 21-89%.",
                "url": "https://github.blog/news-insights/research/research-quantifying-github-copilots-impact-on-developer-productivity-and-happiness/",
            },
            {
                "id": "mckinsey",
                "who": "McKinsey, июнь 2023",
                "what": "Документация кода 45-50% меньше времени, написание кода 35-45%, "
                        "рефакторинг 20-30%, задачи высокой сложности менее 10%.",
                "url": "https://www.mckinsey.com/capabilities/mckinsey-digital/our-insights/unleashing-developer-productivity-with-generative-ai",
            },
            {
                "id": "google",
                "who": "Google enterprise RCT, 2024",
                "what": "Полевой эксперимент в корпоративной разработке: около 21% быстрее "
                        "(оценка ниже лабораторных 56% и ближе к практике).",
                "url": "https://arxiv.org/html/2410.12944",
            },
            {
                "id": "ibm",
                "who": "IBM Software / McKinsey, 2024",
                "what": "Разработчики IBM с gen AI: рост производительности 30-40%. "
                        "Формула ценности: capacity той же команды + cost avoidance найма.",
                "url": "https://www.mckinsey.com/capabilities/tech-and-ai/our-insights/the-gen-ai-skills-revolution-rethinking-your-talent-strategy",
            },
        ],
    }

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    safe_print("OK dataset written")
    safe_print("selected=%d hours=%.1f excluded=%s" % (len(selected), fact_hours, excluded))
    safe_print("period %s .. %s (%s months)" % (first, last, period_months))
    for sc in scenarios:
        safe_print("%-14s +%d%%  saved=%.0f h  %.0f h/mo  %.0f h/y  %.2f FTE" % (
            sc["id"], sc["overhead_pct"], sc["saved_hours"],
            sc["saved_hours_month"], sc["saved_hours_year"], sc["fte_ongoing"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
