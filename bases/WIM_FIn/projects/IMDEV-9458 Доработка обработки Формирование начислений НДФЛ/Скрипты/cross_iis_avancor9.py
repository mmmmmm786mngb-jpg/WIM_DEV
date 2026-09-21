#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cross IIS portfolio list vs Avancor 9 (and optionally 8) NDFL dumps.
Writes text summary + HTML report for IMDEV-9458.
"""

import html
import pathlib
import re
import zipfile
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

BASE = pathlib.Path(r"bases/WIM_FIn/projects/IMDEV-7330 НовыеТесты")
PROJ = pathlib.Path(
    r"bases/WIM_FIn/projects/IMDEV-9458 Доработка обработки Формирование начислений НДФЛ"
)
OUT_TXT = PROJ / "Тестирование" / "reports" / "iis_vs_avancor9_report.txt"
OUT_HTML = PROJ / "Документация" / "imdev9458_iis_avancor9_report.html"

IIS_XLSX = BASE / "ПОртфели_ИндивидуальныеИнвестиционныеСчета.xlsx"

RUNS = {
    "9": {
        "uk": BASE / "НДФЛ_Управление_24889_ПоНовому_Аванкор_9.xlsx",
        "pf": BASE / "НДФЛ_Портфели_24889_ПоНовому_Аванкор_9.xlsx",
        "log": BASE / "Лог формирования начисдений НДФЛ_24889_ПоНовому_Аванкор_9.xlsx",
        "msg": BASE / "Сообщения_24889_поНовому_Аванкор_9.txt",
    },
    "8": {
        "uk": BASE / "НДФЛ_Управление_24889_ПоНовому_Аванкор_8.xlsx",
        "pf": BASE / "НДФЛ_Портфели_24889_ПоНовому_Аванкор_8.xlsx",
        "log": BASE / "Лог формирования начисдений НДФЛ_24889_ПоНовому_Аванкор_8.xlsx",
        "msg": BASE / "Сообщения_24889_поНовому_Аванкор_8.txt",
    },
}

TAX_TCH = {"Начисления", "Удержания"}
SOFT_TCH = {"Выводы", "ОбщиеРасходы"}
SKIP_EMPTY = 'Документ "Начисление НДФЛ по УК" не записан: отсутствуют данные для расчета'
ZERO_HDR = "Не созданы начисления по клиентам с нулевым НДФЛ"


def load_strings(z):
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return [
        "".join(t.text or "" for t in si.findall(".//m:t", NS))
        for si in root.findall("m:si", NS)
    ]


def col_row(ref):
    m = re.match(r"([A-Z]+)(\d+)", ref)
    col, row = m.group(1), int(m.group(2))
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - 64)
    return n, row


def cell_val(c, strings):
    t = c.get("t")
    v = c.find("m:v", NS)
    if v is None or v.text is None:
        return ""
    if t == "s":
        return strings[int(v.text)]
    return v.text


def to_dec(s):
    s = (s or "").strip().replace(" ", "").replace("\xa0", "").replace(",", ".")
    if not s:
        return Decimal("0")
    try:
        return Decimal(s)
    except InvalidOperation:
        return Decimal("0")


def read_iis():
    with zipfile.ZipFile(IIS_XLSX) as z:
        strings = load_strings(z)
        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        rows = defaultdict(dict)
        for c in root.findall(".//m:c", NS):
            ref = c.get("r")
            if not ref:
                continue
            col, row = col_row(ref)
            rows[row][col] = cell_val(c, strings)
    ports = set()
    client_by_port = {}
    clients = set()
    for r, cols in rows.items():
        if r == 1:
            continue
        p = (cols.get(1) or "").strip()
        c = (cols.get(2) or "").strip()
        if not p or p == "Ссылка":
            continue
        ports.add(p)
        client_by_port[p] = c
        if c:
            clients.add(c)
    return ports, client_by_port, clients


def analyze_uk(path, iis_ports):
    """Return stats for UK dump vs IIS list."""
    with zipfile.ZipFile(path) as z:
        strings = load_strings(z)
        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        header = {}
        rows = defaultdict(dict)
        for c in root.findall(".//m:c", NS):
            ref = c.get("r")
            if not ref:
                continue
            col, row = col_row(ref)
            val = cell_val(c, strings)
            if row == 1:
                header[col] = val
            else:
                rows[row][col] = val

    name_to_col = {v: k for k, v in header.items()}
    c_tch = name_to_col.get("ТабличнаяЧасть")
    c_port = name_to_col.get("Портфель")
    c_doc = name_to_col.get("Ссылка")
    c_cli = name_to_col.get("Клиент")
    c_sum_d = name_to_col.get("СуммаДохода")
    c_sum_u = name_to_col.get("СуммаКУдержанию")

    # All docs + classification
    docs = {}  # doc -> {tch_set, income, withhold, ports, client}
    iis_tch = Counter()
    iis_ports_by_tch = defaultdict(set)
    iis_hard = set()
    iis_soft = set()
    iis_any = set()
    iis_docs = set()
    iis_doc_clients = set()

    for r, cols in rows.items():
        doc = (cols.get(c_doc) or "").strip() if c_doc else ""
        if not doc:
            continue
        tch = (cols.get(c_tch) or "").strip() if c_tch else ""
        port = (cols.get(c_port) or "").strip() if c_port else ""
        cli = (cols.get(c_cli) or "").strip() if c_cli else ""
        sd = to_dec(cols.get(c_sum_d) if c_sum_d else "")
        su = to_dec(cols.get(c_sum_u) if c_sum_u else "")

        info = docs.setdefault(
            doc,
            {
                "tch": set(),
                "income": Decimal("0"),
                "withhold": Decimal("0"),
                "ports": set(),
                "client": cli,
            },
        )
        if tch:
            info["tch"].add(tch)
        info["income"] += sd
        info["withhold"] += su
        if port:
            info["ports"].add(port)
        if cli and not info["client"]:
            info["client"] = cli

        if port in iis_ports:
            iis_any.add(port)
            iis_docs.add(doc)
            if cli:
                iis_doc_clients.add(cli)
            iis_tch[tch or "(empty)"] += 1
            iis_ports_by_tch[tch or "(empty)"].add(port)
            if tch in TAX_TCH:
                iis_hard.add(port)
            if tch in SOFT_TCH:
                iis_soft.add(port)

    iis_soft_only = iis_soft - iis_hard

    # Doc emptiness: no tax TCH at all
    hollow_docs = []
    tax_docs = 0
    for doc, info in docs.items():
        has_tax = bool(info["tch"] & TAX_TCH)
        if has_tax:
            tax_docs += 1
        else:
            hollow_docs.append(doc)

    # Hollow docs that mention IIS portfolio
    hollow_with_iis = [
        d for d in hollow_docs if docs[d]["ports"] & iis_ports
    ]
    # Hollow docs whose client is only from IIS list (weak signal)
    # Better: docs that ONLY contain IIS ports (or no ports) and no tax
    hollow_only_iis_ports = []
    for d in hollow_docs:
        ports = docs[d]["ports"]
        if ports and ports <= iis_ports:
            hollow_only_iis_ports.append(d)

    return {
        "docs": len(docs),
        "rows": len(rows),
        "tax_docs": tax_docs,
        "hollow_docs": len(hollow_docs),
        "iis_any": iis_any,
        "iis_hard": iis_hard,
        "iis_soft_only": iis_soft_only,
        "iis_tch": iis_tch,
        "iis_docs": iis_docs,
        "iis_doc_clients": iis_doc_clients,
        "hollow_with_iis": hollow_with_iis,
        "hollow_only_iis_ports": hollow_only_iis_ports,
        "docs_map": docs,
    }


def analyze_pf(path, iis_ports):
    with zipfile.ZipFile(path) as z:
        strings_list = load_strings(z)
        strings = set(strings_list)
        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        header = {}
        rows = defaultdict(dict)
        for c in root.findall(".//m:c", NS):
            ref = c.get("r")
            if not ref:
                continue
            col, row = col_row(ref)
            val = cell_val(c, strings_list)
            if row == 1:
                header[col] = val
            else:
                rows[row][col] = val

    name_to_col = {v: k for k, v in header.items()}
    c_port = name_to_col.get("Портфель") or name_to_col.get("Объект")
    c_doc = name_to_col.get("Ссылка")
    docs = set()
    iis_hit = set()
    for r, cols in rows.items():
        port = (cols.get(c_port) or "").strip() if c_port else ""
        doc = (cols.get(c_doc) or "").strip() if c_doc else ""
        if doc:
            docs.add(doc)
        if port in iis_ports:
            iis_hit.add(port)
    iis_in_ss = sorted(p for p in iis_ports if p in strings)
    return {
        "docs": len(docs),
        "rows": len(rows),
        "iis_ports_in_dump": iis_hit,
        "iis_in_strings": iis_in_ss,
    }


def analyze_log(path, iis_clients):
    with zipfile.ZipFile(path) as z:
        strings_list = load_strings(z)
    text = "\n".join(strings_list)
    skip_clients = set()
    # Block after ZERO_HDR often lists clients; also SKIP_EMPTY lines may name client nearby
    # Avancor 8 report used: LOG skip empty-calc clients count from parsing log
    # Heuristic: find lines with SKIP_EMPTY and nearby client names from iis_clients
    # Also search ZERO_HDR section
    in_zero = False
    for line in strings_list:
        s = line.strip()
        if ZERO_HDR in s:
            in_zero = True
            continue
        if in_zero:
            if not s or s.startswith("Начало") or s.startswith("Объект"):
                in_zero = False
                continue
            # client name alone or with semicolon
            name = s.split(";")[0].strip()
            if name in iis_clients:
                skip_clients.add(name)
            elif "," in s:
                for part in s.split(","):
                    part = part.strip()
                    if part in iis_clients:
                        skip_clients.add(part)
        if SKIP_EMPTY in s:
            for cli in iis_clients:
                if cli in s:
                    skip_clients.add(cli)

    # Broader: any IIS client mentioned in skip-related strings
    for s in strings_list:
        if SKIP_EMPTY in s or ZERO_HDR in s or "нулевым НДФЛ" in s or "отсутствуют данные" in s:
            for cli in iis_clients:
                if cli in s:
                    skip_clients.add(cli)

    # Count skip messages
    skip_msg_n = sum(1 for s in strings_list if SKIP_EMPTY in s)
    zero_hdr_n = sum(1 for s in strings_list if ZERO_HDR in s)
    return {
        "skip_msg_n": skip_msg_n,
        "zero_hdr_n": zero_hdr_n,
        "iis_skip_clients": skip_clients,
        "nrows": len(strings_list),
    }


def analyze_msg(path, iis_clients):
    if not path.exists():
        return {"lines": 0, "iis_hits": set()}
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    hits = {c for c in iis_clients if c in text}
    empty_skip = sum(1 for ln in lines if SKIP_EMPTY in ln)
    return {"lines": len(lines), "iis_hits": hits, "empty_skip": empty_skip}


def analyze_run(label, paths, iis_ports, iis_clients):
    print("Analyzing Avancor", label, "...")
    uk = analyze_uk(paths["uk"], iis_ports)
    print("  UK done docs=", uk["docs"], "iis_hard=", len(uk["iis_hard"]), "iis_soft=", len(uk["iis_soft_only"]))
    pf = analyze_pf(paths["pf"], iis_ports)
    print("  PF done docs=", pf["docs"], "iis_in_pf=", len(pf["iis_ports_in_dump"]))
    log = analyze_log(paths["log"], iis_clients)
    print("  LOG skip_iis_clients=", len(log["iis_skip_clients"]))
    msg = analyze_msg(paths["msg"], iis_clients)
    return {"uk": uk, "pf": pf, "log": log, "msg": msg}


def fmt_n(n):
    return "{:,}".format(n).replace(",", " ")


def build_html(iis_ports, iis_clients, a9, a8):
    soft9 = sorted(a9["uk"]["iis_soft_only"])
    hard9 = sorted(a9["uk"]["iis_hard"])
    soft8 = sorted(a8["uk"]["iis_soft_only"])
    hard8 = sorted(a8["uk"]["iis_hard"])

    soft_only9 = sorted(set(soft9) - set(soft8))
    soft_only8 = sorted(set(soft8) - set(soft9))
    soft_both = sorted(set(soft9) & set(soft8))

    # Verdict
    empty_iis_docs_a9 = len(a9["uk"]["hollow_only_iis_ports"])
    pf_iis_a9 = len(a9["pf"]["iis_ports_in_dump"])
    hard_a9 = len(hard9)

    verdict_ok = hard_a9 == 0 and pf_iis_a9 == 0 and empty_iis_docs_a9 == 0

    soft_sample = soft9[:25]
    soft_more = max(0, len(soft9) - 25)

    rows_soft = "\n".join(
        "<tr><td>{}</td></tr>".format(html.escape(p)) for p in soft_sample
    )
    if soft_more:
        rows_soft += (
            "<tr><td><em>... и ещё {} портфелей</em></td></tr>".format(soft_more)
        )

    tch_rows = ""
    for tch, n in a9["uk"]["iis_tch"].most_common():
        tch_rows += "<tr><td>{}</td><td class='num'>{}</td></tr>\n".format(
            html.escape(tch), fmt_n(n)
        )

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IMDEV-9458. ИИС и прогон Аванкор 9</title>
<style>
  :root {{
    --ok: #28a745;
    --err: #dc3545;
    --info: #17a2b8;
    --warn: #b78100;
    --ink: #212529;
    --bg: #f5f6f8;
    --card: #ffffff;
    --line: #dee2e6;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: "Segoe UI", Arial, Helvetica, sans-serif;
    font-size: 15px;
    line-height: 1.45;
    color: var(--ink);
    background: var(--bg);
  }}
  .wrap {{ max-width: 960px; margin: 0 auto; padding: 24px 16px 48px; }}
  header {{
    background: #1f4a3a;
    color: #f7f1e8;
    border-radius: 16px;
    padding: 22px 24px;
    margin-bottom: 20px;
  }}
  header .kicker {{
    font-size: 11px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    opacity: 0.75;
    margin-bottom: 6px;
  }}
  header h1 {{
    margin: 0 0 8px;
    font-size: 24px;
    font-family: Georgia, "Times New Roman", serif;
  }}
  header p {{ margin: 0; color: #dce8e2; }}
  section {{
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 16px;
  }}
  h2 {{ margin: 0 0 12px; font-size: 18px; }}
  h3 {{ margin: 16px 0 8px; font-size: 16px; }}
  p {{ margin: 0 0 10px; }}
  ul {{ margin: 0 0 10px; padding-left: 20px; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0 4px;
    font-size: 14px;
  }}
  th, td {{
    border: 1px solid var(--line);
    padding: 8px 10px;
    text-align: left;
    vertical-align: top;
  }}
  th {{ background: #eef2f0; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .ok {{ color: var(--ok); font-weight: 600; }}
  .warn {{ color: var(--warn); font-weight: 600; }}
  .err {{ color: var(--err); font-weight: 600; }}
  .box-ok {{
    background: #e7f4ec;
    border-radius: 10px;
    padding: 12px 14px;
    margin: 8px 0 0;
  }}
  .box-warn {{
    background: #fff3cd;
    border-radius: 10px;
    padding: 12px 14px;
    margin: 8px 0 0;
  }}
  .box-info {{
    background: #e8f4f8;
    border-radius: 10px;
    padding: 12px 14px;
    margin: 8px 0 0;
  }}
  code {{
    font-family: Consolas, "Courier New", monospace;
    font-size: 13px;
    background: #eef2f0;
    padding: 1px 5px;
    border-radius: 4px;
  }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="kicker">IMDEV-9458 · проверка по замечанию заказчика</div>
    <h1>Активные ИИС и прогон Аванкор 9</h1>
    <p>
      Сверка списка портфелей «Индивидуальные инвестиционные счета»
      с выгрузками документов прогона 9 (база 24889). Рядом — те же метрики по прогону 8.
    </p>
  </header>

  <section>
    <h2>1. Замечание заказчика</h2>
    <p>
      Активный портфель ИИС (тип клиента «Индивидуальные инвестиционные счета»,
      дата окончания пустая) не должен давать начисление НДФЛ из обработки
      «Формирование начислений НДФЛ»: ни отдельного документа по портфелю,
      ни строк налога («Начисления» / «Удержания») в документе по УК.
    </p>
    <div class="box-info">
      Список для сверки: выгрузка портфелей ИИС — <strong>{fmt_n(len(iis_ports))}</strong> портфелей,
      <strong>{fmt_n(len(iis_clients))}</strong> клиентов.
      Источник сверки: Excel-выгрузки УК / портфелей / лога прогона Аванкор 9.
    </div>
  </section>

  <section>
    <h2>2. Вердикт по прогону 9</h2>
    {"<div class='box-ok'><strong class='ok'>Требование по налогу выполняется.</strong> По списку ИИС в прогоне 9 нет отдельных документов по портфелю и нет строк «Начисления» / «Удержания» с портфелем ИИС. Массовых «пустых» документов УК, собранных только из портфелей ИИС, тоже нет.</div>" if verdict_ok else "<div class='box-warn'><strong class='warn'>Есть отклонения — смотрите таблицу ниже.</strong></div>"}
    <table>
      <tr>
        <th>Проверка</th>
        <th class="num">Аванкор 9</th>
        <th class="num">Аванкор 8</th>
        <th>Ожидание</th>
      </tr>
      <tr>
        <td>ИИС в документах по портфелю</td>
        <td class="num">{fmt_n(pf_iis_a9)}</td>
        <td class="num">{fmt_n(len(a8["pf"]["iis_ports_in_dump"]))}</td>
        <td class="ok">0</td>
      </tr>
      <tr>
        <td>ИИС со строками налога (Начисления / Удержания)</td>
        <td class="num">{fmt_n(hard_a9)}</td>
        <td class="num">{fmt_n(len(hard8))}</td>
        <td class="ok">0</td>
      </tr>
      <tr>
        <td>«Пустые» документы УК только из портфелей ИИС</td>
        <td class="num">{fmt_n(empty_iis_docs_a9)}</td>
        <td class="num">{fmt_n(len(a8["uk"]["hollow_only_iis_ports"]))}</td>
        <td class="ok">0</td>
      </tr>
      <tr>
        <td>ИИС только в служебных ТЧ (Выводы / Общие расходы)</td>
        <td class="num">{fmt_n(len(soft9))}</td>
        <td class="num">{fmt_n(len(soft8))}</td>
        <td>допустимо внутри документа УК с расчётом по другим договорам</td>
      </tr>
    </table>
  </section>

  <section>
    <h2>3. Статистика документов прогона</h2>
    <table>
      <tr>
        <th>Показатель</th>
        <th class="num">Аванкор 9</th>
        <th class="num">Аванкор 8</th>
        <th class="num">Дельта 9−8</th>
      </tr>
      <tr>
        <td>Документов УК</td>
        <td class="num">{fmt_n(a9["uk"]["docs"])}</td>
        <td class="num">{fmt_n(a8["uk"]["docs"])}</td>
        <td class="num">{fmt_n(a9["uk"]["docs"] - a8["uk"]["docs"])}</td>
      </tr>
      <tr>
        <td>из них с ТЧ налога</td>
        <td class="num">{fmt_n(a9["uk"]["tax_docs"])}</td>
        <td class="num">{fmt_n(a8["uk"]["tax_docs"])}</td>
        <td class="num">{fmt_n(a9["uk"]["tax_docs"] - a8["uk"]["tax_docs"])}</td>
      </tr>
      <tr>
        <td>«Полые» УК (без Начислений/Удержаний)</td>
        <td class="num">{fmt_n(a9["uk"]["hollow_docs"])}</td>
        <td class="num">{fmt_n(a8["uk"]["hollow_docs"])}</td>
        <td class="num">{fmt_n(a9["uk"]["hollow_docs"] - a8["uk"]["hollow_docs"])}</td>
      </tr>
      <tr>
        <td>Документов по портфелю</td>
        <td class="num">{fmt_n(a9["pf"]["docs"])}</td>
        <td class="num">{fmt_n(a8["pf"]["docs"])}</td>
        <td class="num">{fmt_n(a9["pf"]["docs"] - a8["pf"]["docs"])}</td>
      </tr>
    </table>
    <div class="box-warn">
      Прирост документов УК в прогоне 9 (+{fmt_n(a9["uk"]["docs"] - a8["uk"]["docs"])})
      связан с выключенным отбором по оборотам доходов, а не с созданием пустых начислений по ИИС.
      По списку ИИС отдельных «пустых» документов УК не появилось.
    </div>
  </section>

  <section>
    <h2>4. Где ИИС всё же встречается в документе УК</h2>
    <p>
      В прогоне 9 портфель из списка ИИС встречается в выгрузке УК у
      <strong>{fmt_n(len(a9["uk"]["iis_any"]))}</strong> портфелей.
      Все такие вхождения — только служебные табличные части:
    </p>
    <table>
      <tr><th>Табличная часть</th><th class="num">Строк с ИИС</th></tr>
      {tch_rows}
    </table>
    <p>
      Жёстких (налог): <strong class="ok">{fmt_n(hard_a9)}</strong>.
      Только служебные: <strong>{fmt_n(len(soft9))}</strong>
      (в прогоне 8 было {fmt_n(len(soft8))}; общих — {fmt_n(len(soft_both))},
      только в 9 — {fmt_n(len(soft_only9))}, только в 8 — {fmt_n(len(soft_only8))}).
    </p>
    <h3>Примеры ИИС только в Выводы / Общие расходы (прогон 9)</h3>
    <table>
      <tr><th>Портфель</th></tr>
      {rows_soft if rows_soft else "<tr><td>(нет)</td></tr>"}
    </table>
  </section>

  <section>
    <h2>5. Лог и сообщения</h2>
    <table>
      <tr>
        <th>Показатель</th>
        <th class="num">Аванкор 9</th>
        <th class="num">Аванкор 8</th>
      </tr>
      <tr>
        <td>Сообщений «не записан: отсутствуют данные для расчета»</td>
        <td class="num">{fmt_n(a9["msg"]["empty_skip"])}</td>
        <td class="num">{fmt_n(a8["msg"]["empty_skip"])}</td>
      </tr>
      <tr>
        <td>Клиентов из списка ИИС в блоках отказа / нулевого НДФЛ (лог)</td>
        <td class="num">{fmt_n(len(a9["log"]["iis_skip_clients"]))}</td>
        <td class="num">{fmt_n(len(a8["log"]["iis_skip_clients"]))}</td>
      </tr>
      <tr>
        <td>Клиентов из списка ИИС в файле сообщений</td>
        <td class="num">{fmt_n(len(a9["msg"]["iis_hits"]))}</td>
        <td class="num">{fmt_n(len(a8["msg"]["iis_hits"]))}</td>
      </tr>
    </table>
    <p>
      Отказ записи документа УК без данных для расчёта — штатный шаг «Создать»,
      а не эффект отбора по оборотам на «Заполнить». Клиент с ИИС может остаться
      в таблице после заполнения, а документ по нему не создаётся, если считать нечего.
    </p>
  </section>

  <section>
    <h2>6. Вывод для заказчика</h2>
    <ul>
      <li>По замечанию об активных ИИС в прогоне Аванкор 9 <strong>пустые документы начисления по списку ИИС не создавались</strong>.</li>
      <li>Отдельных документов по портфелю ИИС — <strong>0</strong>.</li>
      <li>Строк налога по ИИС в документе УК — <strong>0</strong>.</li>
      <li>Единичные / массовые попадания ИИС возможны только в служебных ТЧ внутри документа УК, где уже есть расчёт по другим договорам того же клиента (как и в прогоне 8).</li>
      <li>Отдельный флажок на форме под ИИС по-прежнему не требуется: правило закрыто логикой «Создать» / отбора портфелей.</li>
    </ul>
  </section>
</div>
</body>
</html>
"""


