#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import urllib.parse
import urllib.request

queries = [
    "прогнозирование спроса",
    "demand planner",
    "планирование спроса",
    "Head of Demand",
    "руководитель планирования спроса",
    "S&OP",
    "demand planning",
]
base = "https://api.hh.ru/vacancies"
seen = {}
for q in queries:
    url = (
        f"{base}?text={urllib.parse.quote(q)}&area=1&per_page=50"
        f"&order_by=publication_time&period=3"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "AnyaJobBot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    for v in data.get("items", []):
        vid = v["id"]
        if vid in seen:
            continue
        seen[vid] = {
            "id": vid,
            "name": v.get("name"),
            "employer": (v.get("employer") or {}).get("name"),
            "published_at": v.get("published_at"),
            "salary": v.get("salary"),
            "url": v.get("alternate_url"),
        }

today = [x for x in seen.values() if (x["published_at"] or "").startswith("2026-09-09")]
print("TODAY 2026-09-09 count", len(today))
for x in sorted(today, key=lambda z: z["published_at"] or "", reverse=True):
    sal = x["salary"]
    sal_s = ""
    if sal:
        sal_s = f"{sal.get('from')}-{sal.get('to')} {sal.get('currency')} gross={sal.get('gross')}"
    print("-", x["published_at"], "|", x["employer"], "|", x["name"], "|", sal_s)
    print(" ", x["url"])

print("--- ALL recent unique (top 20 by date) ---")
recent = sorted(seen.values(), key=lambda x: x["published_at"] or "", reverse=True)[:20]
for x in recent:
    print(x["published_at"][:16], "|", x["employer"], "::", x["name"])
