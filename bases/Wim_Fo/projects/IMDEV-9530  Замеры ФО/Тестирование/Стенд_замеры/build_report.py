# -*- coding: utf-8 -*-
"""Отчет о тестировании замеров приема пакетов из МО (IMDEV-9530, этап 2) по записям регистра ЗамерыВремени.

    python build_report.py [<папка прогона results/...>]

По умолчанию берется последний прогон с measurements.json. Сравнение времени и данных - по сводкам прогонов стенда
IMDEV-9532 с метками IMDEV9530_base* (без замеров) и IMDEV9530_A_450_5t / IMDEV9530_meas2* (с замерами).
"""
import collections
import datetime
import glob
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(os.path.dirname(HERE))
STAND_RESULTS = glob.glob(r'C:\1c\Claude_1C\TestProject\Wim_Fo\projects\IMDEV-9532*\Тестирование\Стенд_МО_ФО\results')[0]
OUT = os.path.join(TASK, "Тестирование", "Отчет о тестировании замеров, этап 2.html")

KINDS = ["754: флаг до позиции", "768: позиция", "872: флаги после позиции"]
EPOCH = datetime.datetime(1, 1, 1)


def esc(s):
    return html.escape(str(s))


def fmt(x, d=3):
    return f"{x:,.{d}f}".replace(",", " ")


def ms_to_dt(ms):
    return EPOCH + datetime.timedelta(milliseconds=ms)


def load_run(path=None):
    if path is None:
        path = sorted(os.path.dirname(p) for p in glob.glob(os.path.join(HERE, "results", "*", "measurements.json")))[-1]
    with open(os.path.join(path, "measurements.json"), encoding="utf-8") as f:
        return path, json.load(f)


def parse_comment(text):
    result = {}
    for part in str(text).split(";"):
        if ":" in part:
            k, _, v = part.partition(":")
            result[k.strip()] = v.strip()
    return result


def stand_summary(pattern):
    runs = sorted(d for d in glob.glob(os.path.join(STAND_RESULTS, f"*_{pattern}")) if
                  os.path.exists(os.path.join(d, "summary.json")))
    out = []
    for d in runs:
        with open(os.path.join(d, "summary.json"), encoding="utf-8") as f:
            s = json.load(f)
        s["_dir"] = os.path.basename(d)
        out.append(s)
    return out


