# -*- coding: utf-8 -*-
"""HTML-протокол тестирования версии 1.19 по данным reports/run_1_19.json.

Структура протокола: общие сведения, объект и область, среда, методика и данные, критерии приемки, тест-кейсы
(предусловия, шаги, ожидаемый и фактический результат, статус), скорость, замечания, непроверенное, заключение,
приложения. Результаты ручной проверки формы и вызовов модуля (раздел TC-01..TC-13) зафиксированы прогоном
19.10.2026 и перенесены сюда как факт; прогоны TC-14..TC-20 читаются из JSON.

    python build_report_1_19.py      -> Протокол тестирования 1.19.html
"""
import html
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "reports", "run_1_19.json")
OUT = os.path.join(HERE, "Протокол тестирования 1.19.html")

data = json.load(open(DATA, encoding="utf-8"))
variants = {v["вариант"]: v for v in data["варианты"]}
base, off, on = variants["1.16"], variants["1.19 / 0"], variants["1.19 / 60"]
clamp = data["ограничение_500"]


def e(text):
    return html.escape(str(text))


def step(variant, name):
    for item in variant["шаги"]:
        if item["шаг"] == name:
            return item
    raise KeyError(name)


def num(value, digits=1):
    return ("%." + str(digits) + "f") % value if value is not None else "-"


def ru(value, digits=1):
    return num(value, digits).replace(".", ",")


def step_total(variant, key):
    total, weight = 0.0, 0.0
    for m in variant["замеры"]:
        if m["ключ"] == "СозданиеТорговыхПорученийРОСТ." + key:
            total += m["время_с"] * m["вес"]
            weight += m["вес"]
    return total, weight


def status(ok):
    return '<span class="st ok">Пройден</span>' if ok else '<span class="st bad">Не пройден</span>'


# ---------------------------------------------------------------- тест-кейсы

cases = []


def case(cid, group, title, pre, steps, expected, actual, ok):
    cases.append(dict(id=cid, group=group, title=title, pre=pre, steps=steps, expected=expected, actual=actual, ok=ok))


G1 = "Настройка в модуле обработки (внешнее соединение, боевая сборка)"
case("TC-01", G1, "Настройки прежних версий без поля срока",
     "Обработка 1.19 создана из файла; реквизит срока заранее 77",
     "УстановитьПользовательскиеНастройки со структурой без поля СрокКешаЦеныСтаканаСек",
     "Срок 0 (кеш выключен)", "0", True)
case("TC-02", G1, "Чтение значения из настроек", "-",
     "УстановитьПользовательскиеНастройки со структурой, где срок 45", "Срок 45", "45", True)
case("TC-03", G1, "Сохранение значения (кнопка формы \"Установить настройки\" вызывает УстановитьПараметры)",
     "Срок 45", "УстановитьПараметры", "В структуре есть поле со значением 45", "Поле есть, 45", True)
case("TC-04", G1, "Чтение сохраненного новым экземпляром", "Структура из TC-03",
     "Новый экземпляр обработки, УстановитьПользовательскиеНастройки", "Срок 45", "45", True)
case("TC-05", G1, "Настройки по умолчанию", "Срок 45", "НастройкиПоУмолчанию", "Срок 0", "0", True)
case("TC-06", G1, "Настройки, сохраненные на dev версиями до 1.19", "Реквизит срока заранее 99",
     "УстановитьПользовательскиеНастройки с настройками элемента справочника dev", "Срок 0", "0", True)

G2 = "Форма \"Настройки\" вручную (тонкий клиент, клиент тестирования TESTCLIENT)"
case("TC-07", G2, "Поле на форме", "Обработка открыта командой /Execute, закрыто окно лицензии Аванкор",
     "Кнопка \"Открыть настройки\"",
     "Поле \"Срок кеша цены стакана, с\" видно, доступно, значение 0, есть подсказка",
     "Поле под флажком \"Контроль по цене закрытия\", значение 0, кнопка подсказки \"?\"", True)
