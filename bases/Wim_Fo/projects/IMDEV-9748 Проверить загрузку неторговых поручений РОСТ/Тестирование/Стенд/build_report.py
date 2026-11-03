# -*- coding: utf-8 -*-
"""Протокол тестирования 1.07 против итоговой 1.08 (пункты 1, 2, 4) по results/state_<серия>.json (серия - переменная T9748_SERIES, по умолчанию 3) (IMDEV-9748).

Сверка версий по каждому сценарию: письма (наличие, префикс темы, вложение, абзацы HTML), лог обработки, журнал
регистрации, ключи, веса и признак ошибки замеров. Где правка 1.08 меняет поведение (С5, С7, С9 - пункт 4;
письма без поручений - пункт 1), проверяется ожидаемое различие, в остальном - совпадение. Данные базы (поручения,
РСА/СЧА, дата актуальности, история статусов, статусы и признаки) сравниваются после всех сценариев; портфель Н07
(сценарий С9) сравнивается отдельно. Коды портфелей версий (T9748_C_*, T9748_D_*) приводятся к T9748_X_*.
Время запросов купонов взято из серии 1 (results/state_1.json): правка купонов в сериях одинакова.

    python build_report.py      results/checks_<серия>.json и ../Протокол тестирования 1.08.html
"""
import email
import email.policy
import html
import json
import os
import re
import statistics
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
SERIES = os.environ.get("T9748_SERIES", "3")
TAGS = {"2": ("C", "D"), "3": ("E", "F")}[SERIES]
STATE = os.path.join(RESULTS, f"state_{SERIES}.json")
STATE_1 = os.path.join(RESULTS, "state_1.json")
MAIL_DIR = os.path.join(RESULTS, "mail")
OUT_JSON = os.path.join(RESULTS, f"checks_{SERIES}.json")
OUT_HTML = os.path.join(os.path.dirname(HERE), "Протокол тестирования 1.08.html")
SEPARATE = "_N07"

# Сценарий: условие, ожидание, письмо 1.07, письмо 1.08 (префикс темы или None), поведение одинаково,
# обязательные фрагменты лога 1.07 и 1.08.
SCENARIOS = {
    "С1.НетПортфелей": ("Нет портфелей в статусах поиска", "предупреждение «Не найдено портфелей», поручений 0",
                        "WARN", None, True, "", ""),
    "С2.ТолькоПредупреждения": ("Деньги поступили, но не отправлены брокеру; сумма 0",
                                "предупреждение по портфелю, поручений 0", "WARN", None, True, "", ""),
    "С3.СозданиеПоручений": ("Два портфеля, деньги на брокерском счете", "2 поручения, письмо с отчетом",
                             "OK", "OK", True, "", ""),
    "С4.УжеЕстьПоручение": ("Портфель снова в поиске, поручение уже есть", "предупреждение, поручений 0",
                            "WARN", None, True, "", ""),
    "С5.ОтказСервиса": ("Отказ 1С:ДО (SOAP Fault) по портфелю",
                        "1.07: исключение прерывает запуск, письма нет; 1.08: ошибка портфеля в логе, письмо {FAIL}",
                        None, "FAIL", False, "Ошибка рассылки отчета по почте", "Ошибка вызова сервиса 1С:ДО"),
    "С6.ПереводДСВыведены": ("Вывод подан 2 часа назад", "статус «ДС выведены», затем «Не найдено портфелей»",
                             "WARN", None, True, "", ""),
    "С7.СервисНедоступен": ("Адрес 1С:ДО не отвечает", "ошибка без исключения, письмо {FAIL}; в 1.08 текст ошибки",
                            "FAIL", "FAIL", False, "", "Ошибка подключения к сервису 1С:ДО"),
    "С8.ПоручениеИПредупреждение": ("Поручение по одному портфелю и предупреждение по другому",
                                    "1 поручение, письмо {WARN} с отчетом", "WARN", "WARN", True, "", ""),
    "С9.ОтказИПоручение": ("Отказ 1С:ДО по Н04, деньги на брокерском счете у Н07",
                           "1.07: запуск прерван, Н07 без поручения; 1.08: Н07 получает поручение, письмо {FAIL} "
                           "с отчетом", None, "FAIL", False, "Ошибка рассылки отчета по почте",
                           "Ошибка вызова сервиса 1С:ДО"),
}


