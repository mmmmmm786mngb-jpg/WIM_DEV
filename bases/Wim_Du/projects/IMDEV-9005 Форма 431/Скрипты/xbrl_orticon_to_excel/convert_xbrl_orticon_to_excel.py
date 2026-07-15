#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Konverter XBRL Orticon (NSO PURCB) -> multi-sheet XLSX.
Gruppirovki listov - po suti kak etalon konvertera ORTIKON/CBR.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import zipfile
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

from openpyxl import Workbook
from openpyxl.styles import Font


def qlocal(name: str) -> str:
    if not name:
        return ""
    if "}" in name:
        return name.rsplit("}", 1)[-1]
    if ":" in name:
        return name.split(":", 1)[-1]
    return name


def humanize(value: str) -> str:
    if not value:
        return ""
    v = str(value).strip()
    if "}" in v:
        v = v.rsplit("}", 1)[-1]
    if ":" in v:
        v = v.split(":")[-1]
    for suf in ("Member", "MEMBER", "TypedName", "Typedname"):
        if v.endswith(suf):
            v = v[: -len(suf)]
            break
    v = v.replace("_", " ")
    return v


def excel_sheet_name(name: str, used: set[str]) -> str:
    bad = '[]:*?/\\'
    for ch in bad:
        name = name.replace(ch, " ")
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        name = "List"
    if len(name) > 31:
        name = name[:31]
    base = name
    n = 1
    while name in used:
        suf = "_%d" % n
        name = (base[: 31 - len(suf)] + suf) if len(base) + len(suf) > 31 else base + suf
        n += 1
    used.add(name)
    return name


def is_du(dims: dict) -> bool:
    v = dims.get("Vid_DeyatelnostiAxis", "")
    return "upravleniyu" in v.lower() or "upravlen" in v.lower()


def is_broker(dims: dict) -> bool:
    v = dims.get("Vid_DeyatelnostiAxis", "")
    return "broker" in v.lower()


