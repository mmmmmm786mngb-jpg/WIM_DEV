#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generiruet report_cards_*_confluence.html dlya vstavki v Confluence 7.x cherez
kopirovanie iz brauzera. Tablitsy + inline style, bez CSS grid i bez details.
"""
from __future__ import annotations

import html
import pathlib
import re
import sys

from bs4 import BeautifulSoup, NavigableString

BADGE_BG = {
    "done": "#28a745",
    "close": "#f59e0b",
    "not-done": "#dc3545",
    "pending": "#1d4fa0",
    "no-data": "#8a94a6",
}

DELTA_STYLES = {
    "": "border:1px solid #e2e8f0;background:#ecfeff;border-radius:8px;padding:8px;margin:0 0 10px 0;font-size:12px;",
    "warn": "border:1px solid #fed7aa;background:#fff7ed;border-radius:8px;padding:8px;margin:0 0 10px 0;font-size:12px;",
    "bad": "border:1px solid #fca5a5;background:#fff1f2;border-radius:8px;padding:8px;margin:0 0 10px 0;font-size:12px;",
    "grey": "border:1px solid #e2e8f0;background:#f8fafc;border-radius:8px;padding:8px;margin:0 0 10px 0;font-size:12px;",
    "release": "border:1px solid #f5c0c0;border-left:3px solid #dc3545;background:#fff5f5;border-radius:8px;padding:8px;margin:0 0 10px 0;font-size:12px;color:#7a1a1a;font-weight:600;",
}


def badge_class(badge_el) -> str:
    for k in BADGE_BG:
        if k in badge_el.get("class", []):
            return k
    return "no-data"


def span_badge(badge_el) -> str:
    cls = badge_class(badge_el)
    bg = BADGE_BG[cls]
    t = html.escape(badge_el.get_text(strip=True))
    return (
        f'<span style="font-size:11px;color:#fff;border-radius:12px;padding:4px 10px;'
        f'font-weight:700;background:{bg};white-space:nowrap;">{t}</span>'
    )


def delta_key(classes) -> str:
    if "warn" in classes:
        return "warn"
    if "bad" in classes:
        return "bad"
    if "grey" in classes:
        return "grey"
    if "release" in classes:
        return "release"
    return ""


def block_full_width(block) -> bool:
    st = block.get("style", "") or ""
    return "grid-column" in st and "1 / -1" in st.replace(" ", "")


def inner_html_simple(element) -> str:
    if element is None:
        return ""
    out = []
    for child in element.children:
        if isinstance(child, NavigableString):
            out.append(html.escape(str(child).replace("\xa0", " ")))
        elif child.name == "br":
            out.append("<br>")
        elif child.name == "b":
            out.append("<strong>" + html.escape(child.get_text()) + "</strong>")
        elif child.name == "span":
            st = child.get("style", "")
            tx = html.escape(child.get_text())
            if st:
                out.append(f'<span style="{html.escape(st, quote=True)}">{tx}</span>')
            else:
                out.append(tx)
        elif child.name:
            out.append(inner_html_simple(child))
    return "".join(out)


def emit_tbox(tbox) -> str:
    cl = tbox.get("class", [])
    ist = (tbox.get("style", "") or "").replace(" ", "").lower()
    box_st = "border:1px solid #e2e8f0;border-radius:8px;padding:8px;background:#f8fafc;"
    if "fff1f2" in ist:
        box_st = "border:1px solid #fca5a5;border-radius:8px;padding:8px;background:#fff1f2;"
    if "fff7ed" in ist:
        box_st = "border:1px solid #fcd34d;border-radius:8px;padding:8px;background:#fff7ed;"
    lbl = tbox.select_one(".lbl")
    val = tbox.select_one(".val")
    sub = tbox.select_one(".sub")
    parts = [f'<div style="{box_st}">']
    if lbl:
        parts.append(
            f'<div style="color:#64748b;font-size:11px;font-weight:700;text-transform:uppercase;margin-bottom:3px;">'
            f"{html.escape(lbl.get_text(strip=True))}</div>"
        )
    if val:
        vs = val.get("style", "")
        col_old = "#dc2626" if "old" in cl else None
        col_new = "#0f766e" if "new" in cl else None
        extra = ""
        if col_old and "color" not in vs:
            extra = f"color:{col_old};"
        elif col_new and "color" not in vs:
            extra = f"color:{col_new};"
        vs_safe = (vs + ";") if vs and not vs.endswith(";") else vs
        parts.append(
            f'<div style="font-size:16px;font-weight:700;line-height:1.3;{extra}{vs_safe}">'
            f"{inner_html_simple(val)}</div>"
        )
    if sub:
        parts.append(
            f'<div style="font-size:11px;color:#64748b;margin-top:3px;">'
            f"{inner_html_simple(sub)}</div>"
        )
    parts.append("</div>")
    return "".join(parts)


def emit_meta_table(tbl) -> str:
    rows = []
    rows.append(
        '<table width="100%" cellpadding="5" cellspacing="0" style="border-collapse:collapse;'
        'font-size:12px;margin-bottom:8px;">'
    )
    for tr in tbl.select("tr"):
        tds = []
        th = tr.find("th")
        td = tr.find("td")
        trcl = tr.get("class", [])
        if "meta-target" in trcl:
            th_st = (
                "border:1px solid #c7d2fe;background:#e0e7ff;color:#312e81;font-weight:800;"
                "font-size:11px;text-align:left;vertical-align:top;width:32%;padding:5px 7px;"
                "border-left:4px solid #4338ca;"
            )
            td_st = (
                "border:1px solid #c7d2fe;background:#f5f3ff;color:#1e1b4b;font-weight:700;"
                "font-size:13px;text-align:left;vertical-align:top;padding:5px 7px;"
            )
            if td and "muted-target" in td.get("class", []):
                td_st += "color:#64748b;font-style:italic;"
        else:
            th_st = (
                "border:1px solid #e2e8f0;background:#f8fafc;color:#334155;font-weight:600;"
                "text-align:left;vertical-align:top;width:32%;padding:5px 7px;"
            )
            td_st = (
                "border:1px solid #e2e8f0;background:#fff;text-align:left;"
                "vertical-align:top;padding:5px 7px;color:#0f172a;"
            )
        if th:
            tds.append(f"<th style=\"{th_st}\">{inner_html_simple(th)}</th>")
        else:
            tds.append("<th style=\"border:1px solid #e2e8f0;\"></th>")
        if td:
            tds.append(f"<td style=\"{td_st}\">{inner_html_simple(td)}</td>")
        else:
            tds.append("<td style=\"border:1px solid #e2e8f0;\"></td>")
        rows.append(f"<tr>{''.join(tds)}</tr>")
    rows.append("</table>")
    return "".join(rows)


def emit_card_block(block) -> str:
    top = block.select_one(".top")
    title_el = top.select_one(".title") if top else None
    badge_el = top.select_one(".badge") if top else None
    title = html.escape(title_el.get_text(strip=True)) if title_el else ""
    badge = span_badge(badge_el) if badge_el else ""

    content_el = block.select_one(".content")
    inner_parts = []

    if content_el:
        times_el = content_el.select_one(".times")
        if times_el:
            tboxes = times_el.select(".tbox")
            inner_parts.append(
                '<table width="100%" cellpadding="6" cellspacing="0" border="0" '
                'style="margin-bottom:10px;"><tr valign="top">'
            )
            for tb in tboxes:
                inner_parts.append(f'<td width="50%" style="vertical-align:top;">{emit_tbox(tb)}</td>')
            inner_parts.append("</tr></table>")

        for d in content_el.find_all(
            "div",
            class_=lambda c: bool(c) and "delta" in c,
            recursive=False,
        ):
            dk = delta_key(d.get("class", []))
            st = DELTA_STYLES.get(dk, DELTA_STYLES[""])
            inner_parts.append(
                f'<div style="{st}">{inner_html_simple(d)}</div>'
            )

        for mt in content_el.find_all(
            "table",
            class_=lambda c: bool(c) and "meta-table" in c,
            recursive=False,
        ):
            inner_parts.append(emit_meta_table(mt))

    card = [
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        'style="border:1px solid #dbeafe;border-radius:10px;margin-bottom:14px;'
        'background:#ffffff;border-collapse:separate;overflow:hidden;">',
        "<tr><td style=\"padding:0;\">",
        '<table width="100%" cellpadding="10" cellspacing="0" border="0" '
        'style="border-bottom:1px solid #e2e8f0;"><tr valign="middle">',
        f'<td style="font-weight:700;font-size:14px;color:#0f172a;">{title}</td>',
        f'<td align="right" style="text-align:right;">{badge}</td>',
        "</tr></table>",
        f'<div style="padding:12px;font-size:13px;">{"".join(inner_parts)}</div>',
        "</td></tr></table>",
    ]
    return "".join(card)


def emit_main_table(tbl) -> str:
    out = [
        '<table width="100%" cellpadding="7" cellspacing="0" '
        'style="border-collapse:collapse;font-size:12.5px;margin-top:6px;">'
    ]
    thead = tbl.find("thead")
    if thead:
        for tr in thead.find_all("tr"):
            tds = []
            for i, th in enumerate(tr.find_all("th")):
                st = (
                    "border:1px solid #e2e8f0;background:#eef2ff;color:#312e81;"
                    "font-weight:700;font-size:11px;padding:7px 8px;text-align:left;"
                    "vertical-align:top;border-bottom:2px solid #818cf8;"
                ) if i == 4 else (
                    "border:1px solid #e2e8f0;background:#f8fafc;color:#0f172a;"
                    "font-weight:700;padding:7px 8px;text-align:left;vertical-align:top;"
                )
                tds.append(f"<th style=\"{st}\">{inner_html_simple(th)}</th>")
            out.append(f"<tr>{''.join(tds)}</tr>")
    tbody = tbl.find("tbody")
    if tbody:
        for tr in tbody.find_all("tr"):
            tds = []
            for i, td in enumerate(tr.find_all("td")):
                cls = td.get("class", [])
                base = (
                    "border:1px solid #e2e8f0;padding:7px 8px;text-align:left;"
                    "vertical-align:top;"
                )
                if i == 4:
                    if "muted" in cls:
                        base += "background:#f1f5f9;font-weight:700;border-left:3px solid #cbd5e1;color:#64748b;"
                    else:
                        base += (
                            "background:#faf5ff;font-weight:800;font-size:13px;"
                            "color:#3730a3;border-left:3px solid #7c3aed;"
                        )
                tx = inner_html_simple(td)
                if "ok" in cls:
                    base += "color:#0f766e;font-weight:700;"
                elif "bad" in cls:
                    base += "color:#dc2626;font-weight:700;"
                elif "warn" in cls:
                    base += "color:#b45309;font-weight:700;"
                elif "muted" in cls and i != 4:
                    base += "color:#94a3b8;"
                tds.append(f"<td style=\"{base}\">{tx}</td>")
            out.append(f"<tr>{''.join(tds)}</tr>")
    out.append("</table>")
    return "".join(out)


def research_card(card) -> str:
    classes = card.get("class", [])
    border = "#f0c940"
    bg = "#fffbe6"
    if "in-progress" in classes:
        border = "#7dd3fc"
        bg = "#f0f9ff"
    elif "planned" in classes:
        border = "#cbd5e1"
        bg = "#f8fafc"
    icon = card.select_one(".rc-icon")
    body = card.select_one(".rc-body")
    icon_html = ""
    if icon:
        icl = icon.get("class", [])
        ibg = "#0ea5e9" if "active" in icl else ("#e0a800" if "idea" in icl else "#94a3b8")
        icon_html = (
            f'<td style="width:88px;vertical-align:top;background:{ibg};color:#fff;'
            f'font-size:10px;font-weight:700;text-align:center;border-radius:4px;padding:6px;">'
            f"{html.escape(icon.get_text(strip=True))}</td>"
        )
    else:
        icon_html = "<td></td>"
    body_html = ""
    if body:
        parts = []
        for ch in body.children:
            if isinstance(ch, NavigableString):
                if str(ch).strip():
                    parts.append(html.escape(str(ch).strip()))
            elif ch.name == "div" and "rc-subtask" in ch.get("class", []):
                parts.append(
                    f'<div style="margin-top:5px;margin-left:10px;padding:5px 8px;'
                    f'background:#f1f5f9;border-left:2px solid #94a3b8;border-radius:4px;'
                    f'font-size:11.5px;">{inner_html_simple(ch)}</div>'
                )
            elif ch.name:
                parts.append(inner_html_simple(ch))
        body_html = "".join(parts)
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {border};'
        f'background:{bg};border-radius:7px;margin-bottom:8px;border-collapse:separate;">'
        f'<tr valign="top">{icon_html}<td style="padding:9px 11px;font-size:12.5px;'
        f'color:#0f172a;">{body_html}</td></tr></table>'
    )


def research_section(sec_el) -> str:
    out = []
    h2 = sec_el.find("h2")
    if h2:
        t = html.escape(h2.get_text(strip=True))
        out.append(
            f'<h2 style="font-size:15px;margin:0 0 12px 0;color:#0f172a;">{t}</h2>'
        )
    for rg in sec_el.select(".research-group"):
        gt = rg.select_one(".research-group-title")
        if gt:
            out.append(
                f'<div style="font-size:12px;font-weight:700;text-transform:uppercase;'
                f'letter-spacing:0.05em;color:#64748b;margin:16px 0 8px 0;'
                f'padding-bottom:4px;border-bottom:1px solid #e2e8f0;">'
                f"{html.escape(gt.get_text(strip=True))}</div>"
            )
        for card in rg.select(".research-card"):
            out.append(research_card(card))
    return "".join(out)


def process_grid(grid) -> str:
    blocks = list(
        grid.find_all(
            "div",
            class_=lambda c: bool(c) and "block" in c,
            recursive=False,
        )
    )
    out = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        if block_full_width(b):
            out.append(emit_card_block(b))
            i += 1
            continue
        if i + 1 < len(blocks) and not block_full_width(blocks[i + 1]):
            out.append(
                '<table width="100%" cellpadding="8" cellspacing="0" border="0" '
                'style="margin-bottom:14px;"><tr valign="top">'
            )
            out.append(
                f'<td width="50%" style="vertical-align:top;padding-right:7px;">'
                f"{emit_card_block(blocks[i])}</td>"
            )
            out.append(
                f'<td width="50%" style="vertical-align:top;padding-left:7px;">'
                f"{emit_card_block(blocks[i + 1])}</td>"
            )
            out.append("</tr></table>")
            i += 2
        else:
            out.append(
                '<table width="100%" cellpadding="0" cellspacing="0" border="0" '
                'style="margin-bottom:14px;"><tr valign="top">'
                f'<td width="50%" style="vertical-align:top;padding-right:7px;">'
                f'{emit_card_block(b)}</td><td width="50%"></td></tr></table>'
            )
            i += 1
    return "".join(out)


def build(src: pathlib.Path, dst: pathlib.Path) -> None:
    soup = BeautifulSoup(src.read_text(encoding="utf-8"), "lxml")
    wrap = soup.select_one(".wrap")
    if not wrap:
        raise SystemExit("No .wrap")

    chunks = [
        "<!DOCTYPE html>",
        '<html lang="ru"><head><meta charset="UTF-8">',
        "<title>Отчет (Confluence paste)</title></head>",
        '<body style="margin:12px;font-family:Arial,Helvetica,sans-serif;background:#f1f5f9;'
        'color:#0f172a;font-size:13px;line-height:1.45;">',
        '<div style="max-width:1250px;margin:0 auto;background:transparent;">',
    ]

    hdr = wrap.select_one(".header")
    if hdr:
        h1 = hdr.find("h1")
        h1t = html.escape(h1.get_text(strip=True)) if h1 else ""
        chunks.append(
            '<table width="100%" cellpadding="18" cellspacing="0" style="margin-bottom:16px;'
            'background:#1d4fa0;border-radius:10px;border-collapse:separate;">'
            f'<tr><td style="color:#ffffff;">'
            f'<div style="font-size:26px;font-weight:700;margin:0 0 8px 0;">{h1t}</div>'
        )
        for p in hdr.find_all("p"):
            chunks.append(
                f'<p style="margin:0;font-size:13px;line-height:1.5;opacity:0.95;color:#eef2ff;">'
                f"{inner_html_simple(p)}</p>"
            )
        chunks.append("</td></tr></table>")

    sb = wrap.select_one(".source-box")
    if sb:
        chunks.append(
            '<table width="100%" cellpadding="12" cellspacing="0" style="margin-bottom:14px;'
            'background:#ffffff;border:1px solid #dbeafe;border-radius:10px;">'
            f'<tr><td style="font-size:13px;">{inner_html_simple(sb)}</td></tr></table>'
        )

    kpi = wrap.select_one(".kpi")
    if kpi:
        chunks.append(
            '<table width="100%" cellpadding="8" cellspacing="8" border="0" '
            'style="margin-bottom:16px;border-collapse:separate;">'
            "<tr valign=\"top\">"
        )
        for it in kpi.select(".kpi-item"):
            v = it.select_one(".v")
            le = it.select_one(".l")
            vc = ""
            if v and v.get("style"):
                m = re.search(r"color:\s*#([0-9a-fA-F]{6})", v.get("style", ""))
                if m:
                    vc = f"color:#{m.group(1)};"
            elif v:
                vc = "color:#0f766e;"
            vx = inner_html_simple(v) if v else ""
            lx = html.escape(le.get_text(strip=True)) if le else ""
            chunks.append(
                f'<td align="center" style="width:20%;vertical-align:top;background:#ffffff;'
                f'border:1px solid #e2e8f0;border-radius:8px;padding:10px;">'
                f'<div style="font-size:24px;font-weight:bold;{vc}">{vx}</div>'
                f'<div style="font-size:12px;color:#64748b;margin-top:4px;">{lx}</div></td>'
            )
        chunks.append("</tr></table>")

    zone_res = soup.select_one(".zone-results")
    if zone_res:
        chunks.append(
            '<div style="background:#eef4ff;padding:20px 16px 8px;margin:0 -4px 14px -4px;'
            'border-radius:0;">'
        )
        for child in zone_res.children:
            if not getattr(child, "name", None):
                continue
            cl = child.get("class", [])
            if "section-title" in cl and "results" in cl:
                tx = re.sub(r"\s+", " ", child.get_text(" ", strip=True))
                chunks.append(
                    f'<table width="100%" cellpadding="10" cellspacing="0" style="margin:12px 0;'
                    f'border:1px solid #bfdbfe;border-radius:8px;background:#eff6ff;">'
                    f'<tr><td style="font-size:16px;font-weight:700;color:#1e40af;">'
                    f"{html.escape(tx)}</td></tr></table>"
                )
            elif "base-label" in cl:
                tx = child.get_text(" ", strip=True)
                chunks.append(
                    f'<div style="display:inline-block;margin:14px 0 8px 0;padding:3px 10px;'
                    f'font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.04em;'
                    f'color:#0e7a5f;border:1.5px solid #0e7a5f;border-radius:5px;">'
                    f"{html.escape(tx)}</div>"
                )
            elif "grid" in cl:
                chunks.append(process_grid(child))
            elif "table-wrap" in cl:
                h2 = child.find("h2")
                if h2:
                    chunks.append(
                        f'<h2 style="font-size:15px;margin:14px 0 10px 0;color:#0f172a;">'
                        f"{html.escape(h2.get_text(strip=True))}</h2>"
                    )
                tbl = child.find("table")
                if tbl:
                    chunks.append(
                        '<table width="100%" cellpadding="14" cellspacing="0" '
                        'style="background:#ffffff;border:1px solid #e2e8f0;'
                        'border-radius:10px;margin-bottom:14px;"><tr><td>'
                    )
                    chunks.append(emit_main_table(tbl))
                    chunks.append("</td></tr></table>")
        chunks.append("</div>")

    zone_act = soup.select_one(".zone-actions")
    if zone_act:
        det = zone_act.find("details")
        if det:
            summ = det.find("summary")
            tx = re.sub(r"\s+", " ", summ.get_text(" ", strip=True)) if summ else "План"
            chunks.append(
                '<table width="100%" cellpadding="10" cellspacing="0" style="margin:16px 0 12px 0;'
                'border:1px solid #bbf7d0;border-radius:8px;background:#f0fdf4;">'
                f'<tr><td style="font-size:16px;font-weight:700;color:#166534;">'
                f"{html.escape(tx)}</td></tr></table>"
            )
            rs = det.select_one(".research-section")
            if rs:
                chunks.append(
                    '<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;'
                    'padding:14px;margin-bottom:14px;">'
                )
                chunks.append(research_section(rs))
                chunks.append("</div>")

    summ = wrap.select_one(".summary")
    if summ:
        chunks.append(
            '<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;'
            'padding:14px;font-size:13px;line-height:1.6;">'
        )
        h2 = summ.find("h2")
        if h2:
            chunks.append(
                f'<h2 style="font-size:15px;margin:0 0 8px 0;">'
                f"{html.escape(h2.get_text(strip=True))}</h2>"
            )
        ul = summ.find("ul")
        if ul:
            chunks.append('<ul style="margin:0;padding-left:18px;">')
            for li in ul.find_all("li", recursive=False):
                chunks.append(f"<li style=\"margin-bottom:5px;\">{inner_html_simple(li)}</li>")
            chunks.append("</ul>")
        chunks.append("</div>")

    chunks.append("</div></body></html>")
    dst.write_text("\n".join(chunks), encoding="utf-8")


def main() -> None:
    base = pathlib.Path(__file__).resolve().parent
    src = base / "report_cards_2026_04_05.html"
    dst = base / "report_cards_2026_04_05_confluence.html"
    if len(sys.argv) >= 2:
        src = pathlib.Path(sys.argv[1])
    if len(sys.argv) >= 3:
        dst = pathlib.Path(sys.argv[2])
    build(src, dst)
    print("OK: " + str(dst))


if __name__ == "__main__":
    main()
