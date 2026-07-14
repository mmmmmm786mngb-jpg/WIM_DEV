#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build ms/PP breakdown from mass-mode PFF + report totals."""

import re
from pathlib import Path

PFF = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-9101 "
    r"Перевод ДС на биржу\Тестирование\Новый4_массовое_Замеры_0107_1307.pff"
)
N = 649
REPORT_CREATE_MS = 61431.0  # from Результаты_1407_массовое.txt
TARGET_MS_PP = REPORT_CREATE_MS / N  # ~94.7


def main() -> None:
    text = PFF.read_text(encoding="utf-8-sig")
    pat = re.compile(
        r'\},"([^"]+)",(\d+),"((?:\\.|[^"\\])*)",(\d+),([0-9.]+),([0-9.]+)',
        re.S,
    )
    rows = []
    for m in pat.finditer(text):
        rows.append({
            "mod": m.group(1),
            "line": int(m.group(2)),
            "code": m.group(3).replace("\n", " "),
            "n": int(m.group(4)),
            "t1": float(m.group(5)),
            "t2": float(m.group(6)),
        })

    def find(code_sub: str, mod_sub: str = "", line: int | None = None):
        for r in rows:
            if code_sub not in r["code"]:
                continue
            if mod_sub and mod_sub not in r["mod"]:
                continue
            if line is not None and r["line"] != line:
                continue
            return r
        return None

    create = find("СоздатьПлатежноеПоручение(")
    fill = find("Заполнить(ПоручениеПоДС)")
    write = find("Записать(РежимЗаписиДокумента.Проведение)")
    fill_base = find("ЗаполнитьПоДокументуОснованию")
    template = find("ПолучитьШаблонПоПараметрам")
    mass_st = find("IMDEV9101_СохранитьСтатусыПриМассовомСоздании")
    mass_wr = find("МенеджерЗаписи.Записать()", "IMDEV9101", 59)
    csv_reg = find("ЗарегистрироватьИзменение(Источник)")
    make_doc = find("СоздатьДокумент()")
    dogovor = find("ДоговорДУ = Основание.ДоговорДУ")
    exchange = find("НаборЗаписей.Записать()", "ОбменДаннымиСервер")

    create_s = create["t1"]
    scale = (REPORT_CREATE_MS / 1000.0) / create_s

    def ms(sec: float) -> float:
        return sec * scale * 1000.0 / N

    # Hierarchical exclusive-ish buckets for create
    fill_ms = ms(fill["t1"])
    write_ms = ms(write["t1"])
    other_ms = TARGET_MS_PP - fill_ms - write_ms

    # Nested under fill (informational; may overlap)
    fill_base_ms = ms(fill_base["t1"])
    template_ms = ms(template["t1"])
    dogovor_ms = ms(dogovor["t1"])

    # Nested under write
    write_self_ms = ms(write["t2"])  # platform/self
    mass_st_ms = ms(mass_st["t1"])
    # CSV n=1298 = create+delete; take half for create
    csv_create_ms = ms(csv_reg["t1"] * (649 / 1298))
    exchange_ms = ms(exchange["t1"]) if exchange else 0.0
    write_rest = write_ms - write_self_ms - mass_st_ms - csv_create_ms - exchange_ms

    print(f"TARGET_MS_PP={TARGET_MS_PP:.2f}")
    print(f"scale={scale:.4f} create_pff_s={create_s:.3f}")
    print("--- LEVEL1 ---")
    print(f"fill={fill_ms:.1f}")
    print(f"write={write_ms:.1f}")
    print(f"other={other_ms:.1f}")
    print("--- FILL DETAIL ---")
    print(f"fill_by_base={fill_base_ms:.1f}")
    print(f"template={template_ms:.1f}")
    print(f"dogovor_attr={dogovor_ms:.1f}")
    print("--- WRITE DETAIL ---")
    print(f"write_self={write_self_ms:.1f}")
    print(f"mass_status={mass_st_ms:.1f}")
    print(f"csv_half={csv_create_ms:.1f}")
    print(f"exchange={exchange_ms:.1f}")
    print(f"write_rest={write_rest:.1f}")
    print(f"mass_wr_leaf={ms(mass_wr['t1']):.1f}")
    print(f"make_doc={ms(make_doc['t1']):.1f}")


if __name__ == "__main__":
    main()
