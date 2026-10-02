# -*- coding: utf-8 -*-
"""Отчет о полном тестировании расширения FO_KeyOpsPerf (IMDEV-9530, строки 2, 6, 7, 8, 15, 17).

    python build_report_full.py [<папка прогона results/full_...>]

Источник - measurements.json прогона run_full_tests.py: записи регистра ЗамерыВремени, протокол запусков, сводки
стенда МО-ФО и сверка снимков данных ФО. Диаграммы - встроенный SVG, подсказка при наведении на элемент.
"""
import collections
import datetime
import glob
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(TASK, "Тестирование", "Отчет о тестировании расширения FO_KeyOpsPerf.html")
STAGE3_FULL_PACKING = os.path.join(HERE, "results", "stage3_20261002_164447", "measurements.json")
EPOCH = datetime.datetime(1, 1, 1)
PACK_STEPS = ["КэшВмОписания", "ОчиститьСлужебныеКэши", "ОчиститьДанныеНеактивныхСеансов"]
PACK_REGISTERS = ["БиржевыеТранзакции", "БиржевыеТранзакцииНеторговые", "БиржевыеЗаявкиВнешние",
                  "СообщенияАдаптеров", "СведенияОБиржевыхДисконтах"]
CALL_KINDS = ["754: флаг до позиции", "768: позиция", "872: флаги после позиции", "удаление блокировок",
              "4-й: запуск перерасчета РСА"]
EXPECTED = {
    "6-8": ["ОбменБэкОфис.Пакет", "ОбменБэкОфис.ОперацииПослеОбмена"],
    "6": ["ОбменБэкОфис.РегистрыСведений.ФактическаяПозиция", "ОбменБэкОфис.РегистрыСведений.СтоимостьЧистыхАктивов",
          "ОбменБэкОфис.РегистрыСведений.ДополнительныеСведения", "ОбменБэкОфис.РегистрыСведений.ФинансовыеПоказателиОблигаций"],
    "7": ["ОбменБэкОфис.Справочники.Портфели", "ОбменБэкОфис.Справочники.Субпортфели", "ОбменБэкОфис.Справочники.МестаХранения",
          "ОбменБэкОфис.Справочники.Стратегии", "ОбменБэкОфис.Справочники.Контрагенты",
          "ОбменБэкОфис.Справочники.АффилированныеЛица"],
    "8": ["ОбменБэкОфис.Документы.КотировкиЦБНаБирже", "ОбменБэкОфис.Документы.СделкаСЦеннымиБумагами"],
    "15": ["ИсполнениеСделок", "ИсполнениеСделок.ЗаполнитьТаблицуСделок", "ИсполнениеСделок.Проведение"],
    "17": ["УпаковкаДанных"] + [f"УпаковкаДанных.{s}" for s in PACK_STEPS] + [f"УпаковкаДанных.Сократить.{r}" for r in PACK_REGISTERS],
    "2": ["ПроверкаЛимитов.ПостКонтроль"],
}
ROWS = [
    ("2", "Постконтроль лимитов по всем портфелям", "ПроверкаЛимитовПоПортфелям.ПроверкаПоЛимитамПоРасписанию"),
    ("6", "Загрузка позиций портфелей из МО (регистры)", "ОбменДаннымиБэкОфис: диспетчер регистров"),
    ("7", "Загрузка справочных данных из МО (мандаты, счета, контрагенты)", "ОбменДаннымиБэкОфис: диспетчер справочников"),
    ("8", "Загрузка документов из МО (котировки, сделки)", "ОбменДаннымиБэкОфис: диспетчер документов"),
    ("15", "Исполнение сделок", "ГрупповоеИсполнениеСделок.СоздатьДокументыИсполнения"),
    ("17", "Упаковка данных", "АванкорВыполнениеРегламентныхЗаданий.УпаковкаДанных"),
]


def esc(s):
    return html.escape(str(s))


def fmt(x, d=3):
    return f"{x:,.{d}f}".replace(",", " ")


def parse_comment(text):
    result = {}
    for part in str(text).split(";"):
        if ":" in part:
            k, _, v = part.partition(":")
            result[k.strip()] = v.strip()
    return result


def row_of(key):
    if key == "ПроверкаЛимитов.ПостКонтроль":
        return "2"
    if key.startswith("ИсполнениеСделок"):
        return "15"
    if key.startswith("УпаковкаДанных"):
        return "17"
    if key.startswith("ОбменБэкОфис.РегистрыСведений"):
        return "6"
    if key.startswith("ОбменБэкОфис.Справочники"):
        return "7"
    if key.startswith("ОбменБэкОфис.Документы"):
        return "8"
    return "6-8"


# ---------------- диаграммы ----------------

def hbar(items, unit="с", digits=3, width=760, label_w=300, bar_h=22, note=""):
    """Горизонтальные столбцы: items = [(подпись, значение, подсказка, класс_цвета, метка_статуса)]."""
    if not items:
        return "<p class='lead'>Нет данных.</p>"
    vmax = max(v for _, v, *_ in items) or 1
    plot = width - label_w - 200
    h = len(items) * (bar_h + 8) + 8
    out = [f"<svg class='chart' viewBox='0 0 {width} {h}' role='img' aria-label='{esc(note)}'>"]
    for i, (label, value, tip, cls, status) in enumerate(items):
        y = 6 + i * (bar_h + 8)
        w = max(value / vmax * plot, 2)
        out.append(f"<g class='hit'><title>{esc(tip)}</title>"
                   f"<rect class='hitbox' x='0' y='{y - 3}' width='{width}' height='{bar_h + 6}'/>"
                   f"<text x='{label_w - 8}' y='{y + bar_h / 2 + 4}' class='lbl' text-anchor='end'>{esc(label)}</text>"
                   f"<rect class='bar {cls}' x='{label_w}' y='{y}' width='{w:.1f}' height='{bar_h}' rx='4'/>"
                   f"<text x='{label_w + w + 6:.1f}' y='{y + bar_h / 2 + 4}' class='val'>{fmt(value, digits)} {esc(unit)}"
                   f"{(' · ' + esc(status)) if status else ''}</text></g>")
    out.append(f"<line x1='{label_w}' x2='{label_w}' y1='2' y2='{h - 2}' class='axis'/></svg>")
    return "".join(out)


def grouped_hbar(groups, series, unit="с", digits=1, width=760, label_w=230, bar_h=14):
    """Пары столбцов: groups = [(подпись, [значение по сериям])], series = [(имя, класс)]."""
    vmax = max((v for _, vals in groups for v in vals if v is not None), default=1) or 1
    plot = width - label_w - 80
    block = len(series) * (bar_h + 3) + 12
    h = len(groups) * block + 6
    out = [f"<svg class='chart' viewBox='0 0 {width} {h}' role='img'>"]
    for i, (label, vals) in enumerate(groups):
        y0 = 6 + i * block
        out.append(f"<text x='{label_w - 8}' y='{y0 + block / 2}' class='lbl' text-anchor='end'>{esc(label)}</text>")
        for j, ((name, cls), v) in enumerate(zip(series, vals)):
            if v is None:
                continue
            y = y0 + j * (bar_h + 3)
            w = max(v / vmax * plot, 2)
            out.append(f"<g class='hit'><title>{esc(label)}: {esc(name)} {fmt(v, digits)} {esc(unit)}</title>"
                       f"<rect class='bar {cls}' x='{label_w}' y='{y}' width='{w:.1f}' height='{bar_h}' rx='3'/>"
                       f"<text x='{label_w + w + 6:.1f}' y='{y + bar_h - 3}' class='val'>{fmt(v, digits)}</text></g>")
    out.append(f"<line x1='{label_w}' x2='{label_w}' y1='2' y2='{h - 2}' class='axis'/></svg>")
    legend = "".join(f"<span><i class='sw {cls}'></i>{esc(name)}</span>" for name, cls in series)
    return f"<div class='legend'>{legend}</div>" + "".join(out)