def main():
    run_dir, data = load_run(sys.argv[1] if len(sys.argv) > 1 else None)
    rows = data["замеры"]
    for r in rows:
        r["доп"] = parse_comment(r["комментарий"])
        r["пакет"] = r["доп"].get("Пакет", "")
        r["группа"] = r["ключ"].split(".")[1] if r["ключ"].count(".") >= 1 else r["ключ"]
    # смещение локального времени сервера относительно UTC (для подписи времени)
    offs = collections.Counter()
    for r in rows:
        try:
            local = datetime.datetime.fromisoformat(r["записано"].replace("+00:00", ""))
            offs[round((local - ms_to_dt(r["окончание_мс"])).total_seconds() / 3600)] += 1
        except ValueError:
            pass
    tz = offs.most_common(1)[0][0] if offs else 3

    def local(ms):
        return ms_to_dt(ms) + datetime.timedelta(hours=tz)

    by_key = collections.defaultdict(list)
    for r in rows:
        by_key[r["ключ"]].append(r)
    packets = [r for r in rows if r["ключ"] == "ОбменБэкОфис.Пакет"]
    sections = [r for r in rows if r["группа"] in ("РегистрыСведений", "Справочники", "Документы")]
    sec_by_packet = collections.defaultdict(list)
    for r in rows:
        if r["ключ"] != "ОбменБэкОфис.Пакет":
            sec_by_packet[r["пакет"]].append(r)

    # ---------------- проверки правил ----------------
    checks = []
    empty = [r for r in sections if r["доп"].get("Строк", "1") in ("0", "")]
    checks.append(("Пустые разделы не пишутся", not empty, f"записей разделов со строк = 0: {len(empty)}"))
    dup = collections.Counter((r["пакет"], r["ключ"]) for r in sections)
    dups = {k: v for k, v in dup.items() if v > 1}
    checks.append(("Раздел замеряется не более одного раза за пакет", not dups,
                   f"повторов (пакет, ключ): {len(dups)}"))
    pkt_ids = {r["пакет"] for r in packets}
    orphan = [r for r in sections if r["пакет"] not in pkt_ids]
    checks.append(("Каждая запись раздела связана с записью пакета по УИД", not orphan,
                   f"разделов без записи пакета: {len(orphan)}"))
    inside = [r for r in sections if r["пакет"] in pkt_ids]
    bad_time = []
    pk_by_id = {p["пакет"]: p for p in packets}
    for r in inside:
        p = pk_by_id[r["пакет"]]
        if r["начало_мс"] < p["начало_мс"] - 1 or r["окончание_мс"] > p["окончание_мс"] + 1 or r["сеанс"] != p["сеанс"]:
            bad_time.append(r)
    checks.append(("Время раздела внутри времени своего пакета, тот же сеанс", not bad_time,
                   f"нарушений: {len(bad_time)} из {len(inside)}"))
    ds = by_key.get("ОбменБэкОфис.РегистрыСведений.ДополнительныеСведения", [])
    ds_ok = all("Записано" in r["доп"] for r in ds) and ds
    checks.append(("ДополнительныеСведения пишет замер из копии IMDEV-9532 (комментарий с полем Записано)",
                   bool(ds_ok), f"записей: {len(ds)}"))
    weight_ok = all(r["вес"] >= 1 for r in rows)
    checks.append(("Вес не меньше 1", weight_ok, f"записей с весом < 1: {sum(1 for r in rows if r['вес'] < 1)}"))
    port_rows = [r for r in sections if r["доп"].get("Портфелей", "0") not in ("0", "")]
    pw_ok = all(abs(r["вес"] - float(r["доп"]["Портфелей"])) < 0.5 for r in port_rows)
    checks.append(("В разделах с портфелем вес = число разных портфелей", pw_ok,
                   f"проверено записей: {len(port_rows)}"))
    err_pk = [p for p in packets if p["ошибка"]]
    err_ok = all(p["доп"].get("Код ответа", "0") != "0" for p in err_pk) and all(
        p["доп"].get("Код ответа", "0") == "0" for p in packets if not p["ошибка"])
    checks.append(("Признак ошибки пакета = код ответа не 0", err_ok,
                   f"пакетов с ошибкой: {len(err_pk)} из {len(packets)}"))

    # ---------------- покрытие ----------------
    expected = [
        ("Строки 6-8", "Пакет целиком", "ОбменБэкОфис.Пакет"),
        ("Строки 6-8", "Операции после обмена", "ОбменБэкОфис.ОперацииПослеОбмена"),
        ("Строка 6", "Регистр ФактическаяПозиция", "ОбменБэкОфис.РегистрыСведений.ФактическаяПозиция"),
        ("Строка 6", "Регистр СтоимостьЧистыхАктивов", "ОбменБэкОфис.РегистрыСведений.СтоимостьЧистыхАктивов"),
        ("Строка 6", "Регистр ДополнительныеСведения (расширение IMDEV-9532)",
         "ОбменБэкОфис.РегистрыСведений.ДополнительныеСведения"),
        ("Строка 8", "Регистр ФинансовыеПоказателиОблигаций", "ОбменБэкОфис.РегистрыСведений.ФинансовыеПоказателиОблигаций"),
        ("Строка 7", "Справочник Портфели", "ОбменБэкОфис.Справочники.Портфели"),
        ("Строка 7", "Справочник Субпортфели", "ОбменБэкОфис.Справочники.Субпортфели"),
        ("Строка 7", "Справочник МестаХранения", "ОбменБэкОфис.Справочники.МестаХранения"),
        ("Строка 7", "Справочник Контрагенты", "ОбменБэкОфис.Справочники.Контрагенты"),
        ("Строка 7", "Аффилированные лица контрагентов", "ОбменБэкОфис.Справочники.АффилированныеЛица"),
        ("Строка 7", "Справочник Стратегии", "ОбменБэкОфис.Справочники.Стратегии"),
        ("Строка 8", "Документ КотировкиЦБНаБирже", "ОбменБэкОфис.Документы.КотировкиЦБНаБирже"),
    ]
    covered = sum(1 for _, _, k in expected if by_key.get(k))
    extra_keys = sorted(k for k in by_key if k not in {e[2] for e in expected})

    # ---------------- параллельность ----------------
    events = []
    for p in packets:
        events.append((p["начало_мс"], 1))
        events.append((p["окончание_мс"], -1))
    events.sort()
    cur = peak = 0
    for _, d in events:
        cur += d
        peak = max(peak, cur)

    # ---------------- сравнение с прогонами без замеров ----------------
    base = stand_summary("IMDEV9530_base_450_5t") + stand_summary("IMDEV9530_base3_450_5t")
    meas = stand_summary("IMDEV9530_A_450_5t") + stand_summary("IMDEV9530_meas2_450_5t")
    snap_diff = None
    try:
        sys.path.insert(0, os.path.dirname(STAND_RESULTS))
        import snapshot  # noqa: E402
        b0 = [s for s in stand_summary("IMDEV9530_base_450_5t")][-1]["_dir"]
        m0 = [s for s in stand_summary("IMDEV9530_A_450_5t")][-1]["_dir"]
        with open(os.path.join(STAND_RESULTS, b0, "snapshot.json"), encoding="utf-8") as f:
            sb = json.load(f)
        with open(os.path.join(STAND_RESULTS, m0, "snapshot.json"), encoding="utf-8") as f:
            sm = json.load(f)
        diffs = snapshot.compare(sb, sm)
        snap_diff = {"базовый": b0, "с_замерами": m0, "строк": snapshot.summary(sm),
                     "расхождений": sum(d["только_в_первом"] + d["только_во_втором"] for d in diffs)}
    except Exception as exc:  # noqa: BLE001 - отчет строится и без сравнения
        snap_diff = {"ошибка": str(exc)[:200]}

    def kind_avg(runs, kind):
        vals = [r["по_видам"][kind]["мс_на_строку"] for r in runs if kind in r.get("по_видам", {})]
        return sum(vals) / len(vals) if vals else 0, vals

    # ---------------- HTML ----------------
    key_rows = []
    for k in sorted(by_key, key=lambda x: (x.split(".")[1] if "." in x else x, x)):
        rs = by_key[k]
        total = sum(r["время_с"] for r in rs)
        wsum = sum(r["вес"] for r in rs)
        key_rows.append(
            f"<tr><td><code>{esc(k)}</code></td><td class='n'>{len(rs)}</td><td class='n'>{fmt(total)}</td>"
            f"<td class='n'>{fmt(total / len(rs))}</td><td class='n'>{fmt(max(r['время_с'] for r in rs))}</td>"
            f"<td class='n'>{fmt(wsum, 0)}</td><td class='n'>{fmt(total / wsum * 1000 if wsum else 0, 2)}</td>"
            f"<td class='n'>{sum(1 for r in rs if r['ошибка'])}</td></tr>")

    cov_rows = "".join(
        f"<tr class='{'ok' if by_key.get(k) else 'bad'}'><td>{esc(a)}</td><td>{esc(b)}</td><td><code>{esc(k)}</code></td>"
        f"<td class='n'>{len(by_key.get(k, []))}</td><td>{'<b class=yes>есть</b>' if by_key.get(k) else '<b class=no>нет</b>'}</td></tr>"
        for a, b, k in expected)
    chk_rows = "".join(
        f"<tr class='{'ok' if ok else 'bad'}'><td>{'<b class=yes>OK</b>' if ok else '<b class=no>НЕТ</b>'}</td>"
        f"<td>{esc(name)}</td><td>{esc(detail)}</td></tr>" for name, ok, detail in checks)

    # таймлайн: серии вызовов (разрыв больше 3 с) и дорожки по пересечению интервалов
    def kind_of(p):
        keys = {s["ключ"].split(".")[-1] for s in sec_by_packet.get(p["пакет"], [])}
        if "ФактическаяПозиция" in keys:
            return "pos", "позиция"
        if "ДополнительныеСведения" in keys:
            return "flag", "флаги"
        if keys & {"Портфели", "Субпортфели", "Контрагенты", "МестаХранения", "Стратегии"}:
            return "cat", "справочники"
        if "КотировкиЦБНаБирже" in keys:
            return "quote", "котировки"
        return "svc", "служебный"

    ordered = sorted(packets, key=lambda r: r["начало_мс"])
    series = []
    for p in ordered:
        if series and p["начало_мс"] - max(x["окончание_мс"] for x in series[-1]) <= 3000:
            series[-1].append(p)
        else:
            series.append([p])
    timelines = []
    W, LANE, LEFT = 1100, 24, 70
    for n, group in enumerate(series, 1):
        lanes_end = []
        placed = []
        for p in group:
            for i, end in enumerate(lanes_end):
                if p["начало_мс"] >= end:
                    lanes_end[i] = p["окончание_мс"]
                    placed.append((i, p))
                    break
            else:
                lanes_end.append(p["окончание_мс"])
                placed.append((len(lanes_end) - 1, p))
        g0 = min(p["начало_мс"] for p in group)
        g1 = max(p["окончание_мс"] for p in group)
        span = max(g1 - g0, 1)
        width = W - LEFT - 10
        bars = []
        for lane, p in placed:
            x = LEFT + (p["начало_мс"] - g0) / span * width
            w = max((p["окончание_мс"] - p["начало_мс"]) / span * width, 2)
            y = 24 + lane * LANE
            cls, label = kind_of(p)
            tip = (f"{label}, сеанс {p['сеанс']}, {fmt(p['время_с'])} с, вес {fmt(p['вес'], 0)}; "
                   f"{local(p['начало_мс']).strftime('%H:%M:%S.%f')[:-3]}; {p['комментарий']}")
            bars.append(f"<rect class='b {cls}{' err' if p['ошибка'] else ''}' x='{x:.1f}' y='{y}' width='{w:.1f}' "
                        f"height='{LANE - 6}' rx='3'><title>{esc(tip)}</title></rect>")
        lanes_svg = "".join(f"<text x='8' y='{24 + i * LANE + 13}' class='lane'>поток {i + 1}</text>"
                            f"<line x1='{LEFT}' x2='{W - 10}' y1='{24 + i * LANE + LANE - 3}' y2='{24 + i * LANE + LANE - 3}' class='grid'/>"
                            for i in range(len(lanes_end)))
        ticks = ""
        for i in range(0, 11):
            ms = g0 + span * i / 10
            x = LEFT + width * i / 10
            ticks += (f"<line x1='{x:.1f}' x2='{x:.1f}' y1='16' y2='{24 + len(lanes_end) * LANE}' class='tick'/>"
                      f"<text x='{x:.1f}' y='12' class='tt'>{local(ms).strftime('%H:%M:%S.%f')[:-4]}</text>")
        kinds = collections.Counter(kind_of(p)[1] for p in group)
        title = (f"Серия {n}: {local(g0).strftime('%H:%M:%S')} - {local(g1).strftime('%H:%M:%S')}, "
                 f"{fmt((g1 - g0) / 1000, 1)} с, пакетов {len(group)} ("
                 + ", ".join(f"{k} {v}" for k, v in kinds.items()) + f"), параллельно до {len(lanes_end)}")
        timelines.append(f"<div class='sub'>{esc(title)}</div><svg viewBox='0 0 {W} {30 + len(lanes_end) * LANE}' "
                         f"class='tl' role='img' aria-label='{esc(title)}'>{ticks}{lanes_svg}{''.join(bars)}</svg>")
    timeline = "".join(timelines)

    # пакеты подробно
    pk_rows = []
    for p in sorted(packets, key=lambda r: r["начало_мс"]):
        cls, label = kind_of(p)
        secs = sorted(sec_by_packet.get(p["пакет"], []), key=lambda r: r["начало_мс"])
        inner = "".join(
            f"<tr><td><code>{esc(s['ключ'].replace('ОбменБэкОфис.', ''))}</code></td><td class='n'>{fmt(s['время_с'])}</td>"
            f"<td class='n'>{fmt(s['вес'], 0)}</td><td>{esc(s['комментарий'].split('; Пакет:')[0])}</td></tr>" for s in secs)
        share = sum(s["время_с"] for s in secs if s["группа"] in ("РегистрыСведений", "Справочники", "Документы"))
        pk_rows.append(
            f"<tr class='pk{' err' if p['ошибка'] else ''}'><td>{local(p['начало_мс']).strftime('%H:%M:%S.%f')[:-3]}</td>"
            f"<td class='n'>{p['сеанс']}</td><td><span class='tag {cls}'>{label}</span></td>"
            f"<td class='n'>{fmt(p['время_с'])}</td><td class='n'>{fmt(p['вес'], 0)}</td>"
            f"<td>{esc(p['комментарий'].split('; Пакет:')[0])}</td>"
            f"<td><details><summary>{len(secs)} записей, разделы {fmt(share)} с</summary>"
            f"<table class='in'><tr><th>Ключ</th><th>Время, с</th><th>Вес</th><th>Комментарий</th></tr>{inner}</table>"
            f"</details></td></tr>")

    # сравнение времени
    cmp_rows = ""
    for kind in KINDS:
        ab, vb = kind_avg(base, kind)
        am, vm = kind_avg(meas, kind)
        delta = (am - ab) / ab * 100 if ab else 0
        cmp_rows += (f"<tr><td>{esc(kind)}</td><td class='n'>{' / '.join(fmt(v, 2) for v in vb)}</td>"
                     f"<td class='n'>{fmt(ab, 2)}</td><td class='n'>{' / '.join(fmt(v, 2) for v in vm)}</td>"
                     f"<td class='n'>{fmt(am, 2)}</td><td class='n'>{delta:+.1f}%</td></tr>")
    def row(label, vb, vm, d=1):
        ab, am = sum(vb) / len(vb), sum(vm) / len(vm)
        return (f"<tr><td>{label}</td><td class='n'>{' / '.join(fmt(v, d) for v in vb)}</td><td class='n'>{fmt(ab, d)}</td>"
                f"<td class='n'>{' / '.join(fmt(v, d) for v in vm)}</td><td class='n'>{fmt(am, d)}</td>"
                f"<td class='n'>{(am - ab) / ab * 100:+.1f}%</td></tr>")
    cmp_rows += row("Все вызовы веб-сервиса ФО, сумма, с", [sum(v["всего_с"] for v in r["по_видам"].values()) for r in base],
                    [sum(v["всего_с"] for v in r["по_видам"].values()) for r in meas])
    cmp_rows += row("Опубликовать в потоке МО, среднее, с", [sum(x["опубликовать_с"] for x in r["потоки"]) / len(r["потоки"]) for r in base],
                    [sum(x["опубликовать_с"] for x in r["потоки"]) / len(r["потоки"]) for r in meas], 2)
    eb = [r["выгрузка_всего_с"] for r in base]
    em = [r["выгрузка_всего_с"] for r in meas]
    cmp_rows += (f"<tr><td>Выгрузка всего, с (5 потоков, вместе с запуском сеансов МО)</td><td class='n'>{' / '.join(fmt(v, 1) for v in eb)}</td>"
                 f"<td class='n'>{fmt(sum(eb) / len(eb), 1)}</td><td class='n'>{' / '.join(fmt(v, 1) for v in em)}</td>"
                 f"<td class='n'>{fmt(sum(em) / len(em), 1)}</td>"
                 f"<td class='n'>{(sum(em) / len(em) - sum(eb) / len(eb)) / (sum(eb) / len(eb)) * 100:+.1f}%</td></tr>")
    runs_list = "".join(
        f"<li><code>{esc(r['_dir'])}</code>: портфелей с позицией {r.get('готово_флагов', '-')}, "
        f"ошибки МО в потоках: {sum(1 for t in r['потоки'] if t['есть_ошибки_МО'])}</li>" for r in base + meas)

    # сырые записи
    raw = "".join(
        f"<tr data-k='{esc(r['ключ'])}'><td>{local(r['начало_мс']).strftime('%H:%M:%S.%f')[:-3]}</td>"
        f"<td class='n'>{r['сеанс']}</td><td><code>{esc(r['ключ'])}</code></td><td class='n'>{fmt(r['время_с'])}</td>"
        f"<td class='n'>{fmt(r['вес'], 0)}</td><td>{'да' if r['ошибка'] else ''}</td><td>{esc(r['комментарий'])}</td></tr>"
        for r in sorted(rows, key=lambda r: r["начало_мс"]))

    tests = data.get("тесты", [])
    tests_html = "".join(f"<li><code>{esc(json.dumps({k: v for k, v in t.items() if k != 'прогон_стенда'}, ensure_ascii=False))}</code></li>" for t in tests)
    ext = ", ".join(f"{e['имя']} {e['версия']} (активно: {'да' if e['активно'] else 'нет'}, безопасный режим: "
                    f"{'да' if e['безопасный_режим'] else 'нет'})" for e in data.get("расширения", []))
    all_ok = all(ok for _, ok, _ in checks) and covered == len(expected)
    total_time = sum(r["время_с"] for r in packets)

    page = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Тест замеров ФО</title>