def norm(text):
    return re.sub(r"T9748_[A-Z]_", "T9748_X_", text or "").replace(" 1.07 ", " X ").replace(" 1.08 ", " X ")


def norm_log(text):
    return re.sub(r"МодульОбъекта\(\d+\)", "МодульОбъекта(N)", norm(text)).strip()


def prefix(subject):
    m = re.match(r"\{(\w+)\}", subject)
    return m.group(1) if m else None


def mail_html(name):
    with open(os.path.join(MAIL_DIR, name), "rb") as f:
        msg = email.message_from_binary_file(f, policy=email.policy.default)
    for part in msg.walk():
        if part.get_content_type() == "text/html" and not part.get_filename():
            return part.get_content()
    return ""


def measure_view(run):
    view = {}
    for m in run["замеры"]:
        key = m["ключ"].replace("ЗагрузкаНеторговыхПорученийРОСТ", "").strip(".") or "итого"
        view[key] = {"вес": m["вес"], "комментарий": m["комментарий"], "ошибка": m["ошибка"]}
    return view


def main():
    s = json.load(open(STATE, encoding="utf-8"))
    s1 = json.load(open(STATE_1, encoding="utf-8"))
    mails = {m["файл"]: m for m in s["письма"]}
    runs = {(r["сценарий"], r["версия"]): r for r in s["runs"]}
    cases = []

    def add(cid, title, expected, actual, ok, details=""):
        cases.append({"id": cid, "проверка": title, "ожидается": expected, "фактически": actual,
                      "итог": "ПРОЙДЕН" if ok else "НЕ ПРОЙДЕН", "подробно": details})

    # Данные базы, кроме портфеля Н07
    def by_version(rows):
        out = {}
        for r in rows:
            if r["Портфель"].endswith(SEPARATE):
                continue
            tag = r["Портфель"].split("_")[1]
            out.setdefault(tag, []).append(json.dumps({k: norm(str(x)) for k, x in r.items()}, ensure_ascii=False,
                                                      sort_keys=True))
        tags = sorted(out)
        return [sorted(out[t]) for t in tags] if len(tags) == 2 else [[], []]

    for rows, title in ((s["поручения"], "Документы «Поручение»: вид, сумма, количество, проведен, субпортфель, "
                                         "комментарий"),
                        (s["рса_сча"], "Регистр РСА/СЧА"),
                        (s["дата_актуальности"], "Регистр даты актуальности позиции"),
                        (s["история_статусов"], "История статусов портфелей")):
        a, b = by_version(rows)
        add(f"Д-{len(cases) + 1:02d}", title + " (кроме Н07, см. С-09)", "одинаково в 1.07 и 1.08",
            f"1.07: {len(a)} строк, 1.08: {len(b)} строк, совпадение: {'да' if a == b else 'нет'}", a == b and a)
    props = [r for r in s["сведения"] if "Дата" not in r["Свойство"] and not r["Портфель"].endswith(SEPARATE)]
    key = lambda r: norm(f"{r['Портфель']}|{re.sub(r' [A-Z]$', '', r['Свойство'])}|{r['Значение']}")  # noqa: E731
    pa = sorted(key(r) for r in props if f"_{TAGS[0]}_" in r["Портфель"])
    pb = sorted(key(r) for r in props if f"_{TAGS[1]}_" in r["Портфель"])
    add(f"Д-{len(cases) + 1:02d}", "Статусы портфелей и признак «Позиция выгружена» (кроме Н07)",
        "одинаково в 1.07 и 1.08", f"1.07: {len(pa)}, 1.08: {len(pb)}, совпадение: {'да' if pa == pb else 'нет'}",
        pa == pb and pa)

    for i, (scen, (pre, expected, p107, p108, same, need107, need108)) in enumerate(SCENARIOS.items(), 1):
        a, b = runs[(scen, "1.07")], runs[(scen, "1.08")]
        la, lb = [mails[f] for f in a["письма"]], [mails[f] for f in b["письма"]]
        got107 = prefix(la[0]["тема"]) if la else None
        got108 = prefix(lb[0]["тема"]) if lb else None
        par_b = [len(re.findall(r"<p>", mail_html(f))) for f in b["письма"]]
        ok = got107 == p107 and got108 == p108 and len(la) <= 1 and len(lb) <= 1 and all(p >= 2 for p in par_b)
        if la and lb:
            ok = ok and bool(la[0]["вложения"]) == bool(lb[0]["вложения"])
        ja = [(j["уровень"], norm_log(j["комментарий"])) for j in a["журнал"] if j["уровень"] != "Примечание"]
        jb = [(j["уровень"], norm_log(j["комментарий"])) for j in b["журнал"] if j["уровень"] != "Примечание"]
        ma, mb = measure_view(a), measure_view(b)
        if same:
            ok = ok and norm_log(a["лог"]) == norm_log(b["лог"]) and ja == jb and ma == mb
        else:
            ok = ok and need107 in a["лог"] and need108 in b["лог"] \
                and (ja[-1][0] if ja else "") == "Ошибка" and (jb[-1][0] if jb else "") == "Ошибка" \
                and ma.get("итого", {}).get("ошибка") and mb.get("итого", {}).get("ошибка")
        if scen == "С5.ОтказСервиса":
            ok = ok and set(ma) == {"итого"} and set(mb) == {"итого", "СозданиеПоручений", "Рассылка"}
        if scen == "С9.ОтказИПоручение":
            n07 = {tag: [o for o in s["поручения"] if o["Портфель"] == f"T9748_{tag}_N07"] for tag in TAGS}
            hist = {tag: [h for h in s["история_статусов"] if h["Портфель"] == f"T9748_{tag}_N07"] for tag in TAGS}
            ok = ok and not n07[TAGS[0]] and len(n07[TAGS[1]]) == 1 and n07[TAGS[1]][0]["Проведен"] is True \
                and bool(lb and lb[0]["вложения"]) and not hist[TAGS[0]] and len(hist[TAGS[1]]) == 1
            expected += f"; поручение Н07: 1.07 - 0, 1.08 - 1"
        fmt = lambda ls: ", ".join(f"{{{prefix(x['тема'])}}}" + (" + xlsx" if x["вложения"] else "") for x in ls) or "нет"  # noqa: E731
        actual = (f"письмо 1.07: {fmt(la)}; 1.08: {fmt(lb)} (абзацев HTML {par_b or '-'}); "
                  + (f"лог, журнал, замеры одинаковы: {'да' if ok else 'нет'}" if same else
                     f"лог 1.07: {norm_log(a['лог'])[:120] or '(пусто)'}; лог 1.08: {norm_log(b['лог'])[:160]}"))
        if scen == "С9.ОтказИПоручение":
            actual += (f"; поручение Н07: 1.07 - {len(n07[TAGS[0]])}, 1.08 - {len(n07[TAGS[1]])}"
                       f" (проведено: {'да' if n07[TAGS[1]] and n07[TAGS[1]][0]['Проведен'] is True else 'нет'})")
        if scen == "С5.ОтказСервиса":
            actual += f"; замеры 1.07: {sorted(ma)}, 1.08: {sorted(mb)}"
        add(f"С-{i:02d}", f"{scen}: {pre}", expected, actual, ok,
            f"журнал 1.07: {ja}; журнал 1.08: {jb}; замеры 1.07: {ma}; 1.08: {mb}")

    bench = {}
    for v in ("1.07", "1.08"):
        rs = [r for r in s["runs"] if r["сценарий"].startswith("Б.") and r["версия"] == v]
        vals = {}
        for suf in ("", ".СозданиеПоручений", ".Рассылка"):
            vals[suf.strip(".") or "итого"] = [m["время_с"] for r in rs for m in r["замеры"]
                                                if m["ключ"] == "ЗагрузкаНеторговыхПорученийРОСТ" + suf]
        bench[v] = {"запусков": len(rs), "писем": sum(len(r["письма"]) for r in rs),
                    "логи": sorted({r["лог"] for r in rs}),
                    **{k: {"n": len(x), "медиана_с": round(statistics.median(x), 3),
                           "среднее_с": round(statistics.mean(x), 3), "мин_с": round(min(x), 3),
                           "макс_с": round(max(x), 3)} for k, x in vals.items() if x}}
    add("Б-01", "Пустые запуски: 15 портфелей в поиске, сумма 0 (как на ПРОД), по 10 запусков каждой версии поочередно",
        "писем нет в обеих версиях, лог одинаков, замер есть у каждого запуска",
        f"писем 1.07: {bench['1.07']['писем']}, 1.08: {bench['1.08']['писем']}; лог одинаков: "
        f"{'да' if bench['1.07']['логи'] == bench['1.08']['логи'] else 'нет'}; замеров "
        f"{bench['1.07']['итого']['n']} и {bench['1.08']['итого']['n']}",
        bench["1.07"]["писем"] == 0 and bench["1.08"]["писем"] == 0
        and bench["1.07"]["логи"] == bench["1.08"]["логи"]
        and bench["1.07"]["итого"]["n"] == bench["1.07"]["запусков"]
        and bench["1.08"]["итого"]["n"] == bench["1.08"]["запусков"])
    coupons = {k: v for k, v in s1["запросы"].items() if k.startswith("купоны")}
    result = {"проверок": len(cases), "пройдено": sum(1 for c in cases if c["итог"] == "ПРОЙДЕН"), "проверки": cases,
              "скорость": bench, "купоны_серия_1": coupons,
              "писем": {v: sum(len(r["письма"]) for r in s["runs"] if r["версия"] == v and r["сценарий"] in SCENARIOS)
                        for v in ("1.07", "1.08")}}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    write_html(result, runs, mails)
    print(f"проверок {result['проверок']}, пройдено {result['пройдено']}, писем {result['писем']}")
    for c in cases:
        print(c["id"], c["итог"], c["проверка"][:60], "|", c["фактически"][:260])
    print(json.dumps(bench, ensure_ascii=False))


