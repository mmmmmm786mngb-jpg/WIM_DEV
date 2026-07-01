#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract images and context from profiling DOCX."""

import base64
import re
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DOCX = PROJECT / "ЗадачаМоФО_Реально_По45пакетов.docx"
DOC = PROJECT / "Документация"
OUT_HTML = DOC / "mo_fo_profiling_45_packets_report.html"


def extract_docx_content(docx_path: Path):
    with zipfile.ZipFile(docx_path, "r") as archive:
        document = archive.read("word/document.xml").decode("utf-8")
        rels = archive.read("word/_rels/document.xml.rels").decode("utf-8")

        rid_map = {}
        for match in re.finditer(
            r'Id="(rId\d+)"[^>]*Target="media/(image\d+\.png)"', rels
        ):
            rid_map[match.group(1)] = match.group(2)

        images_b64 = {}
        for name in archive.namelist():
            if name.startswith("word/media/") and name.endswith(".png"):
                data = archive.read(name)
                fname = Path(name).name
                images_b64[fname] = base64.b64encode(data).decode("ascii")

    parts = re.split(r"(<w:drawing[^>]*>.*?</w:drawing>)", document, flags=re.DOTALL)
    text_buf = ""
    ordered_images = []

    for part in parts:
        if part.startswith("<w:drawing"):
            embed = re.search(r'r:embed="(rId\d+)"', part)
            if embed:
                fname = rid_map.get(embed.group(1), "")
                plain = re.sub(r"<[^>]+>", " ", text_buf)
                plain = re.sub(r"\s+", " ", plain).strip()
                ordered_images.append(
                    {
                        "file": fname,
                        "context": plain[-400:] if plain else "",
                    }
                )
        else:
            text_buf += part

    plain_all = re.sub(r"</w:p>", "\n", document)
    plain_all = re.sub(r"<[^>]+>", "", plain_all)
    lines = [line.strip() for line in plain_all.split("\n") if line.strip()]

    return ordered_images, images_b64, lines


COMMON_CSS = """
        :root {
            --ok: #28a745;
            --err: #dc3545;
            --info: #17a2b8;
            --warn-bg: #fff3cd;
            --warn-border: #ffc107;
            --blue-bg: #e7f3ff;
            --blue-border: #17a2b8;
            --text: #212529;
            --muted: #6c757d;
            --border: #dee2e6;
        }
        * { box-sizing: border-box; }
        body {
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.55;
            color: var(--text);
            max-width: 1100px;
            margin: 0 auto;
            padding: 24px 20px 48px;
            background: #f8f9fa;
        }
        h1 { font-size: 1.65rem; margin-bottom: 0.35rem; }
        h2 {
            font-size: 1.25rem;
            margin-top: 2rem;
            padding-bottom: 0.35rem;
            border-bottom: 2px solid var(--info);
        }
        h3 { font-size: 1.05rem; margin-top: 1.25rem; color: #343a40; }
        .meta { color: var(--muted); font-size: 0.95rem; margin-bottom: 1.5rem; }
        .lead {
            background: #fff;
            border-left: 4px solid var(--info);
            padding: 1rem 1.25rem;
            margin: 1.25rem 0;
            border-radius: 0 6px 6px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }
        .box-info {
            background: var(--blue-bg);
            border: 1px solid var(--blue-border);
            padding: 0.85rem 1rem;
            border-radius: 6px;
            margin: 1rem 0;
        }
        .box-warn {
            background: var(--warn-bg);
            border: 1px solid var(--warn-border);
            padding: 0.85rem 1rem;
            border-radius: 6px;
            margin: 1rem 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: #fff;
            margin: 1rem 0;
            font-size: 0.92rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }
        th, td {
            border: 1px solid var(--border);
            padding: 0.55rem 0.75rem;
            text-align: left;
            vertical-align: top;
        }
        th { background: #e9ecef; font-weight: 600; }
        tr:nth-child(even) { background: #f8f9fa; }
        .num { text-align: right; font-variant-numeric: tabular-nums; }
        .err { color: var(--err); font-weight: 600; }
        code {
            background: #e9ecef;
            padding: 0.1rem 0.35rem;
            border-radius: 3px;
            font-size: 0.88em;
        }
        .screenshot {
            background: #fff;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            margin: 1.5rem 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }
        .screenshot img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 0 auto;
            border: 1px solid #ced4da;
        }
        .screenshot-caption {
            font-size: 0.9rem;
            color: var(--muted);
            margin-top: 0.75rem;
            padding-top: 0.5rem;
            border-top: 1px solid var(--border);
        }
        .screenshot-caption strong { color: var(--text); }
        .context {
            font-size: 0.85rem;
            color: #495057;
            margin-bottom: 0.75rem;
            font-style: italic;
        }
        .nav { margin: 1rem 0; font-size: 0.95rem; }
        .nav a { color: var(--info); }
        ol.steps { padding-left: 1.25rem; }
        ol.steps li { margin: 0.35rem 0; }
"""