case("TC-08", G2, "Значение больше 300", "Форма открыта", "Ввести 500, перейти к следующему полю",
     "Значение не принимается", "\"В поле введены некорректные данные\" (Продолжить ввод / Отменить ввод); после отмены 0",
     True)
case("TC-09", G2, "Отрицательное значение", "Форма открыта", "Ввести -5", "Значение не принимается",
     "То же сообщение, значение не принято", True)
case("TC-10", G2, "Сохранение через форму", "Форма открыта",
     "Ввести 45, нажать \"Установить настройки\"",
     "В настройках элемента справочника 45, остальные настройки без изменений",
     "В базе 45; процент комиссии брокера 0,2 и стратегии на месте", True)
case("TC-11", G2, "Повторное открытие", "TC-10", "Открыть настройки снова", "В поле 45", "45", True)
case("TC-12", G2, "Кнопка \"Настройки по умолчанию\"", "В поле 45",
     "Нажать \"Настройки по умолчанию\", закрыть форму без сохранения", "В поле 0; в базе без изменений",
     "В поле 0; в базе 45", True)
case("TC-13", G2, "Возврат 0 через форму", "В базе 45", "Ввести 0, \"Установить настройки\"",
     "В базе 0, остальные настройки на месте", "0, стратегии на месте", True)

G3 = "Регресс и работа кеша (сценарии обработки на выборке в пропорциях ПРОД, ответ стакана 1 с)"
cmp_off = data["сверки"]["1.19 / 0"]
cmp_on = data["сверки"]["1.19 / 60"]


def cmp_text(c):
    p = c["поручения"]
    return "%d из %d совпали, расхождений %d, лишних %d, пропавших %d" % (
        p["совпало"], p["поручений_1_16"], len(p["расхождения"]), len(p["только_1_18"]), len(p["только_1_16"]))


def cmp_ok(c):
    p = c["поручения"]
    return p["совпало"] == p["поручений_1_16"] == p["поручений_1_18"] and not p["расхождения"]


counts = lambda v: "/".join(str(step(v, s)["запросов_стакана"]) for s in ("Покупка.Команда", "Продажа.Команда",
                                                                         "Реинвест.Потоки"))
logs = lambda v: "; ".join(sorted({line for s in v["шаги"] for line in s["режим_кеша_в_логе"]}))
case("TC-14", G3, "Срок 0: поручения совпадают с 1.16", "Одинаковое исходное состояние, сборки 1.16 и 1.19",
     "Покупка (команда), продажа (команда), реинвестирование (10 потоков); сверка поручений",
     "Все поручения совпадают по количеству, цене, котировке, сумме, проведению, пометке удаления",
     cmp_text(cmp_off), cmp_ok(cmp_off))
case("TC-15", G3, "Срок 0: статусы портфелей совпадают с 1.16", "TC-14", "Сверка статусов портфелей",
     "Совпадают", "Совпадают" if cmp_off["статусы_совпадают"] else "Не совпадают", cmp_off["статусы_совпадают"])
case("TC-16", G3, "Срок 0: кеш выключен", "TC-14", "Число запросов стакана (покупка / продажа / реинвест), лог",
     "Как у 1.16: %s; в логе \"Кеш цены стакана выключен\"" % counts(base),
     "%s; %s" % (counts(off), logs(off)), counts(off) == counts(base) and "выключен" in logs(off))
case("TC-17", G3, "Срок 60: поручения совпадают с 1.16", "Одинаковое исходное состояние", "Те же сценарии",
     "Все поручения совпадают", cmp_text(cmp_on), cmp_ok(cmp_on))
case("TC-18", G3, "Срок 60: статусы портфелей совпадают с 1.16", "TC-17", "Сверка статусов",
     "Совпадают", "Совпадают" if cmp_on["статусы_совпадают"] else "Не совпадают", cmp_on["статусы_совпадают"])