def write_html(result, runs, mails):
    e = html.escape
    rows = "".join(
        f"<tr class='{'ok' if c['итог'] == 'ПРОЙДЕН' else 'bad'}'><td>{e(c['id'])}</td><td>{e(c['проверка'])}</td>"
        f"<td>{e(c['ожидается'])}</td><td>{e(c['фактически'])}</td><td class='st'>{e(c['итог'])}</td></tr>"
        for c in result["проверки"])
    b = result["скорость"]
    speed = "".join(
        f"<tr><td>{v}</td><td>{b[v]['запусков']}</td><td>{b[v]['СозданиеПоручений']['медиана_с']}</td>"
        f"<td>{b[v]['СозданиеПоручений']['среднее_с']}</td><td>{b[v]['итого']['медиана_с']}</td>"
        f"<td>{b[v]['писем']}</td></tr>" for v in ("1.07", "1.08"))
    qrows = "".join(f"<tr><td>{e(v['дата'])}</td><td>{v['строк_позиции']}</td><td>{v['медиана_мс']}</td>"
                    f"<td>{v['мин_мс']}</td><td>{v['макс_мс']}</td></tr>" for v in result["купоны_серия_1"].values())
    qrows += "<tr><td>Т-1, копия ПРОД (логи диагностики 28.10)</td><td>позиция дня</td><td>691-998</td><td></td><td></td></tr>"
    samples = ""
    for scen, v in (("С3.СозданиеПоручений", "1.07"), ("С3.СозданиеПоручений", "1.08"), ("С9.ОтказИПоручение", "1.08")):
        name = runs[(scen, v)]["письма"][0]
        body = mail_html(name)
        inner = re.sub(r"(?is).*<body[^>]*>(.*)</body>.*", r"\1", body)
        samples += (f"<div class='mail'><div class='mh'>{e(scen)}, {v}: {e(mails[name]['тема'])}</div>"
                    f"<div class='mb'>{inner}</div><details><summary>HTML письма</summary><pre>{e(body)}</pre>"
                    f"</details></div>")
    page = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Протокол тестирования 1.08</title>
