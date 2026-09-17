#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Подготовка датасета для Презентации 01 "Экономика: стоимость доработок силами Аванкор".

Источники:
  - Jira-выгрузка платных задач Аванкор (.xls = HTML): Key, Summary, Ext Estimate, Paid,
    Time Spent, Component/s, IM Department, Status, External Ref
  - Time Sheet Report (.xls = HTML): фактические часы нашей команды по задачам и датам

Логика расчета:
  - Из поля "Ext Estimate" разбирается смета Аванкор: нормо-часы и стоимость в рублях.
    Отсюда получается фактическая ставка Аванкор (руб./нормо-час).
  - Часы нашей команды берутся из Time Sheet (приоритет) либо из Jira Time Spent.
  - Гипотетическая стоимость "если бы Аванкор делал всё" = (наши часы * надбавка
    + нормо-часы Аванкор) * ставка Аванкор.
  - Экономия = гипотетическая стоимость - фактически оплаченная интеграция.

Учитываются две группы задач:
  1. Платные (Paid = yes) - вендор выставил счет за интеграцию нашего решения.
  2. Бесплатные (Paid = no) - вендор принял наш готовый результат и не выставил счет.
     Часть из них он закрыл бы бесплатно и сам (гарантия на баги, сопровождение),
     поэтому применяется коэффициент доли сопровождения.

Сценарии (см. SCENARIOS): от предельно консервативного до реалистичного -
различаются надбавкой на аналитику вендора и долей бесплатного сопровождения.

Результат: p01_dataset.json (UTF-8) для сборки HTML-презентации.
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
OUT = os.path.join(SCRIPTS, "p01_dataset.json")

AVANCOR_XLS = os.path.join(BASE, "задачиАванкору VTB Capital - JIRA 2026-09-17T13_22_34+0300.xls")
TS_DIR = os.path.join(BASE, "Reprot Time _Время задач")

# Словесные обозначения нормо-часов в сметах Аванкор
WORD_HOURS = {
    "один": 1, "одна": 1, "два": 2, "две": 2, "три": 3, "четыре": 4, "пять": 5,
    "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
}

# Типы задач, которые вендор обязан закрывать бесплатно по гарантии на свой продукт.
# Из расчета экономии по бесплатным задачам исключаются полностью.
WARRANTY_TYPES = ("bug",)

# Сценарии оценки. Отличаются двумя коэффициентами:
#   overhead - надбавка к нашим часам на аналитику и вхождение вендора в контекст.
#              Основание: в IMAPPS-32896 вендор выставил 16 нормо-часов только за
#              анализ при наших 3,5 часах на всю задачу (разработка не оценена).
#   support  - доля бесплатных задач, которую вендор закрыл бы даром в рамках
#              сопровождения (эта часть в экономию не попадает).
SCENARIOS = [
    {
        "id": "min",
        "name": "Консервативный",
        "tag": "нижняя граница",
        "overhead": 1.0,
        "support": 1.0,
        "note": "Вендор тратит ровно столько же часов, сколько наша команда. "
                "Бесплатные задачи не учитываем вовсе.",
    },
    {
        "id": "base",
        "name": "Базовый",
        "tag": "с учетом бесплатных задач",
        "overhead": 1.0,
        "support": 0.5,
        "note": "Надбавки на аналитику вендора нет. Половину бесплатных задач "
                "вендор закрыл бы сам в рамках сопровождения.",
    },
    {
        "id": "real",
        "name": "Реалистичный",
        "tag": "ближе к практике",
        "overhead": 1.4,
        "support": 0.3,
        "note": "Вендору нужно на 40% больше времени: аналитика, изучение нашего "
                "контекста, согласования. По сопровождению прошло бы 30% бесплатных задач.",
    },
]


def safe_print(text):
    """Безопасный вывод в консоль Windows (только ASCII)."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def read_tables(path):
    """Читает HTML-таблицы из файла .xls (Jira-экспорт фактически HTML)."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return pd.read_html(io.StringIO(fh.read()))


def parse_money(text):
    """Извлекает сумму в рублях из текста сметы Аванкор."""
    # "Стоимость составляет 16 800 руб", "16800 руб.", "16 800 рублей"
    match = re.search(r"([\d][\d\s\u00a0]{0,12})\s*(?:руб|р\.)", text, re.IGNORECASE)
    if not match:
        return None
    digits = re.sub(r"[^\d]", "", match.group(1))
    return int(digits) if digits else None