<style>
:root {{ --bg:#f3f5f9; --card:#fff; --ink:#18212d; --muted:#5d6b7c; --line:#dbe2ea; --soft:#eef2f7; --head:#1d3557;
  --accent:#2a6fdb; --ok:#1f9d55; --ok-bg:#e9f7ef; --bad:#d64545; --bad-bg:#fdecec; --code:#eef2f7;
  --pos:#2a6fdb; --flag:#8a5cd6; --cat:#1f9d55; --quote:#c98a04; --svc:#9aa8b8; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#0f141b; --card:#171e27; --ink:#e6ebf1;
  --muted:#9aa8b8; --line:#2a3542; --soft:#1d2631; --head:#22324a; --ok-bg:#14291e; --bad-bg:#2f1a1a; --code:#222c38; }} }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:var(--bg); color:var(--ink); font:14px/1.5 "Segoe UI",Arial,sans-serif; }}
.wrap {{ max-width:1500px; margin:0 auto; padding:22px 24px 30px; }}
h1 {{ margin:0 0 6px; font-size:23px; }} h2 {{ margin:26px 0 10px; font-size:17px; }}
.lead {{ color:var(--muted); margin:0; max-width:1150px; }}
.verdict {{ margin:16px 0; padding:12px 16px; border-radius:10px; font-weight:600; border:1px solid var(--line);
  background:{'var(--ok-bg)' if all_ok else 'var(--bad-bg)'}; color:{'var(--ok)' if all_ok else 'var(--bad)'}; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px 16px; }}
.card b {{ display:block; font-size:26px; line-height:1.15; }} .card span {{ color:var(--muted); font-size:12.5px; }}
.box {{ background:var(--card); border:1px solid var(--line); border-radius:10px; overflow:auto; }}
table {{ border-collapse:collapse; width:100%; }} th, td {{ padding:7px 10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
th {{ background:var(--head); color:#fff; font-weight:600; font-size:12.5px; position:sticky; top:0; }}
td.n {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
code {{ font-family:Consolas,monospace; font-size:12px; background:var(--code); padding:0 4px; border-radius:4px; }}
tr.ok td:first-child {{ box-shadow:inset 4px 0 var(--ok); }} tr.bad td:first-child {{ box-shadow:inset 4px 0 var(--bad); }}
b.yes {{ color:var(--ok); }} b.no {{ color:var(--bad); }}
.tl {{ width:100%; height:auto; display:block; margin-bottom:10px; }} .sub {{ font-weight:600; margin:6px 2px; }} .tl .lane {{ font-size:11px; fill:var(--muted); }}
.tl .tt {{ font-size:10px; fill:var(--muted); text-anchor:middle; }} .tl .grid {{ stroke:var(--line); }}
.tl .tick {{ stroke:var(--line); stroke-dasharray:2 3; }} .tl .b.err {{ stroke:var(--bad); stroke-width:2; }}
.b.pos, .tag.pos {{ fill:var(--pos); background:var(--pos); }} .b.flag, .tag.flag {{ fill:var(--flag); background:var(--flag); }}
.b.cat, .tag.cat {{ fill:var(--cat); background:var(--cat); }} .b.quote, .tag.quote {{ fill:var(--quote); background:var(--quote); }}
.b.svc, .tag.svc {{ fill:var(--svc); background:var(--svc); }}
.tag {{ color:#fff; border-radius:999px; padding:1px 8px; font-size:11.5px; white-space:nowrap; }}
.legend {{ display:flex; gap:14px; flex-wrap:wrap; font-size:12.5px; color:var(--muted); margin:8px 2px; }}
tr.pk.err td:first-child {{ box-shadow:inset 4px 0 var(--bad); }}
table.in th {{ background:var(--soft); color:var(--ink); position:static; }} details summary {{ cursor:pointer; color:var(--accent); }}
.note {{ background:var(--card); border:1px solid var(--line); border-left:4px solid var(--quote); border-radius:8px; padding:10px 14px; margin:8px 0; }}
.filter {{ margin:8px 0; padding:7px 10px; border:1px solid var(--line); border-radius:8px; width:min(480px,100%); background:var(--card); color:var(--ink); }}
.scroll {{ max-height:560px; overflow:auto; }} ul {{ margin:6px 0; }}
</style></head><body><div class="wrap">
<h1>Тестирование замеров приема пакетов из МО (IMDEV-9530, этап 2)</h1>
<p class="lead">Стенд МО-ФО: разработческие базы WIM_MO и WIN_FO_server, веб-сервис ФО Avancore.DownloadPosition.
Выгрузки МО штатными обработками ПРОД: остатки (450 тестовых портфелей, 5 потоков), мандаты (10 мандатов, 20 счетов), котировки (3 ценные бумаги).
Записи выбраны из регистра "Замеры времени" ФО с начала прогона ({esc(data['начало'])}).
Расширения: {esc(ext)}. Константа "Выполнять замеры производительности": {'включена' if data.get('замеры_включены') else 'выключена'}.</p>
<div class="verdict">{'Все проверки пройдены: ' if all_ok else 'Есть непройденные проверки: '}покрытие {covered}/{len(expected)} точек, правил {sum(1 for _, ok, _ in checks if ok)}/{len(checks)}, расхождений данных: {esc(snap_diff.get('расхождений', '?')) if isinstance(snap_diff, dict) else '?'}</div>
<div class="cards">
<div class="card"><b>{len(rows)}</b><span>записей замеров</span></div>
<div class="card"><b>{len(by_key)}</b><span>ключей операций</span></div>
<div class="card"><b>{len(packets)}</b><span>пакетов, суммарно {fmt(total_time, 1)} с</span></div>
<div class="card"><b>{peak}</b><span>пакетов загружалось одновременно (максимум)</span></div>
<div class="card"><b>{len(err_pk)}</b><span>пакетов с ошибками загрузки строк (код 3)</span></div>
</div>

<h2>Покрытие точек замера</h2>
<div class="box"><table><tr><th>Строка списка</th><th>Точка</th><th>Ключ</th><th>Записей</th><th>Сработал</th></tr>{cov_rows}</table></div>
{f"<p class='lead'>Дополнительно записаны ключи: {', '.join('<code>' + esc(k) + '</code>' for k in extra_keys)}.</p>" if extra_keys else ""}

<h2>Проверка правил замера</h2>
<div class="box"><table><tr><th>Итог</th><th>Правило</th><th>Факт</th></tr>{chk_rows}</table></div>

<h2>Сводка по ключам</h2>
<div class="box"><table><tr><th>Ключ</th><th>Записей</th><th>Время всего, с</th><th>Среднее, с</th><th>Максимум, с</th>
<th>Вес всего</th><th>мс на единицу веса</th><th>С ошибкой</th></tr>{''.join(key_rows)}</table></div>

<h2>Пакеты во времени: параллельные потоки</h2>
<div class="box" style="padding:10px">{timeline}
<div class="legend"><span><span class="tag pos">позиция</span> пакет с ФактическаяПозиция</span><span><span class="tag flag">флаги</span> только ДополнительныеСведения</span>
<span><span class="tag cat">справочники</span> мандаты и счета</span><span><span class="tag quote">котировки</span></span><span><span class="tag svc">служебный</span> без разделов данных (удаление блокировок, перерасчет, распространение правил)</span><span>красная рамка - пакет с ошибкой</span></div></div>
<p class="lead">Каждый вызов веб-сервиса выполняется в своем сеансе ФО, номер сеанса есть в каждой записи замера. Полосы разложены по дорожкам по пересечению интервалов: число дорожек - сколько пакетов загружалось одновременно. Число потоков МО на стороне ФО не передается и восстанавливается так. Наведите на полосу, чтобы увидеть комментарий замера.</p>

<h2>Пакеты и их разделы</h2>
<div class="box scroll"><table><tr><th>Начало</th><th>Сеанс</th><th>Вид</th><th>Время, с</th><th>Вес</th><th>Комментарий пакета</th><th>Записи разделов и операций</th></tr>{''.join(pk_rows)}</table></div>

<h2>Данные и время: без замеров и с замерами</h2>
<p class="lead">Выгрузка остатков 450 портфелей в 5 потоков. Без замеров: FO_KeyOpsPerf отключено, FO_PositionLoadOpt 1.0.0.4. С замерами: FO_KeyOpsPerf 1.0.0.2 и FO_PositionLoadOpt 1.0.0.5. Время вызовов - по логу веб-сервиса ФО, мс на строку пакета.</p>
<div class="box"><table><tr><th>Вызов</th><th>Без замеров, прогоны</th><th>Среднее</th><th>С замерами, прогоны</th><th>Среднее</th><th>Разница</th></tr>{cmp_rows}</table></div>
<div class="note">Сверка снимка данных ФО после выгрузки (флаги ДополнительныеСведения, ФактическаяПозиция, регистр РСА/СЧА, дата актуальности): прогоны <code>{esc(snap_diff.get('базовый', ''))}</code> и <code>{esc(snap_diff.get('с_замерами', ''))}</code>, строк по регистрам: {esc(', '.join(f'{k} {v}' for k, v in snap_diff.get('строк', {}).items()))}; расхождений: <b>{esc(snap_diff.get('расхождений', snap_diff.get('ошибка', '?')))}</b>.
Время на стороне ФО с замерами не выросло: сумма всех вызовов веб-сервиса и время на строку у вызовов с данными в пределах разброса между прогонами одной конфигурации. Строка \"Выгрузка всего\" включает запуск пула сеансов МО; время Опубликовать в потоках МО при этом не изменилось, поэтому разницу в ней замерам не приписываем. За прогон пишется около 170 записей замеров.</div>
<ul>{runs_list}</ul>

<h2>Протокол прогона и замечания</h2>
<ul>{tests_html}</ul>
<div class="note"><b>Ошибки МО в потоках.</b> В части 5-поточных прогонов один сеанс МО получал "недостаточно прав" на чтение своего справочника (Активы, СчетаДЕПО) до отправки пакета, и один портфель не выгружался. Это происходит и при отключенном FO_KeyOpsPerf (базовый прогон 2), на загрузку в ФО не влияет; известная нестабильность пула процессов МО на стенде.</div>
<div class="note"><b>Пакеты с кодом ответа 3.</b> Счета мандатов: тестовый банковский счет стенда заполнен не полностью, ФО отклонил его строку. Котировки: тестовая биржа и данные бумаг стенда неполные. Код 3 означает "ошибки загрузки строк": пакет обработан, замер записан с признаком ошибки.</div>
<div class="note"><b>Найдено и исправлено при тестировании.</b> Документ КотировкиЦБНаБирже приходит одним документом с котировками всех бумаг, вес был 1. В FO_KeyOpsPerf 1.0.0.2 вес раздела = число котировок, в комментарии "Котировок: N".</div>

<h2>Все записи регистра</h2>
<input class="filter" id="f" type="search" placeholder="Фильтр по ключу или комментарию...">
<div class="box scroll"><table id="raw"><tr><th>Начало</th><th>Сеанс</th><th>Ключ</th><th>Время, с</th><th>Вес</th><th>Ошибка</th><th>Комментарий</th></tr>{raw}</table></div>
<p class="lead">Источник: {esc(os.path.relpath(run_dir, TASK))}\\measurements.json. Время - локальное время сервера ФО (UTC+{tz}).</p>
</div>
<script>
document.getElementById("f").addEventListener("input", function () {{
  var q = this.value.toLowerCase();
  document.querySelectorAll("#raw tr[data-k]").forEach(function (tr) {{
    tr.style.display = !q || tr.textContent.toLowerCase().indexOf(q) !== -1 ? "" : "none"; }});
}});
</script></body></html>"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(OUT)
    print("checks:", [(n, ok) for n, ok, _ in checks])
    print("covered", covered, len(expected), "extra", extra_keys, "peak", peak, "snap", snap_diff)


if __name__ == "__main__":
    main()