def sheet_title_for(sig: frozenset, dims: dict) -> tuple[str, str]:
    """Return (sheet_title_31_style, toc_description)."""
    axes = set(sig)

    if not axes:
        return (
            "Сопроводительная информация об ",
            "Сопроводительная информация об отчитывающейся организации",
        )
    if axes == {"OKUDAxis"}:
        return (
            "Сопроводительная информация к о",
            "Сопроводительная информация к отчетности. Сведения об ответственных лицах",
        )
    if axes == {"Rek_kred_org_i_schetaTaxis"}:
        return (
            "0420409 Раздел 1 Сведения о бан",
            "0420409 Раздел 1. Сведения о банковских счетах, ежемесячная",
        )
    if axes == {"ID_broker_kliringTaxis", "ID_strokiTaxis"}:
        return (
            "0420409 Раздел 2 Сведения о ден",
            "0420409 Раздел 2. Сведения о денежных средствах у брокера/клиринга",
        )
    if axes == {"ID_strokiTaxis", "Rek_Vyd_ZajmTaxis"}:
        return (
            "0420414 Раздел 1 Выданные займы",
            "0420414 Раздел 1. Выданные займы",
        )
    if axes == {"TechnicalAxis"}:
        return (
            "0420414 Раздел 2 Полученные зай",
            "0420414 Раздел 2. Полученные займы (итоги/технический контекст)",
        )
    if axes == {"ID_strokiTaxis"}:
        return (
            "Информация о документах включен",
            "Информация о документах, включенных в состав пакета с отчетностью",
        )
    if axes == {"ID_strategTaxis"}:
        return (
            "0420431 Раздел 1 Сведения об ос",
            "0420431 Раздел 1. Подраздел 1.1. Информация о стратегиях ДУ",
        )
    if axes == {"ID_CzennojBumagiTaxis"}:
        return (
            "0420459 Раздел 1 Сведения о цен",
            "0420459 Раздел 1. Подраздел 1.1. Сведения о ценных бумагах",
        )

    # 1.2 Postupl/Izyat
    if axes == {
        "ID_strategTaxis",
        "InvestProfileTaxis",
        "KADogAxis",
        "Kod_OKATO_KodOKSMAxis",
        "Kvalificzirovannost_investoraAxis",
        "PriznakIISAxis",
        "Tip_i_status_klienta2Axis",
        "Tip_i_status_klientaAxis",
        "Tip_imushhestvaAxis",
        "Vid_DeyatelnostiAxis",
    }:
        if is_broker(dims):
            return (
                "0420431 Раздел 1 Сведения об _1",
                "0420431 Раздел 1. Подраздел 1.2 (Брокерская деятельность)",
            )
        return (
            "0420431 Раздел 1 Сведения об _2",
            "0420431 Раздел 1. Подраздел 1.2 (Деятельность по управлению ЦБ)",
        )

    # 1.2 KolDog*
    if axes == {
        "ID_strategTaxis",
        "InvestProfileTaxis",
        "KADogAxis",
        "Kod_OKATO_KodOKSMAxis",
        "Kvalificzirovannost_investoraAxis",
        "PriznakIISAxis",
        "Tip_i_status_klienta2Axis",
        "Tip_i_status_klientaAxis",
        "Vid_DeyatelnostiAxis",
    }:
        # otdelnyy list, chtoby ne smeshivat s Postupl; stil imeni kak u etalona
        if is_broker(dims):
            return (
                "0420431 Раздел 1 Договоры брок",
                "0420431 Раздел 1. Подраздел 1.2 количество договоров (брокер)",
            )
        return (
            "0420431 Раздел 1 Договоры ДУ",
            "0420431 Раздел 1. Подраздел 1.2 количество договоров (ДУ)",
        )

    # 1.3 concentration
    if axes == {
        "Kod_OKATO_KodOKSMAxis",
        "Kvalificzirovannost_investoraAxis",
        "RazmSchAxis",
        "Tip_i_status_klienta2Axis",
        "Tip_i_status_klientaAxis",
        "Vid_DeyatelnostiAxis",
    }:
        return (
            "0420431 Раздел 1 Сведения об _3",
            "0420431 Раздел 1. Подраздел 1.3. Концентрация активов и клиентов",
        )

    # Razdel 2 DS
    if axes == {
        "IDBrokeraKOTaxis",
        "ID_strategTaxis",
        "InvestProfileTaxis",
        "KADogAxis",
        "Kod_OKATO_KodOKSMAxis",
        "Kod_ValyutyAxis",
        "Kvalificzirovannost_investoraAxis",
        "PriznakIISAxis",
        "Tip_i_status_klienta2Axis",
        "Tip_i_status_klientaAxis",
        "Tip_imushhestvaAxis",
        "Uroven_riskaAxis",
        "Vid_DeyatelnostiAxis",
    }:
        if is_broker(dims):
            return (
                "0420431 Раздел 2 Сведения о пор",
                "0420431 Раздел 2. Портфель ДС (брокер)",
            )
        return (
            "0420431 Раздел 2 Сведения о п_1",
            "0420431 Раздел 2. Портфель ДС (ДУ)",
        )

    # Razdel 3 deposits
    if axes == {
        "ID_strategTaxis",
        "InvestProfileTaxis",
        "KADogAxis",
        "Kod_OKATO_KodOKSMAxis",
        "Kod_ValyutyAxis",
        "Kvalificzirovannost_investoraAxis",
        "PriznakIISAxis",
        "Tip_i_status_klienta2Axis",
        "Tip_i_status_klientaAxis",
        "Tip_imushhestvaAxis",
        "Uroven_riskaAxis",
        "Vid_DeyatelnostiAxis",
    }:
        tip = dims.get("Tip_imushhestvaAxis", "")
        if is_broker(dims):
            if "Drag" in tip or "Metall" in tip:
                return (
                    "0420431 Раздел 3 Сведения о п_1",
                    "0420431 Раздел 3. Депозиты (брокер, драгметаллы)",
                )
            return (
                "0420431 Раздел 3 Сведения о пор",
                "0420431 Раздел 3. Депозиты (брокер, ДС)",
            )
        if "Drag" in tip or "Metall" in tip:
            return (
                "0420431 Раздел 3 Сведения о п_3",
                "0420431 Раздел 3. Депозиты (ДУ, драгметаллы)",
            )
        return (
            "0420431 Раздел 3 Сведения о п_2",
            "0420431 Раздел 3. Депозиты (ДУ, ДС)",
        )

    # Razdel 4 securities
    if axes == {
        "ID_CzennojBumagiTaxis",
        "ID_strategTaxis",
        "InvestProfileTaxis",
        "KADogAxis",
        "Kod_OKATO_KodOKSMAxis",
        "Kvalificzirovannost_investoraAxis",
        "PriznakIISAxis",
        "Tip_i_status_klienta2Axis",
        "Tip_i_status_klientaAxis",
        "Tip_imushhestvaAxis",
        "Uroven_riskaAxis",
        "Vid_DeyatelnostiAxis",
    }:
        if is_broker(dims):
            return (
                "0420431 Раздел 4 Сведения о пор",
                "0420431 Раздел 4. Портфель ЦБ (брокер)",
            )
        return (
            "0420431 Раздел 4 Сведения о п_1",
            "0420431 Раздел 4. Портфель ЦБ (ДУ)",
        )

    # Razdel 5 other property
    if "Inoe_imushhestvoTaxis" in axes:
        if is_broker(dims):
            return (
                "0420431 Раздел 5 Сведения о пор",
                "0420431 Раздел 5. Иное имущество (брокер)",
            )
        return (
            "0420431 Раздел 5 Сведения о п_1",
            "0420431 Раздел 5. Иное имущество (ДУ)",
        )

    # Razdel 6 PFI
    if "Rek_PFITaxis" in axes or "PoTipamPfiAxis" in axes:
        if is_broker(dims):
            return (
                "0420431 Раздел 6 Сведения о пор",
                "0420431 Раздел 6. ПФИ (брокер)",
            )
        return (
            "0420431 Раздел 6 Сведения о п_1",
            "0420431 Раздел 6. ПФИ (ДУ)",
        )

    # Razdel 7 claims
    if "TipTrebObAxis" in axes and "TrebObAxis" in axes:
        tip = dims.get("TipTrebObAxis", "")
        if "Repo" in tip or "SdelkiRepo" in tip:
            if is_broker(dims):
                return (
                    "0420431 Раздел 7 Сведения о п_2",
                    "0420431 Раздел 7. РЕПО (брокер)",
                )
            return (
                "0420431 Раздел 7 Сведения о п_5",
                "0420431 Раздел 7. РЕПО (ДУ)",
            )
        if is_broker(dims):
            return (
                "0420431 Раздел 7 Сведения о п_1",
                "0420431 Раздел 7. Прочее (брокер)",
            )
        return (
            "0420431 Раздел 7 Сведения о п_4",
            "0420431 Раздел 7. Прочее (ДУ)",
        )

    # fallback
    short = "_".join(sorted(qlocal(a).replace("Axis", "").replace("Taxis", "")[:10] for a in list(axes)[:3]))
    title = excel_sheet_name("Блок_" + short, set())
    return title, "Неклассифицированный блок осей: " + ",".join(sorted(axes))


