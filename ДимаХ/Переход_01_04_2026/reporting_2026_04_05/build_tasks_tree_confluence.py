#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generiruet tasks_tree_table_*_confluence.html dlya vstavki v Confluence 7.x.
Tablitsy + inline style, bez flex/grid.
"""
from __future__ import annotations

import html
import pathlib
import sys

from bs4 import BeautifulSoup, NavigableString

STATUS_STYLE = {
    "done": "background:#d4f0dc;color:#1a6b35;border:1px solid #90d4a8;",
    "close": "background:#fff3cd;color:#856404;border:1px solid #ffc107;",
    "not-done": "background:#fde8e8;color:#9b2020;border:1px solid #f5a0a0;",
    "no-data": "background:#f0f2f5;color:#6b7280;border:1px solid #d1d5db;",
    "pending": "background:#e8f0ff;color:#1d4fa0;border:1px solid #9ec0ff;",
}


def emit_status_span(span_el) -> str:
    cls = span_el.get("class", [])
    key = next((k for k in STATUS_STYLE if k in cls), "no-data")
    st = STATUS_STYLE[key]
    t = html.escape(span_el.get_text(strip=True))
    return (
        f'<span style="display:inline-block;border-radius:4px;padding:3px 8px;'
        f"font-size:11px;font-weight:700;white-space:nowrap;{st}\">{t}</span>"
    )


def emit_inline_span(span_el) -> str:
    """Span s vlozhennym tekstom, br, b (sohranjaet razmetku)."""
    cl = span_el.get("class", [])
    if "status" in cl:
        return emit_status_span(span_el)
    st = span_el.get("style", "")
    extra = ""
    if "muted" in cl:
        extra = "color:#5a6780;"
    merged = st.rstrip()
    if merged and not merged.endswith(";"):
        merged += ";"
    merged += extra
    inner_parts = []
    for ch in span_el.children:
        if isinstance(ch, NavigableString):
            inner_parts.append(html.escape(str(ch).replace("\xa0", " ")))
        elif ch.name == "br":
            inner_parts.append("<br>")
        elif ch.name == "b":
            inner_parts.append("<strong>" + html.escape(ch.get_text()) + "</strong>")
        elif ch.name == "span":
            inner_parts.append(emit_inline_span(ch))
        elif ch.name:
            inner_parts.append(inner_cell_content(ch))
    body = "".join(inner_parts)
    if merged.strip():
        return f'<span style="{html.escape(merged, quote=True)}">{body}</span>'
    return body


def inner_cell_content(cell) -> str:
    out = []
    for child in cell.children:
        if isinstance(child, NavigableString):
            out.append(html.escape(str(child).replace("\xa0", " ")))
        elif child.name == "br":
            out.append("<br>")
        elif child.name == "span":
            out.append(emit_inline_span(child))
        elif child.name == "b":
            out.append("<strong>" + html.escape(child.get_text()) + "</strong>")
        elif child.name:
            out.append(inner_cell_content(child))
    return "".join(out)


def emit_profiler_table(tbl) -> str:
    parts = [
        '<table width="100%" cellpadding="3" cellspacing="0" '
        'style="border-collapse:collapse;font-size:9.5px;line-height:1.35;'
        'border:none;background:#fffef7;">'
    ]
    for section in (tbl.find("thead"), tbl.find("tbody")):
        if not section:
            continue
        for tr in section.find_all("tr"):
            cells = []
            for cell in tr.find_all(["th", "td"]):
                tag = cell.name
                cls = cell.get("class", [])
                st = "padding:3px 5px;border:1px solid #d4dded;vertical-align:top;"
                if tag == "th":
                    st += "background:#eef2ff;font-size:9px;font-weight:700;white-space:nowrap;"
                else:
                    if "pm-rank" in cls:
                        st += (
                            "text-align:center;font-weight:700;background:#f4f6ff;width:2em;"
                        )
                    elif "pm-num" in cls:
                        st += (
                            "text-align:right;font-variant-numeric:tabular-nums;"
                            "white-space:nowrap;"
                        )
                    elif "pm-code" in cls:
                        st += (
                            "font-family:Consolas,Courier New,monospace;font-size:9px;"
                            "word-break:break-word;"
                        )
                    elif "pm-mod" in cls:
                        st += "word-break:break-word;"
                inner = inner_cell_content(cell)
                cells.append(f"<{tag} style=\"{st}\">{inner}</{tag}>")
            parts.append(f"<tr>{''.join(cells)}</tr>")
    parts.append("</table>")
    return "".join(parts)


def emit_timing_list_ul(ul_el) -> str:
    rows = []
    for li in ul_el.find_all("li", recursive=False):
        left = ""
        right = ""
        for sp in li.find_all("span"):
            if "timing-time" in sp.get("class", []):
                right = html.escape(sp.get_text(strip=True))
            else:
                left = inner_cell_content(sp) if sp.find_all() else html.escape(
                    sp.get_text(strip=True)
                )
        rows.append(
            "<tr>"
            f'<td style="border-bottom:1px dashed #d4dded;padding:2px 0;">{left}</td>'
            '<td style="border-bottom:1px dashed #d4dded;padding:2px 0;'
            'text-align:right;font-family:monospace;color:#b04000;">'
            f"{right}</td></tr>"
        )
    return (
        '<table width="100%" cellpadding="0" cellspacing="0" '
        'style="border-collapse:collapse;font-size:11.5px;margin:4px 0 0 0;">'
        + "".join(rows)
        + "</table>"
    )


def emit_research_body_content(body_el) -> str:
    parts = []
    for child in body_el.children:
        if isinstance(child, NavigableString):
            t = str(child)
            if t.strip():
                parts.append(html.escape(t.replace("\xa0", " ")))
        elif child.name == "b":
            parts.append("<strong>" + html.escape(child.get_text()) + "</strong>")
        elif child.name == "br":
            parts.append("<br>")
        elif child.name == "div" and "profiler-mini-wrap" in child.get("class", []):
            tbl = child.select_one("table.profiler-mini")
            if tbl:
                inner_t = emit_profiler_table(tbl)
                parts.append(
                    '<div style="margin-top:8px;border:1px solid #e2d8b8;'
                    'border-radius:5px;background:#fffef7;padding:4px;">'
                    f"{inner_t}</div>"
                )
        elif child.name == "div" and "profiler-mini-caption" in child.get("class", []):
            tx = inner_cell_content(child)
            parts.append(
                f'<div style="font-size:9.5px;color:#5a6780;margin-top:5px;line-height:1.45;">'
                f"{tx}</div>"
            )
        elif child.name == "ul" and "timing-list" in child.get("class", []):
            parts.append(emit_timing_list_ul(child))
        elif child.name:
            parts.append(inner_cell_content(child))
    return "".join(parts)


def emit_research(research_el) -> str:
    icon = research_el.select_one(".research-icon")
    body = research_el.select_one(".research-body")
    icon_t = html.escape(icon.get_text(strip=True)) if icon else "[Research]"
    body_html = emit_research_body_content(body) if body else ""
    return (
        '<table width="100%" cellpadding="0" cellspacing="0" '
        'style="margin:0 0 5px 0;border-collapse:separate;">'
        '<tr valign="top">'
        f'<td style="width:88px;color:#b07800;font-weight:700;font-size:11px;'
        f'padding:2px 6px 0 0;white-space:nowrap;">{icon_t}</td>'
        '<td style="background:#fffbe6;border:1px solid #f0c940;border-left:3px solid #e0a800;'
        'border-radius:6px;padding:5px 8px;font-size:12px;">'
        f"{body_html}</td></tr></table>"
    )


def emit_subtask(sub_el) -> str:
    icon = sub_el.select_one(".subtask-icon")
    body = sub_el.select_one(".subtask-body")
    icon_t = html.escape(icon.get_text(strip=True)) if icon else "[SubTask]"
    body_html = inner_cell_content(body) if body else ""
    return (
        '<table width="100%" cellpadding="0" cellspacing="0" '
        'style="margin:4px 0 4px 18px;border-collapse:separate;">'
        '<tr valign="top">'
        f'<td style="width:72px;color:#555;font-size:10px;font-weight:700;'
        f'padding:2px 6px 0 0;white-space:nowrap;">{icon_t}</td>'
        '<td style="background:#f5f5f5;border:1px solid #b0bac8;border-radius:5px;'
        'padding:4px 8px;font-size:12px;">'
        f"{body_html}</td></tr></table>"
    )


def emit_tree(tree_el) -> str:
    parts = [
        '<div style="margin:6px 0 10px 10px;">',
    ]
    for ch in tree_el.children:
        if not getattr(ch, "name", None):
            continue
        if ch.name == "div" and "research" in ch.get("class", []):
            parts.append(emit_research(ch))
        elif ch.name == "div" and "subtask" in ch.get("class", []):
            parts.append(emit_subtask(ch))
    parts.append("</div>")
    return "".join(parts)


def emit_task_table(tbl) -> str:
    rows = []
    for tr in tbl.find_all("tr"):
        cells = []
        for cell in tr.find_all(["th", "td"]):
            tag = cell.name
            rowspan = cell.get("rowspan")
            colspan = cell.get("colspan")
            rs = f' rowspan="{rowspan}"' if rowspan else ""
            cs = f' colspan="{colspan}"' if colspan else ""
            cls = cell.get("class", [])
            if tag == "th":
                st = (
                    "background:#f0f4fc;font-weight:700;padding:6px 8px;"
                    "border:1px solid #d4dded;text-align:left;white-space:nowrap;"
                )
            else:
                st = (
                    "padding:5px 8px;border:1px solid #d4dded;vertical-align:top;"
                )
                if "ok" in cls:
                    st += "color:#1a7d35;font-weight:700;"
                elif "warn" in cls:
                    st += "color:#b56c00;font-weight:700;"
                elif "bad" in cls:
                    st += "color:#b52020;font-weight:700;"
                elif "muted" in cls:
                    st += "color:#5a6780;"
            inner = inner_cell_content(cell)
            cells.append(f'<{tag} style="{st}"{rs}{cs}>{inner}</{tag}>')
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return (
        '<table width="100%" cellpadding="0" cellspacing="0" '
        'style="border-collapse:collapse;font-size:12.5px;'
        'border:1px solid #d4dded;border-radius:0 0 6px 6px;">'
        + "".join(rows)
        + "</table>"
    )


def emit_task_header(header_el) -> str:
    badge = header_el.select_one(".task-badge")
    title_text = ""
    for child in header_el.children:
        if getattr(child, "name", None) == "span" and "task-badge" in child.get(
            "class", []
        ):
            continue
        if isinstance(child, NavigableString):
            title_text += str(child)
        elif child.name:
            title_text += child.get_text()
    title_text = " ".join(title_text.split())
    badge_html = ""
    if badge:
        bt = html.escape(badge.get_text(strip=True))
        badge_html = (
            f'<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;'
            f"text-transform:uppercase;border-radius:4px;padding:2px 6px;color:#fff;"
            f'background:#1d4fa0;">{bt}</span> '
        )
    tit = html.escape(title_text.strip())
    return (
        '<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:0;">'
        '<tr><td style="vertical-align:middle;'
        "background:#e8f0ff;border:1px solid #d4dded;border-bottom:none;"
        'border-radius:6px 6px 0 0;padding:7px 10px;font-weight:600;'
        'font-size:13px;color:#1d4fa0;">'
        f"{badge_html}{tit}</td></tr></table>"
    )


def emit_note(note_el) -> str:
    tx = inner_cell_content(note_el)
    return (
        '<div style="background:#fff5f5;border:1px solid #f5c0c0;border-left:3px solid #dc3545;'
        'border-radius:5px;padding:4px 8px;font-size:12px;color:#7a1a1a;margin-top:5px;">'
        f"{tx}</div>"
    )


def emit_task(task_el) -> str:
    parts = []
    th = task_el.select_one(".task-header")
    if th:
        parts.append(emit_task_header(th))
    tbl = task_el.find("table", recursive=False)
    if not tbl:
        tbl = task_el.find("table")
    if tbl:
        parts.append(emit_task_table(tbl))
    for note in task_el.select(":scope > .note"):
        parts.append(emit_note(note))
    tree = task_el.select_one(":scope > .tree")
    if tree:
        parts.append(emit_tree(tree))
    return (
        f'<div style="margin-bottom:10px;">{"".join(parts)}</div>'
    )


def emit_base_label(label_el) -> str:
    t = html.escape(label_el.get_text(strip=True))
    return (
        '<div style="display:inline-block;font-size:13px;font-weight:700;border-radius:5px;'
        'padding:3px 11px;margin-bottom:8px;color:#0e7a5f;border:2px solid #0e7a5f;">'
        f"{t}</div>"
    )


def emit_base(base_el) -> str:
    parts = ['<div style="margin-bottom:16px;">']
    lab = base_el.select_one(":scope > .base-label")
    if lab:
        parts.append(emit_base_label(lab))
    for task in base_el.select(":scope > .task"):
        parts.append(emit_task(task))
    parts.append("</div>")
    return "".join(parts)


def emit_block(block_el) -> str:
    title_el = block_el.select_one(".block-title")
    title = html.escape(title_el.get_text(strip=True)) if title_el else ""
    body = block_el.select_one(".block-body")
    inner = ""
    if body:
        for base in body.select(":scope > .base"):
            inner += emit_base(base)
    return (
        '<table width="100%" cellpadding="0" cellspacing="0" '
        'style="margin-bottom:14px;background:#ffffff;border:1px solid #d4dded;'
        'border-radius:10px;border-collapse:separate;overflow:hidden;">'
        f'<tr><td style="margin:0;padding:10px 14px;font-size:14px;font-weight:700;'
        f'background:#f6f8ff;border-bottom:1px solid #d4dded;">{title}</td></tr>'
        f'<tr><td style="padding:14px 14px 6px 14px;">{inner}</td></tr>'
        "</table>"
    )


def emit_header(header_el) -> str:
    h1 = header_el.find("h1")
    meta = header_el.select_one(".meta")
    t1 = html.escape(h1.get_text(strip=True)) if h1 else ""
    meta_html = inner_cell_content(meta) if meta else ""
    return (
        '<table width="100%" cellpadding="18" cellspacing="0" '
        'style="margin-bottom:18px;background:#1b4799;border-radius:10px;border-collapse:separate;">'
        '<tr><td style="color:#ffffff;">'
        f'<div style="font-size:22px;font-weight:700;margin:0 0 6px 0;">{t1}</div>'
        f'<div style="font-size:12px;opacity:0.82;line-height:1.7;">{meta_html}</div>'
        "</td></tr></table>"
    )


def build(src: pathlib.Path, dst: pathlib.Path) -> None:
    soup = BeautifulSoup(src.read_text(encoding="utf-8"), "lxml")
    wrap = soup.select_one(".wrap")
    if not wrap:
        raise SystemExit("No .wrap in tasks_tree_table.html")

    chunks = [
        "<!DOCTYPE html>",
        '<html lang="ru"><head><meta charset="UTF-8">',
        "<title>Отчет дерево задач (Confluence paste)</title></head>",
        '<body style="margin:12px;font-family:Segoe UI,Arial,sans-serif;'
        "background:#f2f5fb;color:#1a2333;font-size:13.5px;line-height:1.55;\">",
        '<div style="max-width:1280px;margin:0 auto;">',
    ]

    hdr = wrap.select_one(":scope > .header")
    if hdr:
        chunks.append(emit_header(hdr))

    for block in wrap.select(":scope > .block"):
        chunks.append(emit_block(block))

    chunks.extend(["</div></body></html>"])
    dst.write_text("".join(chunks), encoding="utf-8")
    print(f"OK: {dst.resolve()}")


def main() -> None:
    here = pathlib.Path(__file__).resolve().parent
    src = here / "tasks_tree_table.html"
    dst = here / "tasks_tree_table_confluence.html"
    if len(sys.argv) >= 2:
        src = pathlib.Path(sys.argv[1])
    if len(sys.argv) >= 3:
        dst = pathlib.Path(sys.argv[2])
    if not src.is_file():
        raise SystemExit(f"Not found: {src}")
    build(src, dst)


if __name__ == "__main__":
    main()
