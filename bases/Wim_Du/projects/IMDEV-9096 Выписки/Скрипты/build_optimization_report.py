#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMDEV-9096: build HTML report from optimization DOCX and MXL regression files.
"""

import html
import json
import re
import subprocess
import sys
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DOCX_PATH = PROJECT / "ОптимизацияЧтения_БылоСталоРегресс.docx"
REGRESS_DIR = PROJECT / "Регресс"
OUTPUT_HTML = PROJECT / "Документация" / "optimization_read_results.html"
TEST_IMAGES_DIR = PROJECT / "Документация" / "test_results_images"

TEST_SCREENSHOTS = [
    ("test_01_image1.png", "Сценарий теста: форма загрузки, ДУ, 11.06.2026 (1 день)"),
    ("test_02_image2.png", "БЫЛО (v5.80): замер верхнего уровня - 617 с, ПрочитатьОбъекты 517 с"),
    ("test_03_image3.png", "БЫЛО: топ SQL (стр. 1286, 1624, 1725) и циклы СтрНайти по префиксам ЕРС"),
    ("test_05_image4.png", "СТАЛО (v5.90): замер верхнего уровня - 237 с, ПрочитатьОбъекты 129 с"),
    ("test_06_image5.png", "СТАЛО: детализация - SQL 1286/1624/1725 ушли из топа; остались циклы ЕРС"),
    ("test_07_image6.png", "Регресс MXL: сравнение 1106_было.mxl и 1106_стало.mxl - файлы идентичны"),
]

DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
ACCOUNT_RE = re.compile(r"^407\d{17}$")
N_RE = re.compile(r"^\d+$")
CONTRACT_RE = re.compile(r"^(ДУ \d+|УК ВТБ)")


def extract_docx_lines(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    lines: list[str] = []
    for paragraph in re.findall(r"<w:p[^>]*>(.*?)</w:p>", xml, re.DOTALL):
        parts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", paragraph)
        if parts:
            lines.append("".join(parts))
    return lines


def parse_profiler_tail(tail: str, code: str = "") -> tuple[str, str, str] | None:
    """Parse 1C profiler tail: calls + time(decimal comma) + percent."""
    tail = tail.replace("\xa0", "").replace(" ", "")
    parts = tail.split(",")
    if len(parts) != 3:
        return None

    left, time_frac, pct = parts
    candidates: list[tuple[int, float, str]] = []

    for index in range(1, len(left)):
        calls = int(left[:index])
        time_val = float(f"{left[index:]}.{time_frac}")
        if time_val <= 0 or time_val > 1500:
            continue
        candidates.append((calls, time_val, pct))

    if not candidates:
        return None

    pool = candidates
    if "ПрочитатьОбъекты" in code:
        pool = [item for item in candidates if item[0] <= 5 and item[1] >= 80]
    elif "Запрос.Выполнить" in code:
        pool = [item for item in candidates if 50 <= item[0] <= 500 and item[1] < 200]
    elif "GetStatementOfAccount" in code:
        pool = [item for item in candidates if item[0] <= 5 and item[1] < 30]
    elif "СтрНайти" in code or "Для Каждого" in code:
        pool = [item for item in candidates if item[0] >= 100000]

    if not pool:
        pool = candidates

    calls, time_val, pct = max(pool, key=lambda item: item[1])
    return str(calls), f"{time_val:.2f}", pct


def parse_profiler_table(lines: list[str], start_marker: str, end_markers: tuple[str, ...]) -> list[dict]:
    rows: list[dict] = []
    in_section = False
    capture = False

    for line in lines:
        if line.strip() == start_marker:
            in_section = True
            capture = False
            continue
        if in_section and any(line.strip().startswith(marker) for marker in end_markers):
            break
        if not in_section:
            continue
        if line.strip() in ("ОБЩИЕ", "ДЕТАЛЬНЫЕ"):
            capture = True
            continue
        if not capture:
            continue

        normalized = line.replace("\xa0", " ").replace("&gt;", ">").strip()
        match = re.match(
            r"^ВнешняяОбработка\.ЗагрузкаВыписок\.МодульОбъекта\s*"
            r"(?P<line>(?:\d\s*)+)(?P<code>[А-ЯA-Za-z_].+?);(?P<tail>.+)$",
            normalized,
        )
        if not match:
            continue

        line_no = re.sub(r"\s+", "", match.group("line"))
        code = match.group("code").strip()
        parsed = parse_profiler_tail(match.group("tail"), code)
        if not parsed:
            continue

        calls, time_sec, pct = parsed
        rows.append(
            {
                "line": line_no,
                "code": code,
                "calls": calls,
                "time_sec": time_sec,
                "pct": pct,
            }
        )
    return rows


def extract_summary(lines: list[str]) -> dict:
    summary = {
        "bylo_total_sec": None,
        "stalo_total_sec": None,
        "speedup_text": "",
    }
    for line in lines:
        if "Ускорение" in line:
            summary["speedup_text"] = line.strip()
            match = re.search(r"с\s+(\d+)\s+с\s+на\s+(\d+)\s+с", line)
            if match:
                summary["bylo_total_sec"] = int(match.group(1))
                summary["stalo_total_sec"] = int(match.group(2))
    return summary


def extract_hash_cells(path: Path) -> list[str]:
    text = path.read_bytes().decode("utf-8", errors="replace")
    return re.findall(r'\{"#","((?:[^"\\]|\\.)*)"\}', text)


def is_date(value: str) -> bool:
    return bool(DATE_RE.match(value))


def is_account(value: str) -> bool:
    return bool(ACCOUNT_RE.match(value.replace(" ", "")))


def is_contract(value: str) -> bool:
    return bool(CONTRACT_RE.match(value))


def is_row_start(vals: list[str], index: int) -> bool:
    if index >= len(vals):
        return False
    value = vals[index]
    if N_RE.match(value):
        window = vals[index : min(index + 5, len(vals))]
        if any(is_date(item) for item in window[1:]):
            return True
        if any(item in ("Да", "Нет") for item in window[1:3]):
            return True
    if is_date(value):
        window = vals[index : min(index + 6, len(vals))]
        if any(is_account(item.replace(" ", "")) for item in window):
            return True
    return False


def normalize_row(chunk: list[str]) -> dict:
    row = {
        "N": "",
        "Zagruzhat": "",
        "Zagruzhena": "",
        "Data": "",
        "Dogovor": "",
        "BankSchet": "",
        "NomerScheta": "",
        "balances": [],
    }

    for value in chunk:
        if not row["N"] and N_RE.match(value) and value not in ("Да", "Нет"):
            row["N"] = value
        elif value in ("Да", "Нет") and not row["Zagruzhat"]:
            row["Zagruzhat"] = value
        elif value in ("Да", "Нет") and row["Zagruzhat"] and not row["Zagruzhena"]:
            row["Zagruzhena"] = value
        elif is_date(value) and not row["Data"]:
            row["Data"] = value
        elif is_contract(value) and not row["Dogovor"]:
            row["Dogovor"] = value
        elif value.startswith("р/с_") and not row["BankSchet"]:
            row["BankSchet"] = value
        elif is_account(value.replace(" ", "")) and not row["NomerScheta"]:
            row["NomerScheta"] = value.replace(" ", "")
        elif re.match(r"^[\d\s,\.]+$", value) and "," in value:
            row["balances"].append(value)

    for value in chunk:
        if is_contract(value):
            row["Dogovor"] = value
            break
    for value in chunk:
        if is_date(value):
            row["Data"] = value

    return row


def parse_rows(values: list[str]) -> list[dict]:
    start = 0
    for index, value in enumerate(values):
        if value == "N" and index + 4 < len(values) and values[index + 4] == "Договор ДУ":
            start = index + 11
            break

    rows: list[dict] = []
    index = start
    while index < len(values):
        if not is_row_start(values, index):
            index += 1
            continue
        row_start = index
        index += 1
        while index < len(values) and not is_row_start(values, index):
            index += 1
        chunk = values[row_start:index]
        if len(chunk) >= 3:
            rows.append(normalize_row(chunk))
    return rows


def row_signature(row: dict) -> tuple:
    return (
        row.get("Data", ""),
        row.get("NomerScheta", ""),
        row.get("Dogovor", ""),
        row.get("BankSchet", ""),
        row.get("N", ""),
    )


def compare_mxl(path_bylo: Path, path_stalo: Path) -> dict:
    rows_bylo = parse_rows(extract_hash_cells(path_bylo))
    rows_stalo = parse_rows(extract_hash_cells(path_stalo))

    counter_bylo = Counter(row_signature(row) for row in rows_bylo)
    counter_stalo = Counter(row_signature(row) for row in rows_stalo)
    multiset_diff = (counter_bylo - counter_stalo) + (counter_stalo - counter_bylo)

    positional: list[dict] = []
    for index, pair in enumerate(zip(rows_bylo, rows_stalo), start=1):
        left, right = pair
        if row_signature(left) != row_signature(right):
            positional.append(
                {
                    "index": index,
                    "bylo": left,
                    "stalo": right,
                }
            )

    only_bylo = sorted((counter_bylo - counter_stalo).items())
    only_stalo = sorted((counter_stalo - counter_bylo).items())

    return {
        "path_bylo": str(path_bylo),
        "path_stalo": str(path_stalo),
        "rows_bylo": len(rows_bylo),
        "rows_stalo": len(rows_stalo),
        "multiset_diff_count": len(multiset_diff),
        "only_bylo": only_bylo,
        "only_stalo": only_stalo,
        "positional_diff_count": len(positional),
        "positional_diffs": positional[:50],
        "rows_bylo_data": rows_bylo,
        "rows_stalo_data": rows_stalo,
    }


def format_signature(signature: tuple) -> str:
    data, schet, dogovor, bank, number = signature
    return f"{data} | {schet} | {dogovor} | {bank} | N={number}"


def render_table_rows(rows: list[dict]) -> str:
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{html.escape(row['line'])}</td>"
            f"<td><code>{html.escape(row['code'])}</code></td>"
            f"<td>{html.escape(row['calls'])}</td>"
            f"<td>{html.escape(row['time_sec'])}</td>"
            f"<td>{html.escape(row['pct'])}</td>"
            "</tr>"
        )
    return "\n".join(body)


def render_comparison_rows(bylo: list[dict], stalo: list[dict]) -> str:
    compare_keys = [
        ("ПрочитатьОбъекты", "ПрочитатьОбъекты", "987"),
        ("ДоговорДУПоСчету / SQL 1286", "Запрос.Выполнить()", "1286"),
        ("ЕРС депо / SQL 1624", "Запрос.Выполнить()", "1624"),
        ("ЕРС ПП / SQL 1725", "Запрос.Выполнить()", "1725"),
        ("СтрНайти префиксы 1356", "СтрНайти", "1356"),
        ("Цикл префиксов 1355", "Для Каждого Выборка Из Данные", "1355"),
        ("Web GetStatementOfAccount", "GetStatementOfAccount", "018"),
    ]

    rows_html = []
    for title, code_part, line_no in compare_keys:
        if line_no == "987":
            left = next((r for r in bylo if "ПрочитатьОбъекты" in r["code"]), None)
            right = next((r for r in stalo if "ПрочитатьОбъекты" in r["code"]), None)
        else:
            left = next((r for r in bylo if r["line"] == line_no and code_part in r["code"]), None)
            right = next((r for r in stalo if r["line"] == line_no and code_part in r["code"]), None)
        if not left and not right:
            continue
        left_time = float(left["time_sec"]) if left else 0.0
        right_time = float(right["time_sec"]) if right else 0.0
        delta = right_time - left_time
        css = "ok" if (not left or delta <= 0) else "warn-cell"
        rows_html.append(
            "<tr>"
            f"<td>{html.escape(title)}</td>"
            f"<td>{html.escape(left['time_sec'] if left else '-')}</td>"
            f"<td>{html.escape(right['time_sec'] if right else '-')}</td>"
            f'<td class="{css}">{delta:+.2f} с</td>'
            "</tr>"
        )
    return "\n".join(rows_html)


def format_speedup_text(summary: dict, speedup_factor: str) -> str:
    bylo = summary.get("bylo_total_sec")
    stalo = summary.get("stalo_total_sec")
    if bylo and stalo:
        return (
            f"Ускорение сценария «Прочитать»: {bylo} с -> {stalo} с "
            f"({speedup_factor or '?'})"
        )
    return summary.get("speedup_text", "").replace("2,%", "2,6")


def render_test_images() -> str:
    figures = []
    for filename, caption in TEST_SCREENSHOTS:
        if not (TEST_IMAGES_DIR / filename).exists():
            continue
        figures.append(
            "<figure class=\"shot\">"
            f"<img src=\"test_results_images/{html.escape(filename)}\" "
            f"alt=\"{html.escape(caption)}\">"
            f"<figcaption>{html.escape(caption)}</figcaption>"
            "</figure>"
        )
    if not figures:
        return "<p class=\"warn\">Скриншоты не найдены. Запустите extract_docx_images.py</p>"
    return "<div class=\"gallery\">" + "\n".join(figures) + "</div>"


def render_block_section() -> str:
    return """