def parse_xbrl(path: Path):
    t0 = time.time()
    contexts = {}
    facts_by_ctx = defaultdict(dict)
    schema_ref = ""
    units = {}

    for event, elem in ET.iterparse(path, events=("end",)):
        tag = qlocal(elem.tag)
        if tag == "schemaRef" and not schema_ref:
            schema_ref = elem.attrib.get("{http://www.w3.org/1999/xlink}href") or elem.attrib.get("href") or ""
        if tag == "unit":
            uid = elem.attrib.get("id", "")
            measure = ""
            for ch in elem.iter():
                if qlocal(ch.tag) == "measure" and ch.text:
                    measure = ch.text.strip()
            units[uid] = measure
            elem.clear()
            continue
        if tag == "context":
            cid = elem.attrib.get("id")
            dims = {}
            period = ""
            entity = ""
            for ch in elem.iter():
                cl = qlocal(ch.tag)
                if cl == "identifier" and ch.text:
                    entity = ch.text.strip()
                elif cl == "instant" and ch.text:
                    period = ch.text.strip()
                elif cl == "startDate" and ch.text:
                    period = "S:" + ch.text.strip()
                elif cl == "endDate" and ch.text:
                    if period.startswith("S:"):
                        period = period[2:] + ".." + ch.text.strip()
                    else:
                        period = "E:" + ch.text.strip()
                elif cl == "explicitMember":
                    dims[qlocal(ch.attrib.get("dimension", ""))] = qlocal((ch.text or "").strip())
                elif cl == "typedMember":
                    dim = qlocal(ch.attrib.get("dimension", ""))
                    val = ""
                    for sub in ch:
                        val = (sub.text or "").strip()
                        break
                    dims[dim] = val
            contexts[cid] = {
                "period": period,
                "entity": entity,
                "dims": dims,
                "sig": frozenset(dims.keys()),
            }
            elem.clear()
            continue
        if "contextRef" in elem.attrib:
            cref = elem.attrib["contextRef"]
            concept = qlocal(elem.tag)
            val = (elem.text or "").strip()
            facts_by_ctx[cref][concept] = val
            elem.clear()

    elapsed = time.time() - t0
    return {
        "contexts": contexts,
        "facts_by_ctx": facts_by_ctx,
        "schema_ref": schema_ref,
        "units": units,
        "parse_sec": elapsed,
    }