def parse_norm_hours(text):
    """Извлекает количество нормо-часов (или оплачиваемых часов) из сметы Аванкор."""
    low = text.lower()
    # Числовая форма: "4 нормо-часа", "0,5 нормо-часа"
    match = re.search(r"([\d]+(?:[.,][\d]+)?)\s*нормо", low)
    if match:
        return float(match.group(1).replace(",", "."))
    # Словесная форма: "один нормо-час"
    match = re.search(r"([а-яё]+)\s+нормо", low)
    if match and match.group(1) in WORD_HOURS:
        return float(WORD_HOURS[match.group(1)])
    # Форма без слова "нормо": "Анализ: 16 часов = 74 880 руб"
    match = re.search(r"([\d]+(?:[.,][\d]+)?)\s*час", low)
    if match:
        return float(match.group(1).replace(",", "."))
    return None


def load_avancor():
    """Загружает задачи Аванкор с разбором смет."""
    df = read_tables(AVANCOR_XLS)[1]
    keep = [
        "Key", "Summary", "Status", "Resolution", "Issue Type", "Component/s",
        "IM Department", "Paid", "Ext Estimate", "Time Spent", "Original Estimate",
        "External Ref", "Created", "Resolved", "Labels", "Epic Link", "Cost Center",
    ]
    cols = [c for c in keep if c in df.columns]
    df = df[cols].copy()

    rows = []
    for _, r in df.iterrows():
        ext = str(r.get("Ext Estimate") or "").strip()
        paid = str(r.get("Paid") or "").strip().lower()
        norm_hours = parse_norm_hours(ext) if ext and ext.lower() != "nan" else None
        cost = parse_money(ext) if ext and ext.lower() != "nan" else None

        jira_secs = r.get("Time Spent")
        jira_hours = round(float(jira_secs) / 3600.0, 2) if pd.notna(jira_secs) else 0.0

        rows.append({
            "key": str(r.get("Key")).strip(),
            "summary": str(r.get("Summary") or "").strip(),
            "status": str(r.get("Status") or "").strip(),
            "resolution": str(r.get("Resolution") or "").strip(),
            "issue_type": str(r.get("Issue Type") or "").strip(),
            "component": str(r.get("Component/s") or "").strip(),
            "department": str(r.get("IM Department") or "").strip(),
            "paid": paid,
            "ext_estimate_raw": ext,
            "avancor_norm_hours": norm_hours,
            "avancor_cost": cost,
            "jira_hours": jira_hours,
            "external_ref": str(r.get("External Ref") or "").strip(),
            "created": str(r.get("Created") or "").strip(),
            "resolved": str(r.get("Resolved") or "").strip(),
            "epic": str(r.get("Epic Link") or "").strip(),
            "cost_center": str(r.get("Cost Center") or "").strip(),
        })
    return rows


def load_timesheets():
    """Собирает фактические часы нашей команды по задачам из всех Time Sheet."""
    per_task = defaultdict(float)
    per_task_entries = defaultdict(int)
    per_task_title = {}
    per_task_dates = defaultdict(list)
    files = []

    for name in sorted(os.listdir(TS_DIR)):
        if not name.lower().endswith(".xls"):
            continue
        path = os.path.join(TS_DIR, name)
        df = read_tables(path)[1]
        df.columns = [str(c) for c in df.columns]
        # Первая строка - заголовки, последняя - Total
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
            per_task_entries[key] += 1
            file_hours += hours
            title = str(r.get("Title") or "").strip()
            if title and title.lower() != "nan":
                per_task_title.setdefault(key, title)
            started = str(r.get("Started") or "").strip()
            if started and started.lower() != "nan":
                per_task_dates[key].append(started)

        files.append({"file": name, "rows": int(len(body)), "hours": round(file_hours, 2)})

    return {
        "per_task": {k: round(v, 2) for k, v in per_task.items()},
        "entries": dict(per_task_entries),
        "titles": per_task_title,
        "dates": dict(per_task_dates),
        "files": files,
    }


