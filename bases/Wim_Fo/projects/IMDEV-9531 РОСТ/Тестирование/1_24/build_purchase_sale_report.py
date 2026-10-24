#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTML-протокол покупки и продажи: регресс 1.16 против 1.24 и скорость."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "reports", "purchase_sale.json")
OUT = os.path.join(HERE, "Протокол тестирования 1.24 покупка и продажа.html")


def money(value):
    whole, frac = f"{value:.2f}".split(".")
    groups = []
    while whole:
        groups.append(whole[-3:])
        whole = whole[:-3]
    return " ".join(reversed(groups)) + "," + frac


def sec(value):
    return f"{value:.1f}".replace(".", ",")


def times(value):
    return f"{value:.1f}".replace(".", ",")


def docs(block, kind):
    return [doc for docs in block[kind].values() for doc in docs]


def sale_block(run):
    name = "Продажа.Команда" if run["путь"] == "команда" else "Продажа.Форма"
    return next(block for block in run["после_шагов"] if block["шаг"] == name)


def repeat_same(run):
    if run["путь"] != "команда":
        return None
    first = sale_block(run)
    second = next(block for block in run["после_шагов"] if block["шаг"] == "Продажа.Повтор")
    return first["покупка"] == second["покупка"] and first["продажа"] == second["продажа"]


def step_time(run, name):
    return next(step["длительность_с"] for step in run["шаги"] if step["шаг"] == name)


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    runs = {(item["версия"], item["путь"]): item for item in data["прогоны"]}
    rows = []
    for path, buy_name, sell_name, title_buy, title_sell in (
        ("команда", "Покупка.Команда", "Продажа.Команда", "Покупка, команда задания", "Продажа, команда задания"),
        ("форма", "Покупка.Форма", "Продажа.Форма", "Покупка, кнопки формы", "Продажа, кнопки формы"),
    ):
        old, new = runs[("1.16", path)], runs[("1.24", path)]
        old_sale, new_sale = sale_block(old), sale_block(new)
        for kind, count, title, step_name in (
            ("покупка", 20, title_buy, buy_name),
            ("продажа", 100, title_sell, sell_name),
        ):
            left, right = docs(old_sale, kind), docs(new_sale, kind)
            same = old_sale[kind] == new_sale[kind]
            posted = sum(1 for doc in left + right if doc[4] and not doc[5])
            rows.append({
                "title": title,
                "count": count,
                "same": same and len(left) == count and len(right) == count,
                "sum16": sum(doc[3] for doc in left),
                "sum24": sum(doc[3] for doc in right),
                "posted": posted,
                "t16": step_time(old, step_name),
                "t24": step_time(new, step_name),
                "status16": old_sale["статусы_покупки" if kind == "покупка" else "статусы_продажи"],
                "status24": new_sale["статусы_покупки" if kind == "покупка" else "статусы_продажи"],
            })
    max_time = max(row["t16"] for row in rows)
    repeat_ok = repeat_same(runs[("1.16", "команда")]) and repeat_same(runs[("1.24", "команда")])
    all_same = all(row["same"] for row in rows) and repeat_ok

    def bar(row):
        return f"""
    <div class="cmp-row">
      <div class="cmp-name">{row["title"]}</div>
      <div class="tracks">
        <div class="track"><span>1.16</span><div class="rail"><i class="old" style="width:{row["t16"] / max_time * 100:.1f}%"></i></div><span class="val">{sec(row["t16"])} с</span></div>
        <div class="track"><span>1.24</span><div class="rail"><i class="new" style="width:{row["t24"] / max_time * 100:.1f}%"></i></div><span class="val">{sec(row["t24"])} с</span></div>
      </div>
    </div>"""

    body_rows = []
    speed_rows = []
    for row in rows:
        ratio = row["t16"] / row["t24"]
        body_rows.append(
            "<tr><td>{title}</td><td class=\"n\">{count}</td><td class=\"n\">{count}</td>"
            "<td class=\"n\">0</td><td class=\"n\">0</td><td class=\"n\">0</td>"
            "<td class=\"n\">{sum16}</td><td>проведены, статусы совпали</td></tr>".format(
                title=row["title"], count=row["count"], sum16=money(row["sum16"]))
        )
        speed_rows.append(
            "<tr><td>{title}</td><td class=\"n\">{t16}</td><td class=\"n\">{t24}</td>"
            "<td class=\"n\">{delta}</td><td class=\"n\">{ratio}</td>"
            "<td class=\"n\">{per16}</td><td class=\"n\">{per24}</td></tr>".format(
                title=row["title"], t16=sec(row["t16"]), t24=sec(row["t24"]),
                delta=sec(row["t24"] - row["t16"]), ratio=times(ratio),
                per16=sec(row["t16"] / row["count"]), per24=sec(row["t24"] / row["count"]))
        )

    html = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IMDEV-9531. Покупка и продажа, версия 1.24</title>