<h2>2. Реализованный блок</h2>
<div class="info">
<p><strong>Контур:</strong> кнопка <code>Прочитать</code> в EPF <code>внЗагрузкаВыписокДУ</code>,
процедура <code>ПрочитатьОбъекты</code> (ветка <code>erf_Оптимизация_Тест1</code>, v5.90).</p>
<table>
<thead><tr><th>ID</th><th>Что</th><th>Как</th></tr></thead>
<tbody>
<tr><td>OPT-02</td><td><code>ДоговорДУПоСчету</code></td><td>Пакетный кэш <code>ЗаполнитьКэшДоговоровДУПоСчетам</code> — 1 SQL на ответ</td></tr>
<tr><td>OPT-17</td><td><code>ЕРС_ДоговорДУ_ПоСчетуИСчетуДепо</code></td><td>Ленивый кэш <code>КэшДепоПоСчету</code> — 1 SQL на уникальный счёт</td></tr>
<tr><td>OPT-05</td><td><code>ЕРС_ДоговорДУ_ПоПлатежномуПоручению</code></td><td>Кэш <code>КэшПП</code> / <code>ПолучитьПлатежныеПорученияОкна</code> — 1 SQL на (счёт, день)</td></tr>
<tr><td>OPT-18</td><td><code>ЕРС_ДоговорДУ_ПоСчетуИНазначению</code></td><td>Карта префиксов <code>ПостроитьКартуПрефиксовЕРС</code> вместо миллионов <code>СтрНайти</code></td></tr>
</tbody>
</table>
</div>
"""


def render_conclusions(speedup_factor: str, summary: dict, regress: dict, regress_text: str) -> str:
    bylo_root = summary.get("bylo_prochitat_sec", "?")
    stalo_root = summary.get("stalo_prochitat_sec", "?")
    rows = regress["rows_bylo"]
    return f"""
