# -*- coding: utf-8 -*-
"""Отчет о тестировании доработки "Заполнить и закрыть" (577-П) с диаграммами: Документация/p577_test_report.html.

python build_test_report.py
Цифры взяты из разборов замеров производительности (DR, UAT2) и сверок стенда; графики строятся встроенным SVG.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Документация", "p577_test_report.html")


def num(x, d=0):
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")


def hm(sec):
    m = round(sec / 60)
    return f"{m // 60} ч {m % 60:02d} мин" if m >= 60 else f"{m} мин"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------- данные ----------
MONTH = [  # вариант, [(этап, секунд, слот цвета)]
    ("По ссылке + перечитывание формы", [("Расчет", 6068.41, 1), ("Запись", 5269.73, 2),
                                                          ("Перечитывание формы", 12715.40, 7)]),
    ("«Заполнить и закрыть»", [("Расчет", 6762.95, 1), ("Запись", 5340.20, 2)], 12117.92),
]
DAY = [
    ("Типовая кнопка (без записи)", [("Расчет", 197, 1), ("Копирование в форму", 21, 6),
                                           ("Передача формы на клиент", 125, 7)]),
    ("«Заполнить и закрыть», прогон 1", [("Расчет", 154.96, 1), ("Запись", 57.48, 2)], 213.37),
    ("«Заполнить и закрыть», прогон 2", [("Расчет", 188.72, 1), ("Запись", 104.03, 2)], 293.65),
]
DONUT = [("Расчет: раздел 9", 2827.72, 1), ("Расчет: раздел 7", 1757.02, 3), ("Расчет: раздел 5", 1445.69, 4),
         ("Расчет: раздел 6", 572.41, 5), ("Расчет: прочие разделы", 6762.95 - 2827.72 - 1757.02 - 1445.69 - 572.41, 6),
         ("Запись документа", 5340.20, 2)]
ROWS = [("Раздел 7", 4149705), ("Раздел 9", 4068253), ("Раздел 6", 659789), ("Раздел 5", 458673),
        ("Раздел 4", 154832), ("Раздел 3", 139315), ("Раздел 8", 58966), ("Раздел 1", 23813), ("Раздел 11", 23813),
        ("Раздел 2", 677), ("Раздел 10", 569)]
PER_ROW = {  # мкс на перенос строки в раздел, по размеру документа (млн строк)
    "Раздел 7": [(0.54, 29.3), (6.74, 115.2), (9.74, 181.6)],
    "Раздел 9": [(0.54, 34.9), (6.74, 149.2), (9.74, 198.3)],
}
TESTS = [
    ("TC-01", "Новый документ: «Заполнить и закрыть»", "Стенд, 2000 строк на раздел",
     "Документ заполнен и записан, форма закрыта; шапка и 11 разделов совпадают с типовым заполнением",
     "Совпадение 11 из 11 разделов и шапки (контрольные суммы)", "pass"),
    ("TC-02", "Проведенный документ с измененной шапкой", "Стенд",
     "Изменение шапки сохранено, документ не перепроведен, разделы совпадают с эталоном",
     "Флаг сохранен, документ проведен, лишних вложений нет, разделы совпадают", "pass"),
    ("TC-03", "Отказ: неподходящий договор ДУ", "Стенд",
     "Документ не меняется, форма открыта, причина показана",
     "Сообщения о причине и «Документ не изменен», данные не изменились", "pass"),
    ("TC-04", "Проведение без файла xtdd", "Стенд",
     "Документ проведен, вложение не создается", "Вложений 0, проведение меньше 5 с (с выгрузкой было 32 с)", "pass"),
    ("TC-05", "Окно итога в интерфейсе 8.2 и «Такси»", "Стенд, DR",
     "Итог виден до нажатия ОК, затем форма закрывается", "Окно ждет ОК, форма закрывается", "pass"),
    ("TC-06", "Заполнение за 1 день, 01.06.2026", "DR-контур",
     "539 915 строк, время меньше типовой кнопки", "213 и 294 с с записью против 343 с без записи", "pass"),
    ("TC-07", "Заполнение за месяц, июнь 2026", "DR-контур",
     "9 738 405 строк, без перечитывания формы", "3 ч 22 мин против 6 ч 41 мин", "pass"),
    ("TC-08", "Заполнение за месяц на UAT2", "UAT2",
     "Ограничение памяти на вызов", "Падение по памяти на 2,28 млн строк (до доработки, расчет не менялся)", "limit"),
]
DEFECTS = [
    ("D-01", "Запись измененного проведенного документа из формы перепроводила его по старым строкам",
     "Форма перепроводит при записи и не учитывает режим «Запись»", "Шапка передается на сервер и записывается вместе с результатом", "1.0.0.1"),
    ("D-02", "Ошибка «Тип не определен» при заполнении измененного документа",
     "Таблица значений отборов передавалась на клиент", "Отборы передаются массивами значений", "1.0.0.1"),
    ("D-03", "После окна итога форма не закрывалась",
     "Неверное число параметров обработчика оповещения", "Исправлена сигнатура обработчика", "1.0.0.1"),
    ("D-04", "Итог заполнения не виден в интерфейсе версии 8.2",
     "В интерфейсе 8.2 нет центра оповещений, всплывающее окно исчезает", "Итог в окне, ожидающем ОК", "1.0.0.3"),
]


# ---------- SVG ----------
def stacked_bars(rows, width=860, unit=3600, unit_label="ч", step=1):
    rows = [(r[0], r[1], r[2] if len(r) > 2 else sum(v for _, v, _ in r[1])) for r in rows]
    total_max = max(tot for _, _, tot in rows)
    left, right, bar_h, gap, top = 250, 110, 26, 30, 28
    plot_w = width - left - right
    h = top + len(rows) * (bar_h + gap) + 30
    scale = plot_w / total_max
    out = [f'<svg viewBox="0 0 {width} {h}" class="chart" role="img">']
    ticks = int(total_max / unit / step) + 1
    for i in range(ticks + 1):
        x = left + i * step * unit * scale
        if x > left + plot_w + 1:
            break
        out.append(f'<line x1="{x:.1f}" y1="{top - 8}" x2="{x:.1f}" y2="{h - 26}" class="grid"/>')
        out.append(f'<text x="{x:.1f}" y="{h - 10}" class="tick" text-anchor="middle">{num(i * step)} {unit_label}</text>')
    for r, (label, segs, tot) in enumerate(rows):
        y = top + r * (bar_h + gap)
        out.append(f'<text x="{left - 12}" y="{y + bar_h / 2 + 5}" class="lbl" text-anchor="end">{esc(label)}</text>')
        x = left
        for name, v, slot in segs:
            w = v * scale
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{max(w - 2, 1):.1f}" height="{bar_h}" rx="3" class="s{slot}">'
                       f'<title>{esc(name)}: {hm(v) if unit == 3600 else num(v) + " с"}</title></rect>')
            if w > 60:
                txt = hm(v) if unit == 3600 else f"{num(v)} с"
                out.append(f'<text x="{x + w / 2:.1f}" y="{y + bar_h / 2 + 5}" class="inbar" text-anchor="middle">{txt}</text>')
            x += w
        out.append(f'<text x="{x + 8:.1f}" y="{y + bar_h / 2 + 5}" class="tot">{hm(tot) if unit == 3600 else num(tot) + " с"}</text>')
    out.append("</svg>")
    return "\n".join(out)


def legend(items):
    return '<div class="legend">' + "".join(
        f'<span><i class="sw s{slot}"></i>{esc(n)}</span>' for n, slot in items) + "</div>"


def donut(data, size=320):
    import math
    cx = cy = size / 2
    r_out, r_in = size / 2 - 10, size / 2 - 62
    total = sum(v for _, v, _ in data)
    out = [f'<svg viewBox="0 0 {size} {size}" class="donut" role="img">']
    a0 = -math.pi / 2
    for name, v, slot in data:
        a1 = a0 + 2 * math.pi * v / total
        large = 1 if a1 - a0 > math.pi else 0
        p = [(cx + r_out * math.cos(a0), cy + r_out * math.sin(a0)), (cx + r_out * math.cos(a1), cy + r_out * math.sin(a1)),
             (cx + r_in * math.cos(a1), cy + r_in * math.sin(a1)), (cx + r_in * math.cos(a0), cy + r_in * math.sin(a0))]
        d = (f"M{p[0][0]:.2f},{p[0][1]:.2f} A{r_out},{r_out} 0 {large} 1 {p[1][0]:.2f},{p[1][1]:.2f} "
             f"L{p[2][0]:.2f},{p[2][1]:.2f} A{r_in},{r_in} 0 {large} 0 {p[3][0]:.2f},{p[3][1]:.2f} Z")
        out.append(f'<path d="{d}" class="s{slot} seg"><title>{esc(name)}: {hm(v)}, {num(v / total * 100, 1)}%</title></path>')
        a0 = a1
    out.append(f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" class="big">{hm(total)}</text>')
    out.append(f'<text x="{cx}" y="{cy + 22}" text-anchor="middle" class="tick">июнь 2026, DR</text>')
    out.append("</svg>")
    rows = "".join(f'<tr><td><i class="sw s{slot}"></i>{esc(n)}</td><td class="n">{hm(v)}</td>'
                   f'<td class="n">{num(v / total * 100, 1)}%</td></tr>' for n, v, slot in data)
    return f'<div class="donutwrap">{"".join(out)}<table class="mini">{rows}</table></div>'


def hbars(rows, width=860, slot=1):
    left, right, bar_h, gap, top = 100, 120, 18, 10, 6
    mx = max(v for _, v in rows)
    plot_w = width - left - right
    h = top + len(rows) * (bar_h + gap) + 6
    out = [f'<svg viewBox="0 0 {width} {h}" class="chart" role="img">']
    for i, (label, v) in enumerate(rows):
        y = top + i * (bar_h + gap)
        w = max(v / mx * plot_w, 2)
        out.append(f'<text x="{left - 10}" y="{y + 14}" class="lbl" text-anchor="end">{esc(label)}</text>')
        out.append(f'<rect x="{left}" y="{y}" width="{w:.1f}" height="{bar_h}" rx="3" class="s{slot}"><title>{esc(label)}: {num(v)} строк</title></rect>')
        out.append(f'<text x="{left + w + 8:.1f}" y="{y + 14}" class="tot">{num(v)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def lines(series, width=860, height=300):
    left, right, top, bottom = 70, 150, 20, 46
    xmax, ymax = 10, 250
    pw, ph = width - left - right, height - top - bottom
    X = lambda x: left + x / xmax * pw
    Y = lambda y: top + ph - y / ymax * ph
    out = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img">']
    for yv in range(0, ymax + 1, 50):
        out.append(f'<line x1="{left}" y1="{Y(yv):.1f}" x2="{left + pw}" y2="{Y(yv):.1f}" class="grid"/>')
        out.append(f'<text x="{left - 8}" y="{Y(yv) + 4:.1f}" class="tick" text-anchor="end">{yv}</text>')
    for xv in range(0, xmax + 1, 2):
        out.append(f'<text x="{X(xv):.1f}" y="{height - 24}" class="tick" text-anchor="middle">{xv} млн</text>')
    out.append(f'<text x="{left + pw / 2}" y="{height - 4}" class="tick" text-anchor="middle">размер документа, строк</text>')
    out.append(f'<text x="14" y="{top + ph / 2}" class="tick" text-anchor="middle" transform="rotate(-90 14 {top + ph / 2})">мкс на строку</text>')
    for slot, (name, pts) in zip((3, 1), series.items()):
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(x):.1f},{Y(y):.1f}" for i, (x, y) in enumerate(pts))
        out.append(f'<path d="{d}" class="ln{slot}"/>')
        for x, y in pts:
            out.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="5" class="dot s{slot}"><title>{name}: {num(y, 0)} мкс при {num(x, 2)} млн строк</title></circle>')
        lx, ly = pts[-1]
        out.append(f'<text x="{X(lx) + 10:.1f}" y="{Y(ly) + 4:.1f}" class="lbl">{name}: {num(ly)} мкс</text>')
    out.append("</svg>")
    return "\n".join(out)


def tiles():
    t = [("3 ч 22 мин", "Заполнение месяца на DR", "было 6 ч 41 мин: в 2 раза быстрее"),
         ("213-294 с", "Один день на DR, с записью", "было 343 с без записи"),
         ("11 из 11", "Разделов совпадают с эталоном", "плюс шапка, контрольные суммы"),
         ("< 5 с", "Проведение без xtdd", "было 32 с, стенд, 22 тыс. строк"),
         ("7 из 7", "Тест-кейсов пройдено", "и 1 ограничение среды (UAT2)"),
         ("4 из 4", "Дефекта исправлено", "найдены в ходе тестирования")]
    return '<div class="tiles">' + "".join(
        f'<div class="tile"><div class="tv">{esc(a)}</div><div class="tl">{esc(b)}</div><div class="ts">{esc(c)}</div></div>'
        for a, b, c in t) + "</div>"


def tests_table():
    badge = {"pass": '<span class="b pass">✓ Пройден</span>', "limit": '<span class="b warn">! Ограничение</span>'}
    rows = "".join(f"<tr><td class='id'>{a}</td><td>{esc(b)}</td><td>{esc(c)}</td><td>{esc(d)}</td><td>{esc(e)}</td><td>{badge[f]}</td></tr>"
                   for a, b, c, d, e, f in TESTS)
    return ('<div class="tbl"><table><thead><tr><th>ID</th><th>Сценарий</th><th>Среда</th><th>Ожидаемый результат</th>'
            f'<th>Фактический результат</th><th>Статус</th></tr></thead><tbody>{rows}</tbody></table></div>')


def defects_table():
    rows = "".join(f"<tr><td class='id'>{a}</td><td>{esc(b)}</td><td>{esc(c)}</td><td>{esc(d)}</td><td class='n'>{e}</td>"
                   f"<td><span class='b pass'>✓ Исправлен</span></td></tr>" for a, b, c, d, e in DEFECTS)
    return ('<div class="tbl"><table><thead><tr><th>ID</th><th>Проявление</th><th>Причина</th><th>Исправление</th>'
            f'<th>Версия</th><th>Статус</th></tr></thead><tbody>{rows}</tbody></table></div>')


def integrity():
    cells = "".join(f'<div class="cell"><b>Раздел {i}</b><span>2 000 / 2 000</span><em>✓ совпадает</em></div>' for i in range(1, 12))
    return f'<div class="grid11">{cells}<div class="cell"><b>Шапка</b><span>28 реквизитов</span><em>✓ совпадает</em></div></div>'


def uat2_bar(width=860):
    left, top, bar_h = 200, 10, 28
    pw = width - left - 140
    rows = [("UAT2, момент падения", 2275386, 8), ("Нужно на месяц", 9738405, 1)]
    out = [f'<svg viewBox="0 0 {width} 110" class="chart" role="img">']
    for i, (n, v, slot) in enumerate(rows):
        y = top + i * 46
        w = v / 9738405 * pw
        out.append(f'<text x="{left - 10}" y="{y + 19}" class="lbl" text-anchor="end">{n}</text>')
        out.append(f'<rect x="{left}" y="{y}" width="{w:.1f}" height="{bar_h}" rx="3" class="s{slot}"><title>{n}: {num(v)} строк</title></rect>')
        out.append(f'<text x="{left + w + 8:.1f}" y="{y + 19}" class="tot">{num(v / 1e6, 2)} млн строк</text>')
    x = left + 2275386 / 9738405 * pw
    out.append(f'<line x1="{x:.1f}" y1="4" x2="{x:.1f}" y2="96" class="limit"/>')
    out.append(f'<text x="{x + 6:.1f}" y="104" class="tick">лимит памяти UAT2 на один вызов</text>')
    out.append("</svg>")
    return "\n".join(out)


CSS = """
:root{--bg:#f6f7f9;--card:#ffffff;--ink:#0b0b0b;--muted:#52514e;--line:#e2e4e8;--grid:#e9eaee;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;--s7:#4a3aa7;--s8:#e34948;
--good:#0f7b3f;--goodbg:#e4f5ea;--warn:#8a5a00;--warnbg:#fff3d6;--accent:#2a78d6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#131416;--card:#1a1a19;--ink:#ffffff;--muted:#c3c2b7;
--line:#2c2e33;--grid:#2a2c30;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#9085e9;
--s8:#e66767;--good:#7fd6a0;--goodbg:#173323;--warn:#f2c66d;--warnbg:#3a2f17;--accent:#3987e5}}
:root[data-theme="dark"]{--bg:#131416;--card:#1a1a19;--ink:#ffffff;--muted:#c3c2b7;--line:#2c2e33;--grid:#2a2c30;
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#9085e9;--s8:#e66767;
--good:#7fd6a0;--goodbg:#173323;--warn:#f2c66d;--warnbg:#3a2f17;--accent:#3987e5}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 "Segoe UI",Arial,sans-serif}
.page{max-width:1080px;margin:0 auto;padding:24px 16px 48px}
header{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px 24px;margin-bottom:16px;
border-top:6px solid var(--accent)}
h1{margin:0 0 6px;font-size:24px}h2{font-size:18px;margin:0 0 12px}.sub{color:var(--muted)}
.verdict{display:inline-block;margin-top:12px;padding:6px 14px;border-radius:999px;background:var(--goodbg);color:var(--good);font-weight:700}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px 18px;margin-top:14px;font-size:13px}
.meta b{display:block;color:var(--muted);font-weight:600;font-size:12px}
section{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px 22px;margin:14px 0}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}@media(max-width:700px){.tiles{grid-template-columns:1fr 1fr}}
.tile{border:1px solid var(--line);border-radius:12px;padding:12px 14px}.tv{font-size:24px;font-weight:700;color:var(--accent)}
.tl{font-size:13px;margin-top:2px}.ts{font-size:12px;color:var(--muted)}
.chart{width:100%;height:auto;display:block}.chart text{fill:var(--ink)}
.grid{stroke:var(--grid);stroke-width:1}.tick{font-size:12px;fill:var(--muted)!important}.lbl{font-size:13px}
.tot{font-size:13px;font-weight:600}.inbar{font-size:12px;fill:#fff!important;font-weight:600}
.limit{stroke:var(--s8);stroke-width:2;stroke-dasharray:5 4}
.s1{fill:var(--s1);background:var(--s1)}.s2{fill:var(--s2);background:var(--s2)}.s3{fill:var(--s3);background:var(--s3)}
.s4{fill:var(--s4);background:var(--s4)}.s5{fill:var(--s5);background:var(--s5)}.s6{fill:var(--s6);background:var(--s6)}
.s7{fill:var(--s7);background:var(--s7)}.s8{fill:var(--s8);background:var(--s8)}
.seg{stroke:var(--card);stroke-width:2}.ln1{fill:none;stroke:var(--s1);stroke-width:2}.ln3{fill:none;stroke:var(--s3);stroke-width:2}
.dot{stroke:var(--card);stroke-width:2}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:13px;margin:4px 0 10px}.sw{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.donutwrap{display:flex;flex-wrap:wrap;align-items:center;gap:18px}.donut{width:300px;max-width:100%}
.donut .big{font-size:26px;font-weight:700;fill:var(--ink)}.donut .tick{font-size:13px}
.mini{border-collapse:collapse;font-size:13px}.mini td{padding:4px 10px;border-bottom:1px solid var(--line)}
.n{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.tbl{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}.tbl table{min-width:820px}
th,td{border-bottom:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.02em}
.id{font-weight:700;white-space:nowrap}
.b{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:700;white-space:nowrap}
.pass{background:var(--goodbg);color:var(--good)}.warn{background:var(--warnbg);color:var(--warn)}
.grid11{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}
.cell{border:1px solid var(--line);border-left:4px solid var(--good);border-radius:10px;padding:8px 10px;font-size:13px}
.cell b,.cell span,.cell em{display:block}.cell span{color:var(--muted)}.cell em{color:var(--good);font-style:normal;font-weight:600}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}
.note{color:var(--muted);font-size:13px;margin:8px 0 0}
ul.clean{margin:6px 0 0;padding-left:18px}ul.clean li{margin:3px 0}
"""


def main():
    month_leg = legend([("Расчет", 1), ("Запись документа", 2), ("Перечитывание формы", 7)])
    day_leg = legend([("Расчет", 1), ("Запись документа", 2), ("Копирование в форму", 6), ("Передача формы на клиент", 7)])
    html = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>577-П: отчет о тестировании</title><style>{CSS}</style></head><body><div class="page">

<header>
<h1>Отчет о тестировании: кнопка «Заполнить и закрыть» для отчета 577-П</h1>
<div class="sub">Документ «(XBRL6.1) Отчет по внутреннему учету 577-П», доработка формы и проведения расширением конфигурации</div>
<div class="verdict">✓ Итог: доработка принята к опытной эксплуатации</div>
<div class="meta">
<div><b>Объект тестирования</b>Расширение «Заполнить и закрыть», версия 1.0.0.3</div>
<div><b>Конфигурация</b>Доверительное управление 1.5.30.3, платформа 8.3.27</div>
<div><b>Среды</b>стенд разработки, DR-контур, UAT2</div>
<div><b>Период тестирования</b>07.10.2026 - 09.10.2026</div>
<div><b>Данные</b>июнь 2026 (DR, UAT2), тестовые данные по 2 000 строк на раздел (стенд)</div>
<div><b>Структура отчета</b>по ISO/IEC/IEEE 29119-3, отчет о завершении тестирования</div>
</div>
</header>

<section><h2>1. Ключевые показатели</h2>{tiles()}</section>

<section><h2>2. Месяц на DR-контуре: из чего складывается время</h2>
{month_leg}{stacked_bars(MONTH)}
<p class="note">Июнь 2026, 9 738 405 строк, оборудование DR как на продуктиве. Перечитывание формы (3 ч 32 мин) убрано полностью,
запись и расчет остались. Разница в расчете (1 ч 41 мин и 1 ч 53 мин) задана нагрузкой на DR, код расчета не менялся.</p>
</section>

<section><h2>3. Один день, 01.06.2026</h2>
{day_leg}{stacked_bars(DAY, width=860, unit=1, unit_label="с", step=60)}
<p class="note">539 915 строк. У типовой кнопки запись выполняется отдельно и в 343 с не входит.</p>
</section>

<section><h2>4. Структура времени заполнения месяца с доработкой</h2>
{donut(DONUT)}
<p class="note">Расчет 56%, запись 44%. Работа формы больше не тратит времени. Дальнейшее ускорение возможно только
в расчете (код вендора) или в записи.</p>
</section>

<section><h2>5. Объем отчета за месяц по разделам</h2>
{hbars(ROWS)}
<p class="note">Разделы 7 и 9 заполняются за каждый календарный день и дают 84% строк.</p>
</section>

<section><h2>6. Стоимость строки растет с размером документа</h2>
{legend([("Раздел 9", 1), ("Раздел 7", 3)])}{lines(PER_ROW)}
<p class="note">Время переноса одной строки результата запроса в табличную часть: на документе в 9,7 млн строк в 5-6 раз
дороже, чем на документе за 1 день. Поэтому время месяца нельзя считать линейно по дням.</p>
</section>

<section><h2>7. Память: почему месяц не заполняется на UAT2</h2>
{uat2_bar()}
<p class="note">Весь расчет идет одним серверным вызовом. На UAT2 лимит памяти на вызов исчерпан на 2,28 млн строк
(9-й день раздела 7). На DR лимита нет, сеанс по счетчику консоли кластера занял 27 ГБ. Доработка этот лимит не снимает:
для проверки месяца на UAT2 нужно увеличить память сервера и параметры кластера.</p>
</section>

<section><h2>8. Тест-кейсы</h2>{tests_table()}</section>

<section><h2>9. Целостность данных (TC-01)</h2>
{integrity()}
<p class="note">Документ, заполненный кнопкой «Заполнить и закрыть», сравнен с эталоном типового заполнения на тех же данных:
по каждому разделу совпадают число строк и контрольная сумма всех значений, по шапке совпадают все реквизиты.</p>
</section>

<section><h2>10. Дефекты, найденные в ходе тестирования</h2>{defects_table()}</section>

<section><h2>11. Ограничения и рекомендации</h2>
<ul class="clean">
<li><b>Память.</b> Расчет месяца в одном вызове: на UAT2 нужно увеличить память и параметры кластера до уровня DR.
От Аванкора требуется заполнение разделов 5, 6, 7, 9 порциями с сохранением вне табличных частей документа.</li>
<li><b>Проведение.</b> Файл xtdd больше не формируется, но проведение остается записью всего документа: для месяца
около 1,5 часа. Если проведение не требуется, месячный документ достаточно заполнить.</li>
<li><b>Открытие заполненного месячного документа</b> по-прежнему загружает в форму все строки и занимает много времени.</li>
<li><b>Типовой релиз.</b> Изменения расширения нужно включить в типовую конфигурацию Аванкора, чтобы не поддерживать их отдельно.</li>
</ul>
</section>

</div></body></html>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(OUT)


if __name__ == "__main__":
    main()