<style>
:root{{--bg:#fff;--fg:#1d2433;--muted:#5b6475;--line:#d9dee7;--ok:#e7f5ec;--bad:#fbe9e9;--head:#eef1f6}}
@media (prefers-color-scheme: dark){{:root{{--bg:#151922;--fg:#e6e9ef;--muted:#9aa3b2;--line:#2c3342;--ok:#18301f;--bad:#3a1d1d;--head:#1e2430}}}}
body{{background:var(--bg);color:var(--fg);font:14px/1.45 Segoe UI,Arial,sans-serif;margin:0 auto;max-width:1200px;padding:16px}}
h1{{font-size:20px}} h2{{font-size:16px;margin-top:28px}} .muted{{color:var(--muted)}}
table{{border-collapse:collapse;width:100%;margin:8px 0}} th,td{{border:1px solid var(--line);padding:6px 8px;vertical-align:top;text-align:left}}
th{{background:var(--head)}} tr.ok td.st{{background:var(--ok)}} tr.bad td.st{{background:var(--bad)}}
.mail{{border:1px solid var(--line);margin:10px 0;padding:8px}} .mh{{font-weight:600}} .mb{{padding:8px;border:1px dashed var(--line);margin:6px 0}}
pre{{white-space:pre-wrap;word-break:break-all;font-size:12px;color:var(--muted)}}
</style></head><body>
<h1>Протокол тестирования обработки «Загрузка неторговых поручений РОСТ» 1.08</h1>
<p class="muted">IMDEV-9748. Разработческая база ФО, 1.08 (письма без поручений только при ошибке и абзацы HTML;
без запроса суммы купонов; отказ 1С:ДО по портфелю не прерывает запуск, текст ошибок) против 1.07 (ПРОД) на одинаковых
данных. Тестовый режим обработки: сумма на брокерском счете без адаптера FIX; 1С:ДО и почтовый сервер - заглушки.</p>
<p><b>Итог: {result['пройдено']} из {result['проверок']} проверок пройдено.</b> Писем в сценариях С1-С9:
1.07 - {result['писем']['1.07']}, 1.08 - {result['писем']['1.08']}.</p>
<h2>Проверки</h2>
<table><tr><th>№</th><th>Проверка</th><th>Ожидается</th><th>Фактически</th><th>Итог</th></tr>{rows}</table>
<h2>Скорость пустого запуска (15 портфелей в поиске, сумма 0), по 10 запусков</h2>
<table><tr><th>Версия</th><th>Запусков</th><th>Создание поручений, медиана, с</th><th>Среднее, с</th>
<th>Весь запуск, медиана, с</th><th>Писем</th></tr>{speed}</table>
<h2>Время запроса суммы купонов (снят в 1.08), 20 повторов</h2>
<table><tr><th>Дата позиции</th><th>Строк позиции на дату</th><th>Медиана, мс</th><th>Мин, мс</th><th>Макс, мс</th></tr>{qrows}</table>
<h2>Образцы писем</h2>{samples}
</body></html>"""
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(page)


if __name__ == "__main__":
    main()