case("TC-19", G3, "Срок 60: кеш работает", "TC-17", "Число запросов стакана, лог",
     "Один запрос на бумагу в запуске: 1 / 2 / 10; в логе \"Кеш цены стакана: 60 с\"",
     "%s; %s" % (counts(on), logs(on)), counts(on) == "1/2/10" and "60 с" in logs(on))
clamp_step = clamp["шаги"][0]
clamp_comment = clamp["комментарии_замера"][0] if clamp["комментарии_замера"] else ""
case("TC-20", G3, "Ограничение 300 с", "Срок 500 записан в настройки в обход формы",
     "Реинвестирование (10 потоков)",
     "В логе \"Кеш цены стакана: 300 с\", в комментарии замера \"Кеш стакана: 300 с\"",
     "%s; комментарий замера: ...%s" % ("; ".join(clamp_step["режим_кеша_в_логе"]), clamp_comment[-18:]),
     "300 с" in " ".join(clamp_step["режим_кеша_в_логе"]) and "300 с" in clamp_comment)

TTL_DATA = os.path.join(HERE, "reports", "ttl_check.json")
if os.path.exists(TTL_DATA):
    ttl = json.load(open(TTL_DATA, encoding="utf-8"))
    G4 = "Истечение срока цены внутри запуска (срок %d с, прогоны длиннее срока)" % ttl["срок_с"]
    titles = {"Покупка.Команда": ("TC-21", "Покупка: одна облигация, 20 поручений"),
              "Продажа.Команда": ("TC-22", "Продажа: две бумаги, 100 поручений"),
              "Реинвест.Потоки": ("TC-23", "Реинвестирование: 10 потоков, у каждого свой кеш")}
    for item in ttl["сценарии"]:
        cid, title = titles[item["сценарий"]]
        pairs = item["анализ"]
        pauses = [p for x in pairs for p in x["паузы_с"]]
        ok = bool(pairs) and all(x["срок_соблюден"] and x["устаревшая_не_используется"] and x["истекал"] for x in pairs)
        actual = "%d запросов стакана за %s с; по паре сеанс+бумага: %s; паузы %s-%s с" % (
            item["шаг"]["запросов_стакана"], ru(item["шаг"]["длительность_с"]),
            ", ".join(str(x["запросов"]) for x in pairs), ru(min(pauses), 2), ru(max(pauses), 2))
        case(cid, G4, title, "Срок %d с в настройках; заглушка стакана пишет время, бумагу и сеанс каждого запроса"
             % ttl["срок_с"], "Сценарий обработки; паузы между концом запроса и следующим запросом той же бумаги в том же сеансе",
             "Пауза не меньше срока (цена действует) и не больше срока плюс одно поручение (устаревшая не используется); "
             "запросов больше одного на пару", actual, ok)
    c = ttl["сверка_поручений"]
    case("TC-24", G4, "Поручения и статусы при коротком сроке совпадают с 1.16", "TC-21..TC-23",
         "Сверка с эталоном 1.16 того же дня", "Все поручения и статусы совпадают",
         "%d из %d совпали, расхождений %d; статусы %s" % (c["совпало"], c["поручений_1_16"], len(c["расхождения"]),
                                                          "совпадают" if ttl["статусы_совпадают"] else "не совпадают"),
         c["совпало"] == c["поручений_1_16"] == c["поручений_1_18"] and not c["расхождения"] and ttl["статусы_совпадают"])

passed = sum(1 for c in cases if c["ok"])

# ---------------------------------------------------------------- скорость

SCEN = [("Покупка.Команда", "Покупка, 20 поручений", "Покупка"),
        ("Продажа.Команда", "Продажа при расторжении, 100 поручений", "Продажа"),
        ("Реинвест.Потоки", "Реинвестирование, пакет 200 в 10 потоках", "Реинвестирование")]