def timeline(packets, sec_by_packet, local, kind_of):
    if not packets:
        return ""
    W, LANE, LEFT = 1100, 24, 70
    ordered = sorted(packets, key=lambda r: r["начало_мс"])
    lanes_end, placed = [], []
    for p in ordered:
        for i, end in enumerate(lanes_end):
            if p["начало_мс"] >= end:
                lanes_end[i] = p["окончание_мс"]
                placed.append((i, p))
                break
        else:
            lanes_end.append(p["окончание_мс"])
            placed.append((len(lanes_end) - 1, p))
    g0 = min(p["начало_мс"] for p in ordered)
    g1 = max(p["окончание_мс"] for p in ordered)
    span = max(g1 - g0, 1)
    width = W - LEFT - 10
    parts = []
    for i in range(11):
        ms = g0 + span * i / 10
        x = LEFT + width * i / 10
        parts.append(f"<line x1='{x:.1f}' x2='{x:.1f}' y1='16' y2='{24 + len(lanes_end) * LANE}' class='tick'/>"
                     f"<text x='{x:.1f}' y='12' class='tt'>{local(ms).strftime('%H:%M:%S')}</text>")
    for i in range(len(lanes_end)):
        parts.append(f"<text x='8' y='{24 + i * LANE + 13}' class='lane'>дорожка {i + 1}</text>")
    for lane, p in placed:
        x = LEFT + (p["начало_мс"] - g0) / span * width
        w = max((p["окончание_мс"] - p["начало_мс"]) / span * width, 2)
        cls, label = kind_of(p)
        secs = sec_by_packet.get(p["пакет"], [])
        tip = (f"{label}: {fmt(p['время_с'])} с, вес {fmt(p['вес'], 0)}, сеанс {p['сеанс']}; {p['комментарий'].split('; Пакет:')[0]}; "
               + "; ".join(f"{s['ключ'].replace('ОбменБэкОфис.', '')} {fmt(s['время_с'])} с" for s in secs))
        parts.append(f"<rect class='bar {cls}{' err' if p['ошибка'] else ''}' x='{x:.1f}' y='{24 + lane * LANE}' "
                     f"width='{w:.1f}' height='{LANE - 6}' rx='3'><title>{esc(tip)}</title></rect>")
    return (f"<svg class='chart tl' viewBox='0 0 {W} {30 + len(lanes_end) * LANE}' role='img' "
            f"aria-label='Пакеты во времени'>{''.join(parts)}</svg>"), len(lanes_end), (g1 - g0) / 1000


