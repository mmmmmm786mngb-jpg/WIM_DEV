#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Разбор JSON-логов проверки цен покупки РОСТ и сборка HTML-отчета.
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "Тестирование" / "RostPurchasePriceCheck"
SOURCES = [
    ("day", ROOT / "rost_purchase_prices_20261016.json"),
    ("month", ROOT / "rost_purchase_prices_20260917.json"),
]
OUT_HTML = ROOT / "purchase_price_analysis.html"
CACHE_TTLS = (20, 30, 40, 50, 60)
CACHE_BUCKETS = (
    (0.05, "до 0,05%", "#067647"),
    (0.20, "0,05-0,2%", "#ca8a04"),
    (0.50, "0,2-0,5%", "#ea580c"),
    (2.00, "0,5-2%", "#dc2626"),
    (None, "больше 2%", "#7f1d1d"),
)


def parse_dt(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")


def fmt_dt(value):
    return parse_dt(value).strftime("%d.%m.%Y %H:%M:%S")


def fmt_day(value):
    return parse_dt(value).strftime("%d.%m.%Y")


def fmt_time(value):
    return parse_dt(value).strftime("%H:%M:%S")


def fmt_num(value, digits=0):
    text = f"{value:,.{digits}f}"
    return text.replace(",", " ")


def fmt_pct(value):
    return f"{value:.4f}".replace(".", ",") + "%"


def fmt_quote(value):
    return f"{value:.6f}".rstrip("0").rstrip(".").replace(".", ",")


def quote_key(value):
    return round(float(value), 6)


def median(values):
    if not values:
        return 0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def percentile(values, ratio):
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * ratio))))
    return ordered[index]


