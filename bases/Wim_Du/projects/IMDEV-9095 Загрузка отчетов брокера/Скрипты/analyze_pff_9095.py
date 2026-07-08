#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse 1C PFF profiling file for IMDEV-9095 analysis."""

import json
import re
from collections import defaultdict
from pathlib import Path

PFF_PATH = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects"
    r"\IMDEV-9095 Загрузка отчетов брокера\Тестирование\Замеры_01_07_2026.pff"
)
OBJ_PATH = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects"
    r"\IMDEV-9095 Загрузка отчетов брокера\Обработки"
    r"\внРаспределениеДоходовПоЦеннымБумагам_epf"
    r"\внРаспределениеДоходовПоЦеннымБумагам\Ext\ObjectModule.bsl"
)
FORM_PATH = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects"
    r"\IMDEV-9095 Загрузка отчетов брокера\Обработки"
    r"\внРаспределениеДоходовПоЦеннымБумагам_epf"
    r"\внРаспределениеДоходовПоЦеннымБумагам\Forms\Форма\Ext\Form\Module.bsl"
)

RECORD_RE = re.compile(
    r'"},"(?P<module>[^"]+)",(?P<line>\d+),"(?P<code>.*?)",'
    r'(?P<hits>\d+),(?P<total>[\d.]+),(?P<pure>[\d.]+),'
    r'(?P<pct_total>[\d.]+),(?P<pct_pure>[\d.]+),'
)
SESSION_RE = re.compile(
    r'\{10,"(?P<host>[^"]+)","",(?P<port>\d+),"",(?P<unknown>\d+),'
    r'"(?P<user>[^"]+)",'
)