def main():
    run_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(
        os.path.dirname(p) for p in glob.glob(os.path.join(HERE, "results", "full_*", "measurements.json")))[-1]
    with open(os.path.join(run_dir, "measurements.json"), encoding="utf-8") as f:
        data = json.load(f)
    rows = data["замеры"]
    for r in rows:
        if str(r["комментарий"]).startswith("{"):
            r["комментарий"] = "(стандартный комментарий БСП)"
        r["доп"] = parse_comment(r["комментарий"])
        r["пакет"] = r["доп"].get("Пакет", "")
        r["строка"] = row_of(r["ключ"])
        r["dt"] = datetime.datetime.fromisoformat(r["записано"].replace("+00:00", ""))
    offs = collections.Counter(round((r["dt"] - (EPOCH + datetime.timedelta(milliseconds=r["окончание_мс"]))).total_seconds() / 3600)
                               for r in rows if r.get("окончание_мс"))
    tz = offs.most_common(1)[0][0] if offs else 3

    def local(ms):
        return EPOCH + datetime.timedelta(milliseconds=ms, hours=tz)

    tests = data["тесты"]
    by_key = collections.defaultdict(list)
    for r in rows:
        by_key[r["ключ"]].append(r)

    # Запись относится к запуску, в интервал которого попадает НАЧАЛО замера (миллисекунды), до начала следующего
    # запуска: соседние запуски часто идут в одну секунду, и окна по секундному времени записи перекрываются.
    for r in rows:
        r["старт"] = local(r["начало_мс"])
    starts = sorted({datetime.datetime.fromisoformat(t["начало"]) for t in tests if "начало" in t})

    def window(t, prefix=""):
        a = datetime.datetime.fromisoformat(t["начало"])
        b = datetime.datetime.fromisoformat(t["окончание"]) + datetime.timedelta(seconds=1)
        nxt = next((s for s in starts if s > a), None)
        if nxt is not None and nxt < b:
            b = nxt
        return [r for r in rows if a <= r["старт"] < b and r["ключ"].startswith(prefix)]

    # Записи строк 2, 15, 17 вне окон запусков протокола - из запусков, повторенных после исправления сценария;
    # в статистику не входят (обмен 6-8 привязан к пакетам, его записи остаются все).
    in_tests = {id(r) for t in tests if "начало" in t for r in window(t)}
    excluded = [r for r in rows if not r["ключ"].startswith("ОбменБэкОфис.") and id(r) not in in_tests]
    rows = [r for r in rows if r["ключ"].startswith("ОбменБэкОфис.") or id(r) in in_tests]
    by_key = collections.defaultdict(list)
    for r in rows:
        by_key[r["ключ"]].append(r)

    checks = collections.defaultdict(list)

    def check(row, name, ok, fact):
        checks[row].append((name, bool(ok), fact))

    # ---------------- обмен (строки 6-8) ----------------
    packets = [r for r in rows if r["ключ"] == "ОбменБэкОфис.Пакет"]
    sections = [r for r in rows if r["строка"] in ("6", "7", "8")]
    sec_by_packet = collections.defaultdict(list)
    for r in rows:
        if r["ключ"].startswith("ОбменБэкОфис.") and r["ключ"] != "ОбменБэкОфис.Пакет":
            sec_by_packet[r["пакет"]].append(r)

    def kind_of(p):
        keys = {s["ключ"].split(".", 2)[-1] for s in sec_by_packet.get(p["пакет"], [])}
        if "ФактическаяПозиция" in keys:
            return "s1", "позиция"
        if "ДополнительныеСведения" in keys:
            return "s2", "флаги"
        if keys & {"СделкаСЦеннымиБумагами"}:
            return "s5", "сделки"
        if keys & {"КотировкиЦБНаБирже", "ФинансовыеПоказателиОблигаций"}:
            return "s4", "котировки"
        if keys & {"Портфели", "Субпортфели", "Контрагенты", "МестаХранения", "Стратегии"}:
            return "s3", "справочники"
        return "svc", "служебный"

    a_tests = {t["метка"]: t for t in tests if t["тест"] == "A"}
    a_base = a_tests.get("base")
    base_rows = window(a_base) if a_base and "начало" in a_base else []
    pos_packets = [p for p in packets if kind_of(p)[1] in ("позиция", "флаги", "служебный")
                   and not (a_base and "начало" in a_base and p in base_rows)]
    empty = [r for r in sections if r["доп"].get("Строк", "1") in ("0", "")]
    for row in ("6", "7", "8"):
        sec = [r for r in sections if r["строка"] == row and r["ключ"] != "ОбменБэкОфис.РегистрыСведений.ДополнительныеСведения"]
        port = [r for r in sec if r["доп"].get("Портфелей", "0") not in ("0", "")]
        check(row, "Пустые разделы не пишутся", not [r for r in empty if r["строка"] == row],
              f"записей раздела со 'Строк: 0': {len([r for r in empty if r['строка'] == row])} из {len(sec)}")
        dup = [k for k, v in collections.Counter((r["пакет"], r["ключ"]) for r in sec).items() if v > 1]
        check(row, "Раздел записан не более одного раза за пакет", not dup, f"повторов: {len(dup)}")
        pk = {p["пакет"]: p for p in packets}
        bad = [r for r in sec if r["пакет"] not in pk or r["сеанс"] != pk[r["пакет"]]["сеанс"]
               or r["начало_мс"] < pk[r["пакет"]]["начало_мс"] - 1 or r["окончание_мс"] > pk[r["пакет"]]["окончание_мс"] + 1]
        check(row, "Раздел связан с пакетом по УИД, время внутри пакета, тот же сеанс", not bad,
              f"нарушений: {len(bad)} из {len(sec)}")
        check(row, "Где в строках есть портфель, вес = число разных портфелей",
              all(abs(r["вес"] - float(r["доп"]["Портфелей"])) < 0.5 for r in port),
              f"проверено записей с портфелями: {len(port)}")
    ds = by_key.get("ОбменБэкОфис.РегистрыСведений.ДополнительныеСведения", [])
    check("6", "ДополнительныеСведения пишет расширение IMDEV-9532 (поле 'Записано')",
          ds and all("Записано" in r["доп"] for r in ds), f"записей: {len(ds)}")
    snap = data.get("сверка_снимков", {})
    check("6", "Данные ФО после выгрузки с расширением и без совпадают (снимок)", snap.get("расхождений") == 0,
          f"строк в снимке: {', '.join(f'{k} {v}' for k, v in snap.get('строк', {}).items())}; расхождений {snap.get('расхождений')}")
    base_ext = [r for r in base_rows if r["ключ"].startswith("ОбменБэкОфис.") and not r["ключ"].endswith("ДополнительныеСведения")]
    check("6", "Без FO_KeyOpsPerf записи пакетов и разделов не пишутся",
          a_base and "начало" in a_base and not base_ext,
          f"записей в окне выгрузки без расширения: FO_KeyOpsPerf {len(base_ext)}, ДополнительныеСведения "
          f"{sum(1 for r in base_rows if r['ключ'].endswith('ДополнительныеСведения'))} (пишет FO_PositionLoadOpt)")
    err_pk = [p for p in packets if p["ошибка"]]
    check("6", "Признак ошибки пакета = код ответа не 0",
          all(p["доп"].get("Код ответа", "0") != "0" for p in err_pk)
          and all(p["доп"].get("Код ответа", "0") == "0" for p in packets if not p["ошибка"]),
          f"пакетов с ошибкой: {len(err_pk)} из {len(packets)}")
    mand = [p for p in packets if kind_of(p)[1] == "справочники"
            and any(s["ключ"].endswith(".Портфели") for s in sec_by_packet[p["пакет"]])]
    aff = by_key.get("ОбменБэкОфис.Справочники.АффилированныеЛица", [])
    check("7", "Справочник Портфели: вес = число элементов (договоров)",
          all(s["вес"] == float(s["доп"]["Строк"]) for p in mand for s in sec_by_packet[p["пакет"]] if s["ключ"].endswith(".Портфели")),
          "; ".join(f"вес {fmt(s['вес'], 0)}, строк {s['доп'].get('Строк')}" for p in mand for s in sec_by_packet[p["пакет"]] if s["ключ"].endswith(".Портфели")))
    check("7", "АффилированныеЛица: только контрагенты с аффилированными лицами",
          len(aff) == 1 and aff[0]["доп"].get("Аффилированных лиц") == "2" and aff[0]["вес"] == 1
          and not any(s["ключ"].endswith(".АффилированныеЛица") for p in mand for s in sec_by_packet[p["пакет"]]),
          f"пакет мандатов (контрагент без аффилированных лиц) - записи нет; тестовый пакет: "
          + "; ".join(f"вес {fmt(r['вес'], 0)}, '{r['комментарий'].split('; Пакет:')[0]}{'; ' + r['комментарий'].split('Аффилированных')[1] if 'Аффилированных' in r['комментарий'] else ''}'" for r in aff))
    quotes = by_key.get("ОбменБэкОфис.Документы.КотировкиЦБНаБирже", [])
    check("8", "КотировкиЦБНаБирже: вес = число котировок в документах",
          quotes and all(r["вес"] == float(r["доп"].get("Котировок", -1)) for r in quotes),
          "; ".join(f"вес {fmt(r['вес'], 0)}, документов {r['доп'].get('Строк')}, котировок {r['доп'].get('Котировок')}" for r in quotes))
    dl = by_key.get("ОбменБэкОфис.Документы.СделкаСЦеннымиБумагами", [])
    check("8", "СделкаСЦеннымиБумагами: портфели из РаспределениеПоПортфелям, вес = портфели",
          len(dl) >= 2 and all(r["вес"] == 3 and r["доп"].get("Портфелей") == "3" for r in dl),
          "; ".join(f"вес {fmt(r['вес'], 0)}, сделок {r['доп'].get('Строк')}, портфелей {r['доп'].get('Портфелей')}" for r in dl))

    # ---------------- строка 15 ----------------
    e = {t["метка"]: t for t in tests if t["тест"] == "E"}
    m_test = next((t for t in tests if t["тест"] == "M"), None)
    rd, rrep, rb = (window(e[k], "ИсполнениеСделок") for k in ("с_замерами", "повторный_запуск", "без_замеров"))
    rm = window(m_test, "ИсполнениеСделок") if m_test else []
    after = e["с_замерами"]["после"]
    before = e["с_замерами"]["до"]
    exp_comment = f"Строк: {before['строк_остатка']}; Сделок: {after['сделок']}; Портфелей: {after['портфелей']}; Запуск: регламентное задание"
    check("15", "Регламентный запуск: три ключа (заполнение, проведение, итог)",
          sorted(r["ключ"] for r in rd) == sorted(EXPECTED["15"]), ", ".join(sorted(r["ключ"] for r in rd)))
    check("15", "Вес = разные портфели, комментарий = факт исполнения",
          rd and all(r["вес"] == after["портфелей"] and r["комментарий"] == exp_comment for r in rd),
          f"вес {sorted({r['вес'] for r in rd})}, '{rd[0]['комментарий'] if rd else ''}'; создано документов {after['документов']} "
          f"(проведено {after['проведено']}), остаток плановой позиции {before['строк_остатка']} -> {after['строк_остатка']} строк")
    check("15", "Повторный запуск: исполнять нечего, документы не задваиваются",
          len(rrep) == 3 and all(r["вес"] == 1 and r["доп"].get("Строк") == "0" for r in rrep)
          and e["повторный_запуск"]["после"]["документов"] == e["повторный_запуск"]["до"]["документов"],
          f"записей {len(rrep)}, вес {sorted({r['вес'] for r in rrep})}, документов {e['повторный_запуск']['до']['документов']} -> {e['повторный_запуск']['после']['документов']}")
    check("15", "Ручной запуск (форма): два ключа, без шага заполнения",
          sorted(r["ключ"] for r in rm) == ["ИсполнениеСделок", "ИсполнениеСделок.Проведение"]
          and all(r["доп"].get("Запуск") == "вручную" for r in rm),
          ", ".join(f"{r['ключ']} ({r['доп'].get('Запуск')})" for r in rm))
    cmp_e = data.get("сравнение_исполнения", {})
    check("15", "Без расширения замеров нет, документы исполнения те же построчно",
          not rb and cmp_e.get("совпадают") and e["без_замеров"]["после"]["документов"] == after["документов"],
          f"записей без расширения {len(rb)}; документов {len(cmp_e.get('с_замерами', []))} и {len(cmp_e.get('без_замеров', []))} "
          f"(портфель, актив, количество, место хранения, тип портфеля, счет, проведен), расхождений {cmp_e.get('расхождений')}")

    # ---------------- строка 2 ----------------
    p_tests = [t for t in tests if t["тест"] == "P"]
    p_rows = {(t["вариант"], t["метка"]): window(t, "ПроверкаЛимитов.ПостКонтроль") for t in p_tests}
    expect = {"пустая": (1, True, "Проверка не выполнялась"), "неактивные": (1, False, "Проверка не выполнялась"),
              "отказ": (20, True, "Фоновые задания"), "рассылка": (20, False, "Фоновые задания"),
              "успех": (20, False, "Фоновые задания")}
    for variant, (weight, error, marker) in expect.items():
        rr = p_rows.get((variant, "с_замерами"), [])
        check("2", f"Вариант '{variant}': одна запись, вес {weight}, ошибка - {'да' if error else 'нет'}",
              len(rr) == 1 and rr[0]["вес"] == weight and rr[0]["ошибка"] == error and marker in rr[0]["комментарий"],
              "; ".join(f"{fmt(r['время_с'])} с, '{r['комментарий']}'" for r in rr) or "записей нет")
    mail = next(t for t in p_tests if t["вариант"] == "рассылка" and t["метка"] == "с_замерами")
    t_mail = p_rows[("рассылка", "с_замерами")][0]["время_с"]
    t_ok = p_rows[("успех", "с_замерами")][0]["время_с"]
    check("2", "Замер включает постановку ведомостей в очередь рассылки",
          mail["очередь_рассылки_после_проверки"] == mail["очередь_рассылки_до"] + 1 and t_mail - t_ok >= 9,
          f"очередь {mail['очередь_рассылки_до']} -> {mail['очередь_рассылки_после_проверки']} (после теста удалено {mail['удалено_из_очереди']}); "
          f"с рассылкой {fmt(t_mail, 1)} с, без нее {fmt(t_ok, 1)} с - штатная пауза 10 с")
    with_res = [list(t["строки_результата"].values())[0] for t in p_tests if t["строки_результата"]]
    diffs = sum(len(set(r) ^ set(with_res[0])) for r in with_res) if with_res else -1
    no_ext = [t for t in p_tests if t["метка"] == "без_замеров"]
    check("2", "Без расширения замера нет, результат проверки тот же построчно",
          all(not p_rows[(t["вариант"], t["метка"])] for t in no_ext) and diffs == 0,
          f"прогонов с проверкой {len(with_res)} по {len(with_res[0]) if with_res else 0} строк, расхождений {diffs} "
          "(поле Замер регистра КэшВмКратко - хронометраж самой проверки - не сравнивается); записей замера без расширения 0")
    check("2", "Тестовые настройки возвращены", all(t["константа_восстановлена"] and t["неактивных_после_теста"] == 0
                                                     and t["очередь_рассылки_после_очистки"] == 0 for t in p_tests),
          "константа НастройкиРассылкиПоЛимитам, неактивные портфели, очередь рассылки - как до теста")

    # ---------------- строка 17 ----------------
    u = {t["метка"]: t for t in tests if t["тест"] == "U"}
    ru, rub = window(u["с_замерами"], "УпаковкаДанных"), window(u["без_замеров"], "УпаковкаДанных")
    u_keys = {r["ключ"]: r for r in ru}
    check("17", "Записаны три шага, пять сокращений регистров и итог", sorted(u_keys) == sorted(EXPECTED["17"]),
          f"записей {len(ru)} из {len(EXPECTED['17'])}; активных торговых дат: {u_keys.get('УпаковкаДанных', {}).get('доп', {}).get('Активных торговых дат')}")
    total = u_keys.get("УпаковкаДанных", {}).get("время_с", 0)
    parts = sum(r["время_с"] for k, r in u_keys.items() if k != "УпаковкаДанных")
    check("17", "Итог не меньше суммы шагов", total + 1e-6 >= parts, f"итог {fmt(total)} с, шаги {fmt(parts)} с")
    check("17", "Без расширения замеров нет, состояние данных после упаковки то же",
          not rub and u["с_замерами"]["после"] == u["без_замеров"]["после"],
          f"записей без расширения {len(rub)}; после упаковки с расширением и без: "
          + ", ".join(f"{k} {v}" for k, v in u["без_замеров"]["после"].items()))

    # ---------------- общая проверка ----------------
    keys_all = [k for v in EXPECTED.values() for k in v]
    covered = sum(1 for k in keys_all if by_key.get(k))
    check("6-8", "Вес каждой записи не меньше 1", all(r["вес"] >= 1 for r in rows), f"записей: {len(rows)}")

    # ---------------- HTML-блоки ----------------
    def records_table(rr):
        if not rr:
            return ""
        body = "".join(
            f"<tr><td>{esc(r['dt'].strftime('%H:%M:%S'))}</td><td class='n'>{r['сеанс']}</td><td><code>{esc(r['ключ'])}</code></td>"
            f"<td class='n'>{fmt(r['время_с'])}</td><td class='n'>{fmt(r['вес'], 0)}</td><td>{'<b class=no>да</b>' if r['ошибка'] else ''}</td>"
            f"<td>{esc(r['комментарий'])}</td></tr>" for r in sorted(rr, key=lambda r: (r["dt"], r["начало_мс"])))
        return (f"<details><summary>Записи регистра \"Замеры времени\": {len(rr)}</summary><div class='box scroll'><table>"
                f"<tr><th>Записано</th><th>Сеанс</th><th>Ключ</th><th>Время, с</th><th>Вес</th><th>Ошибка</th><th>Комментарий</th></tr>"
                f"{body}</table></div></details>")

    def checks_table(row):
        items = checks.get(row, [])
        return ("<div class='box'><table><tr><th>Итог</th><th>Проверка</th><th>Факт</th></tr>" + "".join(
            f"<tr class='{'ok' if ok else 'bad'}'><td><b class='{'yes' if ok else 'no'}'>{'✓ да' if ok else '✗ нет'}</b></td>"
            f"<td>{esc(n)}</td><td>{esc(f)}</td></tr>" for n, ok, f in items) + "</table></div>")

    def key_sum_items(prefix, row, strip):
        agg = collections.OrderedDict()
        for r in sorted((r for r in rows if r["строка"] == row and r["ключ"].startswith(prefix)), key=lambda r: r["ключ"]):
            a = agg.setdefault(r["ключ"], [0.0, 0.0, 0])
            a[0] += r["время_с"]
            a[1] += r["вес"]
            a[2] += 1
        return [(k.replace(strip, ""), v[0], f"{k}: записей {v[2]}, время {fmt(v[0])} с, вес {fmt(v[1], 0)}, "
                 f"{fmt(v[0] / v[1] * 1000 if v[1] else 0, 2)} мс на единицу веса", "s1", f"вес {fmt(v[1], 0)}")
                for k, v in agg.items()]

    # обзор
    per_row = collections.Counter(r["строка"] for r in rows)
    overview = hbar([(f"Строка {n}: {name}", per_row.get(n, 0), f"Строка {n}: {per_row.get(n, 0)} записей", "s1", "")
                     for n, name, _ in ROWS] + [("Строки 6-8: пакет и операции после обмена", per_row.get("6-8", 0),
                                                 "Записи пакета целиком и операций после обмена", "s1", "")],
                    unit="записей", digits=0, label_w=380, note="Записи по строкам")
    cov_rows = "".join(
        f"<tr class='{'ok' if by_key.get(k) else 'bad'}'><td>{esc(n)}</td><td><code>{esc(k)}</code></td>"
        f"<td class='n'>{len(by_key.get(k, []))}</td><td><b class='{'yes' if by_key.get(k) else 'no'}'>{'✓ есть' if by_key.get(k) else '✗ нет'}</b></td></tr>"
        for n, ks in EXPECTED.items() for k in ks)

    # строка 6: таймлайн и сравнение времени
    meas_pk = [p for p in packets if a_tests.get("meas") and "начало" in a_tests["meas"]
               and datetime.datetime.fromisoformat(a_tests["meas"]["начало"]) <= p["dt"] <= datetime.datetime.fromisoformat(a_tests["meas"]["окончание"]) + datetime.timedelta(seconds=1)]
    if not meas_pk:
        meas_pk = [p for p in pos_packets if kind_of(p)[1] in ("позиция", "флаги", "служебный")]
    tl_svg, lanes, tl_span = timeline(meas_pk, sec_by_packet, local, kind_of) if meas_pk else ("", 0, 0)
    summ = data.get("сводки_стенда", {})
    call_groups = [(k, [summ.get("meas", {}).get("по_видам", {}).get(k, {}).get("всего_с"),
                        summ.get("base", {}).get("по_видам", {}).get(k, {}).get("всего_с")]) for k in CALL_KINDS]
    call_chart = grouped_hbar(call_groups, [("с FO_KeyOpsPerf", "s1"), ("без FO_KeyOpsPerf", "s2")], unit="с")
    tot_m = sum(v.get("всего_с", 0) for v in summ.get("meas", {}).get("по_видам", {}).values())
    tot_b = sum(v.get("всего_с", 0) for v in summ.get("base", {}).get("по_видам", {}).values())
    reg_items = [x for x in key_sum_items("ОбменБэкОфис.РегистрыСведений.", "6", "ОбменБэкОфис.РегистрыСведений.")]
    cat_items = key_sum_items("ОбменБэкОфис.Справочники.", "7", "ОбменБэкОфис.Справочники.")
    doc_items = [(f"{r['ключ'].replace('ОбменБэкОфис.Документы.', '')} {r['dt'].strftime('%H:%M:%S')}", r["время_с"],
                  f"{r['ключ']}: {r['комментарий']}", "s1", f"вес {fmt(r['вес'], 0)}") for r in sorted(
        (r for r in rows if r["строка"] == "8"), key=lambda r: r["dt"])]

    # строка 15
    step_items = [(r["ключ"].replace("ИсполнениеСделок.", "") if r["ключ"] != "ИсполнениеСделок" else "итог", r["время_с"],
                   f"{r['ключ']}: {r['комментарий']}", "s1", f"вес {fmt(r['вес'], 0)}") for r in sorted(rd, key=lambda r: r["ключ"])]
    e_rows = "".join(
        f"<tr><td>{esc(lbl)}</td><td>{esc(t['дата'])}</td><td>{'да' if any(x['активно'] for x in t['расширения'] if x['имя'] == 'FO_KeyOpsPerf') else '<b class=no>нет</b>'}</td>"
        f"<td class='n'>{t['до']['строк_остатка']} -> {t['после']['строк_остатка']}</td><td class='n'>{t['до']['документов']} -> {t['после']['документов']}</td>"
        f"<td class='n'>{t['после']['проведено']}</td><td class='n'>{len(window(t, 'ИсполнениеСделок'))}</td></tr>"
        for lbl, t in (("с замерами", e["с_замерами"]), ("повторный запуск", e["повторный_запуск"]), ("без замеров", e["без_замеров"])))

    # строка 2
    var_items = []
    for t in p_tests:
        rr = p_rows[(t["вариант"], t["метка"])]
        lbl = f"{t['вариант']}" + (" (без FO_KeyOpsPerf)" if t["метка"] == "без_замеров" else "")
        if rr:
            r = rr[0]
            var_items.append((lbl, r["время_с"], f"{lbl}: {r['комментарий']}", "crit" if r["ошибка"] else "s1",
                              ("вес " + fmt(r["вес"], 0)) + (", ⚠ ошибка" if r["ошибка"] else "")))
        else:
            var_items.append((lbl, 0.0, f"{lbl}: замер не пишется (расширение выключено), задание {t['задание']['длительность_с']} с",
                              "muted", "записи нет"))

    # строка 17
    pack_items = [(r["ключ"].replace("УпаковкаДанных.", "") if r["ключ"] != "УпаковкаДанных" else "итог", r["время_с"],
                   f"{r['ключ']}: {r['комментарий']}", "s1", "") for r in sorted(ru, key=lambda r: (r["ключ"] != "УпаковкаДанных", r["ключ"]))]
    hist_items = []
    if os.path.exists(STAGE3_FULL_PACKING):
        with open(STAGE3_FULL_PACKING, encoding="utf-8") as f:
            hist = [r for r in json.load(f)["замеры"] if r["ключ"].startswith("УпаковкаДанных") and r["время_с"] > 0.2
                    and "Активных торговых дат: 7" not in str(r["комментарий"])]
        hist_items = [(r["ключ"].replace("УпаковкаДанных.", "") if r["ключ"] != "УпаковкаДанных" else "итог", r["время_с"] / 60,
                       f"{r['ключ']}: {fmt(r['время_с'], 1)} с", "s1", "") for r in sorted(hist, key=lambda r: -r["время_с"])]

    all_checks = [c for v in checks.values() for c in v]
    all_ok = all(ok for _, ok, _ in all_checks)
    ext_now = ", ".join(f"{x['имя']} {x['версия']}" for x in data.get("расширения", []))

    def row_block(n, title, obj, what, rule, charts, extra=""):
        rr = [r for r in rows if r["строка"] == n]
        oks = sum(1 for _, ok, _ in checks.get(n, []) if ok)
        return f"""
<section id="r{n.replace('-', '_')}">
<h2><span class="num">{esc(n)}</span>{esc(title)}</h2>
<div class="cols"><div><div class="k">Перехват</div><div><code>{esc(obj)}</code></div></div>
<div><div class="k">Записей</div><div>{len(rr)}</div></div><div><div class="k">Проверок пройдено</div><div>{oks} из {len(checks.get(n, []))}</div></div></div>
<div class="grid2"><div><h3>Что тестировали</h3>{what}</div><div><h3>Как пишется замер</h3>{rule}</div></div>
{charts}
{extra}
<h3>Проверки</h3>{checks_table(n)}
{records_table(rr)}
</section>"""

    tests_desc = {
        "6": "<ul><li>Выгрузка остатков штатной обработкой МО ПРОД: 450 тестовых портфелей, 5 параллельных потоков, на каждый пакет вызовы 754 / 768 / 872, удаление блокировок, запуск перерасчета РСА.</li><li>Та же выгрузка с выключенным FO_KeyOpsPerf; снимки данных ФО после обеих выгрузок сверяются.</li><li>Котировки (регистр ФинансовыеПоказателиОблигаций).</li></ul>",
        "7": "<ul><li>Выгрузка 10 тестовых мандатов и 20 счетов штатной обработкой МО (справочники Портфели, Стратегии, Контрагенты, МестаХранения, Субпортфели).</li><li>Пакет веб-сервиса с тремя контрагентами, у одного два аффилированных лица.</li></ul>",
        "8": "<ul><li>Выгрузка котировок 3 тестовых бумаг штатной обработкой МО (один документ на все бумаги).</li><li>Два пакета веб-сервиса с тестовыми сделками (4 сделки по 3 портфелям, портфели в табличной части РаспределениеПоПортфелям) - данные для строки 15.</li></ul>",
        "15": "<ul><li>Регламентный путь (фоновое задание с методом АванкорВыполнениеРегламентныхЗаданий.ИсполнениеСделок) по набору сделок на 05.10.2026.</li><li>Повторный запуск на ту же дату.</li><li>Такой же набор на 06.10.2026 - запуск с выключенным FO_KeyOpsPerf; документы исполнения двух наборов сверяются построчно.</li><li>Ручной путь (обработка, как из формы) с пустой таблицей.</li></ul>",
        "2": "<ul><li>Фоновое задание ПроверкаПоЛимитам с временной настройкой рассылки по лимитам: пустая настройка; 2 портфеля, временно неактивные; 20 портфелей на дату без позиции (отказ); 20 портфелей на 29.09.2026 с тестовой настройкой рассылки писем (очередь рассылки) и без нее.</li><li>Успех и рассылка - еще раз с выключенным FO_KeyOpsPerf; строки результата проверки сверяются.</li></ul>",
        "17": "<ul><li>Фоновое задание УпаковкаДанных с расширением и без; число активных торговых дат 7 задано документом настроек торговой части, поэтому выполняется и сокращение пяти регистров обмена.</li><li>Для сравнения на диаграмме - штатная упаковка 02.10.2026 с архивацией накопленных проверок лимитов (этап 3).</li></ul>",
    }
    rules = {
        "6": "<p>Ключ <code>ОбменБэкОфис.РегистрыСведений.&lt;раздел XDTO&gt;</code>, одна запись на непустой раздел пакета. Вес - разные портфели раздела, без портфеля - строки. Комментарий <code>Строк; Портфелей; Пакет: УИД</code>. Пакет целиком - <code>ОбменБэкОфис.Пакет</code>, вес - разные портфели пакета, признак ошибки при коде ответа не 0.</p>",
        "7": "<p>Ключ <code>ОбменБэкОфис.Справочники.&lt;раздел&gt;</code>. Портфели - вес по элементам (договорам); Субпортфели, МестаХранения - разные портфели; прочие - элементы. Второй проход по контрагентам - <code>.АффилированныеЛица</code>, только контрагенты с аффилированными лицами.</p>",
        "8": "<p>Ключ <code>ОбменБэкОфис.Документы.&lt;раздел&gt;</code>. Документы с портфелем - разные портфели (у сделок - из РаспределениеПоПортфелям); котировки - число котировок, в комментарии <code>Котировок</code>.</p>",
        "15": "<p>Ключи <code>ИсполнениеСделок</code>, <code>.ЗаполнитьТаблицуСделок</code> (только регламентный запуск), <code>.Проведение</code>. Вес - разные портфели таблицы сделок. Комментарий <code>Строк; Сделок; Портфелей; Запуск</code>, строка - остаток плановой позиции по сделке (бумага или деньги).</p>",
        "2": "<p>Ключ <code>ПроверкаЛимитов.ПостКонтроль</code> на всю процедуру, включая постановку в очередь рассылки; пишется и при досрочном выходе. Вес - портфели проверки (нет портфелей - 1). Признак ошибки - отказ проверки или пустая настройка.</p>",
        "17": "<p>Ключи <code>УпаковкаДанных</code> и шаги <code>.КэшВмОписания</code>, <code>.ОчиститьСлужебныеКэши</code>, <code>.ОчиститьДанныеНеактивныхСеансов</code>, <code>.Сократить.&lt;регистр&gt;</code> (5, при заданном числе активных торговых дат). Вес 1, комментарий <code>Активных торговых дат</code>.</p>",
    }
    legend_tl = ("<div class='legend'><span><i class='sw s1'></i>позиция</span><span><i class='sw s2'></i>только флаги</span>"
                 "<span><i class='sw svc'></i>служебный (удаление блокировок, перерасчет)</span></div>")
    blocks = [
        row_block("6", "Загрузка позиций портфелей из МО", "ОбменДаннымиБэкОфис.ОбработатьДанные_РегистрыСведений, ЗагрузитьПакет", tests_desc["6"], rules["6"],
                  f"<h3>Пакеты выгрузки 450 портфелей во времени</h3><p class='lead'>Каждый вызов веб-сервиса - свой сеанс ФО; дорожки - пересечение интервалов замеров пакетов. "
                  f"Одновременно до {lanes} пакетов, {fmt(tl_span, 1)} с. Наведите на полосу - разделы пакета.</p>{legend_tl}{tl_svg}"
                  f"<h3>Время раздела регистра, сумма за прогон</h3><p class='lead'>ДополнительныеСведения пишет FO_PositionLoadOpt (IMDEV-9532) в обеих выгрузках - с FO_KeyOpsPerf и без.</p>{hbar(reg_items, label_w=320)}"
                  f"<h3>Время вызовов веб-сервиса ФО: с расширением и без</h3><p class='lead'>По логу веб-сервиса ФО, сумма по виду вызова. Всего: с FO_KeyOpsPerf "
                  f"{fmt(tot_m, 1)} с, без - {fmt(tot_b, 1)} с ({(tot_m - tot_b) / tot_b * 100 if tot_b else 0:+.1f}%), разброс одной конфигурации между прогонами - до 10%.</p>{call_chart}"),
        row_block("7", "Загрузка справочных данных из МО", "ОбменДаннымиБэкОфис.ОбработатьДанные_Справочники", tests_desc["7"], rules["7"],
                  f"<h3>Время раздела справочника, сумма за прогон</h3>{hbar(cat_items, label_w=260)}"),
        row_block("8", "Загрузка документов из МО", "ОбменДаннымиБэкОфис.ОбработатьДанные_Документы", tests_desc["8"], rules["8"],
                  f"<h3>Записи разделов документов</h3>{hbar(doc_items, label_w=330)}"),
        row_block("15", "Исполнение сделок", "ГрупповоеИсполнениеСделок.СоздатьДокументыИсполнения", tests_desc["15"], rules["15"],
                  f"<h3>Шаги исполнения 4 сделок (8 строк) по 3 портфелям</h3>{hbar(step_items, label_w=240)}"
                  f"<h3>Запуски и результат</h3><div class='box'><table><tr><th>Запуск</th><th>Дата поставки</th><th>FO_KeyOpsPerf</th><th>Строк остатка</th>"
                  f"<th>Документов исполнения</th><th>Проведено</th><th>Записей замера</th></tr>{e_rows}</table></div>"),
        row_block("2", "Постконтроль лимитов по всем портфелям", "ПроверкаЛимитовПоПортфелям.ПроверкаПоЛимитамПоРасписанию", tests_desc["2"], rules["2"],
                  f"<h3>Время процедуры по вариантам</h3><p class='lead'>Красным - запись с признаком ошибки (отказ проверки, пустая настройка), серым - прогон без расширения, запись не пишется.</p>"
                  f"{hbar(var_items, label_w=250)}"),
        row_block("17", "Упаковка данных", "АванкорВыполнениеРегламентныхЗаданий.УпаковкаДанных", tests_desc["17"], rules["17"],
                  f"<h3>Шаги упаковки в этом прогоне</h3>{hbar(pack_items, label_w=330)}"
                  + (f"<h3>Штатная упаковка с архивацией (02.10.2026, этап 3), минуты</h3><p class='lead'>64 проверки лимитов переведены в архив, удалено около 15 млн строк подробного кэша. "
                     f"Замер показывает, что почти все время занимает шаг КэшВмОписания.</p>{hbar(hist_items, unit='мин', digits=1, label_w=330)}" if hist_items else "")),
    ]
    # общие записи пакета и операций после обмена
    common = [r for r in rows if r["строка"] == "6-8"]
    pk_kinds = collections.Counter(kind_of(p)[1] for p in packets)
    common_block = f"""
<section id="r6_8"><h2><span class="num">6-8</span>Пакет обмена целиком и операции после обмена</h2>
<p class="lead">Общие для строк 6-8 записи: <code>ОбменБэкОфис.Пакет</code> - вся загрузка пакета (проверка, разделы, операции после обмена, лог
сервиса), <code>ОбменБэкОфис.ОперацииПослеОбмена</code> - внешняя обработка из константы "Операции после обмена". Пакетов в прогоне {len(packets)}:
{esc(', '.join(f'{k} {v}' for k, v in pk_kinds.items()))}.</p>
<h3>Проверки</h3>{checks_table('6-8')}{records_table(common)}</section>"""

    tests_rows = []
    for t in tests:
        kind = {"A": "выгрузка остатков", "B": "мандаты и счета", "C": "котировки", "пакет": "пакет веб-сервиса", "E": "исполнение сделок",
                "M": "исполнение вручную", "P": "постконтроль", "U": "упаковка данных"}.get(t["тест"], t["тест"])
        label = t.get("метка") or t.get("вариант") or ""
        if t["тест"] == "P":
            label = f"{t['вариант']}, {t['метка'].replace('_', ' ')}"
        ext = next((x for x in t.get("расширения", []) if x["имя"] == "FO_KeyOpsPerf"), {})
        state = t.get("задание", {}).get("состояние") or (f"код ответа {t.get('код_ответа')}" if t["тест"] == "пакет" else f"код {t.get('код', 0)}")
        n = len(window(t)) if "начало" in t else "-"
        tests_rows.append(f"<tr><td>{esc(t.get('начало', '')[11:19])}</td><td>{esc(kind)}</td><td>{esc(label)}</td>"
                          f"<td>{'да' if ext.get('активно', True) else '<b class=no>нет</b>'}</td><td>{esc(state)}</td><td class='n'>{n}</td></tr>")
    fails = data.get("сбои", [])
    fails_note = (f"<div class='note'><b>Повторы выгрузки.</b> {len(fails)} запуска выгрузки остатков прерывались до отправки пакетов: сеанс МО получал "
                  f"\"недостаточно прав\" на чтение справочника СчетаМандатов. Известная нестабильность пула сеансов МО на стенде, происходит и без расширения; "
                  f"в ФО эти запуски не дошли и в протокол не включены.</div>") if fails else ""

    page = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Тест FO_KeyOpsPerf</title>
