#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse 1C PFF traces, Word screenshots and JSON snapshots for IMDEV-8663.2 report."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "Тесты_Этап2_34"
OUT = ROOT / "Тестирование" / "reports" / "_stage34_analysis"
OUT.mkdir(parents=True, exist_ok=True)

# PFF line payload after the inner { ... } context block:
# },"Module",Line,"Source",Weight,TimeTotal,TimePure,PctTotal,PctPure,f1,f2,f3,uuid,
REC_RE = re.compile(
    r'\},"((?:[^"]|"")*)",(\d+),"((?:[^"]|"")*)",(\d+),'
    r"([0-9.]+),([0-9.]+),([0-9.]+),([0-9.]+),",
    re.M,
)

MODULE_SHORT = {
    "Документ.РасчетСЧА_РСА.МодульМенеджера": "Документ.РасчетСЧА_РСА (менеджер)",
    "Документ.РасчетСЧА_РСА.МодульОбъекта": "Документ.РасчетСЧА_РСА (объект)",
    "ОбщийМодуль.ИсполняемыеПроцедурыЗакрытияПериода.Модуль": "ИсполняемыеПроцедурыЗакрытияПериода",
    "Справочник.РегламентныеПериоды.МодульМенеджера": "Справочник.РегламентныеПериоды",
    "ОбщийМодуль.ОбщегоНазначенияДУ.Модуль": "ОбщегоНазначенияДУ",
    "ОбщийМодуль.ДлительныеОперации.Модуль": "ДлительныеОперации",
    "ОбщийМодуль.ФоновыеЗаданияСервер.Модуль": "ФоновыеЗаданияСервер",
}

INTEREST_KEYS = (
    "РасчетСЧА_РСА",
    "ПолучитьСуммыРСА",
    "Операция_1000",
    "Хозрасчетный",
    "СтоимостьАктивов",
    "ЗначенияПараметровДоговор",
    "ТекстЗапроса",
    "РегламентныеПериоды",
    "ИсполняемыеПроцедурыЗакрытияПериода",
    "СоответствиеТаблицПоДоговорам",
    "Пакетно",
)


def unescape_1c(s: str) -> str:
    return s.replace('""', '"')