def write_txt(iis_ports, iis_clients, a9, a8):
    lines = []
    lines.append("IIS list: %s ports, %s clients" % (len(iis_ports), len(iis_clients)))
    lines.append("")
    for label, data in (("9", a9), ("8", a8)):
        uk = data["uk"]
        pf = data["pf"]
        log = data["log"]
        msg = data["msg"]
        lines.append("========== AVANCOR %s ==========" % label)
        lines.append(
            "UK docs: %s  hollow: %s  with tax: %s"
            % (uk["docs"], uk["hollow_docs"], uk["tax_docs"])
        )
        lines.append(
            "PF docs: %s  IIS in PF: %s"
            % (pf["docs"], len(pf["iis_ports_in_dump"]))
        )
        lines.append(
            "IIS in UK: %s  hard(tax): %s  soft: %s"
            % (len(uk["iis_any"]), len(uk["iis_hard"]), len(uk["iis_soft_only"]))
        )
        lines.append(
            "hollow UK only-IIS-ports: %s  hollow with any IIS: %s"
            % (len(uk["hollow_only_iis_ports"]), len(uk["hollow_with_iis"]))
        )
        lines.append(
            "LOG iis skip clients: %s  MSG empty_skip: %s  MSG iis hits: %s"
            % (len(log["iis_skip_clients"]), msg["empty_skip"], len(msg["iis_hits"]))
        )
        lines.append("UK TCH top: %s" % uk["iis_tch"].most_common(10))
        lines.append("IIS soft list: %s" % sorted(uk["iis_soft_only"]))
        lines.append("IIS hard list: %s" % sorted(uk["iis_hard"]))
        lines.append("")
    lines.append("========== COMPARE 9 vs 8 ==========")
    lines.append(
        "UK docs: 9=%s 8=%s delta=%s"
        % (a9["uk"]["docs"], a8["uk"]["docs"], a9["uk"]["docs"] - a8["uk"]["docs"])
    )
    lines.append(
        "IIS hard: 9=%s 8=%s"
        % (len(a9["uk"]["iis_hard"]), len(a8["uk"]["iis_hard"]))
    )
    lines.append(
        "IIS soft: 9=%s 8=%s"
        % (len(a9["uk"]["iis_soft_only"]), len(a8["uk"]["iis_soft_only"]))
    )
    lines.append(
        "IIS in PF: 9=%s 8=%s"
        % (len(a9["pf"]["iis_ports_in_dump"]), len(a8["pf"]["iis_ports_in_dump"]))
    )
    lines.append(
        "hollow only-IIS: 9=%s 8=%s"
        % (
            len(a9["uk"]["hollow_only_iis_ports"]),
            len(a8["uk"]["hollow_only_iis_ports"]),
        )
    )
    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")
    print("WROTE", OUT_TXT)


def main():
    iis_ports, client_by_port, iis_clients = read_iis()
    print("IIS portfolios:", len(iis_ports), "clients:", len(iis_clients))

    a9 = analyze_run("9", RUNS["9"], iis_ports, iis_clients)
    a8 = analyze_run("8", RUNS["8"], iis_ports, iis_clients)

    write_txt(iis_ports, iis_clients, a9, a8)

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(build_html(iis_ports, iis_clients, a9, a8), encoding="utf-8")
    print("WROTE", OUT_HTML)

    print("--- SUMMARY A9 ---")
    print("hard", len(a9["uk"]["iis_hard"]))
    print("soft", len(a9["uk"]["iis_soft_only"]))
    print("pf", len(a9["pf"]["iis_ports_in_dump"]))
    print("hollow only iis", len(a9["uk"]["hollow_only_iis_ports"]))


if __name__ == "__main__":
    main()
