#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Датасет презентации 02: эффект Cursor на внутренних задачах (не Аванкор).

Выборка: задачи из выгрузки «внутренние задачи», созданные с 01.11.2025,
отсутствующие в выгрузке задач вендора, с ненулевыми часами, без отмен и дублей.

Часы: Time Sheet (приоритет), иначе Jira Time Spent.
Ставка для денежной оценки: преобладающая ставка Аванкор из презентации 01
(документированный рыночный эквивалент часа разработки 1С).

Коэффициент один, без диапазона. Портфель — доработки существующей конфигурации 1С
(Change Request / оптимизация МО и ДУ). Из исследований этому типу работы соответствует
McKinsey, июнь 2023, «рефакторинг 20-30% меньше времени». Берём середину: 25% быстрее.
Это k = 4/3 (+33% к факту). Лабораторные 55,8% GitHub Copilot (JS HTTP-сервер) не берём.
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

# Коэффициент ускорения. Один, потому что портфель однородный:
# 91% часов — Change Request на существующих конфигурациях Аванкор (оптимизация).
# McKinsey, июнь 2023: рефакторинг 20-30% меньше времени. Середина = 25% быстрее.
# k = 1 / (1 - 0,25) = 4/3. Без Cursor = факт * 4/3. Экономия = факт / 3.
FASTER_PCT = 25.0
OVERHEAD = FASTER_PCT / (100.0 - FASTER_PCT)
K_WITHOUT = 1.0 + OVERHEAD

COEFF = {
    "id": "chosen",
    "name": "Рефакторинг существующего кода 1С",
    "tag": "McKinsey, середина 20-30%",
    "faster_pct": FASTER_PCT,
    "overhead": OVERHEAD,
    "k": K_WITHOUT,
    "note": "91% часов выборки — Change Request: оптимизация уже работающих конфигураций "
            "МО и ДУ, а не написание систем с нуля. McKinsey для рефакторинга дает "
            "20-30% экономии времени. Берём середину: 25% быстрее.",
    "anchor": "McKinsey, Unleashing developer productivity with generative AI, июнь 2023: "
              "refactoring 20-30% less time. Середина 25%. Google enterprise RCT 2024 (~21%) "
              "подтверждает, что полевой эффект близок к нижней границе этой полосы, "
              "а не к лабораторным 56%.",
}


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


