#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build self-contained HTML test report for IMDEV-8663.2 stage 3-4."""

from __future__ import annotations

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "Тестирование" / "reports" / "_stage34_analysis"
SHOTS = ANALYSIS / "shots"
OUT_TEST = ROOT / "Тестирование" / "reports" / "IMDEV-8663 Протокол тестирования пакетного расчета СЧА и РСА.html"
OUT_DOC = ROOT / "Документация" / "02_scha_rsa_group3" / "IMDEV-8663 Протокол тестирования пакетного расчета СЧА и РСА.html"


def b64_img(name: str) -> str:
    data = (SHOTS / name).read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def bar_h(items, max_val, colors, width=720, row_h=36):
    h = 16 + len(items) * row_h
    parts = [
        f'<svg viewBox="0 0 {width} {h}" width="100%" role="img">'
        f'<rect width="{width}" height="{h}" fill="#fff"/>'
    ]
    for i, (label, val, color) in enumerate(items):
        y = 8 + i * row_h
        bw = 0 if max_val <= 0 else max(2, int((width - 280) * val / max_val))
        parts.append(
            f'<text x="8" y="{y + 18}" font-size="13" font-family="Segoe UI, Arial" fill="#16324f">{esc(label)}</text>'
        )
        parts.append(
            f'<rect x="250" y="{y + 6}" width="{bw}" height="18" rx="3" fill="{color}"/>'
        )
        parts.append(
            f'<text x="{258 + bw}" y="{y + 19}" font-size="12" font-family="Consolas, monospace" fill="#333">{fmt_sec(val)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def grouped_bars(pairs, width=720, height=260):
    """pairs: [(label, was, now), ...]"""
    n = len(pairs)
    max_v = max(max(w, n_) for _, w, n_ in pairs) or 1
    left, right, top, bot = 210, 24, 28, 36
    inner_w = width - left - right
    inner_h = height - top - bot
    bw = max(10, inner_w // (n * 3))
    gap = inner_w / n
    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" role="img">',
        f'<rect width="{width}" height="{height}" fill="#fff"/>',
        f'<text x="{left}" y="18" font-size="12" fill="#6c757d" font-family="Segoe UI, Arial">секунды чистого времени</text>',
    ]
    for i, (label, was, now) in enumerate(pairs):
        x0 = left + i * gap + 8
        hw = was / max_v * inner_h
        hn = now / max_v * inner_h
        parts.append(
            f'<rect x="{x0:.1f}" y="{top + inner_h - hw:.1f}" width="{bw}" height="{hw:.1f}" fill="#dc3545"/>'
        )
        parts.append(
            f'<rect x="{x0 + bw + 6:.1f}" y="{top + inner_h - hn:.1f}" width="{bw}" height="{hn:.1f}" fill="#28a745"/>'
        )
        parts.append(
            f'<text x="{x0 + bw:.1f}" y="{height - 10}" text-anchor="middle" font-size="11" font-family="Segoe UI, Arial" fill="#16324f">{esc(label)}</text>'
        )
    parts.append(
        f'<rect x="{width - 170}" y="8" width="12" height="12" fill="#dc3545"/>'
        f'<text x="{width - 154}" y="18" font-size="12" font-family="Segoe UI, Arial">было</text>'
        f'<rect x="{width - 90}" y="8" width="12" height="12" fill="#28a745"/>'
        f'<text x="{width - 74}" y="18" font-size="12" font-family="Segoe UI, Arial">стало</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def donut(slices, size=280, title="стало", subtitle="доля блоков"):
    cx = cy = size / 2
    r = size * 0.34
    r2 = size * 0.48
    total = sum(v for _, v, _ in slices) or 1
    acc = 0.0
    parts = [f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" role="img">']
    for label, val, color in slices:
        a0 = acc / total * 360
        acc += val
        a1 = acc / total * 360
        parts.append(arc(cx, cy, r, r2, a0, a1, color))
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r * 0.72}" fill="#fff"/>')
    parts.append(
        f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" font-size="15" font-family="Segoe UI, Arial" fill="#16324f" font-weight="700">{esc(title)}</text>'
        f'<text x="{cx}" y="{cy + 16}" text-anchor="middle" font-size="12" font-family="Segoe UI, Arial" fill="#6c757d">{esc(subtitle)}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def polar(cx, cy, r, ang):
    import math

    a = math.radians(ang - 90)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def arc(cx, cy, r_in, r_out, a0, a1, color):
    import math

    large = 1 if (a1 - a0) > 180 else 0
    x0, y0 = polar(cx, cy, r_out, a0)
    x1, y1 = polar(cx, cy, r_out, a1)
    x2, y2 = polar(cx, cy, r_in, a1)
    x3, y3 = polar(cx, cy, r_in, a0)
    d = (
        f"M {x0:.2f} {y0:.2f} A {r_out:.2f} {r_out:.2f} 0 {large} 1 {x1:.2f} {y1:.2f} "
        f"L {x2:.2f} {y2:.2f} A {r_in:.2f} {r_in:.2f} 0 {large} 0 {x3:.2f} {y3:.2f} Z"
    )
    return f'<path d="{d}" fill="{color}"/>'


def esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def fmt_sec(v: float) -> str:
    if v >= 60:
        m = int(v // 60)
        s = v - m * 60
        return f"{m} мин {s:.1f} с"
    return f"{v:.1f} с"


def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def fmt_pct(part: float, whole: float, digits: int = 1) -> str:
    return f"{100.0 * part / whole:.{digits}f}".replace(".", ",")


def mmss(total: int) -> str:
    return f"{total // 60} мин {total % 60:02d} с"


def build(data: dict) -> str:
    p = data["protocol"]
    was_w, now_w = p["was_wall"]["total_sec"], p["now_wall"]["total_sec"]
    saved_w = was_w - now_w
    ratio_w = was_w / now_w
    was_d, now_d = p["was_dbg_sec"], p["now_dbg_sec"]
    saved_d = was_d - now_d
    ratio_d = was_d / now_d
    per_was = was_w / p["contracts"]
    per_now = now_w / p["contracts"]

    img1 = b64_img("shot_01.png")
    img2 = b64_img("shot_02.png")
    img3 = b64_img("shot_03.png")
    img4 = b64_img("shot_04.png")
    img5 = b64_img("shot_05.png")
    img6 = b64_img("shot_06.png")

    # APDEX register (screenshot 6): same weight 21994, sequential 1 thread
    was_reg, now_reg = 7297.979, 4125.199
    saved_reg = was_reg - now_reg
    ratio_reg = was_reg / now_reg

    chart_wall = grouped_bars(
        [
            ("Форма (стена)", was_w, now_w),
            ("РС Замеры времени", was_reg, now_reg),
            ("Отладчик 100%", was_d, now_d),
        ],
        width=720,
        height=260,
    )
    chart_queries = grouped_bars(
        [
            ("Запрос БУ", 1424.94, 8.83),
            ("Запрос УУ", 1225.99, 34.64),
            ("Параметры ДУ", 175.48, 68.73),
            ("Проведение док.", 602.22, 550.23),
            ("Контроль портфеля", 422.82, 413.65),
        ],
        width=740,
        height=260,
    )
    chart_modules = bar_h(
        [
            ("РасчетСЧА_РСА, менеджер", 2728.7, "#28a745"),
            ("ОбщегоНазначения", 126.9, "#17a2b8"),
            ("ЗначенияПараметровДоговораДУ", 110.7, "#17a2b8"),
            ("РасчетСЧА_РСА, объект", 84.5, "#20c997"),
            ("РегламентныеПериоды", 69.5, "#6c757d"),
            ("МодульВалютногоУчета", 50.8, "#fd7e14"),
        ],
        2728.7,
        [],
        width=760,
    )
    now_total = 4018.4
    slice_post = 550.2
    slice_write = 427.0
    slice_portf = 413.7
    slice_plan = 402.1
    slice_other = now_total - slice_post - slice_write - slice_portf - slice_plan
    donut_svg = donut(
        [
            ("Проведение документов", slice_post, "#fd7e14"),
            ("Запись РасчетСЧА_РСА", slice_write, "#ffc107"),
            ("Контроль портфеля", slice_portf, "#17a2b8"),
            ("План регл. операций", slice_plan, "#6f42c1"),
            ("Прочее", slice_other, "#adb5bd"),
        ],
        title="стало",
        subtitle="доля блоков",
    )
    # Расшифровка «Прочее» по чистому времени модулей замера «стало»
    # (уже без четырех строк топа: проведение, запись документа, контроль, запись плана).
    o_plan_q = 417.04 + 228.07 + 155.54
    o_regs = 450.41 + 94.46
    o_csv = 233.78
    o_exch = 159.84 + 9.44
    o_close = 130.43 + 12.79 + 4.89
    o_params = 71.37
    o_packet = 62.31
    o_rest = slice_other - (o_plan_q + o_regs + o_csv + o_exch + o_close + o_params + o_packet)
    donut_other = donut(
        [
            ("Запросы плана и периодов", o_plan_q, "#5c6bc0"),
            ("Запись регистров СЧА/РСА", o_regs, "#26a69a"),
            ("Выгрузка CSV", o_csv, "#ec407a"),
            ("Обмен данными", o_exch, "#7e57c2"),
            ("Диспетчер закрытия периода", o_close, "#29b6f6"),
            ("Параметры договора ДУ", o_params, "#66bb6a"),
            ("Пакет БУ/УУ расширения", o_packet, "#ffa726"),
            ("Прогресс, префиксы и прочее", o_rest, "#90a4ae"),
        ],
        size=300,
        title="прочее",
        subtitle=f"{slice_other:,.0f} с = 100%".replace(",", " "),
    )

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>IMDEV-8663.2 — протокол скорости и регресса СЧА/РСА (этапы 3–4)</title>
<style>
body {{ font-family: "Segoe UI", Tahoma, Arial, sans-serif; font-size: 15px; line-height: 1.55;
       color: #212529; background: #f5f6f8; margin: 0; padding: 0; }}
.wrap {{ max-width: 1180px; margin: 0 auto; background: #fff; padding: 32px 44px 60px;
         box-shadow: 0 0 18px rgba(0,0,0,.08); }}
h1 {{ font-size: 26px; color: #16324f; border-bottom: 4px solid #17a2b8; padding-bottom: 12px; margin-top: 0; }}
h2 {{ font-size: 21px; color: #16324f; margin-top: 38px; border-left: 6px solid #17a2b8;
     padding-left: 12px; background: #f0f8fa; padding-top: 6px; padding-bottom: 6px; }}
h3 {{ font-size: 17px; color: #1b4b72; margin-top: 26px; border-bottom: 1px dashed #b7d4e0; padding-bottom: 4px; }}
code {{ font-family: Consolas, "Courier New", monospace; background: #eef2f5; padding: 1px 5px;
       border-radius: 3px; font-size: 13.5px; color: #b8003a; }}
pre {{ background: #f4f6f8; border: 1px solid #d8dee4; padding: 12px 14px; overflow-x: auto;
      font-size: 13px; line-height: 1.45; }}
table {{ border-collapse: collapse; width: 100%; margin: 14px 0 22px 0; font-size: 14px; }}
th {{ background: #16324f; color: #fff; text-align: left; padding: 9px 10px; font-weight: 600; }}
td {{ border: 1px solid #d8dee4; padding: 8px 10px; vertical-align: top; }}
tr:nth-child(even) td {{ background: #fafbfc; }}
td.num {{ text-align: right; white-space: nowrap; font-family: Consolas, monospace; }}
.box {{ padding: 14px 18px; border-radius: 6px; margin: 16px 0; }}
.warn {{ background: #fff8e1; border-left: 6px solid #ffc107; }}
.info {{ background: #e8f4fd; border-left: 6px solid #17a2b8; }}
.ok   {{ background: #eaf7ee; border-left: 6px solid #28a745; }}
.tag {{ display: inline-block; font-size: 12px; padding: 2px 8px; border-radius: 10px;
       color: #fff; font-weight: 600; margin-right: 6px; }}
.t-ok {{ background: #28a745; }}
.t-info {{ background: #17a2b8; }}
.t-warn {{ background: #fd7e14; }}
.small {{ font-size: 13px; color: #6c757d; }}
.shot {{ max-width: 100%; border: 1px solid #d8dee4; border-radius: 6px; margin: 8px 0 8px; }}
.caption {{ font-size: 13px; color: #6c757d; margin: 0 0 18px; }}
.stat {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 16px 0 22px; }}
.stat .card {{ background: #f8fafb; border: 1px solid #d8dee4; border-radius: 8px; padding: 14px 16px; }}
.stat .n {{ font-size: 26px; font-weight: 700; color: #16324f; }}
.stat .l {{ font-size: 13px; color: #6c757d; }}
.charts {{ display: grid; grid-template-columns: 1.4fr 0.9fr; gap: 18px; align-items: center; }}
.legend {{ font-size: 13px; }}
.legend span {{ display: inline-block; width: 12px; height: 12px; margin-right: 6px; vertical-align: middle; }}
@media (max-width: 900px) {{ .stat, .charts {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="wrap">

<h1>Протокол тестирования IMDEV-8663.2<br>
<span style="font-size:19px;font-weight:400;color:#495057;">Пакетный расчет СЧА/РСА: скорость и регресс на РДУ, {fmt_int(p["contracts"])} договоров</span></h1>

<p class="small">
Источник протокола: <code>ТестСкоростиРСА.docx</code>
&nbsp;|&nbsp; Замеры: <code>1308_Было.pff</code>, <code>1308_Стало.pff</code>
&nbsp;|&nbsp; Снимки: <code>scha_rsa_20260813_etalon.json</code>, <code>scha_rsa_20260813_optimiz.json</code>
&nbsp;|&nbsp; Доработка: расширение IM86632, этапы 3–4
</p>

<div class="box ok">
<b>Итог.</b> На контуре РДУ за дату <b>13.08.2026</b> группа <code>3. Расчет СЧА/РСА</code>
по {fmt_int(p["contracts"])} договорам в последовательном режиме (0 потоков) ускорилась
с <b>{mmss(was_w)}</b> до <b>{mmss(now_w)}</b> — в {ratio_w:.2f} раза, экономия
<b>{mmss(saved_w)}</b>. Регистр «Замеры времени» на тех же прогонах (вес 21 994):
<b>7 297,979 с → 4 125,199 с</b>. Регресс документов: <b>{fmt_int(p["contracts"])} = {fmt_int(p["contracts"])}, расхождений 0</b>.
Главный выигрыш — запросы БУ и УУ документа <code>РасчетСЧА_РСА</code>: вместо
{fmt_int(21993)} вызовов на договор осталось по 8 пакетных запросов на пачку.
</div>

<!-- ================================================================ -->
<h2>1. Введение</h2>

<p>Проверка выполнена на рабочей тестовой базе РДУ. Сценарий из протокола:</p>
<ol>
<li>Запуск группы <b>3. Расчет СЧА/РСА</b> <b>без</b> расширения, константа потоков = 0
    (последовательный режим, без фоновых). Дата периода 13.08.2026, отбор физлиц РДУ,
    {fmt_int(p["contracts"])} договоров. Зафиксированы время формы и замер отладчика.</li>
<li>Созданные документы удалены.</li>
<li>Включено расширение IM86632, константа пакетного расчета
    <code>ИспользоватьПредварительныеЗапросыДляРегламентовСЧА_РСА</code> = Истина,
    потоков по-прежнему 0.</li>
<li>Повторный запуск той же группы, тот же отбор. Снова время формы и замер отладчика.</li>
<li>Регрессионная сверка снимков документов операций СЧА/РСА за день
    (обработка <code>СверкаДокументовОперацийСЧА_РСА</code>).</li>
</ol>

<p>Потоки нарочно обнулены: сравнивается именно пакетный расчет СЧА/РСА, а не диспетчер фоновых
из IMDEV-8663.1. Операции 1010/1020/1030 в этом прогоне не пакетятся — менялся только расчет 1000.
Протокол отдельно фиксирует: оба сравниваемых замера в регистре — <b>последовательный режим, 1 поток</b>.</p>

<img class="shot" src="{img1}" alt="Старт расчета без расширения, группа 3, 21993 договора">
<p class="caption">Прогон «было»: форма периода 13.08.2026, группа «3. Расчет СЧА/РСА»,
обработка договора 25 из {fmt_int(p["contracts"])}. База <code>AVC_UAT_RDU_PERFTEST</code>.</p>

<!-- ================================================================ -->
<h2>2. Технология измерений</h2>

<div class="box info">
Это не COM/Python-прогон, а нативный замер платформы 1С и сверка прикладных документов.
Ниже — как именно получены цифры, чтобы их можно было повторить.
</div>

<h3>2.1 Длительная операция и «стеночное» время</h3>
<p>Расчет запускается с формы справочника регламентных периодов командой создания операций.
Платформа показывает прогресс («Обработка договора N из {fmt_int(p["contracts"])}»).
Время «затрачено» в протоколе — это длительность всей длительной операции на форме,
включая запись документов, контроль портфеля и служебные вызовы.</p>
<table>
<tr><th>Параметр</th><th>Значение</th></tr>
<tr><td>Информационная база</td><td><code>AVC_UAT_RDU_PERFTEST</code></td></tr>
<tr><td>Контур</td><td>РДУ, пользователь Admin</td></tr>
<tr><td>Рабочая станция замера</td><td><code>SMSK02MG138</code></td></tr>
<tr><td>Дата периода</td><td>13.08.2026</td></tr>
<tr><td>Группа</td><td>3. Расчет СЧА/РСА (контроль портфеля + расчет РСА + расчет СЧА)</td></tr>
<tr><td>Договоров</td><td>{fmt_int(p["contracts"])}</td></tr>
<tr><td>Режим</td><td>последовательно, константа потоков = 0, без фоновых</td></tr>
<tr><td>Расширение «было»</td><td>выключено</td></tr>
<tr><td>Расширение «стало»</td><td>IM86632, пакетная константа = Истина</td></tr>
</table>

<h3>2.2 Замер производительности (файлы PFF)</h3>
<p>Отладчик платформы пишет замер фонового задания длительной операции в файл <code>.pff</code>.
Каждая строка — модуль, номер строки, исходный текст, число вызовов, чистое время и доля.
Чистое время не включает вложенные вызовы; полное — включает. Сумма чистого времени по всем
строкам совпадает с корневым <code>ВыполнитьМетодКонфигурации</code> (~100%).</p>
<table>
<tr><th>Файл</th><th>Строк замера</th><th>Корень (полное), с</th><th>Сумма чистого, с</th></tr>
<tr><td><code>1308_Было.pff</code></td><td class="num">1 498</td><td class="num">7 174,84</td><td class="num">7 170,67</td></tr>
<tr><td><code>1308_Стало.pff</code></td><td class="num">1 600</td><td class="num">4 018,40</td><td class="num">~4 018</td></tr>
</table>
<p class="small">В «стало» строк больше: появились вызовы расширения IM86632 (пакетные методы).
Корневая строка отладчика в протоколе Word:</p>
<pre>ОбщийМодуль.ДлительныеОперации.Модуль    650    ВыполнитьМетодКонфигурации(...)
было: 1 вызов, 7 174,843501 с, 100,00%
стало: 1 вызов, 4 018,396230 с, 100,00%</pre>

<h3>2.3 Регистр сведений «Замеры времени»</h3>
<p>Штатный регистр производительности платформы (ключевые операции).
В протоколе отбор: дата записи локальная ≥ 09.09.2026 0:00:00,
ключевая операция <code>Д.у. регламентные операции. 3. расчет сча/рса</code>.
Сравниваются две строки с одинаковым весом замера <b>21 994</b>
(тот же объём, что полный отбор РДУ: 21 993 договора) и одним номером сеанса.</p>
<table>
<tr><th>Источник</th><th class="num">Было, с</th><th class="num">Стало, с</th></tr>
<tr><td>Сообщение формы «Затрачено»</td><td class="num">7 298 (121 мин 38 с)</td><td class="num">4 125 (68 мин 45 с)</td></tr>
<tr><td>РС «Замеры времени», выделенные строки</td><td class="num">7 297,979</td><td class="num">4 125,199</td></tr>
<tr><td>Отладчик, <code>ВыполнитьМетодКонфигурации</code></td><td class="num">7 174,844</td><td class="num">4 018,396</td></tr>
</table>
<p>Форма и регистр совпадают. Это третье независимое подтверждение ускорения,
без ручного секундомера и без разбора PFF.</p>

<h3>2.4 Регресс документов</h3>
<p>Обработка <code>СверкаДокументовОперацийСЧА_РСА</code> собирает снимок шапок и табличных частей
документов операций СЧА/РСА за день <b>без номеров документов и номеров строк</b>, затем сравнивает
два JSON. Ключ элемента: <code>docType + contractUid + header + tables</code>.</p>
<table>
<tr><th>Снимок</th><th>Метка</th><th>Документов</th><th>SHA-256 (файл целиком)</th></tr>
<tr><td><code>scha_rsa_20260813_etalon.json</code></td><td>etalon</td><td class="num">{fmt_int(p["contracts"])}</td>
    <td><code>e1605a0f…4045169a</code></td></tr>
<tr><td><code>scha_rsa_20260813_optimiz.json</code></td><td>optimiz</td><td class="num">{fmt_int(p["contracts"])}</td>
    <td><code>c642eb7a…c85ec</code></td></tr>
</table>
<p>Хеши файлов различаются из-за поля <code>label</code> (etalon / optimiz). По содержимому
документов: общих ключей {fmt_int(p["contracts"])}, уникальных слева 0, справа 0,
расхождений значений <b>0</b>. Целые JSON не равны только меткой снимка.</p>

<!-- ================================================================ -->
<h2>3. Статистика</h2>

<div class="stat">
    <div class="card"><div class="n">{ratio_w:.2f}x</div><div class="l">ускорение по форме</div></div>
    <div class="card"><div class="n">{mmss(saved_w)}</div><div class="l">экономия на прогоне</div></div>
    <div class="card"><div class="n">7,4x</div><div class="l">менеджер РасчетСЧА_РСА (чистое)</div></div>
    <div class="card"><div class="n">0</div><div class="l">расхождений регресса</div></div>
</div>

<table>
<tr><th>Метрика</th><th class="num">Было</th><th class="num">Стало</th><th class="num">Дельта</th></tr>
<tr><td>Время на форме</td><td class="num">{mmss(was_w)}</td><td class="num">{mmss(now_w)}</td>
    <td class="num">−{mmss(saved_w)}</td></tr>
<tr><td>РС «Замеры времени», ключевая операция группы 3</td>
    <td class="num">{was_reg:,.3f} с</td><td class="num">{now_reg:,.3f} с</td>
    <td class="num">−{saved_reg:,.3f} с ({ratio_reg:.2f}x)</td></tr>
<tr><td>Отладчик, корень 100%</td><td class="num">{was_d:,.2f} с</td><td class="num">{now_d:,.2f} с</td>
    <td class="num">−{saved_d:,.2f} с ({ratio_d:.2f}x)</td></tr>
<tr><td>На один договор (стена)</td><td class="num">{per_was:.3f} с</td><td class="num">{per_now:.3f} с</td>
    <td class="num">−{per_was - per_now:.3f} с</td></tr>
<tr><td>Вызовы запроса БУ РасчетСЧА_РСА</td><td class="num">{fmt_int(21993)}</td><td class="num">8</td>
    <td class="num">в {21993/8:.0f} раз меньше</td></tr>
<tr><td>Вызовы запроса УУ РасчетСЧА_РСА</td><td class="num">{fmt_int(21993)}</td><td class="num">8</td>
    <td class="num">в {21993/8:.0f} раз меньше</td></tr>
<tr><td>Чистое время запросов БУ+УУ</td><td class="num">2 650,9 с</td><td class="num">43,5 с</td>
    <td class="num">−2 607 с (61x)</td></tr>
<tr><td>Документов в сверке</td><td class="num">{fmt_int(p["contracts"])}</td>
    <td class="num">{fmt_int(p["contracts"])}</td><td class="num">совпало</td></tr>
</table>

{chart_wall}
<p class="caption">Три независимых источника на одном прогоне: сообщение формы, регистр сведений
«Замеры времени» и корневая строка отладчика. Форма и регистр совпадают до секунды
(7 298 с и 4 125 с). Отладчик короче на ~2 минуты — без оболочки длительной операции.</p>

<!-- ================================================================ -->
<h2>4. Детали прогонов</h2>

<h3>4.1 Прогон «было» — без расширения</h3>
<p>Протокол: «Обработано договоров: {fmt_int(p["contracts"])}. Режим: последовательно, без фоновых.
Затрачено: 121 мин 38 сек». Корень отладчика 7 174,84 с.</p>

<img class="shot" src="{img2}" alt="Отладчик было: запросы БУ и УУ по 21993 раза">
<p class="caption">Отладчик «было». Две верхние строки — однодоговорные
<code>Запрос.Выполнить()</code> БУ (стр. 218, 1 424,94 с) и
<code>ЗапросУУ.Выполнить()</code> (стр. 507, 1 225,99 с). Каждый по {fmt_int(21993)} раз.
Вместе ~37% всего прогона.</p>

<h3>4.2 Включение пакетного режима</h3>
<p>Протокол: удаление созданных документов — ок; активация расширения — ок;
константа пакетных запросов СЧА/РСА = Истина — ок; повторный запуск, 0 потоков — ок.</p>

<img class="shot" src="{img3}" alt="Форма периода, группа 3 после включения расширения">
<p class="caption">Тот же период и группа 3 перед прогоном «стало». В дереве отмечены
контроль уменьшения стоимости портфеля, расчет РСА и расчет СЧА.</p>

<h3>4.3 Прогон «стало» — IM86632, пакет включен</h3>
<p>Протокол: «Обработано договоров: {fmt_int(p["contracts"])}. Режим: последовательно, без фоновых.
Затрачено: 68 мин 45 сек». Корень отладчика 4 018,40 с.</p>

<img class="shot" src="{img4}" alt="Отладчик стало: пакетные запросы 8 раз, проведение документов в топе">
<p class="caption">Отладчик «стало». Однодоговорных запросов БУ/УУ в топе нет.
Пакетный УУ расширения: <code>IM86632 Документ.РасчетСЧА_РСА.МодульМенеджера</code>
стр. 1679, <b>8 вызовов</b>, 34,64 с. Пакетный БУ стр. 1634 — 8 вызовов, 8,83 с.
Первые места заняли запись/проведение документов и контроль портфеля — их эта доработка не меняла.</p>

<h3>4.4 Регистр «Замеры времени» — независимое подтверждение</h3>
<p>Протокол: «Результаты замеров в РС Замеры времени (в последовательном режиме 1 поток)».
На скрине отбор по ключевой операции группы 3 за 09.09.2026. Оранжевая рамка — прогон без расширения,
зелёная — с IM86632 и пакетной константой. Вес замера на обеих строках одинаковый.</p>

<img class="shot" src="{img6}" alt="Регистр Замеры времени: 7297.979 с против 4125.199 с при весе 21994">
<p class="caption">Список регистра «Замеры времени», ключевая операция
<code>Д.у. регламентные операции. 3. расчет сча/рса</code>, пользователь Admin.
Оранжевая рамка: 7 297,979 с при весе 21 994. Зелёная: 4 125,199 с при том же весе.</p>

<table>
<tr>
    <th>Строка на скрине</th>
    <th>Начало часа (сервер)</th>
    <th class="num">Время, с</th>
    <th class="num">Вес</th>
    <th>Комментарий</th>
</tr>
<tr>
    <td>04:00</td>
    <td>09.09.2026 4:00:00</td>
    <td class="num">601,610</td>
    <td class="num">3 087</td>
    <td>Другой объём, не сравнивается с полным РДУ</td>
</tr>
<tr>
    <td>07:00</td>
    <td>09.09.2026 7:00:00</td>
    <td class="num">606,440</td>
    <td class="num">3 087</td>
    <td>Тот же меньший объём</td>
</tr>
<tr>
    <td>09:00</td>
    <td>09.09.2026 9:00:00</td>
    <td class="num">1 430,879</td>
    <td class="num">3 087</td>
    <td>Тот же меньший объём, дольше (другой контекст прогона)</td>
</tr>
<tr>
    <td>09:00, короткий</td>
    <td>09.09.2026 9:00:00</td>
    <td class="num">3,214</td>
    <td class="num">4</td>
    <td>Служебный/короткий замер, не полный расчет</td>
</tr>
<tr style="background:#fff3e0;">
    <td><b>Было</b> (оранжевая рамка, сеанс 3)</td>
    <td>09.09.2026 11:00:00<br>локально ~14:55:52</td>
    <td class="num"><b>7 297,979</b></td>
    <td class="num"><b>21 994</b></td>
    <td>Полный отбор РДУ без расширения. Совпадает с формой 121 мин 38 с</td>
</tr>
<tr style="background:#eaf7ee;">
    <td><b>Стало</b> (зелёная рамка, сеанс 3)</td>
    <td>09.09.2026 13:00:00<br>локально ~16:15:37</td>
    <td class="num"><b>4 125,199</b></td>
    <td class="num"><b>21 994</b></td>
    <td>Тот же вес, пакет включен. Совпадает с формой 68 мин 45 с</td>
</tr>
</table>

<div class="box ok">
<b>Вывод по регистру.</b> При одинаковом весе 21 994 и последовательном режиме
группа 3 ускорилась с 7 297,979 с до 4 125,199 с — в {ratio_reg:.2f} раза,
экономия {saved_reg:,.0f} с ({mmss(int(round(saved_reg)))}).
Это тот же прогон, что на форме и в PFF, только измеренный штатной ключевой операцией.
Строки с весом 3 087 — прогоны меньшего объёма в тот же день, в сравнение «было/стало»
полного РДУ они не входят.
</div>

<h3>4.5 Какие блоки ускорены</h3>

<p>Чистое время модуля менеджера <code>Документ.РасчетСЧА_РСА</code>:
<b>3 156 с → 427 с (в 7,4 раза)</b>. Число вызовов строк модуля: 3 367 488 → 153 951.</p>

{chart_queries}
<p class="caption">Чистое время ключевых строк: запросы расчета уехали в пакет (8 сигнатур),
запись документов и контроль портфеля почти те же.</p>

<h4>Прямое следствие пакетной трубы</h4>
<table>
<tr>
    <th>Блок</th>
    <th>Что было</th>
    <th>Что стало</th>
    <th class="num">Экономия чистого</th>
</tr>
<tr>
    <td>Запрос остатков БУ <code>ПолучитьСуммыРСА_СЧА</code> стр. 218</td>
    <td>{fmt_int(21993)} × 1 424,94 с</td>
    <td>8 × <code>ДобавитьДанныеБУПоГруппе</code> / <code>Выгрузить()</code> 8,83 с</td>
    <td class="num">~1 416 с</td>
</tr>
<tr>
    <td>Запрос УУ <code>ПолучитьСуммыРСА_СЧА</code> стр. 507</td>
    <td>{fmt_int(21993)} × 1 225,99 с</td>
    <td>8 × <code>ДобавитьДанныеУУПоГруппе</code> 34,64 с</td>
    <td class="num">~1 191 с</td>
</tr>
<tr>
    <td>Вызов <code>ПолучитьСуммыРСА_СЧА</code> из модуля объекта</td>
    <td>{fmt_int(21993)} раз (однодоговорной путь)</td>
    <td>0: в <code>#Вставка</code> подставляются готовые ТЗ из пакета</td>
    <td class="num">вложенные запросы сняты</td>
</tr>
<tr>
    <td><code>ЗначенияПараметровДоговораДУ</code></td>
    <td>43 986 выборок, 175,48 с</td>
    <td>21 993 выборки + пакетный срез, 68,73 с</td>
    <td class="num">~107 с</td>
</tr>
<tr>
    <td><code>МодульВалютногоУчета</code> (площадка/курсы на договор)</td>
    <td>{fmt_int(21993)} вызовов, 49,3 с</td>
    <td>0 в замере расчета (в пакете не повторяется)</td>
    <td class="num">~49 с</td>
</tr>
<tr>
    <td><code>ОбщегоНазначения</code> (выборки вокруг однодоговорного пути)</td>
    <td>116,8 с на одной строке запроса</td>
    <td>строка исчезла из замера</td>
    <td class="num">~117 с</td>
</tr>
</table>

<p>8 пакетных вызовов — это 8 групп договоров с одинаковой сигнатурой параметров
(наборы счетов БУ / признаки УУ). Методика запроса та же, меняются только отбор
<code>ДоговорДУ В (&amp;ДоговорыГруппы)</code> и группировка.</p>

<h4>Экономия по модулям (чистое время)</h4>
{chart_modules}
<p class="caption">Сколько секунд чистое время модуля стало меньше. Почти весь выигрыш —
менеджер документа расчета. Остальные модули сдвинулись как побочный эффект:
меньше однодоговорных обращений к параметрам, валюте и общим функциям.</p>

<h4>Что не ускорялось и теперь занимает долю «стало»</h4>
<div class="charts">
<div>{donut_svg}</div>
<div class="legend">
<p>После оптимизации топ «стало» — это запись, а не расчет показателей:</p>
<ul>
<li><span style="background:#fd7e14"></span> Проведение подчиненных документов — {fmt_sec(slice_post)} ({fmt_pct(slice_post, now_total)}%)</li>
<li><span style="background:#ffc107"></span> Запись <code>РасчетСЧА_РСА</code> — {fmt_sec(slice_write)} ({fmt_pct(slice_write, now_total)}%)</li>
<li><span style="background:#17a2b8"></span> Запрос контроля уменьшения стоимости портфеля — {fmt_sec(slice_portf)} ({fmt_pct(slice_portf, now_total)}%)</li>
<li><span style="background:#6f42c1"></span> Запись набора плана регл. операций — {fmt_sec(slice_plan)} ({fmt_pct(slice_plan, now_total)}%)</li>
<li><span style="background:#adb5bd"></span> Прочее — {fmt_sec(slice_other)} ({fmt_pct(slice_other, now_total)}%), расшифровка ниже</li>
</ul>
<p>Четыре верхних блока одинаковы по числу вызовов ({fmt_int(21993)} или 20 525). Их эта доработка
не трогает. «Прочее» — это не один кусок, а сумма служебных запросов, записи регистров, CSV и обмена.</p>
</div>
</div>

<h4>Расшифровка блока «Прочее»</h4>
<p>100% на диаграмме — чистое время «Прочего» ({fmt_sec(slice_other)}). В скобках — доля от всего прогона «стало».</p>
<div class="charts">
<div>{donut_other}</div>
<div class="legend">
<ul>
<li><span style="background:#5c6bc0"></span> Запросы плана регл. операций и регламентных периодов —
    {fmt_sec(o_plan_q)} ({fmt_pct(o_plan_q, slice_other)}% прочего, {fmt_pct(o_plan_q, now_total)}% всего)</li>
<li><span style="background:#26a69a"></span> Запись регистров СЧА/РСА после документа —
    {fmt_sec(o_regs)} ({fmt_pct(o_regs, slice_other)}% / {fmt_pct(o_regs, now_total)}%)</li>
<li><span style="background:#ec407a"></span> Выгрузка CSV во внешнюю систему —
    {fmt_sec(o_csv)} ({fmt_pct(o_csv, slice_other)}% / {fmt_pct(o_csv, now_total)}%)</li>
<li><span style="background:#7e57c2"></span> Обмен данными —
    {fmt_sec(o_exch)} ({fmt_pct(o_exch, slice_other)}% / {fmt_pct(o_exch, now_total)}%)</li>
<li><span style="background:#29b6f6"></span> Диспетчер исполняемых процедур закрытия —
    {fmt_sec(o_close)} ({fmt_pct(o_close, slice_other)}% / {fmt_pct(o_close, now_total)}%)</li>
<li><span style="background:#66bb6a"></span> Срез параметров договора ДУ —
    {fmt_sec(o_params)} ({fmt_pct(o_params, slice_other)}% / {fmt_pct(o_params, now_total)}%)</li>
<li><span style="background:#ffa726"></span> Пакетные запросы БУ/УУ расширения IM86632 —
    {fmt_sec(o_packet)} ({fmt_pct(o_packet, slice_other)}% / {fmt_pct(o_packet, now_total)}%)</li>
<li><span style="background:#90a4ae"></span> Прогресс, префиксы номеров и мелочь —
    {fmt_sec(o_rest)} ({fmt_pct(o_rest, slice_other)}% / {fmt_pct(o_rest, now_total)}%)</li>
</ul>
</div>
</div>
<table>
<tr>
    <th>Подблок «Прочего»</th>
    <th>Что это в замере</th>
    <th class="num">Чистое, с</th>
    <th class="num">% прочего</th>
    <th class="num">% всего «стало»</th>
</tr>
<tr>
    <td>Запросы плана и периодов</td>
    <td>Выполнить() в менеджере плана, регламентных периодах и оставшихся строках объекта плана</td>
    <td class="num">{o_plan_q:,.0f}</td>
    <td class="num">{fmt_pct(o_plan_q, slice_other)}</td>
    <td class="num">{fmt_pct(o_plan_q, now_total)}</td>
</tr>
<tr>
    <td>Запись регистров СЧА/РСА</td>
    <td>Модуль объекта расчета: наборы записей, <code>РегистрРСА_СЧА</code> — не путать с <code>ДокументОбъект.Записать</code> на диаграмме выше</td>
    <td class="num">{o_regs:,.0f}</td>
    <td class="num">{fmt_pct(o_regs, slice_other)}</td>
    <td class="num">{fmt_pct(o_regs, now_total)}</td>
</tr>
<tr>
    <td>Выгрузка CSV</td>
    <td><code>ОбработкаСобытийВыгрузкаCSVВоВнешнюСистему</code>, запись во внешнюю систему на каждый документ</td>
    <td class="num">{o_csv:,.0f}</td>
    <td class="num">{fmt_pct(o_csv, slice_other)}</td>
    <td class="num">{fmt_pct(o_csv, now_total)}</td>
</tr>
<tr>
    <td>Обмен данными</td>
    <td><code>ОбменДаннымиСервер</code> и регистр результатов обмена</td>
    <td class="num">{o_exch:,.0f}</td>
    <td class="num">{fmt_pct(o_exch, slice_other)}</td>
    <td class="num">{fmt_pct(o_exch, now_total)}</td>
</tr>
<tr>
    <td>Диспетчер закрытия периода</td>
    <td><code>ИсполняемыеПроцедурыЗакрытияПериода</code>, виды операций, перехват расширения</td>
    <td class="num">{o_close:,.0f}</td>
    <td class="num">{fmt_pct(o_close, slice_other)}</td>
    <td class="num">{fmt_pct(o_close, now_total)}</td>
</tr>
<tr>
    <td>Параметры договора ДУ</td>
    <td>Срез <code>ЗначенияПараметровДоговораДУ</code> (уже быстрее, чем «было», но ещё в цикле)</td>
    <td class="num">{o_params:,.0f}</td>
    <td class="num">{fmt_pct(o_params, slice_other)}</td>
    <td class="num">{fmt_pct(o_params, now_total)}</td>
</tr>
<tr>
    <td>Пакет БУ/УУ расширения</td>
    <td>Сами пакетные запросы IM86632 — теперь малая доля</td>
    <td class="num">{o_packet:,.0f}</td>
    <td class="num">{fmt_pct(o_packet, slice_other)}</td>
    <td class="num">{fmt_pct(o_packet, now_total)}</td>
</tr>
<tr>
    <td>Прогресс, префиксы и прочее</td>
    <td>Сообщения «обработка договора N из M», префиксация номеров, длительные операции, даты запрета</td>
    <td class="num">{o_rest:,.0f}</td>
    <td class="num">{fmt_pct(o_rest, slice_other)}</td>
    <td class="num">{fmt_pct(o_rest, now_total)}</td>
</tr>
<tr>
    <td><b>Итого прочее</b></td>
    <td></td>
    <td class="num"><b>{slice_other:,.0f}</b></td>
    <td class="num"><b>100,0</b></td>
    <td class="num"><b>{fmt_pct(slice_other, now_total)}</b></td>
</tr>
</table>
<p class="caption">Дальнейший выигрыш группы 3 — не пакет СЧА/РСА (он уже 62 с), а запись документов,
регистров, запросы плана/периодов, контроль портфеля и выгрузка CSV.</p>

<!-- ================================================================ -->
<h2>5. Регресс</h2>

<img class="shot" src="{img5}" alt="Сверка документов: 21993 = 21993, расхождений 0">
<p class="caption">Обработка сверки: день 13.08.2026, эталон против optimiz,
{fmt_int(p["contracts"])} документов, расхождений 0, таблица расхождений пустая.
Потоки пометки планов = 12 относятся только к служебной пометке, не к самому расчету.</p>

<table>
<tr><th>Проверка</th><th>Результат</th></tr>
<tr><td>Количество документов в снимках</td>
    <td><span class="tag t-ok">OK</span> {fmt_int(p["contracts"])} = {fmt_int(p["contracts"])}</td></tr>
<tr><td>Ключи, только в эталоне / только после</td>
    <td><span class="tag t-ok">OK</span> 0 / 0</td></tr>
<tr><td>Расхождения шапок и ТЧ</td>
    <td><span class="tag t-ok">OK</span> 0</td></tr>
<tr><td>Дата снимка</td>
    <td><span class="tag t-info">20260813</span> совпадает</td></tr>
</table>

<div class="box ok">
Методика расчета не изменилась: пакетный запрос — тот же текст, что однодоговорной,
плюс колонка договора и отбор по списку. Сверка это подтверждает на полном отборе РДУ.
</div>

<!-- ================================================================ -->
<h2>6. Что умеет эта проверка</h2>
<ul>
<li>Отделить выигрыш пакетного СЧА/РСА от фоновых потоков (константа потоков = 0).</li>
<li>Показать, <b>какие строки кода</b> перестали вызываться {fmt_int(21993)} раз.</li>
<li>Увидеть, что 8 сигнатур покрывают весь отбор (8 пакетных БУ и 8 пакетных УУ).</li>
<li>Подтвердить отсутствие прикладного регресса на полном снимке дня.</li>
<li>Зафиксировать новый потолок: запись документов и контроль портфеля.</li>
<li>Подтвердить ускорение третьим источником — регистром сведений «Замеры времени» при том же весе.</li>
</ul>

<!-- ================================================================ -->
<h2>7. Выводы</h2>

<div class="box ok">
<ol>
<li><b>Ускорено.</b> Группа 3 на {fmt_int(p["contracts"])} договорах РДУ:
    {mmss(was_w)} → {mmss(now_w)}, в {ratio_w:.2f} раза.
    Регистр «Замеры времени»: 7 297,979 с → 4 125,199 с (вес 21 994, 1 поток).
    Отладчик: 7 175 с → 4 018 с.</li>
<li><b>Где выигрыш.</b> Блок расчета показателей документа <code>РасчетСЧА_РСА</code>:
    однодоговорные запросы БУ (стр. 218) и УУ (стр. 507) больше не выполняются в цикле.
    Их заменили пакетные <code>ДобавитьДанныеБУПоГруппе</code> / <code>ДобавитьДанныеУУПоГруппе</code>
    (по 8 вызовов). Чистое время менеджера документа: 3 156 с → 427 с.</li>
<li><b>Побочно быстрее.</b> Срез параметров договора, курсы/площадка, однодоговорные
    обёртки объекта — меньше вызовов, минус ещё ~300 с чистого.</li>
<li><b>Не ускорялось.</b> Проведение и запись документов, контроль уменьшения стоимости
    портфеля, запись плана регл. операций. После оптимизации они дают ~45% оставшегося времени.</li>
<li><b>Регресс.</b> Снимки документов за 13.08.2026 совпали полностью, расхождений нет.</li>
</ol>
</div>

<p class="small">Отчет собран по Word-протоколу (6 скриншотов встроены в файл, включая РС «Замеры времени»),
двум PFF-замерам платформы и двум JSON-снимкам сверки. Картинки не вынесены отдельными файлами.</p>

</div>
</body>
</html>
"""


def main() -> int:
    data = json.loads((ANALYSIS / "analysis.json").read_text(encoding="utf-8"))
    html = build(data)
    for path in (OUT_TEST, OUT_DOC):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        print("OK", path, "bytes", path.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
