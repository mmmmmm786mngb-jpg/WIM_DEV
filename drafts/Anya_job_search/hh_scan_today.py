#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan hh.ru for demand-related vacancies published recently."""

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

queries = [
    "прогнозирование спроса",
    "demand planner",
    "планирование спроса",
    "Head of Demand",
    "руководитель планирования спроса",
    "руководитель направления прогнозированию",
    "S&OP",
    "demand planning",
    "аналитик планирования продаж",
]
base = "https://api.hh.ru/vacancies"
seen = {}

for q in queries:
    params = urllib.parse.urlencode(
        {
            "text": q,
            "area": 1,
            "per_page": 50,
            "order_by": "publication_time",
            "period": 2,
        }
    )
    url = f"{base}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "AnyaJobBot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = json.load(resp)
    except Exception as e:
        print("ERR", q, e)
        continue
    for v in data.get("items", []):
        vid = v["id"]
        if vid in seen:
            continue
        sal = v.get("salary") or {}
        seen[vid] = {
            "id": vid,
            "name": v.get("name"),
            "employer": (v.get("employer") or {}).get("name"),
            "published_at": v.get("published_at"),
            "salary_from": sal.get("from"),
            "salary_to": sal.get("to"),
            "currency": sal.get("currency"),
            "gross": sal.get("gross"),
            "url": v.get("alternate_url"),
            "schedule": (v.get("schedule") or {}).get("name"),
        }

today_prefix = "2026-09-10"
yesterday = "2026-09-09"
today = [x for x in seen.values() if (x["published_at"] or "").startswith(today_prefix)]
yest = [x for x in seen.values() if (x["published_at"] or "").startswith(yesterday)]

print("=== TODAY", today_prefix, "count", len(today), "===")
for x in sorted(today, key=lambda z: z["published_at"] or "", reverse=True):
    sal = ""
    if x["salary_from"] or x["salary_to"]:
        sal = f"{x['salary_from']}-{x['salary_to']} {x['currency']} gross={x['gross']}"
    print(x["published_at"], "|", x["employer"], "|", x["name"], "|", sal)
    print(" ", x["url"])

print("\n=== YESTERDAY", yesterday, "count", len(yest), "(for context) ===")
for x in sorted(yest, key=lambda z: z["published_at"] or "", reverse=True)[:12]:
    print(x["published_at"][:16], "|", x["employer"], "::", x["name"])

print("\n=== TOP 20 by publish time (any of last 2 days pool) ===")
recent = sorted(seen.values(), key=lambda x: x["published_at"] or "", reverse=True)[:20]
for x in recent:
    print(x["published_at"][:16], "|", x["employer"], "::", x["name"])