def parse_pff(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    header_m = re.search(
        r'\{10,"([^"]*)","",(\d+),"",(\d+),"([^"]*)".*,"([^"]*)"\}',
        raw,
    )
    count_m = re.search(r"\{0,(\d+),", raw)
    recs = []
    for m in REC_RE.finditer(raw):
        recs.append(
            {
                "module": unescape_1c(m.group(1)),
                "line": int(m.group(2)),
                "src": unescape_1c(m.group(3)),
                "count": int(m.group(4)),
                "time_total": float(m.group(5)),
                "time_pure": float(m.group(6)),
                "pct_total": float(m.group(7)),
                "pct_pure": float(m.group(8)),
            }
        )
    by_module: dict[str, dict] = defaultdict(
        lambda: {"time_total": 0.0, "time_pure": 0.0, "count": 0, "rows": 0}
    )
    for r in recs:
        b = by_module[r["module"]]
        b["time_total"] += r["time_total"]
        b["time_pure"] += r["time_pure"]
        b["count"] += r["count"]
        b["rows"] += 1

    info = {
        "file": path.name,
        "size": path.stat().st_size,
        "computer": header_m.group(1) if header_m else "",
        "pid": int(header_m.group(2)) if header_m else 0,
        "user": header_m.group(4) if header_m else "",
        "ib": header_m.group(5) if header_m else "",
        "declared_rows": int(count_m.group(1)) if count_m else 0,
        "parsed_rows": len(recs),
        "sum_time_total": sum(r["time_total"] for r in recs),
        "sum_time_pure": sum(r["time_pure"] for r in recs),
        "max_time_total": max((r["time_total"] for r in recs), default=0.0),
        "records": recs,
        "by_module": dict(by_module),
    }
    return info


def top_n(recs: list[dict], key: str, n: int = 25) -> list[dict]:
    return sorted(recs, key=lambda r: r[key], reverse=True)[:n]


def is_interesting(r: dict) -> bool:
    blob = r["module"] + " " + r["src"]
    return any(k in blob for k in INTEREST_KEYS)


def compare_modules(was: dict, now: dict) -> list[dict]:
    keys = set(was["by_module"]) | set(now["by_module"])
    rows = []
    for k in keys:
        a = was["by_module"].get(k, {"time_pure": 0.0, "time_total": 0.0, "count": 0})
        b = now["by_module"].get(k, {"time_pure": 0.0, "time_total": 0.0, "count": 0})
        d_pure = a["time_pure"] - b["time_pure"]
        rows.append(
            {
                "module": k,
                "short": MODULE_SHORT.get(k, k),
                "was_pure": a["time_pure"],
                "now_pure": b["time_pure"],
                "was_total": a["time_total"],
                "now_total": b["time_total"],
                "was_count": a["count"],
                "now_count": b["count"],
                "delta_pure": d_pure,
                "speedup": (a["time_pure"] / b["time_pure"]) if b["time_pure"] > 0.001 else None,
            }
        )
    rows.sort(key=lambda x: x["delta_pure"], reverse=True)
    return rows


def compare_lines(was: dict, now: dict) -> list[dict]:
    def key(r):
        return (r["module"], r["line"], r["src"][:80])

    a_map = {key(r): r for r in was["records"]}
    b_map = {key(r): r for r in now["records"]}
    keys = set(a_map) | set(b_map)
    rows = []
    for k in keys:
        a = a_map.get(k)
        b = b_map.get(k)
        was_t = a["time_pure"] if a else 0.0
        now_t = b["time_pure"] if b else 0.0
        was_c = a["count"] if a else 0
        now_c = b["count"] if b else 0
        src = (a or b)["src"]
        module = (a or b)["module"]
        line = (a or b)["line"]
        delta = was_t - now_t
        if abs(delta) < 0.05 and was_c == now_c:
            continue
        rows.append(
            {
                "module": module,
                "line": line,
                "src": src[:180],
                "was_pure": was_t,
                "now_pure": now_t,
                "was_count": was_c,
                "now_count": now_c,
                "delta_pure": delta,
                "interesting": is_interesting(a or b),
            }
        )
    rows.sort(key=lambda x: x["delta_pure"], reverse=True)
    return rows


def extract_docx_images(docx: Path, dest: Path) -> list[dict]:
    dest.mkdir(parents=True, exist_ok=True)
    rels_map = {}
    with zipfile.ZipFile(docx) as z:
        rels_xml = z.read("word/_rels/document.xml.rels").decode("utf-8")
        for rid, target in re.findall(
            r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels_xml
        ):
            rels_map[rid] = target
        doc_xml = z.read("word/document.xml").decode("utf-8")
        embeds = re.findall(r'r:embed="(rId\d+)"', doc_xml)
        out = []
        for i, rid in enumerate(embeds, 1):
            target = rels_map.get(rid, "")
            inner = "word/" + target.lstrip("/") if not target.startswith("word/") else target
            if inner.startswith("word/../"):
                inner = "word/" + target.split("/")[-1]
            # Target is usually media/image1.png
            if not inner.startswith("word/"):
                inner = "word/" + target
            data = z.read(inner.replace("\\", "/"))
            ext = Path(inner).suffix.lower() or ".png"
            name = f"shot_{i:02d}{ext}"
            (dest / name).write_bytes(data)
            out.append(
                {
                    "index": i,
                    "rid": rid,
                    "target": target,
                    "file": name,
                    "size": len(data),
                    "ext": ext.lstrip("."),
                }
            )
    return out


def json_meta(path: Path) -> dict:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return {
        "name": path.name,
        "size": path.stat().st_size,
        "sha256": h.hexdigest(),
    }


def compare_snapshots(etalon: Path, optim: Path) -> dict:
    a = json.loads(etalon.read_text(encoding="utf-8-sig"))
    b = json.loads(optim.read_text(encoding="utf-8-sig"))
    items_a = a.get("items") or []
    items_b = b.get("items") or []

    def by_key(items):
        m = {}
        dups = 0
        for it in items:
            k = it.get("Ключ") or it.get("key") or json.dumps(it, ensure_ascii=False, sort_keys=True)
            if k in m:
                dups += 1
            m[k] = it
        return m, dups

    ma, dupa = by_key(items_a)
    mb, dupb = by_key(items_b)
    only_a = sorted(set(ma) - set(mb))
    only_b = sorted(set(mb) - set(ma))
    common = set(ma) & set(mb)
    diffs = []
    for k in common:
        if ma[k] != mb[k]:
            diffs.append(k)
            if len(diffs) >= 20:
                break

    def type_counts(items):
        c = defaultdict(int)
        for it in items:
            t = it.get("Тип") or it.get("type") or it.get("Вид") or "?"
            if t == "?":
                for cand in ("ИмяДокумента", "Документ", "documentType"):
                    if cand in it:
                        t = str(it[cand])
                        break
            c[str(t)] += 1
        return dict(c)

    sample_keys = []
    if items_a:
        sample_keys = list(items_a[0].keys())[:20]

    return {
        "etalon": {
            "date": a.get("date"),
            "label": a.get("label"),
            "version": a.get("version"),
            "items": len(items_a),
            "types": type_counts(items_a),
            "dup_keys": dupa,
        },
        "optim": {
            "date": b.get("date"),
            "label": b.get("label"),
            "version": b.get("version"),
            "items": len(items_b),
            "types": type_counts(items_b),
            "dup_keys": dupb,
        },
        "only_etalon": len(only_a),
        "only_optim": len(only_b),
        "value_diffs": len(diffs),
        "identical_items": len(common) - len(diffs) if len(diffs) < 20 else None,
        "common": len(common),
        "sample_item_keys": sample_keys,
        "equal_whole": a == b,
        "only_etalon_sample": only_a[:8],
        "only_optim_sample": only_b[:8],
        "diff_sample": diffs[:8],
    }


def slim(info: dict) -> dict:
    d = dict(info)
    d.pop("records", None)
    d["top_pure"] = top_n(info["records"], "time_pure", 20)
    d["top_total"] = top_n(info["records"], "time_total", 15)
    d["interest"] = [r for r in info["records"] if is_interesting(r)]
    d["interest"].sort(key=lambda r: r["time_pure"], reverse=True)
    d["by_module"] = {
        k: v
        for k, v in sorted(
            info["by_module"].items(), key=lambda kv: kv[1]["time_pure"], reverse=True
        )
    }
    return d


def main() -> int:
    was = parse_pff(SRC / "1308_Было.pff")
    now = parse_pff(SRC / "1308_Стало.pff")
    shots = extract_docx_images(SRC / "ТестСкоростиРСА.docx", OUT / "shots")
    snap = compare_snapshots(
        SRC / "scha_rsa_20260813_etalon.json",
        SRC / "scha_rsa_20260813_optimiz.json",
    )
    payload = {
        "protocol": {
            "date": "13.08.2026",
            "contour": "RDU",
            "ib": was.get("ib") or now.get("ib"),
            "computer": was.get("computer"),
            "contracts": 21993,
            "mode": "posledovatelno, 0 potokov, bez fonovyh",
            "was_wall": {"min": 121, "sec": 38, "total_sec": 121 * 60 + 38},
            "now_wall": {"min": 68, "sec": 45, "total_sec": 68 * 60 + 45},
            "was_dbg_sec": 7174.843501,
            "now_dbg_sec": 4018.396230,
        },
        "was": slim(was),
        "now": slim(now),
        "modules": compare_modules(was, now)[:40],
        "lines_gain": compare_lines(was, now)[:40],
        "lines_loss": sorted(compare_lines(was, now), key=lambda x: x["delta_pure"])[:20],
        "shots": shots,
        "json_files": {
            "etalon": json_meta(SRC / "scha_rsa_20260813_etalon.json"),
            "optim": json_meta(SRC / "scha_rsa_20260813_optimiz.json"),
        },
        "snapshot": snap,
    }
    out_json = OUT / "analysis.json"
    # records already removed in slim
    out_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("OK rows was", was["parsed_rows"], "now", now["parsed_rows"])
    print("OK shots", len(shots))
    print("OK snapshot equal", snap["equal_whole"], "items", snap["etalon"]["items"], snap["optim"]["items"])
    print("OK wrote", out_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