def _norm_fact_value(val: str) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.startswith("mem-int:") or ":" in s and s.split(":", 1)[0].endswith("int"):
        return humanize(s)
    return s


def _collapse_bank_accounts(raw_rows: list[dict]) -> list[dict]:
    """One row per account id: period-dependent amounts become separate columns (as in etalon)."""
    by_acc = {}
    for row in raw_rows:
        acc = row.get("Rek_kred_org_i_scheta") or row.get("Id_scheta") or ""
        if not acc:
            acc = row.get("ContextId", "")
        item = by_acc.setdefault(acc, {"Rek_kred_org_i_scheta": acc})
        period = row.get("Period") or ""
        for k, v in row.items():
            if k in ("Period", "ContextId", "Rek_kred_org_i_scheta"):
                continue
            if k in ("DSKO_BB", "DSKO_ObDt", "DSKO_ObKt"):
                col = "%s_%s" % (k, period.replace("..", "_").replace(":", "_") or "NA")
                item[col] = _norm_fact_value(v)
            elif k not in item or not item[k]:
                item[k] = _norm_fact_value(v)
    return list(by_acc.values())


def build_sheets(parsed: dict):
    contexts = parsed["contexts"]
    facts_by_ctx = parsed["facts_by_ctx"]

    sheets = {}
    used_names = set(["TOC"])

    for cid, ctx in contexts.items():
        facts = facts_by_ctx.get(cid)
        if not facts:
            continue
        title, toc = sheet_title_for(ctx["sig"], ctx["dims"])
        if title not in sheets:
            real = excel_sheet_name(title, used_names)
            sheets[title] = {
                "name": real,
                "toc": toc,
                "columns": [],
                "colset": set(),
                "rows": [],
                "raw_bank": title.startswith("0420409 Раздел 1"),
            }
        bucket = sheets[title]
        row = {"Period": ctx["period"], "ContextId": cid}
        for dim, val in sorted(ctx["dims"].items()):
            col = qlocal(dim).replace("Axis", "").replace("Taxis", "")
            row[col] = val if dim.endswith("Taxis") else humanize(val)
            if col not in bucket["colset"]:
                bucket["colset"].add(col)
                bucket["columns"].append(col)
        for concept, val in sorted(facts.items()):
            row[concept] = _norm_fact_value(val)
            if concept not in bucket["colset"]:
                bucket["colset"].add(concept)
                bucket["columns"].append(concept)
        bucket["rows"].append(row)

    # collapse bank accounts
    for title, bucket in list(sheets.items()):
        if bucket.get("raw_bank"):
            collapsed = _collapse_bank_accounts(bucket["rows"])
            bucket["rows"] = collapsed
            colset = set()
            columns = []
            for row in collapsed:
                for k in row.keys():
                    if k == "ContextId":
                        continue
                    if k not in colset:
                        colset.add(k)
                        columns.append(k)
            # stable order
            head = ["Rek_kred_org_i_scheta"]
            money = sorted([c for c in columns if c.startswith("DSKO_")])
            rest = [c for c in columns if c not in head and c not in money]
            bucket["columns"] = [c for c in head if c in colset] + rest + money
            bucket["colset"] = set(bucket["columns"])

    for bucket in sheets.values():
        if bucket.get("raw_bank"):
            continue
        preferred = ["Period"]
        others = [c for c in bucket["columns"] if c not in ("Period", "ContextId")]
        typed_like = [c for c in others if c.startswith("ID") or c.startswith("Rek") or c.startswith("Id")]
        rest = [c for c in others if c not in typed_like]
        bucket["columns"] = preferred + typed_like + rest

    return sheets


