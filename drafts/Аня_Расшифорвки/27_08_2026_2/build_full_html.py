#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polnyj HTML-protokol: vse slova rasshifrovki, neyasnye podsvetka.
"""

import html
import re
from pathlib import Path

SRC = Path(r"C:\1c\Cursor_1c\WIM_DEV\drafts\Аня_Расшифорвки\27_08_2026_2\transcript.txt")
OUT = Path(r"C:\1c\Cursor_1c\WIM_DEV\drafts\Аня_Расшифорвки\27_08_2026_2\protocol_planicum_full.html")

# (regex, replacement). Replacement None = keep original, only color.
# Longer / more specific first.
FIXES = [
    (r"наименование для пресса", "наименование для прайса"),
    (r"наименований для прайса", "наименований для прайса"),
    (r"навинованию на прайсы", "наименованию для прайса"),
    (r"сборке Даны и Ладженон", "сборке данных и Loginom"),
    (r"спринтейт с задания", "спринт и ТЗ"),
    (r"потянение сотрудник", "подчинённый сотрудник"),
    (r"преддемонды", "предDemand"),
    (r"преддиманды", "предDemand"),
    (r"Дмитрий Сенсович", "Дмитрий Станиславович"),
    (r"Дмитрием Сенсовичем", "Дмитрием Станиславовичем"),
    (r"товар на направлении", "товарное направление"),
    (r"регулярный стен", "регулярный"),
    (r"рех цены", "регулярные цены"),
    (r"рех цена", "регулярная цена"),
    (r"речь цена", "регулярная цена"),
    (r"резцены", "регулярные цены"),
    (r"промо-фразировка", "промо-фазировка"),
    (r"промо фразировке", "промо-фазировке"),
    (r"фразировке", "фазировке"),
    (r"ежемедельная", "еженедельная"),
    (r"расширтные", "расширенные"),
    (r"подружаются", "подгружаются"),
    (r"контрактинку", "контрагента"),
    (r"Днематричные", "Нематричные"),
    (r"днематричный", "нематричный"),
    (r"дематричный", "нематричный"),
    (r"Водел продаж", "отдел продаж"),
    (r"делу продаж", "отделу продаж"),
    (r"дела продавших", "отдела продаж"),
    (r"делопродаж", "отдел продаж"),
    (r"оригинальный отдел", "региональный отдел"),
    (r"оригинальном отделе", "региональном отделе"),
    (r"оригинальные отделы", "региональные отделы"),
    (r"оригинальные ключевые", "региональные ключевые"),
    (r"страдплан", "стратплан"),
    (r"(?<![сcС])тратплан", "стратплан"),
    (r"трат построим", "стратплан построим"),
    (r"порция, тратплан", "порция, стратплан"),
    (r"подорышенный", "подарочный"),
    (r"подражным", "подарочным"),
    (r"подорочный", "подарочный"),
    (r"прираниваем", "приравниваем"),
    (r"светофорум", "Светофор"),
    (r"сетафор", "Светофор"),
    (r"Свето-фор", "Светофор"),
    (r"свето-фор", "Светофор"),
    (r"Миханчева", "Михальчева"),
    (r"Миханчевой", "Михальчевой"),
    (r"Миханчева", "Михальчева"),
    (r"Миха Нтёва", "Михальчева"),
    (r"Миха Нтёв", "Михальчева"),
    (r"у Миханчева", "у Михальчевой"),
    (r"у Миханчевой", "у Михальчевой"),
    (r"Кузнецова Даша", "Кузьмина Даша"),
    (r"Кузмина Даша", "Кузьмина Даша"),
    (r"Кузнецова", "Кузьмина"),
    (r"Ирая", "Ира"),
    (r"Ритти", "Рита"),
    (r"у Ренева", "у Ренёва"),
    (r"с Ренова", "с Ренёвым"),
    (r"с Макаровой", "с Макаровым"),
    (r"Ошану", "Ашану"),
    (r"по Ошану", "по Ашану"),
    (r"подлужнике", "подгузнике"),
    (r"на подлужнике", "на подгузнике"),
    (r"на влажке", "на влажные салфетки"),
    (r"на влажку", "на влажные салфетки"),
    (r"яхена", "гигиена"),
    (r"тоталкерри", "тот артикул"),
    (r"рцшки", "РЦ"),
    (r"на арте", "на РЦ"),
    (r"с арте", "с РЦ"),
    (r"Водиноску", "1С"),
    (r"Водинос", "1С"),
    (r"из-за динас", "из 1С"),
    (r"из-за ДНС", "из 1С"),
    (r"задинас", "1С"),
    (r"за диноз", "из 1С"),
    (r"и за диноз", "из 1С"),
    (r"в ДНС", "в 1С"),
    (r"диманды", "Demand"),
    (r"диманд", "Demand"),
    (r"Ланйкум", "Planicum"),
    (r"планенько", "Planicum"),
    (r"планетки", "Planicum"),
    (r"планетка", "Planicum"),
    (r"паником", "Planicum"),
    (r"планиоры", "плановики"),
    (r"Ладженон", "Loginom"),
    (r"ладжинам", "Loginom"),
    (r"леджиноме", "Loginom"),
    (r"леджином", "Loginom"),
    (r"ладжиноме", "Loginom"),
    (r"ладжином", "Loginom"),
    (r"Ладжном", "Loginom"),
    (r"ладжном", "Loginom"),
    (r"дешборды", "дашборды"),
    (r"Дешборды", "Дашборды"),
    (r"дешборд", "дашборд"),
    (r"дешбур", "дашборд"),
    (r"дашь борда", "дашборда"),
    (r"дашь борд", "дашборд"),
    (r"дашьборда", "дашборда"),
    (r"даже борт", "дашборд"),
    (r"даже бор", "дашборд"),
    (r"Dashboard", "дашборд"),
    (r"тымашек", "ТМА"),
    (r"тымашки", "ТМА"),
    (r"тымашкам", "ТМА"),
    (r"промеки", "промо"),
    (r"промек", "промо"),
    (r"бзайну", "baseline"),
    (r"бэзлайн", "baseline"),
    (r"бейзлайн", "baseline"),
    (r"Бэзлайн", "baseline"),
    (r"эскаюшка", "SKU"),
    (r"эскаюшки", "SKU"),
    (r"искаюшка", "SKU"),
    (r"искаюшки", "SKU"),
    (r"искаюшечку", "SKU"),
    (r"каюшка", "SKU"),
    (r"скаюшка", "SKU"),
    (r"скаюшку", "SKU"),
    (r"эскоешке", "SKU"),
    (r"\bискаю\b", "SKU"),
    (r"УКАМА", "у КАМа"),
    (r"\bкамон\b", "КАМ"),
    (r"\bяком\b", "E-com"),
    (r"\bсимам\b", "СиМ"),
    (r"\bсимов\b", "СиМ"),
    (r"\bсемы\b", "СиМ"),
    (r"дисторы", "дистрибьюторы"),
    (r"дистора", "дистрибьютора"),
    (r"дистор", "дистрибьютор"),
    (r"дисты", "дистры"),
    (r"процессии", "процессы"),
    (r"котенклаба", "1С"),
    (r"на питании", "на лету"),
    (r"те заданиями", "ТЗ"),
    (r"те задания", "ТЗ"),
    (r"Те задания", "ТЗ"),
    (r"с те заданиями", "с ТЗ"),
    (r"распродажить", "распродажа"),
    (r"в подэзе", "в паузе"),
    (r"уши голода", "уши везде"),
    (r"Галак ловилась", "на грабли ловилась"),
    (r"талагирование", "логирование"),
    (r"маней зайти", "самой зайти"),
    (r"деленький", "1С-ный"),
    (r"ворт, тандр", "виджет, Тандер"),
    (r"\bворт\b", "виджет"),
    (r"ливи-бандет", "левый бандл"),
    (r"спай, космотка", "свой, косметика"),
    (r"50-писку", "подписку"),
    (r"перероснуть", "перенести"),
    (r"не греются", "нужны"),
    (r"Сидёт и заканит", "Сводит и закачивает"),
    (r"Закройшу в капюлиты", "закрой, ещё копии"),
    (r"протогрокнула", "потрогала"),
    (r"МДФ формати", "МД-формат"),
    (r"ГМ формати", "ГМ-формат"),
    (r"МК формат", "МК-формат"),
    (r"магниту дома", "Магнит у дома"),
    (r"статистики продаж уже за авто с месяц", "статистика продаж уже за август месяц"),
    (r"циатистики", "статистики"),
    (r"в плане кумперисчитанцев", "в Planicum пересчитан с"),
    (r"целым планеньком", "целом Planicum"),
    (r"планеньку", "Planicum"),
    (r"vo5", "005"),
    (r"Ее надо в сад", "её надо отсюда"),
    (r"12-го год", "горизонт / год"),
    (r"сгадами", "с годами"),
    (r"одиннадцать это", "1С это"),
    (r"\b1s\b", "1С"),
    (r"\bMLD\b", "ML"),
    (r"\bмэль\b", "ML"),
    (r"\bмыль\b", "ML"),
    (r"планикума", "Planicum"),
    (r"планикуме", "Planicum"),
    (r"планикумом", "Planicum"),
    (r"планикуму", "Planicum"),
    (r"Планикуму", "Planicum"),
    (r"планикум", "Planicum"),
    (r"Планикум", "Planicum"),
    (r"планекума", "Planicum"),
    (r"планекуме", "Planicum"),
    (r"планекумом", "Planicum"),
    (r"планекум", "Planicum"),
    (r"Планекум", "Planicum"),
    (r"планику", "Planicum"),
    (r"планеку", "Planicum"),
    (r"в раузере", "в браузере"),
    (r"Хотон и двухгодичной", "Хоть он и двухгодичной"),
    (r"блокхем", "блок-схем"),
    (r"утрею", "утром"),
    (r"без прома", "без промо"),
    (r"все прома", "все промо"),
    (r"прогноз свист", "прогноз, сглаживание"),
    (r"в массоку", "в массовую"),
    (r"иометрия", "Геометрия"),
]

# compile once
COMPILED = [(re.compile(p, re.IGNORECASE), repl) for p, repl in FIXES]


def ts_to_sec(ts: str) -> float:
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def parse_transcript(text: str):
    rows = []
    for line in text.splitlines():
        if line.startswith("---"):
            break
        m = re.match(r"\[(\d{2}:\d{2}:\d{2}) - (\d{2}:\d{2}:\d{2})\]\s*(.*)$", line)
        if not m:
            continue
        rows.append((m.group(1), m.group(2), m.group(3).strip()))
    return rows


def apply_fixes(text: str) -> str:
    marks = []

    def stash(orig: str, new: str) -> str:
        i = len(marks)
        marks.append((orig, new))
        return f"\x00{i}\x00"

    # apply sequentially on remaining raw text
    out = text
    for rx, repl in COMPILED:
        def sub(m, repl=repl):
            orig = m.group(0)
            if orig.replace("ё", "е").lower() == repl.replace("ё", "е").lower():
                return orig
            return stash(orig, repl)

        out = rx.sub(sub, out)

    out = html.escape(out)

    def restore(m):
        orig, new = marks[int(m.group(1))]
        o = html.escape(orig)
        n = html.escape(new)
        if o.lower() == n.lower():
            return n
        return (
            f'<span class="fix" title="Whisper: {o}">{n}</span>'
        )

    return re.sub(r"\x00(\d+)\x00", restore, out)


def group_rows(rows, gap_sec: float = 1.15, max_seg: int = 5, max_span: float = 25.0):
    groups = []
    cur = None
    prev_end = None
    cur_start_sec = None
    for start, end, text in rows:
        if not text:
            continue
        st = ts_to_sec(start)
        en = ts_to_sec(end)
        if cur is None:
            cur = {"start": start, "end": end, "parts": [text]}
            cur_start_sec = st
        else:
            too_long = (len(cur["parts"]) >= max_seg) or ((st - cur_start_sec) >= max_span)
            pause = (st - prev_end) > gap_sec
            if pause or too_long:
                groups.append(cur)
                cur = {"start": start, "end": end, "parts": [text]}
                cur_start_sec = st
            else:
                cur["parts"].append(text)
                cur["end"] = end
        prev_end = en
    if cur:
        groups.append(cur)
    return groups


def minute_bucket(ts: str) -> str:
    h, m, s = ts.split(":")
    total = int(h) * 60 + int(m)
    block = (total // 5) * 5
    hh = block // 60
    mm = block % 60
    return f"{hh:02d}:{mm:02d}"


HTML_HEAD = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Полный протокол слово в слово: Planicum 27.08.2026</title>
<style>
  :root {
    --bg: #f3f6f8;
    --card: #fff;
    --ink: #1a2430;
    --muted: #5a6b7c;
    --line: #d5dee7;
    --accent: #0d6e6e;
    --fix-bg: #fff3a3;
    --fix-ink: #6b4e00;
    --font: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: var(--font); color: var(--ink); background: var(--bg); line-height: 1.62; }
  .top {
    background: linear-gradient(135deg, #0a3d3d 0%, #0d6e6e 55%, #149494 100%);
    color: #fff; padding: 24px 18px 18px;
  }
  .top-inner { max-width: 920px; margin: 0 auto; }
  .top h1 { margin: 0 0 8px; font-size: 1.35rem; }
  .top .meta { opacity: .93; font-size: .92rem; }
  .top .meta span { margin-right: 12px; display: inline-block; }
  .legend {
    max-width: 920px; margin: 14px auto 0; padding: 0 16px;
  }
  .legend-box {
    background: #fff8e1; border-left: 4px solid #e0b100;
    padding: 10px 14px; font-size: .92rem; color: #6b4e00;
  }
  .wrap { max-width: 920px; margin: 0 auto; padding: 12px 16px 48px; }
  h2.block {
    position: sticky; top: 0; z-index: 5;
    background: var(--bg); margin: 22px 0 10px; padding: 8px 0 6px;
    font-size: 1.05rem; color: var(--accent);
    border-bottom: 2px solid #e6f4f4;
  }
  .p {
    background: var(--card); border: 1px solid var(--line); border-radius: 8px;
    padding: 10px 14px; margin: 0 0 8px;
  }
  .p .t {
    display: inline-block; font-family: Consolas, "Courier New", monospace;
    font-size: .75rem; font-weight: 700; color: #fff;
    background: var(--accent); padding: 1px 7px; border-radius: 4px;
    margin-right: 8px;
  }
  .fix {
    background: var(--fix-bg); color: var(--fix-ink);
    padding: 0 3px; border-radius: 3px; border-bottom: 1px dotted #c9a227;
    cursor: help;
  }
  footer { max-width: 920px; margin: 0 auto; padding: 8px 16px 28px; color: var(--muted); font-size: .85rem; }
  a { color: var(--accent); font-weight: 600; }
</style>
</head>
<body>
<header class="top">
  <div class="top-inner">
    <h1>Полный протокол слово в слово: Planicum</h1>
    <div class="meta">
      <span>27.08.2026, ~13:01</span>
      <span>~62 мин</span>
      <span>Аудио: 27.08.2026 13.01.m4a</span>
      <span>Все 1007 фрагментов Whisper</span>
    </div>
  </div>
</header>
<div class="legend">
  <div class="legend-box">
    Жёлтым выделены слова, которые Whisper произнёс неясно и которые правлены по смыслу.
    Наведите курсор — увидите исходное распознавание. Остальной текст не сокращён.
    Краткий протокол: <a href="protocol_planicum.html">protocol_planicum.html</a>.
  </div>
</div>
<main class="wrap">
"""

HTML_FOOT = """
</main>
<footer>Папка: drafts/Аня_Расшифорвки/27_08_2026_2 · Источник: transcript.txt</footer>
</body>
</html>
"""


def main() -> None:
    raw = SRC.read_text(encoding="utf-8")
    rows = parse_transcript(raw)
    groups = group_rows(rows)

    parts = [HTML_HEAD]
    last_bucket = None
    for g in groups:
        bucket = minute_bucket(g["start"])
        if bucket != last_bucket:
            parts.append(f'<h2 class="block">С {bucket}</h2>\n')
            last_bucket = bucket
        joined = " ".join(g["parts"])
        body = apply_fixes(joined)
        stamp = g["start"][3:] if g["start"].startswith("00:") else g["start"]
        stamp2 = g["end"][3:] if g["end"].startswith("00:") else g["end"]
        parts.append(
            f'<p class="p"><span class="t">{html.escape(stamp)}–{html.escape(stamp2)}</span> {body}</p>\n'
        )

    parts.append(HTML_FOOT)
    OUT.write_text("".join(parts), encoding="utf-8")
    print("rows", len(rows), "groups", len(groups), "out", OUT, "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