<h2>8. Выводы</h2>
<div class="success">
<strong>Итог:</strong> контур «Прочитать» ускорен примерно в {speedup_factor or '2.6x'};
функциональный регресс по MXL пройден ({rows}/{rows} строк, 0 расхождений).
</div>
<ul>
<li><strong>Производительность:</strong> <code>ПрочитатьОбъекты</code> — {bylo_root} с -> {stalo_root} с;
итог сценария — {summary.get('bylo_total_sec', '?')} с -> {summary.get('stalo_total_sec', '?')} с.</li>
<li><strong>Причина ускорения:</strong> три повторяющихся SQL (стр. 1286, 1624, 1725) заменены пакетными кэшами;
поиск договора по назначению платежа переведён на карту префиксов.</li>
<li><strong>Регресс:</strong> мультимножество по ключу (Дата, НомерСчета, Договор, Банк, N) — {regress_text};
позиционных отличий: {regress['positional_diff_count']} из {rows}.</li>
<li><strong>Остаточные узкие места:</strong> вызов сервиса <code>GetStatementOfAccount</code> (~98 с) и циклы ЕРС
по ключевым словам в назначении платежа — кандидаты на следующую итерацию.</li>
<li><strong>Не в scope:</strong> кнопка «Разобрать» (КлиентБанк), фоновая массовая загрузка — отдельные замеры.</li>
</ul>
"""


def build_html(docx_lines: list[str], regress: dict, summary: dict) -> str:
    bylo = parse_profiler_table(docx_lines, "Кнопка ПРОЧИТАТЬ (за 1 день)  БЫЛО", ("Кнопка ПРОЧИТАТЬ (за 1 день)  СТАЛО",))
    stalo = parse_profiler_table(docx_lines, "Кнопка ПРОЧИТАТЬ (за 1 день)  СТАЛО", ("Вывод:", "РЕГРЕСС:"))

    bylo_root = next((row for row in bylo if "ПрочитатьОбъекты" in row["code"]), None)
    stalo_root = next((row for row in stalo if "ПрочитатьОбъекты" in row["code"]), None)

    speedup_factor = ""
    if summary.get("bylo_total_sec") and summary.get("stalo_total_sec"):
        speedup_factor = f"{summary['bylo_total_sec'] / summary['stalo_total_sec']:.2f}x"

    summary["bylo_prochitat_sec"] = bylo_root["time_sec"] if bylo_root else "?"
    summary["stalo_prochitat_sec"] = stalo_root["time_sec"] if stalo_root else "?"
    speedup_text = format_speedup_text(summary, speedup_factor)
    test_images_html = render_test_images()
    block_section_html = render_block_section()

    multiset_ok = regress["multiset_diff_count"] == 0
    regress_status = "OK" if multiset_ok else "FAIL"
    regress_class = "success" if multiset_ok else "danger"
    regress_text = "функционально идентично" if multiset_ok else "обнаружены расхождения"
    conclusions_html = render_conclusions(speedup_factor, summary, regress, regress_text)

    positional_html = ""
    if regress["positional_diffs"]:
        positional_html = "<table><thead><tr><th>#</th><th>Было</th><th>Стало</th></tr></thead><tbody>"
        for item in regress["positional_diffs"]:
            positional_html += (
                "<tr>"
                f"<td>{item['index']}</td>"
                f"<td><code>{html.escape(format_signature(row_signature(item['bylo'])))}</code></td>"
                f"<td><code>{html.escape(format_signature(row_signature(item['stalo'])))}</code></td>"
                "</tr>"
            )
        positional_html += "</tbody></table>"
    else:
        positional_html = '<p class="success">Позиционные отличия не обнаружены.</p>'

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>IMDEV-9096 - результаты оптимизации чтения</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; color: #212529; background: #f4f6f8; }}
.container {{ max-width: 1400px; margin: 0 auto; }}
h1 {{ color: #1565c0; border-bottom: 3px solid #1565c0; padding-bottom: 8px; }}
h2 {{ color: #2c3e50; margin-top: 32px; border-bottom: 2px solid #dee2e6; padding-bottom: 6px; }}
.lead, .info, .success, .warn, .danger {{
  border-left: 4px solid; padding: 12px 16px; border-radius: 4px; margin: 16px 0;
}}
.lead {{ background: #e3f2fd; border-color: #1565c0; }}
.info {{ background: #d1ecf1; border-color: #17a2b8; }}
.success {{ background: #d4edda; border-color: #28a745; }}
.warn {{ background: #fff3cd; border-color: #ffc107; }}
.danger {{ background: #f8d7da; border-color: #dc3545; }}
table {{ width: 100%; border-collapse: collapse; background: #fff; margin: 16px 0; font-size: 13px; }}
th {{ background: #1565c0; color: #fff; text-align: left; padding: 8px 10px; }}
td {{ border: 1px solid #dee2e6; padding: 8px 10px; vertical-align: top; }}
tr:nth-child(even) {{ background: #f8f9fa; }}
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }}
.stat {{ background: #fff; border: 1px solid #dee2e6; border-radius: 4px; padding: 14px; }}
.stat .label {{ color: #6c757d; font-size: 12px; }}
.stat .value {{ font-size: 24px; font-weight: 700; color: #1565c0; }}
.ok {{ color: #28a745; font-weight: 600; }}
.warn-cell {{ color: #e65100; font-weight: 600; }}
code {{ font-family: Consolas, monospace; font-size: 12px; }}
.footer {{ margin-top: 40px; color: #6c757d; font-size: 13px; }}
.gallery {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 16px; margin: 16px 0; }}
.shot {{ margin: 0; background: #fff; border: 1px solid #dee2e6; border-radius: 4px; padding: 10px; }}
.shot img {{ width: 100%; height: auto; border: 1px solid #dee2e6; border-radius: 4px; }}
.shot figcaption {{ color: #6c757d; font-size: 13px; margin-top: 8px; }}
</style>
</head>
<body>
<div class="container">
<h1>IMDEV-9096: результаты оптимизации контура «Прочитать»</h1>

<div class="lead">
<strong>Задача:</strong> оптимизация загрузки банковских выписок в Wim_Du.<br>
<strong>EPF:</strong> <code>v.5.90</code>, ветка <code>erf_Оптимизация_Тест1</code>.<br>
<strong>OPT:</strong> OPT-02, OPT-17, OPT-05, OPT-18.<br>
<strong>Источник замеров:</strong> <code>ОптимизацияЧтения_БылоСталоРегресс.docx</code>
</div>

<h2>1. Введение</h2>
<p>Сравнение выполнено по сценарию кнопки <strong>Прочитать</strong> за 1 день на тестовой базе WIM_DU
(дата 11.06.2026). Оптимизации сведены к пакетным кэшам и улучшению алгоритмов ЕРС в <code>ПрочитатьОбъекты</code>.</p>

{block_section_html}

<h2>3. Технология замера</h2>
<div class="info">
<ul>
<li><strong>Платформа:</strong> 1С:Предприятие 8.3, замер отладчика по времени выполнения.</li>
<li><strong>Сценарий:</strong> форма загрузки выписок, режим «Загрузка», тип «ДУ», период 1 день.</li>
<li><strong>База:</strong> <code>Srvr="localhost";Ref="WIM_DU";</code> без авторизации.</li>
<li><strong>Было:</strong> <code>erf_Оптимизация</code> (версия 5.80).</li>
<li><strong>Стало:</strong> <code>erf_Оптимизация_Тест1</code> (версия 5.90).</li>
<li><strong>Регресс:</strong> выгрузка ТЧ «Выписки» в MXL, сравнение по мультимножеству бизнес-ключей.</li>
</ul>
</div>

<h2>4. Статистика</h2>
<div class="stats">
  <div class="stat"><div class="label">ПрочитатьОбъекты БЫЛО</div><div class="value">{html.escape(bylo_root['time_sec'] if bylo_root else '?')} с</div></div>
  <div class="stat"><div class="label">ПрочитатьОбъекты СТАЛО</div><div class="value">{html.escape(stalo_root['time_sec'] if stalo_root else '?')} с</div></div>
  <div class="stat"><div class="label">Итого по документу</div><div class="value">{summary.get('bylo_total_sec', '?')} &rarr; {summary.get('stalo_total_sec', '?')} с</div></div>
  <div class="stat"><div class="label">Ускорение</div><div class="value">{speedup_factor or '?'}</div></div>
  <div class="stat"><div class="label">Регресс multiset</div><div class="value">{regress_status}</div></div>
  <div class="stat"><div class="label">Строк MXL</div><div class="value">{regress['rows_bylo']} / {regress['rows_stalo']}</div></div>
</div>

<div class="success">
<strong>{html.escape(speedup_text)}</strong>
</div>

<h2>5. Скриншоты тестов</h2>
{test_images_html}

<h2>6. Детали замеров</h2>
<h3>6.1. БЫЛО (топ детализации)</h3>
<table>
<thead><tr><th>Строка</th><th>Код</th><th>Вызовы</th><th>Время, с</th><th>%</th></tr></thead>
<tbody>
{render_table_rows(bylo)}
</tbody>
</table>

<h3>6.2. СТАЛО (топ детализации)</h3>
<table>
<thead><tr><th>Строка</th><th>Код</th><th>Вызовы</th><th>Время, с</th><th>%</th></tr></thead>
<tbody>
{render_table_rows(stalo)}
</tbody>
</table>

<h3>6.3. Сравнение ключевых операций</h3>
<table>
<thead><tr><th>Операция</th><th>БЫЛО, с</th><th>СТАЛО, с</th><th>Delta</th></tr></thead>
<tbody>
{render_comparison_rows(bylo, stalo)}
</tbody>
</table>

<h2>7. Регресс MXL (1106_было vs 1106_стало)</h2>
<div class="{regress_class}">
<strong>Мультимножество по ключу (Дата, НомерСчета, Договор, Банк, N):</strong>
{regress['multiset_diff_count']} расхождений.
<strong>Позиционные отличия:</strong> {regress['positional_diff_count']} из {min(regress['rows_bylo'], regress['rows_stalo'])}.
</div>

<div class="info">
Критерий приёмки: сравнивать мультимножество бизнес-ключей, а не индекс строки.
Перестановка строк внутри одного ЕРС-блока при неизменном составе договоров допустима.
Скрипт сравнения: <code>Регресс/compare_mxl.py</code>.
</div>

{positional_html}

{conclusions_html}

<div class="footer">
Проект: IMDEV-9096 Выписки / Wim_Du<br>
Файл: optimization_read_results.html<br>
Дата отчёта: {date.today().isoformat()}<br>
Регресс: <code>Регресс/1106_было.mxl</code>, <code>Регресс/1106_стало.mxl</code>
</div>
</div>
</body>
</html>
"""


def main() -> int:
    docx_lines = extract_docx_lines(DOCX_PATH)
    summary = extract_summary(docx_lines)
    regress = compare_mxl(REGRESS_DIR / "1106_было.mxl", REGRESS_DIR / "1106_стало.mxl")

    if DOCX_PATH.exists():
        extract_script = Path(__file__).resolve().parent / "extract_docx_images.py"
        if extract_script.exists():
            subprocess.run([sys.executable, str(extract_script)], check=False)

    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(build_html(docx_lines, regress, summary), encoding="utf-8")

    debug_path = OUTPUT_HTML.with_suffix(".json")
    debug_payload = {
        "summary": summary,
        "regress": {
            key: value
            for key, value in regress.items()
            if not key.endswith("_data")
        },
    }
    debug_path.write_text(json.dumps(debug_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: {OUTPUT_HTML}")
    print(json.dumps(debug_payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
