#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка HTML-отчета по задачам Аванкора (Розница ДУ) из выгрузки Jira CSV.
"""

from __future__ import annotations

import csv
import html
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

CSV_PATH = Path(__file__).with_name("VTB Capital - JIRA 2026-09-14T05_36_27+0300.csv")
OUT_PATH = Path(__file__).with_name("avancor_retail_du_report_2026-09-14.html")
HOUR_RATE = 3900

COMP_MAP = {
    "AvancoreDU": "ДУ 1.5",
    "AvancoreFinance": "ДУ 2.0",
    "AvancorePIF": "ПИФ 2.0",
}


def col_indices(header: list[str], name: str) -> list[int]:
    return [i for i, h in enumerate(header) if h == name]


def parse_created(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.split(" +")[0].strip(), "%d/%b/%y %H:%M")
    except ValueError:
        return None


def parse_ext_estimate(ext: str) -> tuple[int, int]:
    """Возвращает (нормо-часы, стоимость в рублях)."""
    if not ext:
        return 0, 0

    hours = 0
    match = re.search(r"(\d+)\s*нормо-час", ext, re.IGNORECASE)
    if match:
        hours = int(match.group(1))
    else:
        match = re.search(r"Анализ:\s*(\d+)\s*час", ext, re.IGNORECASE)
        if match:
            hours = int(match.group(1))

    cost = 0
    match = re.search(r"Стоимость составляет\s*([\d\s]+)\s*руб", ext, re.IGNORECASE)
    if match:
        cost = int(re.sub(r"\s+", "", match.group(1)))
    else:
        match = re.search(r"=\s*([\d\s]+)\s*руб", ext, re.IGNORECASE)
        if match:
            cost = int(re.sub(r"\s+", "", match.group(1)))

    if hours and not cost:
        cost = hours * HOUR_RATE
    if cost and not hours and cost % HOUR_RATE == 0:
        hours = cost // HOUR_RATE

    return hours, cost


def extract_asp_from_text(text: str) -> str:
    if not text:
        return ""
    match = re.search(r"lk\.avancore\.ru/tasks/(ASP-\d+)", text, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"ASP-\d+", text)
    return match.group(0) if match else ""


def extract_asp(
    row: list[str],
    external_ref_idx: int,
    portal_idx: int,
    desc_idx: int,
    comment_idxs: list[int],
) -> str:
    # Приоритет: External Ref (ссылка на ASP у вендора), затем Portal link
    for idx in (external_ref_idx, portal_idx, desc_idx):
        if idx < 0 or idx >= len(row):
            continue
        asp = extract_asp_from_text(row[idx] or "")
        if asp:
            return asp

    for idx in comment_idxs:
        if idx >= len(row) or not row[idx]:
            continue
        asp = extract_asp_from_text(row[idx])
        if asp:
            return asp

    return ""


def fmt_money(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def fmt_created(dt: datetime | None) -> str:
    if not dt:
        return "Не указано"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def load_tasks() -> list[dict]:
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = list(reader)

    key_i = col_indices(header, "Issue key")[0]
    summary_i = col_indices(header, "Summary")[0]
    paid_i = col_indices(header, "Custom field (Paid)")[0]
    portal_i = col_indices(header, "Custom field (Portal link)")[0]
    external_ref_cols = col_indices(header, "Custom field (External Ref)")
    external_ref_i = external_ref_cols[0] if external_ref_cols else -1
    ext_i = col_indices(header, "Custom field (Ext Estimate)")[0]
    comp_i = col_indices(header, "Component/s")[0]
    created_i = col_indices(header, "Created")[0]
    labels_i = col_indices(header, "Labels")
    desc_i = col_indices(header, "Description")[0]
    comment_i = col_indices(header, "Comment")

    tasks: list[dict] = []
    for row in rows:
        labels = [row[i] for i in labels_i if i < len(row) and row[i]]
        if "Retail_DU" not in labels:
            continue

        is_paid = (row[paid_i] or "").strip().lower() == "yes"
        hours, cost = parse_ext_estimate(row[ext_i] or "")
        if not is_paid:
            hours, cost = 0, 0

        created = parse_created(row[created_i] or "")
        component = row[comp_i] or ""
        system = COMP_MAP.get(component, component or "Не указано")

        tasks.append(
            {
                "key": row[key_i],
                "summary": (row[summary_i] or "").strip(),
                "paid": is_paid,
                "hours": hours,
                "cost": cost,
                "created": created,
                "system": system,
                "asp": extract_asp(row, external_ref_i, portal_i, desc_i, comment_i),
            }
        )

    tasks.sort(key=lambda item: item["created"] or datetime.min)
    return tasks


def build_html(tasks: list[dict]) -> str:
    total = len(tasks)
    paid_n = sum(1 for t in tasks if t["paid"])
    free_n = total - paid_n
    total_hours = sum(t["hours"] for t in tasks)
    total_cost = sum(t["cost"] for t in tasks)

    by_system: dict[str, dict] = defaultdict(lambda: {"n": 0, "paid": 0, "free": 0, "h": 0, "c": 0})
    by_month_paid: dict[str, dict] = defaultdict(lambda: {"paid_n": 0, "h": 0, "c": 0})
    by_month_all: dict[str, int] = defaultdict(int)

    created_dates = [t["created"] for t in tasks if t["created"]]
    if created_dates:
        period_start = min(created_dates).strftime("%Y-%m")
        period_end = max(created_dates).strftime("%Y-%m")
        period_label = f"{period_start} - {period_end}"
    else:
        period_label = "не определен"

    for task in tasks:
        system = by_system[task["system"]]
        system["n"] += 1
        if task["paid"]:
            system["paid"] += 1
        else:
            system["free"] += 1
        system["h"] += task["hours"]
        system["c"] += task["cost"]

        if task["created"]:
            month = task["created"].strftime("%Y-%m")
        else:
            month = "Без даты"
        by_month_all[month] += 1
        if task["paid"]:
            by_month_paid[month]["paid_n"] += 1
            by_month_paid[month]["h"] += task["hours"]
            by_month_paid[month]["c"] += task["cost"]

    system_order = sorted(by_system.keys())
    month_order = sorted(m for m in by_month_all if m != "Без даты")
    if "Без даты" in by_month_all:
        month_order.append("Без даты")

    # Fill months that have only free tasks into paid table too for continuity
    for month in month_order:
        _ = by_month_paid[month]

    detail_rows = []
    for task in tasks:
        badge = (
            '<span class="badge badge-paid">Платно</span>'
            if task["paid"]
            else '<span class="badge badge-free">Бесплатно</span>'
        )
        asp = html.escape(task["asp"] or "-")
        summary = html.escape(task["summary"])
        jira = (
            f'<a href="https://jira/browse/{html.escape(task["key"])}">'
            f'{html.escape(task["key"])}</a>'
        )
        detail_rows.append(
            "<tr>"
            f"<td>{html.escape(task['system'])}</td>"
            f"<td>{asp}</td>"
            f"<td>{summary}</td>"
            f"<td>{fmt_created(task['created'])}</td>"
            f"<td>{jira}</td>"
            f"<td>{badge}</td>"
            f"<td>{task['hours']}</td>"
            f"<td>{fmt_money(task['cost']) if task['cost'] else 0}</td>"
            "</tr>"
        )

    system_rows = []
    for name in system_order:
        stats = by_system[name]
        system_rows.append(
            "<tr>"
            f"<td>{html.escape(name)}</td>"
            f"<td>{stats['n']}</td>"
            f"<td>{stats['paid']}</td>"
            f"<td>{stats['free']}</td>"
            f"<td>{stats['h']}</td>"
            f"<td>{fmt_money(stats['c'])} руб.</td>"
            "</tr>"
        )

    month_rows = []
    for month in month_order:
        stats = by_month_paid[month]
        month_rows.append(
            "<tr>"
            f"<td>{html.escape(month)}</td>"
            f"<td>{stats['paid_n']}</td>"
            f"<td>{stats['h']}</td>"
            f"<td>{fmt_money(stats['c'])} руб.</td>"
            "</tr>"
        )

    # Conclusions
    conclusions = []
    if system_order and total_hours:
        top_system = max(system_order, key=lambda name: by_system[name]["h"])
        top = by_system[top_system]
        share_h = round(100.0 * top["h"] / total_hours, 1) if total_hours else 0
        share_c = round(100.0 * top["c"] / total_cost, 1) if total_cost else 0
        conclusions.append(
            f"<p><b>1.</b> Основная платная нагрузка пришлась на <b>{html.escape(top_system)}</b>: "
            f"{top['h']} из {total_hours} нормо-часов ({share_h}%) и "
            f"{fmt_money(top['c'])} руб. из {fmt_money(total_cost)} руб. ({share_c}%).</p>"
        )
    free_by_system = []
    for name in system_order:
        stats = by_system[name]
        if stats["free"]:
            free_by_system.append(f"{html.escape(name)}: {stats['free']} из {stats['n']}")
    if free_by_system:
        conclusions.append(
            "<p><b>2.</b> Бесплатные работы: " + "; ".join(free_by_system) + ".</p>"
        )
    if len(conclusions) < 2:
        conclusions.append(
            f"<p><b>2.</b> Средняя ставка составляет <b>{fmt_money(HOUR_RATE)} руб.</b> за нормо-час.</p>"
        )

    system_cost_labels = ", ".join(f'"{html.escape(name)}"' for name in system_order)
    system_cost_data = ", ".join(str(by_system[name]["c"]) for name in system_order)
    system_hours_data = ", ".join(str(by_system[name]["h"]) for name in system_order)
    month_labels = ", ".join(f'"{html.escape(m)}"' for m in month_order)
    month_task_counts = ", ".join(str(by_month_all[m]) for m in month_order)

    # color palette for systems
    palette = ["#6f42c1", "#17a2b8", "#0d6efd", "#20c997", "#fd7e14"]
    system_colors = ", ".join(
        f'"{palette[i % len(palette)]}"' for i in range(len(system_order))
    )
    hours_colors = ", ".join(
        f'"{["#0d6efd", "#20c997", "#6f42c1", "#17a2b8", "#fd7e14"][i % 5]}"'
        for i in range(len(system_order))
    )

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчет по затратам на Аванкор - Розница ДУ</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg: #f4f7fb;
            --card: #ffffff;
            --text: #1f2d3d;
            --muted: #6b7b8c;
            --ok: #28a745;
            --error: #dc3545;
            --info: #17a2b8;
            --violet: #6f42c1;
            --border: #dbe4ef;
            --shadow: 0 4px 14px rgba(15, 42, 71, 0.08);
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }}

        .header {{
            background: linear-gradient(120deg, #1d4e89, #0f7ca5);
            color: #ffffff;
            border-radius: 14px;
            padding: 28px;
            box-shadow: var(--shadow);
        }}

        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 30px;
        }}

        .header p {{
            margin: 6px 0;
            color: #e7f4ff;
        }}

        .section {{
            margin-top: 22px;
            background: var(--card);
            border-radius: 14px;
            padding: 20px;
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
        }}

        .section h2 {{
            margin: 0 0 14px 0;
            font-size: 22px;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 14px;
        }}

        .stat-card {{
            background: #f9fcff;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 14px;
        }}

        .stat-title {{
            color: var(--muted);
            font-size: 14px;
            margin-bottom: 8px;
        }}

        .stat-value {{
            font-size: 30px;
            font-weight: 700;
        }}

        .ok {{
            color: var(--ok);
        }}

        .error {{
            color: var(--error);
        }}

        .violet {{
            color: var(--violet);
        }}

        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
            gap: 16px;
        }}

        .chart-box {{
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px;
            background: #fcfeff;
        }}

        .chart-box h3 {{
            margin: 0 0 10px 0;
            font-size: 17px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}

        th, td {{
            border: 1px solid var(--border);
            padding: 8px 9px;
            vertical-align: top;
            text-align: left;
        }}

        th {{
            background: #eef5fb;
        }}

        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 12px;
            color: #ffffff;
        }}

        .badge-paid {{
            background: var(--error);
        }}

        .badge-free {{
            background: var(--ok);
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }}

        @media (max-width: 900px) {{
            .summary-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .result-box {{
            background: #f6fbff;
            border-left: 6px solid var(--violet);
            padding: 14px;
            border-radius: 10px;
            margin-top: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Отчет по задачам Аванкора в проекте "Розница ДУ"</h1>
            <p><b>Подготовлено по запросу:</b> Анастасии Ксенофонтовой</p>
            <p><b>Период задач:</b> {period_label}</p>
            <p><b>Дата формирования:</b> 2026-09-14</p>
        </div>

        <div class="section">
            <h2>Ключевая статистика</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-title">Всего задач</div>
                    <div class="stat-value">{total}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Платных задач</div>
                    <div class="stat-value error">{paid_n}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Бесплатных задач</div>
                    <div class="stat-value ok">{free_n}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Всего нормо-часов</div>
                    <div class="stat-value violet">{total_hours}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Итоговая стоимость</div>
                    <div class="stat-value error">{fmt_money(total_cost)} руб.</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Средняя цена часа</div>
                    <div class="stat-value">{fmt_money(HOUR_RATE)} руб.</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Своды с группировкой</h2>
            <div class="summary-grid">
                <div>
                    <h3>Свод по системам</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Система</th>
                                <th>Всего задач</th>
                                <th>Платных</th>
                                <th>Бесплатных</th>
                                <th>Нормо-часы</th>
                                <th>Стоимость</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(system_rows)}
                            <tr>
                                <th>Итого</th>
                                <th>{total}</th>
                                <th>{paid_n}</th>
                                <th>{free_n}</th>
                                <th>{total_hours}</th>
                                <th>{fmt_money(total_cost)} руб.</th>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div>
                    <h3>Свод по месяцам (стоимость)</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Месяц</th>
                                <th>Платных задач</th>
                                <th>Нормо-часы</th>
                                <th>Стоимость</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(month_rows)}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Детальная таблица задач</h2>
            <table>
                <thead>
                    <tr>
                        <th>Система</th>
                        <th>ASP</th>
                        <th>Название задачи</th>
                        <th>Создана</th>
                        <th>Jira</th>
                        <th>Тип</th>
                        <th>Нормо-часы</th>
                        <th>Стоимость</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(detail_rows)}
                    <tr>
                        <th colspan="2">Итого</th>
                        <th>{total} задач</th>
                        <th>-</th>
                        <th>-</th>
                        <th>{paid_n} платно / {free_n} бесплатно</th>
                        <th>{total_hours}</th>
                        <th>{fmt_money(total_cost)}</th>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Выводы и возможности</h2>
            <div class="result-box">
                {''.join(conclusions)}
            </div>
        </div>

        <div class="section">
            <h2>Диаграммы и графики</h2>
            <div class="charts-grid">
                <div class="chart-box">
                    <h3>Платные vs Бесплатные</h3>
                    <canvas id="paidFreeChart"></canvas>
                </div>
                <div class="chart-box">
                    <h3>Стоимость по системам</h3>
                    <canvas id="systemCostChart"></canvas>
                </div>
                <div class="chart-box">
                    <h3>Нормо-часы по системам</h3>
                    <canvas id="systemHoursChart"></canvas>
                </div>
                <div class="chart-box">
                    <h3>Количество задач по месяцам</h3>
                    <canvas id="monthlyTasksChart"></canvas>
                </div>
            </div>
        </div>
    </div>

    <script>
        const commonLegend = {{
            labels: {{
                usePointStyle: true,
                boxWidth: 10
            }}
        }};

        new Chart(document.getElementById("paidFreeChart"), {{
            type: "doughnut",
            data: {{
                labels: ["Платные", "Бесплатные"],
                datasets: [{{
                    data: [{paid_n}, {free_n}],
                    backgroundColor: ["#dc3545", "#28a745"]
                }}]
            }},
            options: {{
                plugins: {{ legend: commonLegend }}
            }}
        }});

        new Chart(document.getElementById("systemCostChart"), {{
            type: "bar",
            data: {{
                labels: [{system_cost_labels}],
                datasets: [{{
                    label: "Стоимость, руб.",
                    data: [{system_cost_data}],
                    backgroundColor: [{system_colors}]
                }}]
            }},
            options: {{
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{ beginAtZero: true }}
                }}
            }}
        }});

        new Chart(document.getElementById("systemHoursChart"), {{
            type: "bar",
            data: {{
                labels: [{system_cost_labels}],
                datasets: [{{
                    label: "Нормо-часы",
                    data: [{system_hours_data}],
                    backgroundColor: [{hours_colors}]
                }}]
            }},
            options: {{
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{ beginAtZero: true }}
                }}
            }}
        }});

        new Chart(document.getElementById("monthlyTasksChart"), {{
            type: "line",
            data: {{
                labels: [{month_labels}],
                datasets: [{{
                    label: "Количество задач",
                    data: [{month_task_counts}],
                    borderColor: "#17a2b8",
                    backgroundColor: "rgba(23, 162, 184, 0.2)",
                    fill: true,
                    tension: 0.25
                }}]
            }},
            options: {{
                plugins: {{ legend: commonLegend }},
                scales: {{
                    y: {{ beginAtZero: true }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""


def main() -> None:
    tasks = load_tasks()
    html_text = build_html(tasks)
    OUT_PATH.write_text(html_text, encoding="utf-8")

    paid_n = sum(1 for t in tasks if t["paid"])
    free_n = len(tasks) - paid_n
    total_hours = sum(t["hours"] for t in tasks)
    total_cost = sum(t["cost"] for t in tasks)
    print(f"OK report: {OUT_PATH.name}")
    print(f"tasks={len(tasks)} paid={paid_n} free={free_n} hours={total_hours} cost={total_cost}")
    for task in tasks:
        created = fmt_created(task["created"])
        kind = "PAID" if task["paid"] else "FREE"
        print(
            f"{task['system']}|{task['asp']}|{task['key']}|{kind}|"
            f"{task['hours']}|{task['cost']}|{created}|{task['summary'][:70]}"
        )


if __name__ == "__main__":
    main()