# Captions matched to actual DOCX screenshots (profiler 1C)
DEFAULT_CAPTIONS = [
    {
        "title": "Форма обработки перед замером",
        "desc": (
            "Внешняя обработка «Выгрузка остатков МО ФО» v.1.35: "
            "адрес WS <code>http://smsk02mg138u/AVC_PP_RETAIL_FO/ws/avancore_ws.1cws?wsdl</code>, "
            "<code>Количество портфелей в пакете = 45</code>, дата позиции 01.07.2026. "
            "Вкладка «Ценные бумаги» — табличная часть перед заполнением/публикацией."
        ),
    },
    {
        "title": "ЗАПОЛНИТЬ — профилировщик, общий вид",
        "desc": (
            "Окно «Замер производительности» после нажатия <strong>Заполнить</strong>. "
            "Корневой вызов <code>ЗаполнитьНаСервере()</code> — ~41,6 с (93,9%). "
            "Основное время: <code>ОбработкаОбъект.Заполнить</code>, запросы "
            "<code>СЧА_РСА_НаДату</code>, <code>ЦенныеБумагиНаДату</code>, <code>ДенежныеСредстваНаДату</code>."
        ),
    },
    {
        "title": "ЗАПОЛНИТЬ — сортировка по чистому времени",
        "desc": (
            "Тот же замер <strong>Заполнить</strong>, колонка «Врем. чистое». "
            "Топ: <code>Запрос.Выполнить().Выгрузить()</code> (~9,5 с), "
            "<code>ЗаполнитьНаСервере</code> (~9,4 с), запросы по ЦБ и ДС. "
            "В отчете по публикации этот этап не входит в 4 ч 49 мин."
        ),
    },
    {
        "title": "ОПУБЛИКОВАТЬ — профилировщик, общий вид",
        "desc": (
            "Замер после <strong>Опубликовать</strong> (режим «Общее»). "
            "Корень: <code>Опубликовать</code> — <strong>117 356,8 с</strong> (99,84%). "
            "Внутри видны три WS-вызова: строки <strong>872</strong> (10 349 с, 59,5%), "
            "<strong>754</strong> (3 586 с, 20,6%), <strong>768</strong> (2 365 с, 13,6%). "
            "По 470 вызовов каждого — по одному на пакет из 45 мандатов."
        ),
    },
    {
        "title": "ОПУБЛИКОВАТЬ — сортировка по чистому времени",
        "desc": (
            "Детальный вид замера <strong>Опубликовать</strong> (колонка «Врем. чистое»). "
            "Подтверждает ранжирование: 872 &gt; 754 &gt; 768. "
            "Также видны <code>ВыполнитьПерерасчетРСА</code> (строка 1526, ~467 с) "
            "и высокочастотные проверки в цикле (строка 683, 21 115 раз)."
        ),
    },
]


def img_block(b64: str, caption: dict, context: str, index: int) -> str:
    return f"""
    <div class="screenshot" id="screenshot-{index}">
        <h3>{caption["title"]}</h3>
        <img src="data:image/png;base64,{b64}" alt="{caption['title']}" />
        <p class="screenshot-caption"><strong>Пояснение:</strong> {caption["desc"]}</p>
    </div>
    """


def build_html(ordered_images, images_b64, doc_lines):
    blocks = []
    for i, item in enumerate(ordered_images):
        fname = item["file"]
        b64 = images_b64.get(fname, "")
        cap = DEFAULT_CAPTIONS[i] if i < len(DEFAULT_CAPTIONS) else {
            "title": f"Скриншот {i + 1} из DOCX ({fname})",
            "desc": "Скриншот из документа замеров.",
        }
        blocks.append(img_block(b64, cap, item.get("context", ""), i + 1))

    doc_text_preview = ""
    for line in doc_lines[:25]:
        safe = line.replace("&", "&amp;").replace("<", "&lt;")
        doc_text_preview += f"<li>{safe}</li>\n"

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Замеры обмена МО-ФО: пакеты по 45 мандатов</title>
    <style>{COMMON_CSS}</style>
