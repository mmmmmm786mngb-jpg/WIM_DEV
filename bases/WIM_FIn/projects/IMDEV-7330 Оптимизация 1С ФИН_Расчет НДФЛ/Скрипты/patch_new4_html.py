#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Patch new4 HTML with 61-client classification."""

from decimal import Decimal
from html import escape
from pathlib import Path
import json

DOC = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\WIM_FIn\projects\IMDEV-7330 Оптимизация 1С ФИН_Расчет НДФЛ\Документация"
)


def fmt(v) -> str:
    d = Decimal(str(v))
    if d == d.to_integral():
        return f"{int(d):,}".replace(",", " ")
    return f"{d:,.2f}".replace(",", " ")


def main() -> None:
    probe = json.loads((DOC / "imdev7330_ndfl_new4_uk_diff_clients.json").read_text(encoding="utf-8"))
    html_path = DOC / "imdev7330_ndfl_old_vs_new4_diff.html"
    html = html_path.read_text(encoding="utf-8")
    kinds_ru = {
        "invest_vychet_like_platonov": "Как Платонов: доход тот же, вычет зеркально",
        "withhold_only": "Только удержание",
        "income_moved": "Сдвиг дохода / меньше Начисления",
        "other": "Смешанное",
    }
    rows = []
    for d in probe["docs"]:
        cl = ", ".join(d.get("clients") or ["?"])
        delta = d.get("delta_n4_vs_old") or {}
        cls = "bad" if d["kind"] == "income_moved" else "warn"
        rows.append(
            "<tr class='" + cls + "'><td>" + escape(kinds_ru[d["kind"]]) + "</td>"
            "<td class='sig'>" + escape(d["num"]) + "</td><td>" + escape(cl) + "</td>"
            "<td class='num'>" + str(d["old_rows"]) + "/" + str(d["n3_rows"]) + "/" + str(d["n4_rows"]) + "</td>"
            "<td class='num'>" + escape(fmt(delta.get("СуммаДохода", "0"))) + "</td>"
            "<td class='num'>" + escape(fmt(delta.get("СуммаВычета", "0"))) + "</td>"
            "<td class='num'>" + escape(fmt(delta.get("СуммаКУдержанию", "0"))) + "</td>"
            "<td>" + ("да" if d.get("n3_matched_old") else "нет") + "</td></tr>"
        )
    block = """
<div class="box info">
<b>Сверка с прогоном ПоНовому3</b>
В ПоНовому3 с эталоном по суммам УК расходился только Платонов (1 документ).
В ПоНовому4 расходятся 61 документ: Платонов плюс 60 клиентов, которые в ПоНовому3 совпадали с эталоном.
Портфели (включая Платонова) совпали с эталоном построчно.
</div>
<h2>Классификация 61 УК</h2>
<p>32 — тот же паттерн, что у Платонова (доход тот же, вычет зеркально).
19 — только удержание. 8 — сдвиг дохода, часть строк Начисления пропала. 2 — смешанные.</p>
<table>
<thead><tr><th>Тип</th><th>Номер УК</th><th>Клиент</th><th>Строк старый/n3/n4</th>
<th>Дельта дохода</th><th>Дельта вычета</th><th>Дельта к удержанию</th><th>n3=эталон</th></tr></thead>
<tbody>
""" + "".join(rows) + """
</tbody></table>
"""
    old = '<div class="box out"><b>Вывод</b>Есть расхождения. См. таблицы ниже.</div>'
    new = (
        '<div class="box out"><b>Вывод</b>'
        "Не всё совпало. Портфели — полное совпадение с эталоном 27292 (включая Платонова). "
        "УК Платонова: структура ТЧ как в эталоне (12 строк, 4 начисления), доход совпал; "
        "осталась дельта инвествычета +8 481 и к удержанию -1 272. "
        "Ещё 60 УК, которые в ПоНовому3 совпадали с эталоном, в ПоНовому4 разошлись. "
        "Самые тяжёлые — 8 клиентов со сдвигом дохода (у Бабарыкина П.Н. доход -836 млн)."
        "</div>" + block
    )
    if old not in html:
        raise SystemExit("verdict block not found")
    html_path.write_text(html.replace(old, new, 1), encoding="utf-8")
    print("HTML patched, rows=" + str(len(rows)))


if __name__ == "__main__":
    main()