<style>
:root {{ color-scheme: light; --bg:#f9f9f7; --card:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --line:#e1e0d9; --axis:#c3c2b7;
  --head:#1d3557; --soft:#f0efec; --code:#f0efec; --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100; --s5:#e87ba4;
  --good:#0ca30c; --good-ink:#006300; --crit:#d03b3b; --ok-bg:#e9f7ef; --bad-bg:#fdecec; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ color-scheme: dark; --bg:#0d0d0d; --card:#1a1a19; --ink:#ffffff; --ink2:#c3c2b7;
  --line:#2c2c2a; --axis:#383835; --head:#22324a; --soft:#262624; --code:#262624; --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500;
  --s5:#d55181; --good-ink:#0ca30c; --ok-bg:#13261a; --bad-bg:#2f1a1a; }} }}
:root[data-theme="dark"] {{ color-scheme: dark; --bg:#0d0d0d; --card:#1a1a19; --ink:#ffffff; --ink2:#c3c2b7; --line:#2c2c2a; --axis:#383835;
  --head:#22324a; --soft:#262624; --code:#262624; --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181; --good-ink:#0ca30c;
  --ok-bg:#13261a; --bad-bg:#2f1a1a; }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:var(--bg); color:var(--ink); font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }}
.wrap {{ max-width:1180px; margin:0 auto; padding:24px 16px 40px; }}
h1 {{ margin:0 0 8px; font-size:24px; }} h2 {{ margin:0 0 12px; font-size:19px; display:flex; align-items:center; gap:10px; }}
h3 {{ margin:18px 0 8px; font-size:15px; }} .lead {{ color:var(--ink2); margin:0 0 8px; }}
section {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px 18px 12px; margin:18px 0; }}
.num {{ background:var(--head); color:#fff; border-radius:8px; padding:2px 10px; font-size:15px; }}
.verdict {{ margin:16px 0; padding:12px 16px; border-radius:10px; font-weight:600; border:1px solid var(--line);
  background:{'var(--ok-bg)' if all_ok else 'var(--bad-bg)'}; color:{'var(--good-ink)' if all_ok else 'var(--crit)'}; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin:12px 0; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px 16px; }}
.card b {{ display:block; font-size:26px; line-height:1.15; }} .card span {{ color:var(--ink2); font-size:12.5px; }}
.cols {{ display:flex; flex-wrap:wrap; gap:24px; margin:0 0 6px; }} .k {{ color:var(--muted); font-size:12px; }}
.grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }} @media (max-width:760px) {{ .grid2 {{ grid-template-columns:1fr; }} }}
.box {{ border:1px solid var(--line); border-radius:10px; overflow:auto; }} .scroll {{ max-height:460px; }}
table {{ border-collapse:collapse; width:100%; }} th, td {{ padding:6px 10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
th {{ background:var(--head); color:#fff; font-weight:600; font-size:12.5px; position:sticky; top:0; }}
td.n {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
code {{ font-family:Consolas,monospace; font-size:12px; background:var(--code); padding:0 4px; border-radius:4px; }}
tr.ok td:first-child {{ box-shadow:inset 4px 0 var(--good); }} tr.bad td:first-child {{ box-shadow:inset 4px 0 var(--crit); }}
b.yes {{ color:var(--good-ink); }} b.no {{ color:var(--crit); }}
details summary {{ cursor:pointer; color:var(--s1); margin:12px 0 6px; }}
.chart {{ width:100%; height:auto; display:block; }} .chart .lbl {{ font-size:12px; fill:var(--ink2); }} .chart .val {{ font-size:12px; fill:var(--ink); }}
.chart .axis {{ stroke:var(--axis); }} .chart .tick {{ stroke:var(--line); stroke-dasharray:2 3; }} .chart .tt, .chart .lane {{ font-size:10.5px; fill:var(--muted); }}
.chart .tt {{ text-anchor:middle; }} .hitbox {{ fill:transparent; }} .hit:hover .hitbox {{ fill:var(--soft); }}
.bar.s1 {{ fill:var(--s1); }} .bar.s2 {{ fill:var(--s2); }} .bar.s3 {{ fill:var(--s3); }} .bar.s4 {{ fill:var(--s4); }} .bar.s5 {{ fill:var(--s5); }}
.bar.svc, .bar.muted {{ fill:var(--muted); }} .bar.crit {{ fill:var(--crit); }} .bar.err {{ stroke:var(--crit); stroke-width:2; }}
.tl .bar {{ stroke:var(--card); stroke-width:1; }}
.legend {{ display:flex; gap:16px; flex-wrap:wrap; font-size:12.5px; color:var(--ink2); margin:6px 0; }}
.sw {{ display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:6px; vertical-align:-1px; }}
.sw.s1 {{ background:var(--s1); }} .sw.s2 {{ background:var(--s2); }} .sw.svc {{ background:var(--muted); }}
.note {{ border:1px solid var(--line); border-left:4px solid var(--s4); border-radius:8px; padding:10px 14px; margin:10px 0; background:var(--card); }}
nav {{ display:flex; flex-wrap:wrap; gap:8px; margin:10px 0; }} nav a {{ color:var(--s1); text-decoration:none; border:1px solid var(--line); border-radius:999px; padding:3px 12px; background:var(--card); }}
</style></head><body><div class="wrap">
<h1>Тестирование расширения FO_KeyOpsPerf: замеры ключевых операций ФО</h1>
<p class="lead">IMDEV-9530. Расширение добавляет замеры подсистемы БСП "Оценка производительности" для шести строк списка ключевых операций:
2, 6, 7, 8, 15, 17. Тестирование - разработческие базы: ФО (WIN_FO_server) и стенд МО-ФО IMDEV-9532. Все операции запускались штатными
механизмами (выгрузки МО, веб-сервис ФО, фоновые задания с методами регламентных заданий), каждая - с расширением и для сравнения без него.
Расширения: {esc(ext_now)}. Константа "Выполнять замеры производительности": {'включена' if data.get('замеры_включены') else 'выключена'}.
Прогон начат {esc(data['начало'].replace('T', ' '))}.</p>
<div class="verdict">{'✓ Все проверки пройдены' if all_ok else '✗ Есть непройденные проверки'}: ключей {covered} из {len(keys_all)}, проверок
{sum(1 for _, ok, _ in all_checks if ok)} из {len(all_checks)}; результат операций с расширением и без совпадает</div>
<div class="cards">
<div class="card"><b>{len(rows)}</b><span>записей в регистре "Замеры времени" за прогон</span></div>
<div class="card"><b>{len(by_key)}</b><span>ключей операций и шагов</span></div>
<div class="card"><b>{len(tests)}</b><span>запусков операций</span></div>
<div class="card"><b>{len(packets)}</b><span>пакетов обмена МО -> ФО</span></div>
<div class="card"><b>{snap.get('расхождений', '?')}</b><span>расхождений данных ФО после выгрузки с расширением и без</span></div>
</div>
<nav>{''.join(f"<a href='#r{n}'>Строка {n}</a>" for n, _, _ in ROWS)}<a href='#r6_8'>Пакет целиком</a><a href='#proto'>Протокол</a></nav>

<section><h2>Записи регистра по строкам списка</h2>{overview}
<details><summary>Покрытие ключей плана (Р4): {covered} из {len(keys_all)}</summary><div class='box'><table><tr><th>Строка</th><th>Ключ</th><th>Записей</th><th>Записан</th></tr>{cov_rows}</table></div></details>
</section>
{''.join(blocks)}
{common_block}
<section id="proto"><h2>Протокол запусков</h2>
<div class='box scroll'><table><tr><th>Начало</th><th>Операция</th><th>Вариант</th><th>FO_KeyOpsPerf</th><th>Состояние</th><th>Записей замеров</th></tr>{''.join(tests_rows)}</table></div>
{fails_note}
{''.join(f"<div class='note'><b>Примечание.</b> {esc(x)}</div>" for x in data.get("примечания", []))}
{f"<div class='note'><b>Повторенные запуски.</b> {len(excluded)} записей строк 2, 15, 17 относятся к запускам, повторенным после исправления сценария, и в отчет не включены: первые запуски 'без расширения' шли из сеанса, открытого до выключения FO_KeyOpsPerf (фоновое задание получает расширения сеанса-инициатора, поэтому замеры писались), первая упаковка - при непроведенном документе настроек торговой части. Повтор - из нового сеанса после выключения.</div>" if excluded else ""}
<div class="note"><b>Тестовые данные</b> (сделки T9530, контрагенты T9530_K1..K3, настройка рассылки "T9530 тест рассылки", документ настроек торговой части с 7 активными
торговыми датами) остаются в разработческой базе. Поле Замер регистра КэшВмКратко - собственный хронометраж проверки лимитов (мс на строку) - в сверке
результата проверки не участвует.</div>
<p class="lead">Источник: {esc(os.path.relpath(run_dir, TASK))}\\measurements.json; время записи - локальное время сервера ФО.</p>
</section>
</div></body></html>"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(OUT)
    for row in ["6-8", "6", "7", "8", "15", "2", "17"]:
        for n, ok, fact in checks.get(row, []):
            print("OK  " if ok else "FAIL", row, n, "|", str(fact)[:160])
    print("покрытие", covered, len(keys_all))


if __name__ == "__main__":
    main()