</head>
<body>
    <h1>Замеры обмена МО &rarr; ФО (PP Retail)</h1>
    <p class="meta">
        Проект IMDEV-8829 внВыгрузкаОстатковМО_ФО &bull;
        Источник: <code>ЗадачаМоФО_Реально_По45пакетов.docx</code> (скриншоты профилировщика 1С) &bull;
        Дата отчета: 30.06.2026
    </p>

    <div class="lead">
        Отчет воспроизводит <strong>исходные скриншоты</strong> из документа замеров:
        как запускалась обработка, что было заполнено и что показал профилировщик 1С
        при <code>КоличествоПортфелейВПакете = 45</code>.
    </div>

    <p class="nav">
        Детальные цепочки МО &rarr; ФО: <a href="mo_fo_ws_754_768_872_processing.html">mo_fo_ws_754_768_872_processing.html</a>
        &bull; <a href="mo_fo_ws_calls_optimization.html">оптимизация</a>
    </p>

    <h2>1. Как проводился замер</h2>
    <ol class="steps">
        <li>База MO PP Retail (PROD_AVC_Retail_MO), внешняя обработка <code>внВыгрузкаОстатковМО_ФО</code> v.1.35.</li>
        <li>На форме: <code>Количество портфелей в пакете = 45</code>, дата позиции 01.07.2026.</li>
        <li>Включен <strong>Замер производительности</strong> (меню конфигуратора / отладка).</li>
        <li>Нажата кнопка <strong>Заполнить</strong> — скриншоты 2–3 в DOCX (~42 с, запросы к БД МО).</li>
        <li>Нажата кнопка <strong>Опубликовать</strong> — скриншоты 4–5 (~4 ч 49 мин, WS на ФО).</li>
    </ol>

    <div class="box-info">
        <strong>Итог публикации (скриншот 4):</strong>
        <code>Опубликовать</code> = <strong>~17 357 с</strong> (~4 ч 49 мин, 99,84% замера).
        Пакетов: <strong>470</strong>, по <strong>4</strong> вызова <code>DownloadPosition</code> на пакет.
    </div>

    <h2>2. Что заполнилось (текст из DOCX)</h2>
    <table>
        <tr><th>Табличная часть</th><th class="num">Строк</th></tr>
        <tr><td>СЧА (РСА)</td><td class="num">21 191</td></tr>
        <tr><td>Денежные средства</td><td class="num">21 117</td></tr>
        <tr><td>Ценные бумаги</td><td class="num">62 936</td></tr>
        <tr><td>Остальные ТЧ</td><td>пустые</td></tr>
    </table>

    <h2>3. Скриншоты из документа замеров</h2>
    <p>PNG-изображения извлечены из <code>ЗадачаМоФО_Реально_По45пакетов.docx</code> и встроены в HTML (base64).</p>

    <h3>3.1. Форма обработки</h3>
    {blocks[0]}

    <h3>3.2. ЗАПОЛНИТЬ — замер производительности</h3>
    {blocks[1]}
    {blocks[2]}

    <h3>3.3. ОПУБЛИКОВАТЬ — замер производительности</h3>
    <div class="box-warn">
        Основной отчет по узким местам обмена — раздел ниже и скриншоты 4–5.
        Именно здесь видны строки <strong>754</strong>, <strong>768</strong>, <strong>872</strong>.
    </div>
    {blocks[3]}
    {blocks[4]}

    <h2>4. Расшифровка цифр со скриншотов «Опубликовать»</h2>
    <table>
        <tr>
            <th>Строка МО</th>
            <th>Операция</th>
            <th class="num">Вызовов</th>
            <th class="num">Суммарно, с</th>
            <th class="num">%</th>
            <th class="num">Среднее, с</th>
        </tr>
        <tr>
            <td>872</td>
            <td><code>DownloadPosition(ПакетХДТОФлагПозиции)</code></td>
            <td class="num">470</td>
            <td class="num err">10 349</td>
            <td class="num">59,5%</td>
            <td class="num">~22,0</td>
        </tr>
        <tr>
            <td>754</td>
            <td><code>DownloadPosition(ПакетХДТОФлагПозицииНеВыгружена)</code></td>
            <td class="num">470</td>
            <td class="num">3 586</td>
            <td class="num">20,6%</td>
            <td class="num">~7,6</td>
        </tr>
        <tr>
            <td>768</td>
            <td><code>DownloadPosition(ПакетХДТО)</code> - позиция</td>
            <td class="num">470</td>
            <td class="num">2 365</td>
            <td class="num">13,6%</td>
            <td class="num">~5,0</td>
        </tr>
        <tr>
            <td>1526</td>
            <td><code>ВыполнитьПерерасчетРСА</code> &rarr; DownloadPosition</td>
            <td class="num">470</td>
            <td class="num">467</td>
            <td class="num">2,7%</td>
            <td class="num">~1,0</td>
        </tr>
    </table>

    <h2>5. Текст из DOCX (фрагмент)</h2>
    <ul>
        {doc_text_preview}
    </ul>

    <h2>6. Выводы</h2>
    <div class="box-info">
        <ul>
            <li>На скриншотах 4–5 профилировщика видно: <strong>872</strong> (59,5%) &gt; <strong>754</strong> (20,6%) &gt; <strong>768</strong> (13,6%).</li>
            <li>Заполнить (~42 с) и Опубликовать (~4 ч 49 мин) — разные этапы; узкое место обмена — только публикация.</li>
            <li>Детальный разбор цепочек на ФО: <a href="mo_fo_ws_calls_optimization.html">mo_fo_ws_calls_optimization.html</a>.</li>
        </ul>
    </div>

    <p class="meta">
        Пересборка HTML из DOCX:
        <code>python Скрипты/extract_docx_images.py</code>
    </p>
</body>
</html>
"""


def main():
    if not DOCX.exists():
        raise FileNotFoundError(f"DOCX not found: {DOCX}")

    ordered, b64_map, lines = extract_docx_content(DOCX)
    html = build_html(ordered, b64_map, lines)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"OK: {len(ordered)} images embedded -> {OUT_HTML}")
    for i, item in enumerate(ordered, 1):
        print(f"  {i}. {item['file']}")


if __name__ == "__main__":
    main()
