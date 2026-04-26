#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build report_cards HTML tuned for Confluence import: table border/cellpadding + inline styles.
Source: report_cards_2026_04_14.html
Output: report_cards_confluence_import.html
"""

from __future__ import annotations

import re
from pathlib import Path

DIR = Path(__file__).resolve().parent
SRC = DIR / "report_cards_2026_04_14.html"
DST = DIR / "report_cards_confluence_import.html"

BANNER = """
<div style="border:1px solid #c9b87a;padding:12px 14px;margin:0 0 18px 0;background:#fffbeb;font-size:12.5px;line-height:1.55;color:#1a2333;">
<p style="margin:0 0 8px 0;font-weight:bold;">Импорт в Confluence (карточки)</p>
<ul style="margin:0;padding-left:18px;">
<li>По FAQ Atlassian: при импорте HTML часть CSS из &lt;style&gt; может не перенестись; заданы border/cellpadding и инлайн-стили ячеек таблиц и бейджей.</li>
<li>FAQ: <a href="https://support.atlassian.com/confluence-cloud/docs/faq-import-data-from-html-to-confluence/">https://support.atlassian.com/confluence-cloud/docs/faq-import-data-from-html-to-confluence/</a></li>
</ul>
</div>
"""

META_TABLE_OPEN = (
    '<table class="meta-table" border="1" cellpadding="6" cellspacing="0" '
    'style="border-collapse:collapse;width:100%;font-size:12px;margin-bottom:8px;border:1px solid #e2e8f0;">'
)

SUMMARY_TABLE_OPEN = (
    '<table border="1" cellpadding="7" cellspacing="0" '
    'style="border-collapse:collapse;width:100%;font-size:12.5px;border:1px solid #e2e8f0;">'
)

META_TH = (
    "border:1px solid #e2e8f0;padding:6px 8px;vertical-align:top;text-align:left;"
    "background-color:#f8fafc;color:#334155;font-weight:700;width:38%;"
)
META_TD = "border:1px solid #e2e8f0;padding:6px 8px;vertical-align:top;text-align:left;"
META_TARGET_TH = (
    "border:1px solid #c7d2fe;padding:6px 8px;vertical-align:top;text-align:left;"
    "background-color:#eef2ff;color:#312e81;font-weight:800;font-size:11px;"
    "text-transform:uppercase;letter-spacing:0.06em;border-left:4px solid #4338ca;border-top:2px solid #c7d2fe;width:38%;"
)
META_TARGET_TD = (
    "border:1px solid #c7d2fe;padding:6px 8px;vertical-align:top;text-align:left;"
    "background-color:#f5f3ff;font-weight:700;font-size:13px;color:#1e1b4b;"
    "line-height:1.45;border-top:2px solid #c7d2fe;"
)
META_TARGET_TD_MUTED = META_TARGET_TD + "color:#64748b;font-weight:600;font-style:italic;"
META_TD_MUTED = META_TD + "color:#64748b;font-style:italic;"

SUM_TH = (
    "border:1px solid #e2e8f0;padding:7px 8px;vertical-align:top;text-align:left;"
    "background-color:#f8fafc;font-weight:700;"
)
SUM_TH_GOAL = (
    "border:1px solid #818cf8;padding:7px 8px;vertical-align:top;text-align:left;"
    "background-color:#eef2ff;color:#312e81;font-size:11px;font-weight:800;"
    "text-transform:uppercase;letter-spacing:0.05em;border-bottom:2px solid #818cf8;white-space:nowrap;"
)

TD_SUM_BASE = "border:1px solid #e2e8f0;padding:7px 8px;vertical-align:top;text-align:left;"
TD_SUM_OK = TD_SUM_BASE + "color:#0f766e;font-weight:700;"
TD_SUM_BAD = TD_SUM_BASE + "color:#dc2626;font-weight:700;"
TD_SUM_WARN = TD_SUM_BASE + "color:#b45309;font-weight:700;"
TD_SUM_MUTED = TD_SUM_BASE + "color:#94a3b8;font-weight:600;"
TD_SUM_GOAL = (
    TD_SUM_BASE + "background-color:#faf5ff;font-weight:800;font-size:13px;color:#3730a3;"
    "border-left:3px solid #7c3aed;"
)
TD_SUM_GOAL_MUTED = (
    TD_SUM_BASE + "background-color:#f1f5f9;color:#64748b;font-weight:700;border-left:3px solid #cbd5e1;"
)

BADGE_STYLES = {
    "done": "font-size:11px;color:#ffffff;border-radius:12px;padding:4px 10px;white-space:nowrap;font-weight:700;background:#28a745;",
    "close": "font-size:11px;color:#ffffff;border-radius:12px;padding:4px 10px;white-space:nowrap;font-weight:700;background:#f59e0b;",
    "not-done": "font-size:11px;color:#ffffff;border-radius:12px;padding:4px 10px;white-space:nowrap;font-weight:700;background:#dc3545;",
    "pending": "font-size:11px;color:#ffffff;border-radius:12px;padding:4px 10px;white-space:nowrap;font-weight:700;background:#1d4fa0;",
    "no-data": "font-size:11px;color:#ffffff;border-radius:12px;padding:4px 10px;white-space:nowrap;font-weight:700;background:#8a94a6;",
}

DELTA_RELEASE = (
    "border-radius:8px;padding:8px;font-size:12px;margin-bottom:10px;border:1px solid #f5c0c0;"
    "border-left:3px solid #dc3545;background:#fff5f5;color:#7a1a1a;font-weight:600;"
)
DELTA_STYLES_MAP = {
    "delta release": DELTA_RELEASE,
    "delta warn": "border-radius:8px;padding:8px;font-size:12px;margin-bottom:10px;border:1px solid #fed7aa;background:#fff7ed;",
    "delta bad": "border-radius:8px;padding:8px;font-size:12px;margin-bottom:10px;border:1px solid #fca5a5;background:#fff1f2;",
    "delta grey": "border-radius:8px;padding:8px;font-size:12px;margin-bottom:10px;border:1px solid #e2e8f0;background:#f8fafc;",
    "delta": "border-radius:8px;padding:8px;font-size:12px;margin-bottom:10px;border:1px solid #e2e8f0;background:#ecfeff;",
}


def patch_meta_table_inner(inner: str) -> str:
    s = inner
    s = s.replace('<tr class="meta-target"><th>', f'<tr class="meta-target"><th style="{META_TARGET_TH}">')
    s = s.replace("<tr><th>", f'<tr><th style="{META_TH}">')
    s = re.sub(
        r'(<tr class="meta-target"><th style="[^"]+">[^<]*</th>)<td class="muted-target">',
        rf'\1<td style="{META_TARGET_TD_MUTED}">',
        s,
    )
    s = re.sub(
        r'(<tr class="meta-target"><th style="[^"]+">[^<]*</th>)<td>',
        rf'\1<td style="{META_TARGET_TD}">',
        s,
    )
    s = s.replace("</th><td class=\"muted-target\">", f'</th><td style="{META_TD_MUTED}">')
    s = s.replace("</th><td>", f'</th><td style="{META_TD}">')
    return s


def patch_all_meta_tables(html: str) -> str:
    pattern = re.compile(r'<table class="meta-table">(.*?)</table>', re.DOTALL)

    def repl(m: re.Match[str]) -> str:
        inner = patch_meta_table_inner(m.group(1))
        return META_TABLE_OPEN + inner + "</table>"

    return pattern.sub(repl, html)


def patch_summary_table(html: str) -> str:
    marker = "<h2>Сводная таблица всех задач</h2>\n        <table>"
    if marker not in html:
        return html
    html = html.replace(marker, "<h2>Сводная таблица всех задач</h2>\n        " + SUMMARY_TABLE_OPEN, 1)
    thead_old = """            <thead>
                <tr>
                    <th>База</th>
                    <th>Задача</th>
                    <th>БЫЛО (минут/1000 объектов)</th>
                    <th>СТАЛО (минут/1000 объектов)</th>
                    <th>Цель (минут/1000 объектов)</th>
                    <th>Ускорение</th>
                    <th>Статус</th>
                </tr>
            </thead>"""
    thead_new = f"""            <thead>
                <tr>
                    <th style="{SUM_TH}">База</th>
                    <th style="{SUM_TH}">Задача</th>
                    <th style="{SUM_TH}">БЫЛО (минут/1000 объектов)</th>
                    <th style="{SUM_TH}">СТАЛО (минут/1000 объектов)</th>
                    <th style="{SUM_TH_GOAL}">Цель (минут/1000 объектов)</th>
                    <th style="{SUM_TH}">Ускорение</th>
                    <th style="{SUM_TH}">Статус</th>
                </tr>
            </thead>"""
    html = html.replace(thead_old, thead_new, 1)

    anchor = "Сводная таблица всех задач"
    pos = html.find(anchor)
    if pos == -1:
        return html
    t_start = html.find("<tbody>", pos)
    t_end = html.find("</tbody>", t_start)
    if t_start == -1 or t_end == -1:
        return html
    before = html[:t_start]
    tb = html[t_start:t_end]
    after = html[t_end:]

    for cls, sty in [
        ("ok", TD_SUM_OK),
        ("bad", TD_SUM_BAD),
        ("warn", TD_SUM_WARN),
        ("muted", TD_SUM_MUTED),
    ]:
        tb = tb.replace(f'<td class="{cls}">', f'<td style="{sty}">')

    def fix_summary_tr_row(tr: str) -> str:
        it = list(re.finditer(r"<td([^>]*)>", tr))
        if len(it) < 7:
            return tr
        m5 = it[4]
        attrs = m5.group(1)
        if "style=" in attrs or "class=" in attrs:
            return tr
        end_o = m5.end()
        c = tr.find("</td>", end_o)
        if c == -1:
            return tr
        body = tr[end_o:c]
        text_inner = re.sub(r"<[^>]+>", "", body).strip()
        use_muted = text_inner in ("—", "уточняется") or text_inner.startswith("ориентир")
        sty = TD_SUM_GOAL_MUTED if use_muted else TD_SUM_GOAL
        return tr[: m5.start()] + f'<td style="{sty}">' + body + tr[c:]

    tb = re.sub(r"<tr>\s*\n.*?</tr>", lambda m: fix_summary_tr_row(m.group(0)), tb, flags=re.DOTALL)

    tb = tb.replace("<td><span", f'<td style="{TD_SUM_BASE}"><span')
    tb = re.sub(r"<td>", f'<td style="{TD_SUM_BASE}">', tb)

    html = before + tb + after
    return html


def patch_badges(html: str) -> str:
    for name, sty in BADGE_STYLES.items():
        html = html.replace(
            f'<div class="badge {name}">',
            f'<div class="badge {name}" style="{sty}">',
        )
    return html


def patch_deltas(html: str) -> str:
    html = html.replace(
        '<div class="delta release" style="margin-top:6px">',
        f'<div class="delta release" style="margin-top:6px;{DELTA_RELEASE}">',
    )
    for cls in ("delta release", "delta warn", "delta bad", "delta grey", "delta"):
        sty = DELTA_STYLES_MAP[cls]
        html = html.replace(f'<div class="{cls}">', f'<div class="{cls}" style="{sty}">')
    return html


def main() -> None:
    html = SRC.read_text(encoding="utf-8")
    html = html.replace("<title>", "<title>Confluence import: ", 1)
    html = html.replace("<body>", "<body>\n" + BANNER, 1)

    html = patch_all_meta_tables(html)
    html = patch_summary_table(html)
    html = patch_badges(html)
    html = patch_deltas(html)

    DST.write_text(html, encoding="utf-8")
    print("Wrote", DST)


if __name__ == "__main__":
    main()