def compute_effect(fact_hours, rate, period_months):
    """Считает высвобожденные часы и рубли при одном коэффициенте.

    Параметры:
      fact_hours     - Число - фактические часы с Cursor
      rate           - Число - ставка Аванкор, руб./ч
      period_months  - Число - длина периода выборки, месяцы

    Возвращаемое значение:
      Структура - без Cursor, экономия часов, рубли за период / месяц / год.
    """
    sc = dict(COEFF)
    without = fact_hours * sc["k"]
    saved = without - fact_hours
    money = int(round(saved * rate))
    months = period_months if period_months else 1.0
    hours_month = saved / months
    hours_year = hours_month * 12.0
    sc.update({
        "overhead_pct": int(round(sc["overhead"] * 100)),
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
        "money_check": "%s ч x %s руб/ч = %s руб" % (
            round(saved, 2), int(rate), money),
    })
    return sc


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

    effect = compute_effect(fact_hours, rate, period_months)
    k = effect["k"]
    ovh = effect["overhead"]

    for row in selected:
        row["without_hours"] = round(row["our_hours"] * k, 2)
        row["saved_hours"] = round(row["without_hours"] - row["our_hours"], 2)

    by_component = {}
    for r in selected:
        agg = by_component.setdefault(r["component"], {
            "component": r["component"], "tasks": 0, "hours": 0.0,
        })
        agg["tasks"] += 1
        agg["hours"] += r["our_hours"]
    for agg in by_component.values():
        agg["hours"] = round(agg["hours"], 2)
        agg["saved"] = round(agg["hours"] * ovh, 2)

    by_type = {}
    for r in selected:
        kind = r["issue_type"] or "Прочее"
        agg = by_type.setdefault(kind, {"issue_type": kind, "tasks": 0, "hours": 0.0})
        agg["tasks"] += 1
        agg["hours"] += r["our_hours"]
    for agg in by_type.values():
        agg["hours"] = round(agg["hours"], 2)

    cr = next((t for t in by_type.values() if t["issue_type"] == "Change Request"), None)
    cr_share = round(100.0 * cr["hours"] / fact_hours, 1) if cr and fact_hours else 0.0

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
        saved = round(hours * ovh, 2)
        cum_h += hours
        cum_s += saved
        timeline.append({
            "month": month,
            "tasks": monthly[month]["tasks"],
            "hours": hours,
            "saved": saved,
            "cumulative_hours": round(cum_h, 2),
            "cumulative_saved": round(cum_s, 2),
        })

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
        "k": round(k, 4),
        "overhead": round(ovh, 4),
        "faster_pct": effect["faster_pct"],
        "overhead_pct": effect["overhead_pct"],
        "without_hours": effect["without_hours"],
        "saved_hours": effect["saved_hours"],
        "saved_hours_month": effect["saved_hours_month"],
        "saved_hours_year": effect["saved_hours_year"],
        "saved_money": effect["saved_money"],
        "saved_money_month": effect["saved_money_month"],
        "saved_money_year": effect["saved_money_year"],
        "person_months": effect["person_months"],
        "fte_ongoing": effect["fte_ongoing"],
        "cr_share": cr_share,
        "timesheet_files": ts["files"],
        "timesheet_hours_total": round(sum(f["hours"] for f in ts["files"]), 2),
        "assignees": sorted({r["assignee"] for r in selected if r["assignee"]}),
    }

    payload = {
        "summary": summary,
        "coeff": effect,
        "scenarios": [effect],
        "tasks": sorted(selected, key=lambda r: -r["our_hours"]),
        "by_component": sorted(by_component.values(), key=lambda a: -a["hours"]),
        "by_type": sorted(by_type.values(), key=lambda a: -a["hours"]),
        "timeline": timeline,
        "sources": [
            {
                "id": "mckinsey_ref",
                "fit": "chosen",
                "who": "McKinsey, июнь 2023, рефакторинг",
                "what": "Доработки существующего кода: 20-30% меньше времени. "
                        "Середина 25% — выбранный коэффициент. Совпадает с типом наших задач.",
            },
            {
                "id": "google",
                "fit": "support",
                "who": "Google enterprise RCT, 2024",
                "what": "Полевой замер в корпоративной разработке: около 21% быстрее. "
                        "Подтверждает, что 25% не завышены относительно лаборатории.",
            },
            {
                "id": "mckinsey_new",
                "fit": "reject",
                "who": "McKinsey, июнь 2023, новый код",
                "what": "Написание нового кода: 35-45% меньше времени. Не берём: "
                        "у нас не greenfield, а оптимизация уже работающих конфигураций.",
            },
            {
                "id": "github",
                "fit": "reject",
                "who": "GitHub Copilot / Peng et al., 2022-2023",
                "what": "Лаборатория: HTTP-сервер на JavaScript, 55,8% быстрее. "
                        "Не берём: не 1С, не существующая конфигурация, не корпоративный контур.",
            },
            {
                "id": "ibm",
                "fit": "context",
                "who": "IBM Software / McKinsey, 2024",
                "what": "Не источник коэффициента, а формула ценности: "
                        "value = capacity той же команды + cost avoidance найма.",
            },
        ],
    }

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    safe_print("OK dataset written")
    safe_print("selected=%d hours=%.1f excluded=%s" % (len(selected), fact_hours, excluded))
    safe_print("period %s .. %s (%s months)" % (first, last, period_months))
    safe_print("k=%.4f  faster=%.0f%%  saved=%.0f h  %.0f h/mo  %.0f h/y" % (
        effect["k"], effect["faster_pct"], effect["saved_hours"],
        effect["saved_hours_month"], effect["saved_hours_year"]))
    safe_print("money period=%d  year=%d  rate=%.0f  check=%s" % (
        effect["saved_money"], effect["saved_money_year"], rate, effect["money_check"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