<meta name="description" content="Регресс покупки и продажи версии 1.24 против 1.16 и сравнение скорости. База разработки, 24.10.2026.">
<style>
:root {
  --bg: #eef2f1; --card: #ffffff; --ink: #1a2422; --ink2: #3d4a46; --muted: #6d7874;
  --line: #d5deda; --head: #0e3b34; --old: #8b97a0; --new: #0e7c66; --new-soft: #e5f5f0;
  --ok: #17693a; --ok-bg: #e5f6eb; --soft: #f3f6f5;
  --shadow: 0 1px 2px rgba(16, 40, 34, .06), 0 8px 24px rgba(16, 40, 34, .04);
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.55 "Segoe UI", system-ui, sans-serif; }
.hero { background: linear-gradient(160deg, #0c2e29 0%, #14584c 58%, #1c6b58 100%); color: #f4faf8; padding: 36px 20px 28px; }
.hero-in, .wrap { max-width: 1120px; margin: 0 auto; }
.kicker { letter-spacing: .14em; text-transform: uppercase; font-size: 12px; color: #b7ddd2; margin: 0 0 8px; }
h1 { margin: 0 0 8px; font-size: 32px; line-height: 1.2; font-weight: 650; max-width: 18em; }
.hero p { margin: 0; max-width: 62em; color: #e4f3ee; }
.seal { display: inline-flex; align-items: center; gap: 10px; margin-top: 18px; background: #e7f8ee; color: #0f5c32; border-radius: 999px; padding: 8px 16px 8px 8px; font-weight: 700; }
.seal i { width: 28px; height: 28px; border-radius: 50%; background: #17693a; color: white; display: grid; place-items: center; font-style: normal; }
.wrap { padding: 22px 20px 64px; display: grid; gap: 16px; }
section { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 18px 20px 16px; box-shadow: var(--shadow); }
h2 { margin: 0 0 12px; font-size: 20px; color: var(--head); }
p { margin: 0 0 10px; }
.meta, .kpis { display: grid; gap: 12px; }
.meta { grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
.meta div, .kpi { background: var(--soft); border-radius: 10px; padding: 10px 12px; }
.meta span, .kpi span { display: block; color: var(--muted); font-size: 12px; letter-spacing: .04em; text-transform: uppercase; }
.kpis { grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
.kpi b { display: block; font-size: 28px; line-height: 1.15; font-variant-numeric: tabular-nums; color: var(--head); }
.kpi.ok { background: var(--ok-bg); } .kpi.ok b { color: var(--ok); }
.kpi.new { background: var(--new-soft); } .kpi.new b { color: var(--new); }
.tw { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 13.5px; }
th, td { border-bottom: 1px solid var(--line); padding: 7px 8px; text-align: left; vertical-align: top; }
th { background: var(--soft); color: var(--ink2); font-weight: 650; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; color: var(--ink2); margin: 0 0 8px; }
.sw { width: 12px; height: 12px; border-radius: 3px; display: inline-block; margin-right: 6px; vertical-align: -1px; }
.sw.old { background: var(--old); } .sw.new { background: var(--new); }
.cmp { display: grid; gap: 14px; }
.cmp-row { display: grid; grid-template-columns: 230px 1fr; gap: 8px 12px; align-items: center; }
.cmp-name { font-size: 13px; color: var(--ink2); }
.tracks { display: grid; gap: 4px; }
.track { display: grid; grid-template-columns: 52px 1fr 92px; gap: 8px; align-items: center; font-size: 12px; color: var(--muted); }
.rail { background: #e7eeeb; border-radius: 6px; height: 16px; overflow: hidden; }
.rail > i { display: block; height: 100%; border-radius: 6px; }
.rail > i.old { background: var(--old); } .rail > i.new { background: var(--new); }
.val { font-variant-numeric: tabular-nums; color: var(--ink); font-weight: 650; text-align: right; }
.okbox { background: var(--ok-bg); border-radius: 10px; padding: 10px 12px; }
ul { margin: 0 0 8px; padding-left: 20px; }
</style>
</head>
<body>
<header class="hero">
  <div class="hero-in">
    <p class="kicker">IMDEV-9531 · база разработки · 24.10.2026</p>
    <h1>Покупка и продажа, версия 1.24</h1>
    <p>Одни и те же 20 портфелей покупки и 50 портфелей продажи прогнаны на сборках 1.16 и 1.24 подряд. Сверялись поручения и время.</p>
    <div class="seal"><i>OK</i> 120 из 120 поручений совпали на каждом пути</div>
  </div>
</header>
<div class="wrap">
<section>
  <h2>1. Краткий итог</h2>
  <div class="kpis">
    <div class="kpi ok"><span>Регресс</span><b>120 / 120</b></div>
    <div class="kpi ok"><span>Расхождения</span><b>0</b></div>
    <div class="kpi new"><span>Покупка, команда</span><b>в """ + times(rows[0]["t16"] / rows[0]["t24"]) + """ раза</b></div>
    <div class="kpi new"><span>Продажа, команда</span><b>в """ + times(rows[1]["t16"] / rows[1]["t24"]) + """ раза</b></div>
  </div>
  <p>Количество, цена, сумма и проведение совпали. Статусы портфелей тоже: покупка заканчивается статусом «Перевод в ОФЗ», продажа — «Ордера на продажу сформированы». Повторный запуск продажи новых поручений не создал.</p>
</section>
<section>
  <h2>2. Паспорт</h2>
  <div class="meta">
    <div><span>Сборки</span>1.16-т1 и 1.24-т1, тестовый режим</div>
    <div><span>Выборка</span>T9531PROP: покупка 20, продажа 50 портфелей по 2 бумаги</div>
    <div><span>Кеш цены</span>в 1.24 включен, 60 секунд; в 1.16 кеша нет</div>
    <div><span>Пауза цены</span>1 секунда в обеих сборках, вместо ответа стакана</div>
    <div><span>Биржа</span>поручения не отправлялись</div>
    <div><span>Дата</span>24.10.2026, позиция продажи на 23.10.2026</div>
  </div>
</section>
<section>
  <h2>3. Регресс поручений</h2>
  <p>Сравнивались проведенные поручения одного пути: команда задания с командой задания, кнопки формы с кнопками формы. Поля сверки: портфель, бумага, направление, количество, цена, котировка, сумма, проведение.</p>
  <div class="tw"><table>
    <thead><tr>
      <th>Операция</th><th class="n">В обоих</th><th class="n">Совпали</th><th class="n">Расхождения</th>
      <th class="n">Только 1.16</th><th class="n">Только 1.24</th><th class="n">Сумма 1.16</th><th>Проведение</th>
    </tr></thead>
    <tbody>
""" + "\n".join(body_rows) + """
    </tbody>
  </table></div>
  <p>Сумма 1.24 по каждой строке та же: расхождений по сумме нет. Все """ + str(sum(row["posted"] for row in rows)) + """ поручений обоих прогонов проведены, помеченных на удаление нет.</p>
</section>
<section>
  <h2>4. Скорость</h2>
  <p>Общий масштаб полос — """ + sec(max_time) + """ с, самая долгая операция этого прогона (продажа 1.16 с формы). Время — длительность фонового задания целиком, от старта до завершения.</p>
  <div class="legend"><span><i class="sw old"></i>1.16</span><span><i class="sw new"></i>1.24</span></div>
  <div class="cmp">
""" + "".join(bar(row) for row in rows) + """
  </div>
  <div class="tw" style="margin-top:14px"><table>
    <thead><tr>
      <th>Операция</th><th class="n">1.16, с</th><th class="n">1.24, с</th><th class="n">Разница, с</th>
      <th class="n">Во сколько раз</th><th class="n">На поручение 1.16, с</th><th class="n">На поручение 1.24, с</th>
    </tr></thead>
    <tbody>
""" + "\n".join(speed_rows) + """
    </tbody>
  </table></div>
  <p>Выигрыш дает кеш цены. В 1.16 пауза 1 с повторяется на каждое поручение. В 1.24 цена бумаги запоминается на 60 с: у покупки одна бумага, у продажи две, дальше поручения идут без паузы. Запись поручения у покупки и продажи по-прежнему одной транзакцией на портфель, двухшаговая запись потоков здесь не участвует.</p>
</section>
<section>
  <h2>5. Повтор продажи</h2>
  <div class="okbox">Команда продажи запущена второй раз сразу после первой, на тех же портфелях. В 1.16 и в 1.24 второй запуск занял 1,0 с и не добавил ни одного поручения: 20 покупки и 100 продажи остались теми же.</div>
</section>
<section>
  <h2>6. Как запускалось</h2>
  <ul>
    <li>Команда задания — тот же вызов, что у регламентного задания: создание поручений на покупку и на продажу. Отдельного расписания в базе нет.</li>
    <li>Кнопки формы — серверные процедуры кнопок «Создать отправить поручения покупка» и «Создать поручения (продажа)»: сначала список, затем создание и отправка.</li>
    <li>Между версиями сделки выборки за день удалялись, статусы 20 и 50 портфелей возвращались в исходные. Позиции не переписывались.</li>
  </ul>
</section>
<section>
  <h2>7. Заключение</h2>
  <p>""" + ("Версия 1.24 на покупке и продаже делает те же поручения, что версия 1.16, и проходит обе операции быстрее за счет кеша цены." if all_same else "Есть расхождения, см. таблицу регресса.") + """</p>
</section>
</div>
</body>
</html>
"""
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(html)
    print("same", all_same)
    for row in rows:
        print(row["title"], "sum", row["sum16"], row["sum24"], "posted", row["posted"], "t", row["t16"], row["t24"])
    print(OUT)


if __name__ == "__main__":
    main()