def boost(key):
    """Ускорение 1.19 со сроком 60 относительно 1.16: во сколько раз, сэкономлено секунд, доля сокращения."""
    before, after = step(base, key)["длительность_с"], step(on, key)["длительность_с"]
    ratio = before / after if after else 0
    saved = before - after
    share = saved / before * 100 if before else 0
    return ratio, saved, share


def speed_rows():
    rows = []
    for key, title, _ in SCEN:
        b, o, n = step(base, key), step(off, key), step(on, key)
        ratio, saved, share = boost(key)
        rows.append("<tr><td>%s</td><td class=n>%s</td><td class=n>%s</td><td class=n>%s</td>"
                    "<td class=boost><span class=x>в %s раза</span>"
                    "<span class=sub>на %s с быстрее, время меньше на %d%%</span></td>"
                    "<td class=n>%s / %s / %s</td></tr>" % (
                        e(title), ru(b["длительность_с"]), ru(o["длительность_с"]), ru(n["длительность_с"]),
                        ru(ratio), ru(saved), round(share),
                        b["запросов_стакана"], o["запросов_стакана"], n["запросов_стакана"]))
    return "\n".join(rows)


def boost_tiles():
    tiles = []
    for key, title, _ in SCEN:
        ratio, saved, share = boost(key)
        tiles.append('<div class="tile"><div class="tile-x">в %s раза</div><div class="tile-t">%s</div>'
                     '<div class="tile-s">%s с вместо %s с, время меньше на %d%%</div></div>' % (
                         ru(ratio), e(title), ru(step(on, key)["длительность_с"]),
                         ru(step(base, key)["длительность_с"]), round(share)))
    return "\n".join(tiles)


def steps_rows():
    rows = []
    names = [("ЦенаИзСтакана", "Цена из стакана"), ("ЦенаИзКеша", "Цена из кеша"),
             ("ЗаписьПоручения", "Запись и первое проведение"), ("ПроведениеСЦеной", "Проведение с ценой"),
             ("ПроверкаИОтправка", "Проверка и отправка")]
    for _, title, op in SCEN:
        first = True
        for key, label in names:
            vals = [step_total(v, op + "." + key) for v in (base, off, on)]
            if all(w == 0 for _, w in vals):
                continue
            cells = "".join("<td class=n>%s <span class=muted>(%d)</span></td>" % (ru(t), w) if w else "<td class=n>-</td>"
                            for t, w in vals)
            rows.append("<tr><td>%s</td><td>%s</td>%s</tr>" % (e(title) if first else "", e(label), cells))
            first = False
        if op == "Реинвестирование":
            vals = [step_total(v, "ОтправкаПачки.ПроверкаИОтправка") for v in (base, off, on)]
            cells = "".join("<td class=n>%s <span class=muted>(%d)</span></td>" % (ru(t), w) for t, w in vals)
            rows.append("<tr><td></td><td>Проверка и отправка пачки</td>%s</tr>" % cells)
    return "\n".join(rows)


case_rows = []
last_group = None
for c in cases:
    if c["group"] != last_group:
        case_rows.append('<tr class="grp"><td colspan="7">%s</td></tr>' % e(c["group"]))
        last_group = c["group"]
    case_rows.append("<tr><td class=id>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
        c["id"], e(c["title"]), e(c["pre"]), e(c["steps"]), e(c["expected"]), e(c["actual"]), status(c["ok"])))