def parse_jira_date(text):
    """Преобразует дату Jira ('11/Sep/26 8:44 +0300') в ISO-строку."""
    if not text or text.lower() == "nan":
        return None
    match = re.match(r"(\d{2})/([A-Za-z]{3})/(\d{2})", text)
    if not match:
        return None
    try:
        dt = datetime.strptime("%s/%s/%s" % match.groups(), "%d/%b/%y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def compute_scenario(scenario, priced, unpaid_billable, base_rate):
    """Считает экономию по одному сценарию оценки.

    Параметры:
      scenario        - Структура - описание сценария из SCENARIOS (overhead, support)
      priced          - Массив - платные задачи вендора с разобранной сметой
      unpaid_billable - Массив - бесплатные задачи без гарантийных (Bug)
      base_rate       - Число - преобладающая ставка вендора, руб./нормо-час

    Возвращаемое значение:
      Структура - суммы по платным и бесплатным задачам, итоговая экономия.
    """
    k_ovh = scenario["overhead"]
    k_sup = scenario["support"]

    # Платные задачи: вендор уже получил оплату за интеграцию
    paid_hypo = 0
    paid_hours = 0.0
    for r in priced:
        hours = r["our_hours"] * k_ovh + (r["avancor_norm_hours"] or 0.0)
        paid_hours += hours
        paid_hypo += int(round(hours * r["rate_used"]))
    paid_fact = sum(r["fact_cost"] for r in priced)

    # Бесплатные задачи: часть ушла бы в сопровождение, остальное вендор выставил бы в счет
    free_hours_raw = sum(r["our_hours"] for r in unpaid_billable)
    free_hours_billable = free_hours_raw * (1.0 - k_sup)
    free_hours = free_hours_billable * k_ovh
    free_hypo = int(round(free_hours * base_rate))

    hypo_total = paid_hypo + free_hypo
    saving_total = hypo_total - paid_fact

    return {
        "id": scenario["id"],
        "name": scenario["name"],
        "tag": scenario["tag"],
        "note": scenario["note"],
        "overhead": k_ovh,
        "support": k_sup,
        "overhead_pct": int(round((k_ovh - 1.0) * 100)),
        "support_pct": int(round(k_sup * 100)),
        "paid_hours": round(paid_hours, 2),
        "paid_hypo": paid_hypo,
        "paid_fact": paid_fact,
        "paid_saving": paid_hypo - paid_fact,
        "free_hours_raw": round(free_hours_raw, 2),
        "free_hours_billable": round(free_hours_billable, 2),
        "free_hours": round(free_hours, 2),
        "free_hypo": free_hypo,
        "hypo_total": hypo_total,
        "fact_total": paid_fact,
        "saving_total": saving_total,
        "cost_ratio": round(1.0 * hypo_total / paid_fact, 2) if paid_fact else 0.0,
        "saving_pct": round(100.0 * saving_total / hypo_total, 1) if hypo_total else 0.0,
    }


def main():
    avancor = load_avancor()
    ts = load_timesheets()

    # Фактическая ставка Аванкор по сметам, где есть и часы, и стоимость
    rates = []
    for row in avancor:
        if row["avancor_norm_hours"] and row["avancor_cost"]:
            rates.append(round(row["avancor_cost"] / row["avancor_norm_hours"], 2))
    rate_counts = {}
    for r in rates:
        rate_counts[r] = rate_counts.get(r, 0) + 1
    base_rate = max(rate_counts, key=rate_counts.get) if rate_counts else 3900.0

    # Обогащаем задачи часами из Time Sheet и расчетами
    for row in avancor:
        key = row["key"]
        ts_hours = ts["per_task"].get(key, 0.0)
        row["ts_hours"] = ts_hours
        row["ts_entries"] = ts["entries"].get(key, 0)
        row["our_hours"] = ts_hours if ts_hours > 0 else row["jira_hours"]
        row["hours_source"] = "timesheet" if ts_hours > 0 else ("jira" if row["jira_hours"] else "none")
        row["created_iso"] = parse_jira_date(row["created"])
        row["resolved_iso"] = parse_jira_date(row["resolved"])

        rate = base_rate
        if row["avancor_norm_hours"] and row["avancor_cost"]:
            rate = round(row["avancor_cost"] / row["avancor_norm_hours"], 2)
        row["rate_used"] = rate

        fact_cost = row["avancor_cost"] or 0
        av_hours = row["avancor_norm_hours"] or 0.0
        hypo_hours = row["our_hours"] + av_hours
        row["hypo_hours"] = round(hypo_hours, 2)
        row["hypo_cost"] = int(round(hypo_hours * rate))
        row["fact_cost"] = int(fact_cost)
        row["saving"] = row["hypo_cost"] - row["fact_cost"]

    # Признак незавершенной сметы (разработка еще не оценена вендором)
    for row in avancor:
        raw = row["ext_estimate_raw"].lower()
        row["estimate_open"] = "ожида" in raw or "?" in raw

    paid_yes = [r for r in avancor if r["paid"] == "yes"]
    priced = [r for r in paid_yes if r["avancor_cost"]]
    unpaid = [r for r in avancor if r["paid"] != "yes"]

    # Бесплатные задачи: отделяем гарантийные (Bug) от тех, что вендор выставил бы в счет
    for r in unpaid:
        r["warranty"] = r["issue_type"].strip().lower() in WARRANTY_TYPES
        r["billable_candidate"] = not r["warranty"] and r["our_hours"] > 0
    unpaid_billable = [r for r in unpaid if r["billable_candidate"]]
    unpaid_warranty = [r for r in unpaid if r["warranty"]]
    unpaid_no_hours = [r for r in unpaid if not r["warranty"] and r["our_hours"] <= 0]

    # Разрез бесплатных задач по типу
    unpaid_by_type = {}
    for r in unpaid:
        kind = r["issue_type"] or "Прочее"
        agg = unpaid_by_type.setdefault(kind, {
            "issue_type": kind, "tasks": 0, "hours": 0.0, "warranty": r["warranty"],
        })
        agg["tasks"] += 1
        agg["hours"] += r["our_hours"]
    for agg in unpaid_by_type.values():
        agg["hours"] = round(agg["hours"], 2)

    # Сценарии оценки: от нижней границы до реалистичной
    scenarios = [compute_scenario(sc, priced, unpaid_billable, base_rate) for sc in SCENARIOS]

    # Разрез по конфигурациям Аванкор
    by_component = {}
    for r in priced:
        comp = r["component"] or "Прочее"
        agg = by_component.setdefault(comp, {
            "component": comp, "tasks": 0, "our_hours": 0.0, "avancor_hours": 0.0,
            "fact_cost": 0, "hypo_cost": 0, "saving": 0,
        })
        agg["tasks"] += 1
        agg["our_hours"] += r["our_hours"]
        agg["avancor_hours"] += r["avancor_norm_hours"] or 0.0
        agg["fact_cost"] += r["fact_cost"]
        agg["hypo_cost"] += r["hypo_cost"]
        agg["saving"] += r["saving"]
    for agg in by_component.values():
        agg["our_hours"] = round(agg["our_hours"], 2)
        agg["avancor_hours"] = round(agg["avancor_hours"], 2)

    # Накопленная экономия по месяцам создания задачи
    monthly = defaultdict(lambda: {"saving": 0, "fact": 0, "hypo": 0, "tasks": 0, "hours": 0.0})
    for r in priced:
        stamp = r["resolved_iso"] or r["created_iso"]
        if not stamp:
            continue
        month = stamp[:7]
        monthly[month]["saving"] += r["saving"]
        monthly[month]["fact"] += r["fact_cost"]
        monthly[month]["hypo"] += r["hypo_cost"]
        monthly[month]["tasks"] += 1
        monthly[month]["hours"] += r["our_hours"]
    timeline = []
    cumulative = 0
    for month in sorted(monthly):
        cumulative += monthly[month]["saving"]
        timeline.append({
            "month": month,
            "saving": monthly[month]["saving"],
            "cumulative": cumulative,
            "fact": monthly[month]["fact"],
            "hypo": monthly[month]["hypo"],
            "tasks": monthly[month]["tasks"],
            "hours": round(monthly[month]["hours"], 2),
        })

    summary = {
        "tasks_total": len(avancor),
        "tasks_paid": len(paid_yes),
        "tasks_priced": len(priced),
        "tasks_unpaid": len(unpaid),
        "unpaid_hours": round(sum(r["our_hours"] for r in unpaid), 2),
        "unpaid_billable_tasks": len(unpaid_billable),
        "unpaid_billable_hours": round(sum(r["our_hours"] for r in unpaid_billable), 2),
        "unpaid_warranty_tasks": len(unpaid_warranty),
        "unpaid_warranty_hours": round(sum(r["our_hours"] for r in unpaid_warranty), 2),
        "unpaid_no_hours_tasks": len(unpaid_no_hours),
        "base_rate": base_rate,
        "rate_distribution": rate_counts,
        "rate_min": min(rates) if rates else None,
        "rate_max": max(rates) if rates else None,
        "our_hours_priced": round(sum(r["our_hours"] for r in priced), 2),
        "avancor_norm_hours_priced": round(sum(r["avancor_norm_hours"] or 0 for r in priced), 2),
        "fact_cost_total": sum(r["fact_cost"] for r in priced),
        "hypo_cost_total": sum(r["hypo_cost"] for r in priced),
        "saving_total": sum(r["saving"] for r in priced),
        "timesheet_files": ts["files"],
        "timesheet_hours_total": round(sum(f["hours"] for f in ts["files"]), 2),
        "timesheet_tasks": len(ts["per_task"]),
    }
    summary["saving_pct"] = (
        round(100.0 * summary["saving_total"] / summary["hypo_cost_total"], 1)
        if summary["hypo_cost_total"] else 0.0
    )
    summary["fact_share_pct"] = (
        round(100.0 * summary["fact_cost_total"] / summary["hypo_cost_total"], 1)
        if summary["hypo_cost_total"] else 0.0
    )
    # Во сколько раз полная разработка дороже фактической интеграции
    summary["cost_ratio"] = (
        round(1.0 * summary["hypo_cost_total"] / summary["fact_cost_total"], 2)
        if summary["fact_cost_total"] else 0.0
    )
    # Доля работ, выполненная нашей командой (в часах)
    total_hours = summary["our_hours_priced"] + summary["avancor_norm_hours_priced"]
    summary["our_hours_share_pct"] = (
        round(100.0 * summary["our_hours_priced"] / total_hours, 1) if total_hours else 0.0
    )

    # Диапазон оценки: от нижней границы до реалистичного сценария
    summary["saving_min"] = min(sc["saving_total"] for sc in scenarios)
    summary["saving_max"] = max(sc["saving_total"] for sc in scenarios)

    payload = {
        "summary": summary,
        "tasks": avancor,
        "scenarios": scenarios,
        "unpaid_tasks": sorted(unpaid, key=lambda r: -r["our_hours"]),
        "unpaid_by_type": sorted(unpaid_by_type.values(), key=lambda a: -a["hours"]),
        "by_component": sorted(by_component.values(), key=lambda a: -a["saving"]),
        "timeline": timeline,
        "timesheet_per_task": ts["per_task"],
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    safe_print("OK dataset written")
    safe_print("tasks total=%d paid=%d priced=%d" % (
        summary["tasks_total"], summary["tasks_paid"], summary["tasks_priced"]))
    safe_print("base rate = %.0f RUB/hour; distribution=%s" % (base_rate, rate_counts))
    safe_print("our hours (priced) = %.1f ; avancor norm-hours = %.1f" % (
        summary["our_hours_priced"], summary["avancor_norm_hours_priced"]))
    safe_print("fact = %d RUB ; hypo = %d RUB ; saving = %d RUB (%.1f%%)" % (
        summary["fact_cost_total"], summary["hypo_cost_total"],
        summary["saving_total"], summary["saving_pct"]))
    safe_print("timesheet: files=%d hours=%.1f tasks=%d" % (
        len(ts["files"]), summary["timesheet_hours_total"], summary["timesheet_tasks"]))
    safe_print("")
    safe_print("free tasks: %d total = %d billable (%.1f h) + %d warranty (%.1f h) + %d without hours" % (
        summary["tasks_unpaid"], summary["unpaid_billable_tasks"], summary["unpaid_billable_hours"],
        summary["unpaid_warranty_tasks"], summary["unpaid_warranty_hours"],
        summary["unpaid_no_hours_tasks"]))
    safe_print("")
    safe_print("%-16s %-9s %-9s %12s %12s %12s" % (
        "SCENARIO", "OVERHEAD", "SUPPORT", "PAID_SAVE", "FREE_HYPO", "TOTAL_SAVE"))
    for sc in scenarios:
        safe_print("%-16s x%-8.1f %-8d%% %12d %12d %12d" % (
            sc["id"], sc["overhead"], sc["support_pct"],
            sc["paid_saving"], sc["free_hypo"], sc["saving_total"]))


if __name__ == "__main__":
    sys.exit(main())