def esc(value):
    return (str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def asset_kind(code):
    if code.startswith("ОФЗ"):
        return "ОФЗ"
    if "ETF" in code:
        return "ETF"
    return "ПИФ"


def bucket_index(deviation):
    for index, (limit, _title, _color) in enumerate(CACHE_BUCKETS):
        if limit is None or deviation <= limit:
            return index
    return len(CACHE_BUCKETS) - 1


def shortest_ttl(seconds):
    for ttl in CACHE_TTLS:
        if seconds <= ttl:
            return ttl
    return None


def analyze(data):
    iterations = data["iterations"]
    asset_rows = []
    order_stats = {
        "total": 0,
        "compared": 0,
        "deleted": 0,
        "unposted": 0,
    }
    responsibles = defaultdict(int)
    by_day = {}
    by_asset = {}
    gaps = []
    durations = []
    minutes = defaultdict(int)
    cross = {
        "pairs": 0,
        "same": 0,
        "changed": 0,
        "mixed": 0,
        "changes": [],
    }
    previous_by_day_asset = {}
    differing = []

    for iteration in iterations:
        started = parse_dt(iteration["startedAt"])
        finished = parse_dt(iteration["finishedAt"])
        durations.append((finished - started).total_seconds())
        day_key = started.strftime("%Y-%m-%d")
        bucket = f"{started.hour:02d}:{started.minute // 10 * 10:02d}"
        minutes[bucket] += 1

        day = by_day.setdefault(day_key, {
            "iterations": 0,
            "orders": 0,
            "comparable": 0,
            "same": 0,
            "different": 0,
            "single": 0,
            "max_deviation": 0,
        })
        day["iterations"] += 1
        day["orders"] += iteration["ordersTotal"]

        order_stats["total"] += iteration["ordersTotal"]
        order_stats["compared"] += iteration["ordersCompared"]

        orders_by_asset = defaultdict(list)
        for order in iteration["orders"]:
            orders_by_asset[order["isin"]].append(order)
            if order["deletionMark"]:
                order_stats["deleted"] += 1
            if not order["posted"]:
                order_stats["unposted"] += 1
            if order["responsible"]:
                responsibles[order["responsible"]] += 1

        for asset in iteration["assets"]:
            row = {
                "day": day_key,
                "index": iteration["index"],
                "started": iteration["startedAt"],
                "finished": iteration["finishedAt"],
                "asset": asset["asset"],
                "code": asset["assetCode"],
                "isin": asset["isin"],
                "orders": asset["ordersCompared"],
                "distinct": asset["distinctQuotes"],
                "min": float(asset["minQuote"]),
                "max": float(asset["maxQuote"]),
                "deviation": float(asset["deviationPercent"]),
                "verdict": asset["verdict"],
            }
            comparable = row["orders"] >= 2
            if comparable:
                day["comparable"] += 1
            if row["verdict"] == "Одинаковая":
                day["same"] += 1
            elif row["verdict"] == "Разные цены":
                day["different"] += 1
                day["max_deviation"] = max(day["max_deviation"], row["deviation"])
            elif row["verdict"] == "Одна заявка":
                day["single"] += 1

            book = by_asset.setdefault(row["isin"], {
                "asset": row["asset"],
                "code": row["code"],
                "isin": row["isin"],
                "same": 0,
                "different": 0,
                "single": 0,
                "deviations": [],
                "max_deviation": 0,
            })
            if row["verdict"] == "Одинаковая":
                book["same"] += 1
            elif row["verdict"] == "Разные цены":
                book["different"] += 1
                book["deviations"].append(row["deviation"])
                book["max_deviation"] = max(book["max_deviation"], row["deviation"])
            elif row["verdict"] == "Одна заявка":
                book["single"] += 1

            compared_orders = [item for item in orders_by_asset[row["isin"]] if item["includedInComparison"]]
            compared_orders.sort(key=lambda item: (item["date"], item["number"]))
            row["points"] = [(parse_dt(item["date"]), float(item["quote"])) for item in compared_orders]
            row["safe_cache"] = (
                cache_seconds_without_change(row["points"]) if row["verdict"] == "Разные цены" else None
            )
            counts = defaultdict(int)
            sequence = []
            for item in compared_orders:
                key = quote_key(item["quote"])
                counts[key] += 1
                sequence.append(key)
            row["quote_counts"] = sorted(counts.items())
            row["sequence"] = sequence
            row["monotonic"] = sequence == sorted(sequence) or sequence == sorted(sequence, reverse=True)
            if row["verdict"] == "Разные цены":
                differing.append(row)
            asset_rows.append(row)

            stable_quote = sequence[0] if sequence and len(set(sequence)) == 1 else None
            prev_key = (day_key, row["isin"])
            previous = previous_by_day_asset.get(prev_key)
            if previous is not None and sequence:
                previous_quote, previous_time = previous
                near = (started - previous_time).total_seconds() <= 20 * 60
                if near:
                    cross["pairs"] += 1
                    if previous_quote is None or stable_quote is None:
                        cross["mixed"] += 1
                    elif previous_quote == stable_quote:
                        cross["same"] += 1
                    else:
                        cross["changed"] += 1
                        base = previous_quote if previous_quote else 0
                        change = ((stable_quote - previous_quote) / base * 100) if base else 0
                        cross["changes"].append(abs(change))
            if sequence:
                previous_by_day_asset[prev_key] = (stable_quote, started)

        if len(iterations) > 1:
            pass

    ordered_iterations = sorted(iterations, key=lambda item: item["startedAt"])
    for left, right in zip(ordered_iterations, ordered_iterations[1:]):
        delta = (parse_dt(right["startedAt"]) - parse_dt(left["startedAt"])).total_seconds()
        if 0 < delta <= 40 * 60:
            gaps.append(delta)

    verdicts = defaultdict(int)
    for row in asset_rows:
        verdicts[row["verdict"]] += 1

    deviations = [row["deviation"] for row in differing]
    distinct_counts = defaultdict(int)
    monotonic_count = 0
    for row in differing:
        distinct_counts[row["distinct"]] += 1
        if row["monotonic"]:
            monotonic_count += 1

    comparable = verdicts["Одинаковая"] + verdicts["Разные цены"]
    cache = {ttl: cache_effect(asset_rows, ttl) for ttl in CACHE_TTLS}
    return {
        "period_start": data["periodStart"],
        "period_end": data["periodEnd"],
        "gap": data["gapSeconds"],
        "generated": data["generatedAt"],
        "iterations": len(iterations),
        "orders": order_stats,
        "verdicts": dict(verdicts),
        "comparable": comparable,
        "different_share": (verdicts["Разные цены"] / comparable * 100) if comparable else 0,
        "deviations": deviations,
        "distinct_counts": dict(distinct_counts),
        "monotonic": monotonic_count,
        "by_day": by_day,
        "by_asset": by_asset,
        "minutes": minutes,
        "gaps": gaps,
        "durations": durations,
        "cross": cross,
        "differing": differing,
        "responsibles": dict(responsibles),
        "cache": cache,
    }


def cache_seconds_without_change(points):
    """Самый длинный целый срок кеша без подмены цены. None, если чужая цена уже в ту же секунду."""
    if len(points) < 2:
        return None
    span = int((points[-1][0] - points[0][0]).total_seconds())
    last_safe = None
    for ttl in range(0, span + 1):
        if cache_substitutions(points, ttl):
            break
        last_safe = ttl
    return last_safe


def cache_substitutions(points, ttl):
    """Прогон кеша 1.18: цена действует, пока с момента проверки не прошло больше ttl секунд."""
    cached_quote = None
    cached_at = None
    hits = []
    for moment, quote in points:
        if cached_at is not None and (moment - cached_at).total_seconds() <= ttl:
            if quote_key(quote) != quote_key(cached_quote):
                low = min(cached_quote, quote)
                high = max(cached_quote, quote)
                deviation = (high - low) / low * 100 if low else 0
                hits.append({
                    "seconds": (moment - cached_at).total_seconds(),
                    "book": quote,
                    "cached": cached_quote,
                    "deviation": deviation,
                })
        else:
            cached_quote = quote
            cached_at = moment
    return hits


def cache_effect(rows, ttl):
    deviations = []
    groups = 0
    untouched = 0
    differing_groups = 0
    buckets = [0 for _bucket in CACHE_BUCKETS]
    by_kind = {}
    cases = []
    for row in rows:
        if row["verdict"] == "Разные цены":
            differing_groups += 1
        hits = cache_substitutions(row.get("points", []), ttl)
        if not hits:
            if row["verdict"] == "Разные цены":
                untouched += 1
            continue
        groups += 1
        kind = asset_kind(row["code"])
        kind_book = by_kind.setdefault(kind, {"orders": 0, "groups": 0, "deviations": []})
        kind_book["groups"] += 1
        worst = max(hits, key=lambda item: item["deviation"])
        cases.append({
            "started": row["started"],
            "code": row["code"],
            "isin": row["isin"],
            "orders": len(hits),
            "book": worst["book"],
            "cached": worst["cached"],
            "seconds": worst["seconds"],
            "deviation": worst["deviation"],
            "ttl_from": shortest_ttl(worst["seconds"]),
            "safe_cache": row.get("safe_cache"),
        })
        for hit in hits:
            deviations.append(hit["deviation"])
            buckets[bucket_index(hit["deviation"])] += 1
            kind_book["orders"] += 1
            kind_book["deviations"].append(hit["deviation"])
    cases.sort(key=lambda item: (-item["deviation"], item["started"]))
    return {
        "ttl": ttl,
        "orders": len(deviations),
        "groups": groups,
        "untouched": untouched,
        "differing_groups": differing_groups,
        "median": median(deviations),
        "p90": percentile(deviations, 0.9),
        "max": max(deviations, default=0),
        "buckets": buckets,
        "by_kind": by_kind,
        "cases": cases,
    }


def bars(days):
    peak = max((item["different"] for item in days.values()), default=1) or 1
    rows = []
    for key in sorted(days):
        item = days[key]
        width = int(round(item["different"] / peak * 100))
        label = datetime.strptime(key, "%Y-%m-%d").strftime("%d.%m")
        rows.append(
            "<div class='bar-row'>"
            f"<div class='bar-label'>{label}</div>"
            f"<div class='bar-track'><div class='bar-fill' style='width:{width}%'></div></div>"
            f"<div class='bar-value'>{item['different']}</div>"
            "</div>"
        )
    return "\n".join(rows)


def safe_cache_text(value):
    if value is None:
        return "нет"
    return fmt_num(value, 0)


def safe_cache_sentence(rows):
    total = len(rows)
    present = [row["safe_cache"] for row in rows if row.get("safe_cache") is not None]
    missing = total - len(present)
    if not total:
        return "Расхождений нет."
    if not present:
        return (
            f"Ни в одном из {fmt_num(total)} запусков нет срока кеша без подмены: "
            "другая цена стоит уже в ту же секунду."
        )
    return (
        f"Срок кеша без единой подмены есть в {fmt_num(len(present))} запусках из {fmt_num(total)}: "
        f"от {fmt_num(min(present), 0)} до {fmt_num(max(present), 0)} с, "
        f"медиана {fmt_num(median(present), 0)} с. "
        f"В остальных {fmt_num(missing)} другая цена стоит уже в ту же секунду, и такого срока нет."
    )


def quote_text(row):
    parts = []
    for quote, count in row["quote_counts"]:
        parts.append(f"{fmt_quote(quote)} x {count}")
    return ", ".join(parts)


def differing_table(rows, limit=None):
    shown = sorted(rows, key=lambda item: (-item["deviation"], item["started"]))
    if limit:
        shown = shown[:limit]
    body = []
    for row in shown:
        walk = "цена шла в одну сторону" if row["monotonic"] else "цена колебалась"
        body.append(
            "<tr>"
            f"<td>{esc(fmt_dt(row['started']))}</td>"
            f"<td>{esc(row['code'])}<div class='muted'>{esc(row['isin'])}</div></td>"
            f"<td class='num'>{row['orders']}</td>"
            f"<td class='num'>{row['distinct']}</td>"
            f"<td class='num'>{esc(fmt_quote(row['min']))}</td>"
            f"<td class='num'>{esc(fmt_quote(row['max']))}</td>"
            f"<td class='num bad'>{esc(fmt_pct(row['deviation']))}</td>"
            f"<td class='num'>{esc(safe_cache_text(row.get('safe_cache')))}</td>"
            f"<td>{esc(quote_text(row))}<div class='muted'>{walk}</div></td>"
            "</tr>"
        )
    if not body:
        body.append("<tr><td colspan='9'>Расхождений нет.</td></tr>")
    return "\n".join(body)


def asset_table(books):
    ranked = sorted(
        books.values(),
        key=lambda item: (-item["different"], -item["max_deviation"], item["code"]),
    )
    body = []
    for item in ranked:
        if item["different"] == 0 and item["same"] == 0:
            continue
        compared = item["same"] + item["different"]
        share = item["different"] / compared * 100 if compared else 0
        typical = median(item["deviations"]) if item["deviations"] else 0
        body.append(
            "<tr>"
            f"<td>{esc(item['code'])}<div class='muted'>{esc(item['asset'])}</div></td>"
            f"<td class='num'>{item['same']}</td>"
            f"<td class='num'>{item['different']}</td>"
            f"<td class='num'>{item['single']}</td>"
            f"<td class='num'>{fmt_num(share, 1).replace('.', ',')}%</td>"
            f"<td class='num'>{esc(fmt_pct(typical) if item['deviations'] else '-')}</td>"
            f"<td class='num'>{esc(fmt_pct(item['max_deviation']) if item['deviations'] else '-')}</td>"
            "</tr>"
        )
    return "\n".join(body)


def day_table(days):
    body = []
    for key in sorted(days):
        item = days[key]
        share = item["different"] / item["comparable"] * 100 if item["comparable"] else 0
        body.append(
            "<tr>"
            f"<td>{datetime.strptime(key, '%Y-%m-%d').strftime('%d.%m.%Y')}</td>"
            f"<td class='num'>{item['iterations']}</td>"
            f"<td class='num'>{fmt_num(item['orders'])}</td>"
            f"<td class='num'>{item['comparable']}</td>"
            f"<td class='num'>{item['same']}</td>"
            f"<td class='num'>{item['different']}</td>"
            f"<td class='num'>{fmt_num(share, 1).replace('.', ',')}%</td>"
            f"<td class='num'>{esc(fmt_pct(item['max_deviation']) if item['different'] else '-')}</td>"
            "</tr>"
        )
    return "\n".join(body)


def hour_table(minutes):
    body = []
    for key in sorted(minutes):
        if minutes[key] == 0:
            continue
        body.append(f"<tr><td>{key}</td><td class='num'>{minutes[key]}</td></tr>")
    return "\n".join(body)


def kind_cell(stats, kind):
    book = stats["by_kind"].get(kind)
    if not book or not book["orders"]:
        return "<td class='num'>-</td><td class='num'>-</td>"
    return (
        f"<td class='num'>{fmt_num(book['orders'])}</td>"
        f"<td class='num'>{esc(fmt_pct(max(book['deviations'])))}</td>"
    )


def cache_table(series):
    body = []
    for ttl in CACHE_TTLS:
        item = series[ttl]
        mark = " class='proposed'" if ttl == 60 else ""
        note = "сейчас в 1.18" if ttl == 60 else ""
        body.append(
            f"<tr{mark}>"
            f"<td>{ttl} с<div class='muted'>{note}</div></td>"
            f"<td class='num'>{fmt_num(item['orders'])}</td>"
            f"<td class='num'>{fmt_num(item['groups'])}</td>"
            f"<td class='num'>{esc(fmt_pct(item['median']) if item['orders'] else '-')}</td>"
            f"<td class='num'>{esc(fmt_pct(item['p90']) if item['orders'] else '-')}</td>"
            f"<td class='num bad'>{esc(fmt_pct(item['max']) if item['orders'] else '-')}</td>"
            f"{kind_cell(item, 'ОФЗ')}"
            f"{kind_cell(item, 'ПИФ')}"
            f"{kind_cell(item, 'ETF')}"
            f"<td class='num'>{fmt_num(item['untouched'])}</td>"
            "</tr>"
        )
    return "\n".join(body)


def cache_chart(series):
    width = 760
    height = 280
    left = 48
    right = 16
    top = 28
    bottom = 36
    plot_width = width - left - right
    plot_height = height - top - bottom
    peak = max((series[ttl]["orders"] for ttl in CACHE_TTLS), default=1) or 1
    slot = plot_width / len(CACHE_TTLS)
    bar_width = min(72, slot * 0.62)
    colors = [color for _limit, _title, color in CACHE_BUCKETS]
    parts = [
        f"<svg viewBox='0 0 {width} {height}' role='img' aria-label='Подмена цены кешем по сроку'>"
    ]
    for step in range(5):
        value = peak * step / 4
        y = top + plot_height - (plot_height * step / 4)
        label = fmt_num(round(value))
        parts.append(
            f"<line x1='{left}' y1='{y:.1f}' x2='{width - right}' y2='{y:.1f}' stroke='#e6ebf1'/>"
        )
        parts.append(
            f"<text x='{left - 8}' y='{y + 4:.1f}' text-anchor='end' class='axis'>{label}</text>"
        )
    for index, ttl in enumerate(CACHE_TTLS):
        item = series[ttl]
        x = left + slot * index + (slot - bar_width) / 2
        y = top + plot_height
        if item["orders"]:
            for bucket, color in zip(item["buckets"], colors):
                height_px = plot_height * bucket / peak
                y -= height_px
                parts.append(
                    f"<rect x='{x:.1f}' y='{y:.1f}' width='{bar_width:.1f}' height='{height_px:.1f}' fill='{color}'/>"
                )
        else:
            parts.append(
                f"<rect x='{x:.1f}' y='{top + plot_height - 2}' width='{bar_width:.1f}' height='2' fill='#e6ebf1'/>"
            )
        label_y = min(y, top + plot_height) - 6
        parts.append(
            f"<text x='{x + bar_width / 2:.1f}' y='{label_y:.1f}' text-anchor='middle' class='bar-num'>{fmt_num(item['orders'])}</text>"
        )
        parts.append(
            f"<text x='{x + bar_width / 2:.1f}' y='{height - 12}' text-anchor='middle' class='axis'>{ttl} с</text>"
        )
    parts.append("</svg>")
    return "\n".join(parts)


def cache_legend():
    items = []
    for _limit, title, color in CACHE_BUCKETS:
        items.append(f"<span class='legend'><i style='background:{color}'></i>{title}</span>")
    return "\n".join(items)


def cache_cases(cases, limit):
    shown = cases[:limit]
    body = []
    for row in shown:
        if row["ttl_from"] == CACHE_TTLS[0]:
            reach = "при любом из этих сроков"
        else:
            reach = f"от {row['ttl_from']} с"
        body.append(
            "<tr>"
            f"<td>{esc(fmt_dt(row['started']))}</td>"
            f"<td>{esc(row['code'])}<div class='muted'>{esc(row['isin'])}</div></td>"
            f"<td class='num'>{row['orders']}</td>"
            f"<td class='num'>{esc(fmt_quote(row['cached']))}</td>"
            f"<td class='num'>{esc(fmt_quote(row['book']))}</td>"
            f"<td class='num'>{fmt_num(row['seconds'], 0)}</td>"
            f"<td class='num bad'>{esc(fmt_pct(row['deviation']))}</td>"
            f"<td class='num'>{esc(safe_cache_text(row.get('safe_cache')))}</td>"
            f"<td>{reach}</td>"
            "</tr>"
        )
    if not body:
        body.append("<tr><td colspan='9'>Кеш не подменил бы ни одной цены.</td></tr>")
    return "\n".join(body)


def cache_section(day, month):
    month_60 = month["cache"][60]
    month_20 = month["cache"][20]
    day_60 = day["cache"][60]
    worst = month_60["cases"][0] if month_60["cases"] else None
    tiny = month_60["buckets"][0]
    pif_60 = month_60["by_kind"].get("ПИФ", {}).get("orders", 0)
    pif_20 = month_20["by_kind"].get("ПИФ", {}).get("orders", 0)
    ofz_60 = month_60["by_kind"].get("ОФЗ", {}).get("orders", 0)
    worst_text = ""
    if worst:
        worst_text = (
            f" Самая большая, {esc(fmt_pct(worst['deviation']))} у {esc(worst['code'])},"
            f" возникает через {fmt_num(worst['seconds'], 0)} с после проверки"
            f" и попадает во все пять сроков."
        )
    return f"""
<h2>Какую цену записал бы кеш</h2>
<div class="panel">
<p>Кеш версии 1.18 хранит цену с момента проверки стакана. Пока с этой проверки не прошло больше срока, следующее поручение той же бумаги получает сохраненную цену и в стакан не ходит. Когда срок вышел, строка удаляется: поручение снова спрашивает стакан и кладет в кеш уже новую цену. В начале каждого запуска кеш пустой.</p>
<p>Ниже для сроков 20, 30, 40, 50 и 60 секунд посчитано, скольким поручениям кеш записал бы другую котировку, чем стакан дал в их момент. Время берется из даты документа, точность до секунды: разница ровно в срок еще берется из кеша, на секунду больше идет новый запрос. Подмена считается как (большая котировка - меньшая) / меньшая. Пачка та же, что в остальном отчете: пауза между поручениями не больше {month['gap']} секунд.</p>
<p>При сроке 60 секунд, как сейчас в 1.18, за месяц кеш подменил бы цену в {fmt_num(month_60['orders'])} поручениях, это {fmt_num(month_60['groups'])} запусков из {fmt_num(month_60['differing_groups'])} с разной ценой. Медиана подмены {esc(fmt_pct(month_60['median']))}, 90-й перцентиль {esc(fmt_pct(month_60['p90']))}, максимум {esc(fmt_pct(month_60['max']))}. Из этих поручений {fmt_num(tiny)} отличаются от стакана не больше чем на 0,05%. Основной объем дают длинные пачки ОФЗ: {fmt_num(ofz_60)} поручений. У ПИФ акций таких поручений {fmt_num(pif_60)}.{worst_text}</p>
<p>Срок 20 секунд оставляет {fmt_num(month_20['orders'])} поручений, из них ПИФ акций {fmt_num(pif_20)}. Максимум тот же, {esc(fmt_pct(month_20['max']))}: он случается раньше 20 секунд. 16 октября при 60 секундах: {fmt_num(day_60['orders'])} поручений в {fmt_num(day_60['groups'])} запусках, максимум {esc(fmt_pct(day_60['max']))}. Число запусков по срокам растет не строго, потому что более длинный срок сдвигает момент, когда кеш сбрасывается и берет новую цену.</p>
<p>{safe_cache_sentence(month['differing'])} Общего срока на все запуски нет.</p>
</div>
<h3>Месяц, подмена по сроку кеша</h3>
<p>Высота столбца - число поручений, которым записали бы цену кеша вместо цены стакана. Цвет - размер этой подмены.</p>
<div class="panel chart">{cache_chart(month['cache'])}
<div class="legend-row">{cache_legend()}</div>
</div>
<div class="wrap"><table>
<thead><tr>
<th>Срок</th>
<th class="num">Поручений</th>
<th class="num">Запусков</th>
<th class="num">Медиана</th>
<th class="num">90%</th>
<th class="num">Максимум</th>
<th class="num">ОФЗ, шт</th>
<th class="num">ОФЗ, макс</th>
<th class="num">ПИФ, шт</th>
<th class="num">ПИФ, макс</th>
<th class="num">ETF, шт</th>
<th class="num">ETF, макс</th>
<th class="num">Сдвиг после срока</th>
</tr></thead>
<tbody>
{cache_table(month['cache'])}
</tbody></table></div>
<p class="muted">Столбец «Сдвиг после срока» - запуски, где котировки бумаги разошлись, но уже после истечения кеша. Там обработка сходила бы в стакан заново и записала новую цену. Строка 60 секунд выделена: такой срок стоит в версии 1.18.</p>

<h3>16 октября, тот же расчет</h3>
<div class="panel chart">{cache_chart(day['cache'])}
<div class="legend-row">{cache_legend()}</div>
</div>
<div class="wrap"><table>
<thead><tr>
<th>Срок</th>
<th class="num">Поручений</th>
<th class="num">Запусков</th>
<th class="num">Медиана</th>
<th class="num">90%</th>
<th class="num">Максимум</th>
<th class="num">ОФЗ, шт</th>
<th class="num">ОФЗ, макс</th>
<th class="num">ПИФ, шт</th>
<th class="num">ПИФ, макс</th>
<th class="num">ETF, шт</th>
<th class="num">ETF, макс</th>
<th class="num">Сдвиг после срока</th>
</tr></thead>
<tbody>
{cache_table(day['cache'])}
</tbody></table></div>

<h3>Крупнейшие подмены при сроке 60 секунд</h3>
<p>Берется самая большая подмена внутри запуска. «Секунд» - сколько прошло с проверки, цену которой кеш еще держит. «Без подмены, с» - самый длинный срок кеша, при котором в этом запуске у бумаги не меняется ни одна цена: на секунду дольше кеш уже пишет чужую. «Нет» значит, что другая котировка стоит в ту же секунду, и такого срока нет. Колонка «С какого срока» показывает, с какого из пяти сроков эта подмена уже случается.</p>
<div class="wrap"><table>
<thead><tr><th>Начало запуска</th><th>Бумага</th><th class="num">Поручений</th><th class="num">Цена кеша</th><th class="num">Цена стакана</th><th class="num">Секунд</th><th class="num">Подмена</th><th class="num">Без подмены, с</th><th>С какого срока</th></tr></thead>
<tbody>
{cache_cases(month['cache'][60]['cases'], 15)}
</tbody></table></div>
"""


def conclusion(day, month):
    day_diff = day["verdicts"].get("Разные цены", 0)
    day_comp = day["comparable"]
    month_diff = month["verdicts"].get("Разные цены", 0)
    month_comp = month["comparable"]
    max_day = max(day["deviations"], default=0)
    max_month = max(month["deviations"], default=0)
    med_month = median(month["deviations"])
    p90 = percentile(month["deviations"], 0.9)
    over_two = sum(1 for value in month["deviations"] if value > 2)
    two_quotes = month["distinct_counts"].get(2, 0)
    mono = month["monotonic"]
    cross_changed = month["cross"]["changed"]
    cross_same = month["cross"]["same"]
    cross_pairs = cross_same + cross_changed
    cross_share = cross_changed / cross_pairs * 100 if cross_pairs else 0
    return {
        "day_diff": day_diff,
        "day_comp": day_comp,
        "month_diff": month_diff,
        "month_comp": month_comp,
        "max_day": max_day,
        "max_month": max_month,
        "med_month": med_month,
        "p90": p90,
        "over_two": over_two,
        "two_quotes": two_quotes,
        "mono": mono,
        "cross_changed": cross_changed,
        "cross_same": cross_same,
        "cross_share": cross_share,
        "cross_median": median(month["cross"]["changes"]),
    }


def render(day, month, facts):
    month_days = len(month["by_day"])
    gap_med = median(month["gaps"]) / 60
    dur_med = median(month["durations"])
    responsible = ", ".join(sorted(month["responsibles"])) or "не указан"
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Цены покупки РОСТ: одинаковая котировка внутри запуска</title>
<style>
body {{ margin: 0; background: #f4f6f8; color: #1c2430; font: 16px/1.5 "Segoe UI", sans-serif; }}
main {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 64px; }}
h1 {{ font-size: 32px; line-height: 1.2; margin: 0 0 8px; }}
h2 {{ font-size: 22px; margin: 36px 0 12px; }}
h3 {{ font-size: 18px; margin: 24px 0 8px; }}
p {{ margin: 8px 0; }}
.lead {{ color: #4b5565; max-width: 860px; }}
.cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 20px 0; }}
.card {{ background: #fff; border: 1px solid #e3e8ee; border-radius: 12px; padding: 16px; }}
.card .k {{ color: #667085; font-size: 13px; }}
.card .v {{ font-size: 28px; font-weight: 650; margin-top: 4px; }}
.card .s {{ color: #667085; font-size: 13px; }}
.bad {{ color: #b42318; }}
.good {{ color: #067647; }}
.panel {{ background: #fff; border: 1px solid #e3e8ee; border-radius: 12px; padding: 18px 20px; margin: 14px 0; }}
.conclusion {{ background: #eef6ff; border: 1px solid #c9def8; }}
.warn {{ background: #fff7ed; border: 1px solid #fed7aa; }}
table {{ width: 100%; border-collapse: collapse; background: #fff; }}
th, td {{ border-bottom: 1px solid #e6ebf1; padding: 8px 10px; text-align: left; vertical-align: top; }}
th {{ background: #f8fafc; font-size: 13px; color: #475467; }}
td.num, th.num {{ text-align: right; white-space: nowrap; }}
.muted {{ color: #667085; font-size: 12px; }}
.bar-row {{ display: grid; grid-template-columns: 52px 1fr 36px; gap: 8px; align-items: center; margin: 3px 0; }}
.bar-label, .bar-value {{ font-size: 12px; color: #475467; }}
.bar-track {{ background: #eef2f6; height: 10px; border-radius: 6px; }}
.bar-fill {{ background: #b42318; height: 10px; border-radius: 6px; }}
.chart svg {{ width: 100%; height: auto; display: block; }}
.chart .axis {{ fill: #667085; font-size: 12px; }}
.chart .bar-num {{ fill: #1c2430; font-size: 12px; font-weight: 650; }}
.legend-row {{ display: flex; flex-wrap: wrap; gap: 14px; margin-top: 8px; }}
.legend {{ display: inline-flex; align-items: center; gap: 6px; color: #475467; font-size: 13px; }}
.legend i {{ width: 12px; height: 12px; border-radius: 3px; display: inline-block; }}
tr.proposed td {{ background: #eef6ff; }}
.wrap {{ overflow-x: auto; border: 1px solid #e3e8ee; border-radius: 12px; }}
ul {{ margin: 8px 0 8px 20px; }}
@media (max-width: 900px) {{ .cards {{ grid-template-columns: 1fr 1fr; }} }}
</style>
</head>
<body>
<main>
<h1>Одинаковая ли цена у одной бумаги внутри запуска покупки РОСТ</h1>
<p class="lead">Сравнивается котировка, которую обработка записала в поручение. Один запуск - пачка поручений с паузой не больше {month['gap']} секунд. В сравнение входят только проведенные поручения без пометки удаления. Период месяца: {esc(fmt_day(month['period_start']))} - {esc(fmt_day(month['period_end']))}. День 16.10 разобран отдельно и входит в этот месяц.</p>

<div class="panel conclusion">
<h2 style="margin-top:0">Вывод</h2>
<p>Внутри одного запуска цена одной бумаги чаще всего одна и та же. За месяц из {fmt_num(facts['month_comp'])} сравнений, где заявок было две и больше, разошлись {fmt_num(facts['month_diff'])}, это {fmt_num(facts['month_diff'] / facts['month_comp'] * 100, 1).replace('.', ',')}%. 16 октября таких случаев {facts['day_diff']} из {facts['day_comp']}.</p>
<p>Общая медиана отклонения {esc(fmt_pct(facts['med_month']))}, но она смешана из разных бумаг. У ОФЗ, когда цены расходятся, это шаг стакана: типично 0,02-0,08%, максимум по выпускам около 0,3%. У ПИФ акций типичное отклонение 0,43%, 90-й перцентиль по всем бумагам {esc(fmt_pct(facts['p90']))}. Больше 2% случилось один раз: 22.09, ПИФ акций, котировки 44,85 и 46,20, отклонение {esc(fmt_pct(facts['max_month']))}. Порог 2% в обработке сравнивает два уровня одного снимка стакана, а не котировки соседних поручений, поэтому такой сдвиг между заявками он не останавливает.</p>
<p>Из {fmt_num(facts['month_diff'])} расхождений в {fmt_num(facts['two_quotes'])} было ровно две разные котировки, в {fmt_num(facts['mono'])} цена шла в одну сторону от первой заявки к последней. Это движение стакана за те секунды, пока обработка по очереди создает поручения.</p>
<p>Между соседними запусками одного дня, если в обоих у бумаги была одна котировка, она изменилась в {fmt_num(facts['cross_changed'])} парах из {fmt_num(facts['cross_same'] + facts['cross_changed'])} ({fmt_num(facts['cross_share'], 1).replace('.', ',')}%). Медиана этого сдвига {esc(fmt_pct(facts['cross_median']))}. Цену нельзя запомнить на все 10 минут до следующего регламента: примерно в половине следующих запусков она уже другая. Внутри текущего запуска повторный запрос чаще дает ту же цену, а если нет, то у ОФЗ расхождение на сотые доли процента.</p>
</div>

<div class="cards">
<div class="card"><div class="k">Запусков за месяц</div><div class="v">{fmt_num(month['iterations'])}</div><div class="s">{month_days} торговых дней, медиана паузы {fmt_num(gap_med, 1).replace('.', ',')} мин</div></div>
<div class="card"><div class="k">Поручений в сравнении</div><div class="v">{fmt_num(month['orders']['compared'])}</div><div class="s">всего документов {fmt_num(month['orders']['total'])}, удаленных {fmt_num(month['orders']['deleted'])}</div></div>
<div class="card"><div class="k">Бумаг с одной ценой</div><div class="v good">{fmt_num(month['verdicts'].get('Одинаковая', 0))}</div><div class="s">из {fmt_num(facts['month_comp'])} сравнений двух и более заявок</div></div>
<div class="card"><div class="k">Бумаг с разными ценами</div><div class="v bad">{fmt_num(facts['month_diff'])}</div><div class="s">максимум отклонения {esc(fmt_pct(facts['max_month']))}</div></div>
</div>

<h2>Как устроены запуски</h2>
<div class="panel">
<p>Медианная длительность пачки поручений {fmt_num(dur_med, 0)} секунд. Ответственный в поручениях: {esc(responsible)}. Удаленные и непроведенные документы в вердикт не входят: удаленных {fmt_num(month['orders']['deleted'])}, непроведенных {fmt_num(month['orders']['unposted'])}.</p>
<p>Одна заявка на бумагу внутри запуска не считается ни совпадением, ни расхождением: так было {fmt_num(month['verdicts'].get('Одна заявка', 0))} раз. Сравнивать в этом случае не с чем.</p>
</div>

<h2>16 октября</h2>
<div class="cards">
<div class="card"><div class="k">Запусков</div><div class="v">{fmt_num(day['iterations'])}</div><div class="s">{esc(fmt_day(day['period_start']))}</div></div>
<div class="card"><div class="k">Поручений в сравнении</div><div class="v">{fmt_num(day['orders']['compared'])}</div><div class="s">всего {fmt_num(day['orders']['total'])}</div></div>
<div class="card"><div class="k">Одинаковая цена</div><div class="v good">{fmt_num(day['verdicts'].get('Одинаковая', 0))}</div><div class="s">две и более заявки</div></div>
<div class="card"><div class="k">Разные цены</div><div class="v bad">{facts['day_diff']}</div><div class="s">максимум {esc(fmt_pct(facts['max_day']))}</div></div>
</div>
<p>Все расхождения этого дня. Процент считается как (максимальная котировка - минимальная) / минимальная. Колонка «Без подмены, с» - самый длинный срок кеша, при котором в этом запуске у бумаги не меняется ни одна цена. {safe_cache_sentence(day['differing'])}</p>
<div class="wrap"><table>
<thead><tr><th>Начало запуска</th><th>Бумага</th><th class="num">Заявок</th><th class="num">Цен</th><th class="num">Мин</th><th class="num">Макс</th><th class="num">Отклонение</th><th class="num">Без подмены, с</th><th>Состав котировок</th></tr></thead>
<tbody>
{differing_table(day['differing'])}
</tbody></table></div>

<h2>Месяц 17.09 - 16.10</h2>
<p>18.09 выделяется объемом: 7 659 поручений за день. В остальные дни поручений от 100 до 1 500. На долю расхождений этот день не влияет: разных цен там 5 из 41 сравнений.</p>
<h3>Сколько расхождений по дням</h3>
<p>Высота полосы - число бумаг, у которых внутри запуска оказалось больше одной котировки.</p>
<div class="panel">{bars(month['by_day'])}</div>
<div class="wrap"><table>
<thead><tr><th>День</th><th class="num">Запусков</th><th class="num">Поручений</th><th class="num">Сравнений</th><th class="num">Одинаковая</th><th class="num">Разные</th><th class="num">Доля разных</th><th class="num">Макс. отклонение</th></tr></thead>
<tbody>
{day_table(month['by_day'])}
</tbody></table></div>

<h3>По бумагам</h3>
<p>Доля считается только по запускам, где заявок на бумагу было две или больше. Типичное отклонение - медиана по тем запускам, где цены разошлись.</p>
<div class="wrap"><table>
<thead><tr><th>Бумага</th><th class="num">Одинаковая</th><th class="num">Разные</th><th class="num">Одна заявка</th><th class="num">Доля разных</th><th class="num">Типичное</th><th class="num">Максимум</th></tr></thead>
<tbody>
{asset_table(month['by_asset'])}
</tbody></table></div>

<h3>Самые большие отклонения за месяц</h3>
<p>{safe_cache_sentence(month['differing'])} Колонка «Без подмены, с» показывает этот срок по каждому запуску. На секунду дольше кеш уже пишет чужую цену.</p>
<div class="wrap"><table>
<thead><tr><th>Начало запуска</th><th>Бумага</th><th class="num">Заявок</th><th class="num">Цен</th><th class="num">Мин</th><th class="num">Макс</th><th class="num">Отклонение</th><th class="num">Без подмены, с</th><th>Состав котировок</th></tr></thead>
<tbody>
{differing_table(month['differing'], 25)}
</tbody></table></div>

<h3>В какое время идут запуски</h3>
<p>Число пачек поручений по десятиминутным отметкам. Регламент виден как повторяющиеся слоты, а не как случайные сделки в течение дня.</p>
<div class="wrap"><table>
<thead><tr><th>Время</th><th class="num">Запусков за месяц</th></tr></thead>
<tbody>
{hour_table(month['minutes'])}
</tbody></table></div>
{cache_section(day, month)}
<h2>Что из этого следует</h2>
<div class="panel warn">
<ul>
<li>Повторно запрашивать стакан на ту же бумагу внутри одного запуска почти не на что: цена совпадает в {fmt_num((facts['month_comp'] - facts['month_diff']) / facts['month_comp'] * 100, 1).replace('.', ',')}% сравнений.</li>
<li>У ОФЗ расхождение, когда оно есть, не больше нескольких десятых процента. Заметный ход дает ПИФ акций: типично 0,43%, один раз 22.09 на {esc(fmt_pct(facts['max_month']))}.</li>
<li>К следующему запуску котировка той же бумаги меняется в {fmt_num(facts['cross_share'], 1).replace('.', ',')}% пар, медиана сдвига {esc(fmt_pct(facts['cross_median']))}. Общий кэш цены на интервал регламента закроет заявки по предыдущему стакану примерно в половине случаев.</li>
<li>16 октября не выделяется на фоне месяца: {facts['day_diff']} расхождений из {facts['day_comp']} сравнений, максимум {esc(fmt_pct(facts['max_day']))}.</li>
<li>Срок кеша 60 секунд за месяц подменил бы стакан в {fmt_num(month['cache'][60]['orders'])} поручениях ({fmt_num(month['cache'][60]['groups'])} запусков). Медиана этой подмены {esc(fmt_pct(month['cache'][60]['median']))}, у {fmt_num(month['cache'][60]['buckets'][0])} поручений она не больше 0,05%. Максимум {esc(fmt_pct(month['cache'][60]['max']))} возникает через несколько секунд, поэтому срок 20 секунд оставляет его и снижает число поручений до {fmt_num(month['cache'][20]['orders'])}.</li>
</ul>
</div>
</main>
</body>
</html>
"""


def main():
    loaded = {}
    for key, path in SOURCES:
        with path.open(encoding="utf-8") as handle:
            loaded[key] = analyze(json.load(handle))
        cache_line = [
            (ttl, item["orders"], item["groups"], round(item["max"], 4))
            for ttl, item in loaded[key]["cache"].items()
        ]
        print(key, loaded[key]["iterations"], loaded[key]["verdicts"], cache_line)
    facts = conclusion(loaded["day"], loaded["month"])
    html = render(loaded["day"], loaded["month"], facts)
    OUT_HTML.write_text(html, encoding="utf-8")
    print("html", OUT_HTML.name, "bytes", OUT_HTML.stat().st_size)


if __name__ == "__main__":
    main()