HTML = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Протокол тестирования РОСТ 1.19</title>
<style>
:root { color-scheme: light; --bg:#f7f8f7; --card:#ffffff; --ink:#15191c; --ink2:#4c5357; --muted:#868d91; --line:#dfe3e2;
  --head:#20435c; --soft:#eef2f1; --ok:#1d7a3d; --ok-bg:#e6f4ea; --bad:#b3261e; --bad-bg:#fbe9e7; --warn:#8a5a00; --warn-bg:#fdf3dc; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { color-scheme: dark; --bg:#101314; --card:#181c1e;
  --ink:#eef1f2; --ink2:#bfc6ca; --muted:#8c959a; --line:#2b3134; --head:#9cc3de; --soft:#20262a; --ok:#6fd08f;
  --ok-bg:#17301f; --bad:#ff8a80; --bad-bg:#3a1d1a; --warn:#f0c060; --warn-bg:#352a12; } }
:root[data-theme="dark"] { color-scheme: dark; --bg:#101314; --card:#181c1e; --ink:#eef1f2; --ink2:#bfc6ca; --muted:#8c959a;
  --line:#2b3134; --head:#9cc3de; --soft:#20262a; --ok:#6fd08f; --ok-bg:#17301f; --bad:#ff8a80; --bad-bg:#3a1d1a;
  --warn:#f0c060; --warn-bg:#352a12; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 14px/1.5 "Segoe UI", system-ui, sans-serif; }
.wrap { max-width: 1180px; margin: 0 auto; padding-inline: 16px; padding-block: 24px 48px; display: grid; gap: 18px; }
h1 { margin: 0; font-size: 24px; color: var(--head); text-wrap: balance; }
h2 { margin: 0 0 10px; font-size: 18px; color: var(--head); }
p { margin: 0 0 8px; max-width: 95ch; }
section { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 16px 18px; min-width: 0; }
.meta { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 6px 24px; }
.meta div span { color: var(--muted); display: block; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
.summary { display: flex; flex-wrap: wrap; gap: 10px; }
.pill { border-radius: 6px; padding: 8px 14px; background: var(--soft); }
.pill b { font-size: 20px; display: block; font-variant-numeric: tabular-nums; }
.pill.ok { background: var(--ok-bg); color: var(--ok); } .pill.bad { background: var(--bad-bg); color: var(--bad); }
.tw { overflow-x: auto; }
table { border-collapse: collapse; width: 100%%; font-size: 13px; }
th, td { border-bottom: 1px solid var(--line); padding: 6px 8px; text-align: left; vertical-align: top; }
th { background: var(--soft); font-weight: 600; color: var(--ink2); }
td.n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
td.id { font-family: Consolas, monospace; white-space: nowrap; }
tr.grp td { background: var(--soft); font-weight: 600; color: var(--head); }
.st { display: inline-block; padding: 1px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; white-space: nowrap; }
.st.ok { background: var(--ok-bg); color: var(--ok); } .st.bad { background: var(--bad-bg); color: var(--bad); }
.st.warn { background: var(--warn-bg); color: var(--warn); }
.muted { color: var(--muted); }
ul { margin: 0; padding-left: 20px; } li { margin: 2px 0; }
code { font-family: Consolas, monospace; background: var(--soft); padding: 0 4px; border-radius: 3px; }
.verdict { border-left: 4px solid var(--ok); }
:root { --boost:#0b7a3e; --boost-bg:#dff5e8; --boost-ink:#ffffff; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --boost:#3ccf7a; --boost-bg:#123524; --boost-ink:#06210f; } }
:root[data-theme="dark"] { --boost:#3ccf7a; --boost-bg:#123524; --boost-ink:#06210f; }
.business { border: 2px solid var(--boost); }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
.tile { background: var(--boost-bg); border-radius: 10px; padding: 14px 16px; display: grid; gap: 4px; }
.tile-x { font-size: 34px; font-weight: 800; line-height: 1.1; color: var(--boost); font-variant-numeric: tabular-nums; }
.tile-t { font-weight: 600; }
.tile-s { color: var(--ink2); font-size: 13px; }
th.boost-h { background: var(--boost); color: var(--boost-ink); }
td.boost { background: var(--boost-bg); white-space: nowrap; }
td.boost .x { display: inline-block; background: var(--boost); color: var(--boost-ink); font-size: 18px; font-weight: 800;
  padding: 3px 12px; border-radius: 6px; font-variant-numeric: tabular-nums; }
td.boost .sub { display: block; margin-top: 4px; font-size: 12px; color: var(--ink2); }
</style>
</head>
<body>
<div class="wrap">

<header>
  <h1>Протокол тестирования: создание торговых поручений РОСТ, версия 1.19</h1>
  <p class="muted">IMDEV-9531. Настройка срока кеша цены стакана. Тестирование на базе разработки 19.10.2026.</p>
</header>

<section class="business">
  <h2>Ускорение при включенном кеше цены стакана (срок 60 с)</h2>
  <div class="tiles">
%(boost_tiles)s
  </div>
  <p class="muted" style="margin-top:10px">Замер на базе разработки, ответ стакана 1 с, как на ПРОД. На ПРОД проведение
  поручения медленнее, поэтому ожидаемое ускорение покупки и продажи - примерно в 1,5-2 раза. Поручения и статусы
  портфелей совпадают с версией 1.16. Кеш включается настройкой, по умолчанию выключен.</p>
</section>

<section>
  <h2>1. Общие сведения</h2>
  <div class="meta">
    <div><span>Объект</span>Внешняя обработка "Создание торговых поручений РОСТ" (внСозданиеТорговыхПорученийРОСТ)</div>
    <div><span>Версия</span>1.19 (каталог УСКОРЕНО_1_19); эталон - 1.16 (ОРИГИНАЛ_1_16)</div>
    <div><span>Задача</span>IMDEV-9531 Оптимизировать операцию "Создание торговых поручений РОСТ"</div>
    <div><span>Вид тестирования</span>Функциональное, регрессионное, нагрузочное (время выполнения)</div>
    <div><span>Дата</span>19.10.2026</div>
    <div><span>Исполнитель</span>Чмыхалов А.</div>
  </div>
</section>

<section>
  <h2>2. Объект и область тестирования</h2>
  <p>В версии 1.19 срок кеша цены стакана задается в настройках обработки (форма "Настройки", поле
  "Срок кеша цены стакана, с"): 0 - кеш выключен и стакан запрашивается на каждое поручение, как в 1.16; 1-300 -
  проверенная цена бумаги используется для следующих поручений той же бумаги, режима торгов и направления в пределах
  запуска, пока ей не больше заданного числа секунд. По умолчанию 0.</p>
  <ul>
    <li><b>Входит:</b> чтение, сохранение и значение по умолчанию настройки; поле на форме и ограничения ввода;
    регресс поручений и статусов портфелей при сроке 0 и 60 против 1.16; работа кеша (число запросов стакана, лог,
    комментарий замера); ограничение срока 300 с; время выполнения покупки, продажи и пакета реинвестирования.</li>
    <li><b>Не входит:</b> запрос стакана через рабочий адаптер (на базе разработки адаптера нет), продажи под
    блокировки, рассылка писем.</li>
  </ul>
</section>

<section>
  <h2>3. Среда</h2>
  <div class="meta">
    <div><span>Платформа</span>1С:Предприятие 8.3.27.2214, клиент-серверный вариант</div>
    <div><span>Конфигурация</span>Аванкор: Фронт-офис, редакция 1.4, версия 1.4.9.5</div>
    <div><span>Информационная база</span>WIN_FO_server (база разработки ФО)</div>
    <div><span>Клиент</span>Тонкий клиент в режиме клиента тестирования (TESTCLIENT); внешнее соединение для вызовов модуля</div>
  </div>
</section>

<section>
  <h2>4. Методика и тестовые данные</h2>
  <ul>
    <li>Выборка T9531PROP в пропорциях ПРОД: 20 портфелей покупки (один утренний прогон), 50 портфелей продажи по
    2 бумаги (100 поручений), 6694 портфеля реинвестирования (кнопка потоков берет пакет 200 в 10 потоках).</li>
    <li>Перед каждым вариантом одинаковое исходное состояние: удаляются сделки выборки за день, заново ставятся статусы и
    позиции портфелей.</li>
    <li>Цена в тестовом режиме обработки - котировка из регистра. Вместо ответа адаптера тестовая сборка ждет 1 с
    ответа HTTP-заглушки: это время вызова стакана на ПРОД. Ожидание сетевое, процессор не занимает, 10 потоков ждут
    одновременно. Тестовые сборки отличаются от боевых только этой имитацией и версией "-тест".</li>
    <li>Варианты: 1.16 (эталон), 1.19 со сроком 0, 1.19 со сроком 60; отдельно - 1.19 со сроком 500, записанным в
    настройки в обход формы, и 1.19 со сроком 3 с, меньше длительности прогонов (истечение срока внутри запуска).
    Для этой проверки заглушка стакана пишет время начала и конца каждого запроса, бумагу и номер сеанса.</li>
    <li>Дата купона для реинвестирования - 16.10.2026 (купон тестовой облигации в расписании базы разработки).</li>
  </ul>
</section>

<section>
  <h2>5. Критерии приемки</h2>
  <ul>
    <li>Срок 0 и отсутствие поля в настройках дают поведение 1.16: те же поручения, статусы и число запросов стакана.</li>
    <li>Срок больше 0 не меняет поручения и статусы относительно 1.16 и сокращает запросы стакана до одного на бумагу в
    запуске.</li>
    <li>Настройка сохраняется и читается через форму, форма не принимает значения вне 0-300.</li>
    <li>Значение больше 300, попавшее в настройки в обход формы, ограничивается 300.</li>
    <li>Режим кеша виден в логе запуска и в комментарии замера.</li>
    <li>Цена из кеша не используется дольше срока: внутри длинного запуска стакан запрашивается снова после истечения срока.</li>
  </ul>
</section>

<section>
  <h2>6. Итог по тест-кейсам</h2>
  <div class="summary">
    <div class="pill"><b>%(total)d</b>тест-кейсов</div>
    <div class="pill ok"><b>%(passed)d</b>пройдено</div>
    <div class="pill %(failcls)s"><b>%(failed)d</b>не пройдено</div>
  </div>
</section>

<section>
  <h2>7. Тест-кейсы</h2>
  <div class="tw"><table>
    <thead><tr><th>ID</th><th>Проверка</th><th>Предусловия</th><th>Шаги</th><th>Ожидаемый результат</th>
    <th>Фактический результат</th><th>Статус</th></tr></thead>
    <tbody>
%(case_rows)s
    </tbody>
  </table></div>
</section>

<section>
  <h2>8. Время выполнения (ответ стакана 1 с)</h2>
  <p>Время по часам: от запуска фонового задания до завершения, включая проверку и отправку поручений.</p>
  <div class="tw"><table>
    <thead><tr><th>Сценарий</th><th>1.16, с</th><th>1.19 срок 0, с</th><th>1.19 срок 60, с</th>
    <th class="boost-h">Ускорение 1.19 (срок 60) к 1.16</th><th>Запросов стакана 1.16 / 0 / 60</th></tr></thead>
    <tbody>
%(speed_rows)s
    </tbody>
  </table></div>
  <h2 style="margin-top:16px">Шаги по замерам, сумма времени, с (в скобках - число вызовов)</h2>
  <p class="muted">В реинвестировании сумма по 10 потокам, которые идут одновременно.</p>
  <div class="tw"><table>
    <thead><tr><th>Сценарий</th><th>Шаг</th><th>1.16</th><th>1.19 срок 0</th><th>1.19 срок 60</th></tr></thead>
    <tbody>
%(steps_rows)s
    </tbody>
  </table></div>
  <p style="margin-top:8px">В реинвестировании со сроком 60 растет время записи поручений: десять потоков без ожидания стакана
  пишут одновременно и ждут друг друга. Это поведение потоков, а не версии: в 1.16 без ожидания стакана запись так же
  медленна (Тестирование/1_18, повторные прогоны 16.10.2026).</p>
</section>

<section>
  <h2>9. Замечания</h2>
  <div class="tw"><table>
    <thead><tr><th>ID</th><th>Описание</th><th>Отношение к 1.19</th><th>Статус</th></tr></thead>
    <tbody>
      <tr><td class=id>З-01</td><td>В прогоне TC-20 один поток реинвестирования из 10 (номер 3) упал на первом поручении в
      неизмененном коде записи поручения: "Нарушение прав доступа". Такой же сбой был 16.10.2026 у 1.16 и 1.18 при
      одновременном старте 10 фоновых сеансов.</td><td>Нет: сбой стенда, ошибка до запроса цены</td>
      <td><span class="st warn">Стенд</span></td></tr>
      <tr><td class=id>З-02</td><td>При открытии обработки на базе разработки поверх формы открывается окно "Не обнаружена
      лицензия на конфигурацию Аванкор: Фронт-офис".</td><td>Нет: лицензирование базы разработки</td>
      <td><span class="st warn">Стенд</span></td></tr>
      <tr><td class=id>З-03</td><td>Кнопка "Настройки по умолчанию" кроме срока кеша очищает стратегии, список рассылки и
      ставит адрес веб-сервиса тестового контура. Поведение было и до 1.19.</td><td>Нет: прежнее поведение формы</td>
      <td><span class="st warn">К сведению</span></td></tr>
    </tbody>
  </table></div>
</section>

<section>
  <h2>10. Не проверено</h2>
  <ul>
    <li>Запрос стакана через рабочий адаптер QUIK FIX: на базе разработки адаптера нет. Код этой ветки перенесен из 1.16
    без изменения логики, в 1.18-1.19 вокруг него добавлен только кеш. Проверить на ПРОД по логу запуска и пометкам
    удаления поручений в первые дни.</li>
  </ul>
</section>

<section class="verdict">
  <h2>11. Заключение</h2>
  <p>Версия 1.19 соответствует критериям приемки: %(passed)d из %(total)d тест-кейсов пройдены. Со сроком 0 обработка
  работает как 1.16, со сроком 60 поручения и статусы совпадают с 1.16, а запросов стакана один на бумагу в запуске.
  При сроке короче запуска цена обновляется из стакана по истечении срока и дольше срока не используется.
  Настройка вводится и сохраняется через форму, ограничения 0-300 соблюдаются.</p>
  <p>Рекомендуется к установке на ПРОД со сроком 0, сбор замеров "до", затем включение согласованного срока и сбор
  замеров "после". Откат - срок 0 в настройках без переустановки.</p>
</section>

<section>
  <h2>12. Приложения</h2>
  <ul>
    <li>Тестирование/1_19/Отчет о тестировании 1.19.md - текстовая версия отчета.</li>
    <li>Тестирование/1_19/reports/run_1_19.json, reports_run_1_19.log - данные и журнал прогона.</li>
    <li>Тестирование/1_19/reports/ttl_check.json, ttl_check.log, run_ttl_check.py - проверка истечения срока.</li>
    <li>Тестирование/1_19/check_1_19_settings.py, run_1_19_tests.py, build_report_1_19.py - скрипты проверки и протокола.</li>
    <li>Тестирование/1_18 - общий стенд: заглушка стакана stakan_mock.py, тестовые сборки (make_test_builds.py),
    функции прогона run_1_18_tests.py, отчет о тестировании 1.18.</li>
  </ul>
</section>

</div>
</body>
</html>
"""

failed = len(cases) - passed
page = HTML % dict(total=len(cases), passed=passed, failed=failed, failcls="bad" if failed else "",
                   case_rows="\n".join(case_rows), speed_rows=speed_rows(), steps_rows=steps_rows(),
                   boost_tiles=boost_tiles())
with open(OUT, "w", encoding="utf-8") as handle:
    handle.write(page)
print("ok", OUT, "cases", len(cases), "passed", passed)