def load_line_map(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    proc_at = {}
    current = None
    for idx, text in enumerate(lines, start=1):
        m = re.match(r"(Процедура|Функция)\s+([^(]+)", text.strip())
        if m:
            current = m.group(2).strip()
            proc_at[idx] = current
        elif current:
            proc_at[idx] = current
    return lines, proc_at


def parse_sessions(text):
    sessions = []
    for m in SESSION_RE.finditer(text):
        sessions.append(
            {
                "host": m.group("host"),
                "user": m.group("user"),
                "offset": m.start(),
            }
        )
    return sessions


def parse_records(text, start=0, end=None):
    chunk = text[start:end] if end else text[start:]
    records = []
    for m in RECORD_RE.finditer(chunk):
        records.append(
            {
                "module": m.group("module"),
                "line": int(m.group("line")),
                "code": m.group("code"),
                "hits": int(m.group("hits")),
                "total": float(m.group("total")),
                "pure": float(m.group("pure")),
                "pct_total": float(m.group("pct_total")),
                "pct_pure": float(m.group("pct_pure")),
            }
        )
    return records


def is_epf_module(module):
    return "tempstorage" in module or "2e3de4d9" in module


def main():
    text = PFF_PATH.read_text(encoding="utf-8")
    obj_lines, obj_proc = load_line_map(OBJ_PATH)
    form_lines, form_proc = load_line_map(FORM_PATH)
    sessions = parse_sessions(text)

    out = {
        "file": str(PFF_PATH),
        "base": "AVC_REGR_CLEAN_DU",
        "sessions": [],
        "summary": {},
    }

    for i, sess in enumerate(sessions):
        start = sess["offset"]
        end = sessions[i + 1]["offset"] if i + 1 < len(sessions) else len(text)
        recs = parse_records(text, start, end)

        epf_recs = [r for r in recs if is_epf_module(r["module"])]
        config_recs = [r for r in recs if not is_epf_module(r["module"])]

        # Top-level EPF blocks (empty code, low line numbers often = procedures)
        epf_top = sorted(
            [r for r in epf_recs if r["code"] == "" and r["hits"] <= 2],
            key=lambda r: r["total"],
            reverse=True,
        )[:10]

        # EPF object module lines with code from line map
        epf_obj = []
        for r in epf_recs:
            if r["line"] in obj_proc:
                epf_obj.append({**r, "procedure": obj_proc[r["line"]]})
        epf_obj_by_proc = defaultdict(float)
        epf_obj_hits = defaultdict(int)
        for r in epf_obj:
            epf_obj_by_proc[r["procedure"]] += r["total"]
            epf_obj_hits[r["procedure"]] = max(epf_obj_hits[r["procedure"]], r["hits"])

        # Key external processor lines
        epf_key = sorted(epf_obj, key=lambda r: r["total"], reverse=True)[:25]

        # Config modules aggregate
        mod_agg = defaultdict(float)
        mod_hits = defaultdict(int)
        for r in config_recs:
            mod_agg[r["module"]] += r["total"]
            mod_hits[r["module"]] += r["hits"]
        top_modules = sorted(mod_agg.items(), key=lambda x: x[1], reverse=True)[:15]

        # Document posting stats
        doc_write = [
            r
            for r in config_recs
            if r["module"] == "Документ.ОперацияПоСчетуБрокера.МодульОбъекта"
            and "Записать" in r["code"]
        ]
        doc_count = max((r["hits"] for r in doc_write), default=0)

        obmen = sum(
            r["total"]
            for r in config_recs
            if r["module"] == "ОбщийМодуль.ОбменДаннымиСобытия.Модуль"
        )
        kurs = sum(
            r["total"]
            for r in config_recs
            if r["module"] == "ОбщийМодуль.МодульВалютногоУчета.Модуль"
        )
        buh = sum(
            r["total"]
            for r in config_recs
            if r["module"] == "ОбщийМодуль.БухгалтерскийУчет.Модуль"
        )
        aktiv = sum(
            r["total"]
            for r in config_recs
            if r["module"] == "ОбщийМодуль.АктивСервер.Модуль"
        )

        total_epf = sum(r["total"] for r in epf_recs)
        total_all = sum(r["total"] for r in recs)

        sess_data = {
            "index": i + 1,
            "host": sess["host"],
            "user": sess["user"],
            "records": len(recs),
            "total_sec": round(total_all, 3),
            "epf_sec": round(total_epf, 3),
            "epf_top_blocks": [
                {
                    "line": r["line"],
                    "total_sec": round(r["total"], 3),
                    "pct": round(r["pct_total"], 2),
                    "procedure": obj_proc.get(r["line"]) or form_proc.get(r["line"], "?"),
                }
                for r in epf_top
            ],
            "epf_by_procedure": {
                k: {
                    "total_sec": round(v, 3),
                    "hits": epf_obj_hits[k],
                }
                for k, v in sorted(epf_obj_by_proc.items(), key=lambda x: x[1], reverse=True)
            },
            "epf_hot_lines": [
                {
                    "line": r["line"],
                    "procedure": r["procedure"],
                    "code": obj_lines[r["line"] - 1].strip()[:120],
                    "hits": r["hits"],
                    "total_sec": round(r["total"], 3),
                    "pct": round(r["pct_total"], 3),
                }
                for r in epf_key
            ],
            "documents_posted_approx": doc_count,
            "config_hot_modules": [
                {"module": m, "total_sec": round(t, 3), "hits": mod_hits[m]}
                for m, t in top_modules
            ],
            "aggregates": {
                "obmen_dannymi_sec": round(obmen, 3),
                "kurs_valyut_sec": round(kurs, 3),
                "buh_uchet_sec": round(buh, 3),
                "aktiv_server_sec": round(aktiv, 3),
            },
        }
        out["sessions"].append(sess_data)

    # Global summary from session 2 (main create)
    if len(out["sessions"]) >= 2:
        s2 = out["sessions"][1]
        docs = s2["documents_posted_approx"]
        create_sec = s2["total_sec"]
        out["summary"] = {
            "fill_session_sec": out["sessions"][0]["total_sec"] if out["sessions"] else None,
            "create_session_sec": create_sec,
            "documents_posted": docs,
            "sec_per_document": round(create_sec / docs, 3) if docs else None,
            "epf_create_sec": s2["epf_sec"],
        }

    report_path = PFF_PATH.parent / "reports" / "zamery_01_07_2026_analysis.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # ASCII console output
    print("PFF analysis OK")
    print("sessions:", len(out["sessions"]))
    for s in out["sessions"]:
        print(f"\n=== Session {s['index']} ({s['host']}) total={s['total_sec']}s epf={s['epf_sec']}s ===")
        if s["epf_top_blocks"]:
            print("EPF top blocks:")
            for b in s["epf_top_blocks"][:5]:
                print(f"  line {b['line']} {b['procedure']}: {b['total_sec']}s ({b['pct']}%)")
        if s["epf_by_procedure"]:
            print("EPF by procedure:")
            for name, data in list(s["epf_by_procedure"].items())[:8]:
                print(f"  {name}: {data['total_sec']}s hits={data['hits']}")
        print(f"docs posted ~{s['documents_posted_approx']}")
        print("config modules top3:")
        for m in s["config_hot_modules"][:3]:
            print(f"  {m['module']}: {m['total_sec']}s")
        print("aggregates:", s["aggregates"])
    if out["summary"]:
        print("\nSUMMARY:", out["summary"])
    print("report:", report_path)


if __name__ == "__main__":
    main()
