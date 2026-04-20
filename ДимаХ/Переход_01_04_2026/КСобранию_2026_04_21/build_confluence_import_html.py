#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build HTML tuned for Confluence import: table border/cellpadding + inline cell styles.
Source: tasks_tree_table_grouped_2026_04_14.html
Output: tasks_tree_table_confluence_import.html
"""

from __future__ import annotations

import re
from pathlib import Path

DIR = Path(__file__).resolve().parent
SRC = DIR / "tasks_tree_table_grouped_2026_04_14.html"
DST = DIR / "tasks_tree_table_confluence_import.html"

BASE_TD = "border:1px solid #d4dded;padding:6px 8px;vertical-align:top;"
BASE_TH = (
    "background-color:#f0f4fc;font-weight:bold;border:1px solid #d4dded;"
    "padding:6px 8px;text-align:left;vertical-align:top;"
)
PM_TD = "border:1px solid #d4dded;padding:3px 5px;vertical-align:top;font-size:9.5px;"
PM_TH = (
    "background-color:#eef2ff;font-weight:bold;border:1px solid #d4dded;"
    "padding:3px 5px;text-align:left;vertical-align:top;font-size:9px;"
)

TABLE_MAIN = (
    '<table border="1" cellpadding="6" cellspacing="0" '
    'style="border-collapse:collapse;width:100%;font-size:12.5px;border:1px solid #d4dded;">'
)

TABLE_PROF = (
    '<table class="profiler-mini" border="1" cellpadding="3" cellspacing="0" '
    'style="border-collapse:collapse;width:100%;font-size:9.5px;line-height:1.35;border:1px solid #d4dded;">'
)

BANNER = """
<div style="border:1px solid #c9b87a;padding:12px 14px;margin:0 0 18px 0;background:#fffbeb;font-size:12.5px;line-height:1.55;color:#1a2333;">
<p style="margin:0 0 8px 0;font-weight:bold;">Импорт в Confluence</p>
<ul style="margin:0;padding-left:18px;">
<li>По FAQ Atlassian (Confluence Cloud, импорт HTML): переносятся таблицы, заголовки, списки, жирный текст; оформление цвета текста/фона может упроститься.</li>
<li>В этом файле у таблиц заданы атрибуты <code>border</code>, <code>cellpadding</code>, <code>cellspacing</code> и инлайн-стили ячеек (границы, отступы, часть цветов) — выше шанс сохранить сетку таблицы.</li>
<li>Импорт: ZIP с HTML (документация Confluence Cloud) или вставка через редактор / HTML macro в вашей конфигурации.</li>
<li>FAQ Atlassian: <a href="https://support.atlassian.com/confluence-cloud/docs/faq-import-data-from-html-to-confluence/">https://support.atlassian.com/confluence-cloud/docs/faq-import-data-from-html-to-confluence/</a></li>
</ul>
</div>
"""

STATUS_STYLES = {
    "done": (
        "display:inline-block;border-radius:4px;padding:3px 8px;font-size:11px;font-weight:bold;"
        "background-color:#d4f0dc;color:#1a6b35;border:1px solid #90d4a8;"
    ),
    "close": (
        "display:inline-block;border-radius:4px;padding:3px 8px;font-size:11px;font-weight:bold;"
        "background-color:#fff3cd;color:#856404;border:1px solid #ffc107;"
    ),
    "not-done": (
        "display:inline-block;border-radius:4px;padding:3px 8px;font-size:11px;font-weight:bold;"
        "background-color:#fde8e8;color:#9b2020;border:1px solid #f5a0a0;"
    ),
    "pending": (
        "display:inline-block;border-radius:4px;padding:3px 8px;font-size:11px;font-weight:bold;"
        "background-color:#e8f0ff;color:#1d4fa0;border:1px solid #9ec0ff;"
    ),
    "no-data": (
        "display:inline-block;border-radius:4px;padding:3px 8px;font-size:11px;font-weight:bold;"
        "background-color:#f0f2f5;color:#6b7280;border:1px solid #d1d5db;"
    ),
}


def patch_profiler_table(html: str) -> str:
    marker = '<table class="profiler-mini">'
    pos = html.find(marker)
    if pos == -1:
        return html
    start = pos
    end = html.find("</table>", start) + len("</table>")
    seg = html[start:end]
    seg = seg.replace(marker, TABLE_PROF, 1)
    seg = seg.replace("<th>", f'<th style="{PM_TH}">')
    seg = re.sub(
        r'<td class="pm-rank">',
        f'<td style="{PM_TD}text-align:center;font-weight:700;background-color:#f4f6ff;width:2em;">',
        seg,
    )
    seg = re.sub(
        r'<td class="pm-mod">',
        f'<td style="{PM_TD}word-break:break-word;">',
        seg,
    )
    seg = re.sub(
        r'<td class="pm-num">',
        f'<td style="{PM_TD}text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;">',
        seg,
    )
    seg = re.sub(
        r'<td class="pm-code">',
        f'<td style="{PM_TD}font-family:Consolas,Courier New,monospace;font-size:9px;word-break:break-word;">',
        seg,
    )
    return html[:start] + seg + html[end:]


def main() -> None:
    html = SRC.read_text(encoding="utf-8")

    html = html.replace("<title>", "<title>Confluence import: ", 1)

    html = html.replace('<table class="profiler-mini">', "__PROFILER_PLACEHOLDER__", 1)
    html = html.replace("<table>", TABLE_MAIN)
    html = html.replace("__PROFILER_PLACEHOLDER__", '<table class="profiler-mini">', 1)
    html = patch_profiler_table(html)

    html = html.replace("<th>", f'<th style="{BASE_TH}">')

    for cls, sty in [
        ("ok", f'{BASE_TD}color:#1a7d35;font-weight:bold;'),
        ("warn", f'{BASE_TD}color:#b56c00;font-weight:bold;'),
        ("bad", f'{BASE_TD}color:#b52020;font-weight:bold;'),
        ("muted", f"{BASE_TD}color:#5a6780;"),
    ]:
        html = html.replace(f'<td class="{cls}">', f'<td style="{sty}">')

    html = html.replace('<td rowspan="3">', f'<td rowspan="3" style="{BASE_TD}">')
    html = html.replace('<td rowspan="3"><span', f'<td rowspan="3" style="{BASE_TD}"><span')

    html = html.replace("<td>", f'<td style="{BASE_TD}">')

    for name, sty in STATUS_STYLES.items():
        html = html.replace(
            f'<span class="status {name}">',
            f'<span class="status {name}" style="{sty}">',
        )

    html = html.replace("<body>", "<body>\n" + BANNER, 1)

    DST.write_text(html, encoding="utf-8")
    print("Wrote", DST)


if __name__ == "__main__":
    main()