def write_xlsx(path: Path, parsed: dict, sheets: dict):
    wb = Workbook(write_only=False)
    # TOC
    ws = wb.active
    ws.title = "TOC"
    ws.append([parsed.get("schema_ref") or ""])
    ws.append([])
    ws.append(["Default Aspect"])
    ws.append(["category", "value"])
    # periods
    periods = sorted({c["period"] for c in parsed["contexts"].values() if c["period"]})
    entities = sorted({c["entity"] for c in parsed["contexts"].values() if c["entity"]})
    if periods:
        ws.append(["Period samples", "; ".join(periods[:5])])
    if entities:
        ws.append(["Identifier", entities[0]])
    ws.append(["Scheme", "http://www.cbr.ru"])
    ws.append(["Generator", "внВыгрузкаXBRLОртиконВXLSX / convert_xbrl_orticon_to_excel.py"])
    ws.append(["ParseSec", round(parsed.get("parse_sec", 0), 2)])
    ws.append([])
    ws.append(["No.", "table", "description"])
    bold = Font(bold=True)

    ordered = sorted(sheets.values(), key=lambda b: b["name"])
    n = 1
    for bucket in ordered:
        ws.append([n, bucket["name"], bucket["toc"]])
        n += 1

    for bucket in ordered:
        wss = wb.create_sheet(title=bucket["name"])
        cols = bucket["columns"]
        wss.append(cols)
        for cell in wss[1]:
            cell.font = bold
        for row in bucket["rows"]:
            wss.append([row.get(c, "") for c in cols])

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def resolve_input(path: Path) -> Path:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".xbrl")]
            if not names:
                raise RuntimeError("ZIP without .xbrl")
            out = path.with_suffix(".extracted.xbrl")
            out.write_bytes(z.read(names[0]))
            return out
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description="XBRL Orticon -> XLSX")
    ap.add_argument("input", help="path to .xbrl or .zip")
    ap.add_argument("-o", "--output", help="output .xlsx path")
    args = ap.parse_args(argv)

    inp = Path(args.input)
    if not inp.exists():
        print("ERROR: file not found:", inp)
        return 2

    out = Path(args.output) if args.output else inp.with_name(inp.stem + "_converted.xlsx")

    print("Input:", inp)
    t0 = time.time()
    xbrl_path = resolve_input(inp)
    print("Parsing...")
    parsed = parse_xbrl(xbrl_path)
    print(
        "OK parse: contexts=%d fact_ctx=%d sec=%.1f"
        % (len(parsed["contexts"]), len(parsed["facts_by_ctx"]), parsed["parse_sec"])
    )
    print("Building sheets...")
    sheets = build_sheets(parsed)
    print("Sheets with data:", len(sheets))
    for title, b in sorted(sheets.items(), key=lambda x: -len(x[1]["rows"]))[:15]:
        print("  %5d rows | %s" % (len(b["rows"]), b["name"]))
    print("Writing:", out)
    write_xlsx(out, parsed, sheets)
    print("DONE sec=%.1f size=%d" % (time.time() - t0, out.stat().st_size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
