#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Преобразование HTML-отчета (карточки) в DOCX для импорта в Confluence.

Используются таблицы и заливки ячеек вместо CSS grid/flex -- так форматирование
лучше переносится из Word во встроенный импорт Confluence.
"""
from __future__ import annotations

import pathlib
import re
import sys

from bs4 import BeautifulSoup, NavigableString
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

BADGE_HEX = {
    "done": "28A745",
    "close": "F59E0B",
    "not-done": "DC3545",
    "pending": "1D4FA0",
    "no-data": "8A94A6",
}

DELTA_FILL = {
    "": "ECFEFF",
    "warn": "FFF7ED",
    "bad": "FFF1F2",
    "grey": "F8FAFC",
    "release": "FFF5F5",
}


def set_cell_shading(cell, fill_hex: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill_hex)
    shd.set(qn("w:val"), "clear")
    tc_pr.append(shd)


def set_cell_margins(cell, top=80, bottom=80, left=120, right=120) -> None:
    tc = cell._tc
    tc_mar = OxmlElement("w:tcMar")
    for side, val in (
        ("top", top),
        ("bottom", bottom),
        ("left", left),
        ("right", right),
    ):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        tc_mar.append(el)
    tc_pr = tc.get_or_add_tcPr()
    tc_pr.append(tc_mar)


def parse_rgb_from_style(style: str) -> RGBColor | None:
    if not style:
        return None
    m = re.search(r"color:\s*#([0-9a-fA-F]{6})", style)
    if m:
        h = m.group(1)
        return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    m2 = re.search(
        r"color:\s*rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", style
    )
    if m2:
        return RGBColor(int(m2.group(1)), int(m2.group(2)), int(m2.group(3)))
    return None


def paragraph_clear(paragraph) -> None:
    paragraph.text = ""


def add_inline_runs(paragraph, element) -> None:
    if element is None:
        return

    def walk(node):
        if isinstance(node, NavigableString):
            paragraph.add_run(str(node).replace("\xa0", " "))
            return
        if not hasattr(node, "name") or node.name is None:
            return
        if node.name == "br":
            paragraph.add_run().add_break()
            return
        if node.name == "b":
            r = paragraph.add_run(node.get_text())
            r.bold = True
            return
        if node.name == "span":
            r = paragraph.add_run(node.get_text())
            rgb = parse_rgb_from_style(node.get("style", ""))
            if rgb:
                r.font.color.rgb = rgb
            st = node.get("style", "")
            r.bold = "font-weight:700" in st or "font-weight:bold" in st
            return
        for ch in node.children:
            walk(ch)

    walk(element)


def badge_class_from_element(badge_el) -> str:
    classes = badge_el.get("class", [])
    for c in BADGE_HEX:
        if c in classes:
            return c
    return "no-data"


def add_card(doc: Document, block) -> None:
    is_wide = False
    st = block.get("style", "") or ""
    if "grid-column" in st and "1 / -1" in st.replace(" ", ""):
        is_wide = True

    outer = doc.add_table(rows=1, cols=1)
    outer.autofit = False
    outer.alignment = WD_TABLE_ALIGNMENT.CENTER
    outer.columns[0].width = Inches(6.2 if not is_wide else 6.5)
    oc = outer.rows[0].cells[0]
    set_cell_margins(oc, top=40, bottom=40, left=80, right=80)
    set_cell_shading(oc, "FFFFFF")
    inner_doc = oc

    top_el = block.select_one(".top")
    title_el = top_el.select_one(".title") if top_el else None
    badge_el = top_el.select_one(".badge") if top_el else None

    hdr = inner_doc.add_table(rows=1, cols=2)
    hdr.autofit = True
    c0, c1 = hdr.rows[0].cells
    c0.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    c1.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p0 = c0.paragraphs[0]
    p0.paragraph_format.space_after = Pt(0)
    if title_el:
        r = p0.add_run(title_el.get_text(strip=True))
        r.bold = True
        r.font.size = Pt(11)
    p1 = c1.paragraphs[0]
    p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p1.paragraph_format.space_after = Pt(0)
    if badge_el:
        btext = badge_el.get_text(strip=True)
        bcls = badge_class_from_element(badge_el)
        run = p1.add_run(" " + btext + " ")
        run.bold = True
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        set_cell_shading(c1, BADGE_HEX[bcls])
    for brdr in hdr.rows[0].cells:
        set_cell_margins(brdr, top=30, bottom=30, left=60, right=60)

    content_el = block.select_one(".content")
    if not content_el:
        doc.add_paragraph()
        return

    times_el = content_el.select_one(".times")
    if times_el:
        tboxes = times_el.select(".tbox")
        tt = inner_doc.add_table(rows=1, cols=max(1, len(tboxes)))
        tt.autofit = True
        for i, tbox in enumerate(tboxes):
            cell = tt.rows[0].cells[i]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            set_cell_shading(cell, "F8FAFC")
            set_cell_margins(cell, top=40, bottom=40, left=50, right=50)
            st_box = tbox.get("style", "")
            if "fff1f2" in st_box.replace(" ", "").lower():
                set_cell_shading(cell, "FFF1F2")
            if "fff7ed" in st_box.replace(" ", "").lower():
                set_cell_shading(cell, "FFF7ED")
            lbl = tbox.select_one(".lbl")
            val = tbox.select_one(".val")
            sub = tbox.select_one(".sub")
            cl = tbox.get("class", [])
            is_old = "old" in cl
            is_new = "new" in cl
            if lbl:
                pl = cell.add_paragraph()
                pl.paragraph_format.space_after = Pt(2)
                rl = pl.add_run(lbl.get_text(strip=True))
                rl.font.size = Pt(8)
                rl.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
                rl.bold = True
            if val:
                pv = cell.add_paragraph()
                pv.paragraph_format.space_after = Pt(2)
                add_inline_runs(pv, val)
                for r in pv.runs:
                    r.font.size = Pt(12)
                    r.bold = True
                if is_old:
                    for r in pv.runs:
                        r.font.color.rgb = RGBColor(0xDC, 0x26, 0x26)
                elif is_new:
                    for r in pv.runs:
                        r.font.color.rgb = RGBColor(0x0F, 0x76, 0x6E)
            if sub:
                ps = cell.add_paragraph()
                add_inline_runs(ps, sub)
                for r in ps.runs:
                    r.font.size = Pt(9)
                    r.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    deltas = content_el.find_all(
        "div",
        class_=lambda c: bool(c) and "delta" in c,
        recursive=False,
    )
    for delta_el in deltas:
        dclasses = delta_el.get("class", [])
        dkey = ""
        if "warn" in dclasses:
            dkey = "warn"
        elif "bad" in dclasses:
            dkey = "bad"
        elif "grey" in dclasses:
            dkey = "grey"
        elif "release" in dclasses:
            dkey = "release"
        dt = inner_doc.add_table(rows=1, cols=1)
        dc = dt.rows[0].cells[0]
        set_cell_shading(dc, DELTA_FILL.get(dkey, DELTA_FILL[""]))
        set_cell_margins(dc, top=50, bottom=50, left=70, right=70)
        dp = dc.paragraphs[0]
        dp.paragraph_format.space_after = Pt(0)
        paragraph_clear(dp)
        add_inline_runs(dp, delta_el)
        for r in dp.runs:
            r.font.size = Pt(10)

    meta_tables = content_el.find_all(
        "table",
        class_=lambda c: bool(c) and "meta-table" in c,
        recursive=False,
    )
    for mt in meta_tables:
        rows = mt.select("tr")
        if not rows:
            continue
        mtab = inner_doc.add_table(rows=len(rows), cols=2)
        mtab.style = "Table Grid"
        for ri, tr in enumerate(rows):
            th = tr.find("th")
            td = tr.find("td")
            c_a = mtab.rows[ri].cells[0]
            c_b = mtab.rows[ri].cells[1]
            tr_class = tr.get("class", [])
            if "meta-target" in tr_class:
                set_cell_shading(c_a, "E0E7FF")
                set_cell_shading(c_b, "F5F3FF")
            else:
                set_cell_shading(c_a, "F8FAFC")
            paragraph_clear(c_a.paragraphs[0])
            paragraph_clear(c_b.paragraphs[0])
            if th:
                add_inline_runs(c_a.paragraphs[0], th)
            if td:
                add_inline_runs(c_b.paragraphs[0], td)
            if "meta-target" in tr_class:
                for cell in (c_a, c_b):
                    for p in cell.paragraphs:
                        for r in p.runs:
                            r.bold = True
            for cell in (c_a, c_b):
                for p in cell.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(9)

    doc.add_paragraph()


def add_main_table(doc: Document, table_el) -> None:
    rows = table_el.select("tr")
    if not rows:
        return
    ncol = len(rows[0].find_all(["th", "td"]))
    tbl = doc.add_table(rows=len(rows), cols=ncol)
    tbl.style = "Table Grid"
    for ri, tr in enumerate(rows):
        cells = tr.find_all(["th", "td"])
        for ci, cell_el in enumerate(cells):
            c = tbl.rows[ri].cells[ci]
            paragraph_clear(c.paragraphs[0])
            add_inline_runs(c.paragraphs[0], cell_el)
            if cell_el.name == "th":
                set_cell_shading(c, "EEF2FF" if ci == 4 else "F1F5F9")
                for r in c.paragraphs[0].runs:
                    r.bold = True
            if cell_el.name == "td" and ci == 4:
                cl = cell_el.get("class", [])
                set_cell_shading(c, "F1F5F9" if "muted" in cl else "FAF5FF")
            td_class = cell_el.get("class", [])
            for r in c.paragraphs[0].runs:
                r.font.size = Pt(9)
                if "ok" in td_class:
                    r.font.color.rgb = RGBColor(0x0F, 0x76, 0x6E)
                    r.bold = True
                elif "bad" in td_class:
                    r.font.color.rgb = RGBColor(0xDC, 0x26, 0x26)
                    r.bold = True
                elif "warn" in td_class:
                    r.font.color.rgb = RGBColor(0xB4, 0x53, 0x09)
                    r.bold = True
                elif "muted" in td_class:
                    r.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)
    doc.add_paragraph()


def add_research_card(doc: Document, card) -> None:
    classes = card.get("class", [])
    fill = "FFFBF0"
    if "in-progress" in classes:
        fill = "F0F9FF"
    elif "planned" in classes:
        fill = "F8FAFC"

    t = doc.add_table(rows=1, cols=2)
    t.autofit = False
    t.columns[0].width = Inches(1.15)
    t.columns[1].width = Inches(5.2)
    ic, bc = t.rows[0].cells
    icon_el = card.select_one(".rc-icon")
    if icon_el:
        if "active" in icon_el.get("class", []):
            set_cell_shading(ic, "0EA5E9")
        elif "idea" in icon_el.get("class", []):
            set_cell_shading(ic, "E0A800")
        else:
            set_cell_shading(ic, "94A3B8")
        paragraph_clear(ic.paragraphs[0])
        ip = ic.paragraphs[0]
        ip.alignment = WD_ALIGN_PARAGRAPH.CENTER
        ir = ip.add_run(icon_el.get_text(strip=True))
        ir.font.size = Pt(8)
        ir.bold = True
        ir.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    set_cell_shading(bc, fill)
    set_cell_margins(bc, top=50, bottom=50, left=70, right=70)
    set_cell_margins(ic, top=50, bottom=50, left=40, right=40)

    body = card.select_one(".rc-body")
    if body:
        first = True
        for sub in body.children:
            if isinstance(sub, NavigableString):
                if str(sub).strip():
                    bp = bc.paragraphs[0] if first else bc.add_paragraph()
                    first = False
                    bp.add_run(str(sub).strip())
                continue
            if sub.name == "div" and "rc-subtask" in sub.get("class", []):
                sp = bc.add_paragraph()
                first = False
                add_inline_runs(sp, sub)
                for r in sp.runs:
                    r.font.size = Pt(9)
                    r.font.color.rgb = RGBColor(0x33, 0x41, 0x55)
                continue
            if sub.name:
                bp = bc.paragraphs[0] if first else bc.add_paragraph()
                first = False
                paragraph_clear(bp)
                add_inline_runs(bp, sub)
    doc.add_paragraph()


def add_research_section(doc: Document, section_el) -> None:
    h2 = section_el.find("h2")
    if h2:
        p = doc.add_paragraph()
        r = p.add_run(h2.get_text(strip=True))
        r.bold = True
        r.font.size = Pt(14)
    for rg in section_el.select(".research-group"):
        gt = rg.select_one(".research-group-title")
        if gt:
            gp = doc.add_paragraph()
            gr = gp.add_run(gt.get_text(strip=True))
            gr.bold = True
            gr.font.size = Pt(10)
            gr.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
        for card in rg.select(".research-card"):
            add_research_card(doc, card)


def convert(html_path: pathlib.Path, docx_path: pathlib.Path) -> None:
    raw = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, "lxml")
    doc = Document()

    sec = doc.sections[0]
    sec.left_margin = Inches(0.7)
    sec.right_margin = Inches(0.7)

    wrap = soup.select_one(".wrap")
    if not wrap:
        raise SystemExit("No .wrap in HTML")

    header_el = wrap.select_one(".header")
    if header_el:
        ht = doc.add_table(rows=1, cols=1)
        hc = ht.rows[0].cells[0]
        set_cell_shading(hc, "1D4FA0")
        set_cell_margins(hc, top=120, bottom=120, left=140, right=140)
        h1 = hc.paragraphs[0]
        h1t = header_el.find("h1")
        if h1t:
            r = h1.add_run(h1t.get_text(strip=True))
            r.bold = True
            r.font.size = Pt(18)
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        for pe in header_el.find_all("p"):
            hp = hc.add_paragraph()
            add_inline_runs(hp, pe)
            for r in hp.runs:
                r.font.size = Pt(10)
                r.font.color.rgb = RGBColor(0xEE, 0xF2, 0xFF)
        doc.add_paragraph()

    src_el = wrap.select_one(".source-box")
    if src_el:
        st = doc.add_table(rows=1, cols=1)
        sc = st.rows[0].cells[0]
        set_cell_shading(sc, "FFFFFF")
        set_cell_margins(sc, top=80, bottom=80, left=100, right=100)
        sp = sc.paragraphs[0]
        paragraph_clear(sp)
        add_inline_runs(sp, src_el)
        for r in sp.runs:
            r.font.size = Pt(10)
        doc.add_paragraph()

    kpi_el = wrap.select_one(".kpi")
    if kpi_el:
        items = kpi_el.select(".kpi-item")
        kt = doc.add_table(rows=1, cols=len(items))
        kt.autofit = True
        for i, it in enumerate(items):
            cell = kt.rows[0].cells[i]
            set_cell_shading(cell, "FFFFFF")
            set_cell_margins(cell, top=60, bottom=60, left=40, right=40)
            v = it.select_one(".v")
            le = it.select_one(".l")
            if v:
                vp = cell.add_paragraph()
                vp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                add_inline_runs(vp, v)
                for r in vp.runs:
                    r.bold = True
                    r.font.size = Pt(16)
            if le:
                lp = cell.add_paragraph()
                lp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                lr = lp.add_run(le.get_text(strip=True))
                lr.font.size = Pt(9)
                lr.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
        doc.add_paragraph()

    zone_res = soup.select_one(".zone-results")
    if zone_res:
        for child in zone_res.children:
            if not getattr(child, "name", None):
                continue
            cl = child.get("class", [])
            if "section-title" in cl and "results" in cl:
                tt = doc.add_table(rows=1, cols=1)
                tc = tt.rows[0].cells[0]
                set_cell_shading(tc, "EFF6FF")
                set_cell_margins(tc, top=70, bottom=70, left=100, right=100)
                main_t = child.get_text(" ", strip=True)
                main_t = re.sub(r"\s+", " ", main_t)
                p = tc.paragraphs[0]
                r = p.add_run(main_t)
                r.bold = True
                r.font.size = Pt(12)
                r.font.color.rgb = RGBColor(0x1E, 0x40, 0xAF)
                doc.add_paragraph()
            elif "base-label" in cl:
                bp = doc.add_paragraph()
                br = bp.add_run(child.get_text(" ", strip=True))
                br.bold = True
                br.font.size = Pt(10)
                br.font.color.rgb = RGBColor(0x0E, 0x7A, 0x5F)
            elif "grid" in cl:
                for block in child.find_all(
                    "div",
                    class_=lambda c: bool(c) and "block" in c,
                    recursive=False,
                ):
                    add_card(doc, block)
            elif "table-wrap" in cl:
                h2 = child.find("h2")
                if h2:
                    hp = doc.add_paragraph()
                    hr = hp.add_run(h2.get_text(strip=True))
                    hr.bold = True
                    hr.font.size = Pt(13)
                tbl = child.find("table")
                if tbl:
                    add_main_table(doc, tbl)

    zone_act = soup.select_one(".zone-actions")
    if zone_act:
        det = zone_act.find("details")
        if det:
            summ = det.find("summary")
            if summ:
                tt = doc.add_table(rows=1, cols=1)
                tc = tt.rows[0].cells[0]
                set_cell_shading(tc, "F0FDF4")
                set_cell_margins(tc, top=70, bottom=70, left=100, right=100)
                tx = summ.get_text(" ", strip=True)
                tx = re.sub(r"\s+", " ", tx)
                p = tc.paragraphs[0]
                r = p.add_run(tx)
                r.bold = True
                r.font.size = Pt(12)
                r.font.color.rgb = RGBColor(0x16, 0x65, 0x34)
                doc.add_paragraph()
            rs = det.select_one(".research-section")
            if rs:
                add_research_section(doc, rs)

    summary_el = wrap.select_one(".summary")
    if summary_el:
        h2 = summary_el.find("h2")
        if h2:
            sp = doc.add_paragraph()
            sr = sp.add_run(h2.get_text(strip=True))
            sr.bold = True
            sr.font.size = Pt(14)
        box = doc.add_table(rows=1, cols=1)
        bc = box.rows[0].cells[0]
        set_cell_shading(bc, "FFFFFF")
        set_cell_margins(bc, top=80, bottom=80, left=100, right=100)
        ul = summary_el.find("ul")
        if ul:
            for li in ul.find_all("li", recursive=False):
                lp = bc.add_paragraph()
                lp.paragraph_format.left_indent = Inches(0.2)
                lp.style = "List Bullet"
                paragraph_clear(lp)
                add_inline_runs(lp, li)
                for r in lp.runs:
                    r.font.size = Pt(10)

    doc.save(str(docx_path))


def main() -> None:
    base = pathlib.Path(__file__).resolve().parent
    html = base / "report_cards_2026_04_05.html"
    out = base / "report_cards_2026_04_05.docx"
    if len(sys.argv) >= 2:
        html = pathlib.Path(sys.argv[1])
    if len(sys.argv) >= 3:
        out = pathlib.Path(sys.argv[2])
    convert(html, out)
    print("OK: " + str(out))


if __name__ == "__main__":
    main()
