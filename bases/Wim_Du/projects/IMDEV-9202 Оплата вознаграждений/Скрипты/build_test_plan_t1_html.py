#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate detailed IMDEV-9202 T-1 test plan HTML with embedded screenshots."""

import base64
import pathlib

ROOT = pathlib.Path(r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-9202 Оплата вознаграждений")
ASSETS = ROOT / "Документация" / "test_plan_t1_assets"
OUT = ROOT / "Документация" / "test_plan_t1_detailed.html"


def img(name: str) -> str:
    data = (ASSETS / name).read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f'data:image/png;base64,{b64}'


I = {f"image{n}.png": img(f"image{n}.png") for n in range(1, 13)}

html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IMDEV-9202. План и результаты тестирования на Т-1</title>
<style>
:root {{
  --navy: #1f3c88; --ok: #28a745; --ok-bg: #eaf7ec; --err: #dc3545; --err-bg: #fdecee;
  --info: #17a2b8; --info-bg: #e8f4fc; --warn: #b78103; --warn-bg: #fff8e1;
  --text: #1c2430; --muted: #5c6570; --line: #d9dee3; --bg: #eef1f5;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: Calibri, "Segoe UI", Arial, sans-serif; color: var(--text); background: var(--bg); line-height: 1.5; font-size: 15px; }}
.page {{ max-width: 1100px; margin: 0 auto; background: #fff; box-shadow: 0 12px 40px rgba(31,60,136,.12); }}
.hero {{ background: linear-gradient(135deg, #16306e 0%, #1f3c88 55%, #2a56b8 100%); color: #fff; padding: 28px 36px 22px; }}
.hero h1 {{ margin: 0 0 8px; font-size: 24px; font-weight: 600; }}
.hero .lead {{ margin: 0 0 16px; opacity: .95; }}
.kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }}
.kpi {{ background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.22); border-radius: 8px; padding: 10px 12px; }}
.kpi .v {{ font-size: 20px; font-weight: 700; display: block; }}
.kpi .l {{ font-size: 12px; opacity: .85; }}
.content {{ padding: 8px 36px 40px; }}
h2 {{ font-size: 19px; color: var(--navy); margin: 28px 0 10px; padding-bottom: 6px; border-bottom: 2px solid #e3e8ef; }}
h3 {{ font-size: 16px; color: #24365c; margin: 18px 0 8px; }}
p {{ margin: 0 0 10px; }}
ul, ol {{ margin: 0 0 12px; padding-left: 22px; }}
li {{ margin-bottom: 5px; }}
.box {{ border-left: 5px solid var(--info); background: var(--info-bg); padding: 12px 16px; margin: 12px 0 16px; }}
.box.good {{ border-left-color: var(--ok); background: var(--ok-bg); }}
.box.warn {{ border-left-color: #ffc107; background: var(--warn-bg); }}
.box.bad {{ border-left-color: var(--err); background: var(--err-bg); }}
table.grid {{ width: 100%; border-collapse: collapse; font-size: 14px; margin: 10px 0 16px; }}
table.grid th, table.grid td {{ border: 1px solid var(--line); padding: 8px 10px; vertical-align: top; text-align: left; }}
table.grid th {{ background: #eef2f7; color: #26385c; }}
table.grid tr:nth-child(even) td {{ background: #fafbfc; }}
.shot {{ margin: 12px 0 18px; border: 1px solid var(--line); background: #fafbfc; }}
.shot img {{ display: block; max-width: 100%; height: auto; }}
.shot .cap {{ padding: 8px 12px; font-size: 13px; color: var(--muted); border-top: 1px solid var(--line); }}
.step {{ border: 1px solid var(--line); margin: 0 0 16px; }}
.step .hd {{ background: #f0f3f8; padding: 10px 14px; font-weight: 700; color: var(--navy); border-bottom: 1px solid var(--line); }}
.step .bd {{ padding: 12px 14px; }}
.two {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 10px 0 16px; }}
.card {{ border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; }}
.card.was {{ border-top: 4px solid var(--err); background: var(--err-bg); }}
.card.will {{ border-top: 4px solid var(--ok); background: var(--ok-bg); }}
.chart-wrap {{ margin: 14px 0 18px; padding: 14px; border: 1px solid var(--line); background: #fafbfc; }}
.chart-wrap h3 {{ margin-top: 0; }}
.bar-row {{ display: flex; align-items: center; margin: 8px 0; font-size: 13px; }}
.bar-lbl {{ width: 210px; flex-shrink: 0; color: #334; }}
.bar-track {{ flex: 1; background: #e8edf3; height: 28px; position: relative; border-radius: 4px; overflow: hidden; }}
.bar-fill {{ height: 28px; display: flex; align-items: center; padding-left: 10px; color: #fff; font-weight: 700; font-size: 13px; }}
.bar-fill.slow {{ background: #dc3545; }}
.bar-fill.fast {{ background: #28a745; }}
.bar-fill.mid {{ background: #17a2b8; }}
.muted {{ color: var(--muted); font-size: 13px; }}
code {{ background: #f4f6f8; padding: 1px 5px; border-radius: 3px; font-size: 13px; }}
pre {{ background: #f4f6f8; border: 1px solid var(--line); padding: 12px 14px; overflow: auto; font-size: 13px; margin: 8px 0 14px; white-space: pre-wrap; }}
.toc a {{ color: var(--navy); text-decoration: none; }}
.toc li {{ margin-bottom: 4px; }}
.footer {{ padding: 14px 36px 28px; border-top: 1px solid var(--line); color: var(--muted); font-size: 13px; }}
@media (max-width: 800px) {{
  .kpis, .two {{ grid-template-columns: 1fr 1fr; }}
}}
</style>
</head>
<body>
<div class="page">

<div class="hero">
  <div class="muted" style="color:#cfe0ff;margin-bottom:6px;">IMDEV-9202 · база Т-1 · день 11.08.2026 · прогон 21.08.2026</div>
  <h1>План и результаты тестирования: поступления на р/с Розничное ДУ</h1>
  <p class="lead">Что разработали, как тестировали на Т-1, какой прирост скорости получили, что уточнили по расхождению ЕБС/ЕРС и планам бизнеса.</p>
  <div class="kpis">
    <div class="kpi"><span class="v">5 052</span><span class="l">документов за день</span></div>
    <div class="kpi"><span class="v">15,14</span><span class="l">док/с параллельно</span></div>
    <div class="kpi"><span class="v">~4,7x</span><span class="l">быстрее последовательного</span></div>
    <div class="kpi"><span class="v">0</span><span class="l">ошибок создания</span></div>
  </div>
</div>

<div class="content">

<div class="box good">
<strong>Итог приёмки на Т-1.</strong> Обе платежки «Перевод» обработаны; создано <b>5 028</b> поступлений параллельно (332 с) + <b>24</b> последовательно (7,5 с); ошибок 0.
Текущие версии к внедрению: <code>внЗагрузкаВыписокДУ</code> <b>6.05</b>, <code>внПоступленияНаРасчетныйСчет_РозничноеДУ</code> <b>1.10</b>
(на скринах прогона выписка ещё <b>6.04</b> — функционально тот же релизный контур).
</div>

<ol class="toc">
  <li><a href="#s1">1. Что разработали</a></li>
  <li><a href="#s2">2. Стенд и исходные данные</a></li>
  <li><a href="#s3">3. План тестирования (пошагово)</a></li>
  <li><a href="#s4">4. Результаты по скорости</a></li>
  <li><a href="#s5">5. Регресс снимков</a></li>
  <li><a href="#s6">6. Уточнение по ЕБС/ЕРС и Оплате ВУК</a></li>
  <li><a href="#s7">7. Критерии приёмки</a></li>
</ol>

<!-- ========== 1 ========== -->
<h2 id="s1">1. Что разработали</h2>

<table class="grid">
<tr><th>Обработка</th><th>Оригинал</th><th>Оптимизация</th><th>Суть</th></tr>
<tr>
  <td><code>внЗагрузкаВыписокДУ</code></td>
  <td>6.00</td>
  <td><b>6.05</b></td>
  <td>Две платежки «Перевод» в одном дне; {{ВнешниеОбработки.Создать(..., Ложь)}}; краткая диагностика сумм</td>
</tr>
<tr>
  <td><code>внПоступленияНаРасчетныйСчет_РозничноеДУ</code></td>
  <td>1.04 (БР=Истина)</td>
  <td><b>1.10</b> (БР=Ложь)</td>
  <td>Параллель 5×50; fallback; фикс JOIN/РАЗЛИЧНЫЕ; идемпотентность; замеры</td>
</tr>
<tr>
  <td><code>внТестСбросПоступленийРДУ</code> (тест)</td>
  <td>—</td>
  <td>1.10+</td>
  <td>Сброс/снимок/регресс для повторяемых прогонов</td>
</tr>
</table>

<div class="two">
  <div class="card was">
    <h3>Было (узкое место)</h3>
    <ul>
      <li>Последовательное проведение каждого поступления (~3 док/с)</li>
      <li>Одна платежка: если в выборке и расторжение, и ВУК — сверка суммы ломается</li>
      <li>Безопасный режим блокировал фон при старте из выписки</li>
    </ul>
  </div>
  <div class="card will">
    <h3>Стало</h3>
    <ul>
      <li>~15 док/с на пачке &gt;50 (5 потоков)</li>
      <li>Отбор группы «Перевод ДС при расторжении» / остаток под вторую платежку</li>
      <li>Фон работает: SafeMode=Нет у поступлений + Создать(..., Ложь) из выписки</li>
    </ul>
  </div>
</div>

<!-- ========== 2 ========== -->
<h2 id="s2">2. Стенд и исходные данные</h2>
<table class="grid">
<tr><th>Параметр</th><th>Значение</th></tr>
<tr><td>База</td><td>Т-1 (копия контура для проверки)</td></tr>
<tr><td>Операционный день</td><td><b>11.08.2026</b></td></tr>
<tr><td>Пул / счёт</td><td>Розничное ДУ · р/с_ВТБ_ДС_RUR_EPC · Только Перевод</td></tr>
<tr><td>Платежки в выписке</td><td>№<b>274957</b> = 7 581 485,57 · №<b>279725</b> = 50 932 652,00</td></tr>
<tr><td>Объём поступлений за день</td><td><b>5 052</b> проведённых, сумма 58 514 137,57</td></tr>
<tr><td>Дата прогона</td><td>21.08.2026, старт ~07:39, финиш ~07:44:42</td></tr>
</table>

<!-- ========== 3 ========== -->
<h2 id="s3">3. План тестирования (пошагово)</h2>
<p>Основание: <code>План тестирования 9202 на Т_1.docx</code>. Ниже — тот же сценарий с пояснениями «зачем» и скриншотами.</p>

<div class="step">
  <div class="hd">Шаг 1. Выбрать день и оценить объём</div>
  <div class="bd">
    <p><b>Действие.</b> В тестовой обработке «сброс поступлений РДУ» указать период, дату операции <b>11.08.2026</b>, пул Розничное ДУ, «Только Перевод» → <b>Заполнить</b>.</p>
    <p><b>Ожидание.</b> В таблице день 11.08 показывает ~5 052 проведённых документов — это целевой объём нагрузочного прогона.</p>
    <div class="shot"><img src="{I['image1.png']}" alt="Статистика по дням, выбран 11.08"><div class="cap">Рис. 1. Статистика поступлений: день 11.08.2026 — 5 052 документа.</div></div>
  </div>
</div>

<div class="step">
  <div class="hd">Шаг 2. Заполнить банковскую выписку за 11.08</div>
  <div class="bd">
    <p><b>Действие.</b> Открыть «Банковские выписки», дата 11.08.2026, тип счетов ДУ, только ЕРС → прочитать/разобрать.</p>
    <p><b>Ожидание.</b> В выписке видны две платежки «Перевод» с суммами 7 581 485,57 и 50 932 652.</p>
    <div class="shot"><img src="{I['image2.png']}" alt="Заполнение выписки"><div class="cap">Рис. 2. Настройки выписки за 11.08.2026.</div></div>
    <div class="shot"><img src="{I['image3.png']}" alt="Две платежки в выписке"><div class="cap">Рис. 3. Две платежки Перевод в одном дне (основание сценария «две платежки»).</div></div>
  </div>
</div>

<div class="step">
  <div class="hd">Шаг 3. Снимок «было» и сброс поступлений</div>
  <div class="bd">
    <p><b>Действие.</b> Вспомогательной обработкой: сохранить снимок для регресса → удалить поступления за день → вернуть поручениям статус <b>Новый</b>.</p>
    <p><b>Зачем.</b> Повторяемый прогон «с нуля» и эталон для сравнения полей после пересоздания.</p>
    <div class="shot"><img src="{I['image4.png']}" alt="Форма сброса"><div class="cap">Рис. 4. Подготовка сброса: дата операции 11.08, пул Розничное ДУ.</div></div>
    <div class="shot"><img src="{I['image5.png']}" alt="Удаление документов"><div class="cap">Рис. 5. Удаление ранее созданных поступлений (параллельный сброс).</div></div>
    <div class="shot"><img src="{I['image6.png']}" alt="Статус после удаления"><div class="cap">Рис. 6. После удаления: поручения готовы к повторному созданию поступлений.</div></div>
  </div>
</div>

<div class="step">
  <div class="hd">Шаг 4. Запустить «Зачисления на р/с Розничного ДУ»</div>
  <div class="bd">
    <p><b>Действие.</b> В форме выписки нажать кнопку <b>«Зачисления на р/с Розничного ДУ»</b>. Дождаться окончания (старт ~07:39).</p>
    <p><b>Ожидание системы.</b> Выписка создаёт обработку поступлений без безопасного режима; для Перевод при необходимости отбирает группу под первую платежку, создаёт пачку, затем вторую платежку по остатку; поступления идут параллельно порциями по 50.</p>
    <div class="shot"><img src="{I['image7.png']}" alt="Кнопка Зачисления"><div class="cap">Рис. 7. Кнопка запуска сценария из банковской выписки.</div></div>
    <div class="shot"><img src="{I['image8.png']}" alt="Ожидание выполнения"><div class="cap">Рис. 8. Выполнение массового создания (ожидание).</div></div>
  </div>
</div>

<div class="step">
  <div class="hd">Шаг 5. Проверить сообщения и замеры</div>
  <div class="bd">
    <p><b>Действие.</b> Вернуться на вкладку выписки, прочитать окно сообщений и автозамеры.</p>
    <p><b>Факт прогона 21.08.2026 07:44:42:</b></p>
<pre>IMDEV-9202 Создать: Режим=Параллельно, потоков=5, порция=50; БезопасныйРежим=Нет;
  Порций=101; Документов=5028; Создано=5028; Ошибок=0; УдельныйВес=15,14 док/с; Время=332,0 сек

IMDEV-9202 Создать: Режим=Последовательно; Документов=24; Создано=24; Ошибок=0;
  УдельныйВес=3,21 док/с; Время=7,5 сек

Все выполнено. (Обе платежки успешно обработаны)</pre>
    <div class="shot"><img src="{I['image9.png']}" alt="Сообщения о скорости"><div class="cap">Рис. 9. Сообщения: параллель 15,14 док/с на 5 028 док. + хвост 24 док. последовательно.</div></div>
    <div class="shot"><img src="{I['image10.png']}" alt="Автозамеры"><div class="cap">Рис. 10. Замеры производительности внесены автоматически.</div></div>
  </div>
</div>

<div class="step">
  <div class="hd">Шаг 6. Снимок «стало» и сравнение регресса</div>
  <div class="bd">
    <p><b>Действие.</b> Сохранить снимок после создания → сравнить с эталоном «было».</p>
    <div class="shot"><img src="{I['image11.png']}" alt="Сохранение снимка"><div class="cap">Рис. 11. Сохранение снимка «стало».</div></div>
    <div class="shot"><img src="{I['image12.png']}" alt="Сравнение регресса ЕБС ЕРС"><div class="cap">Рис. 12. Регресс: отличия полей ДоговорКонтрагента (ЕБС→ЕРС), СчетКонтрагента, НазначениеПлатежа — см. раздел 6.</div></div>
  </div>
</div>

<!-- ========== 4 ========== -->
<h2 id="s4">4. Результаты по скорости</h2>

<div class="chart-wrap">
  <h3>Скорость создания, док/с</h3>
  <p class="muted">Параллельный режим vs фактический последовательный хвост того же прогона (эталон «как оригинал» по темпу).</p>
  <div class="bar-row">
    <div class="bar-lbl">Параллельно (5 потоков)</div>
    <div class="bar-track"><div class="bar-fill fast" style="width:100%">15,14 док/с · 5 028 док · 332 с</div></div>
  </div>
  <div class="bar-row">
    <div class="bar-lbl">Последовательно (хвост)</div>
    <div class="bar-track"><div class="bar-fill slow" style="width:21%">3,21 док/с · 24 док · 7,5 с</div></div>
  </div>
  <p class="muted">Отношение 15,14 / 3,21 ≈ <b>4,7×</b>.</p>
</div>

<div class="chart-wrap">
  <h3>Время на полный объём дня (~5 052 док.)</h3>
  <p class="muted">Оценка «если весь день гнать последовательно» при 3,21 док/с vs факт прогона.</p>
  <div class="bar-row">
    <div class="bar-lbl">Оценка последовательно</div>
    <div class="bar-track"><div class="bar-fill slow" style="width:100%">~1 574 с (~26 мин)</div></div>
  </div>
  <div class="bar-row">
    <div class="bar-lbl">Факт (параллель + хвост)</div>
    <div class="bar-track"><div class="bar-fill fast" style="width:22%">~340 с (~5,7 мин)</div></div>
  </div>
  <p class="muted">Экономия порядка <b>20 минут</b> на этом дне (~4,6× быстрее полной последовательной оценки).</p>
</div>

<svg viewBox="0 0 640 220" width="100%" style="margin:8px 0 16px;background:#fafbfc;border:1px solid #d9dee3;">
  <text x="20" y="28" fill="#1f3c88" font-size="14" font-family="Calibri,Arial" font-weight="700">Сравнение времени на ~5052 документа</text>
  <!-- slow bar -->
  <rect x="160" y="55" width="440" height="42" fill="#dc3545" rx="4"/>
  <text x="20" y="82" fill="#334" font-size="13" font-family="Calibri,Arial">Последовательно</text>
  <text x="175" y="82" fill="#fff" font-size="13" font-family="Calibri,Arial" font-weight="700">~1574 сек (~26 мин)</text>
  <!-- fast bar -->
  <rect x="160" y="120" width="95" height="42" fill="#28a745" rx="4"/>
  <text x="20" y="147" fill="#334" font-size="13" font-family="Calibri,Arial">Оптимизация</text>
  <text x="175" y="147" fill="#fff" font-size="13" font-family="Calibri,Arial" font-weight="700">~340 сек</text>
  <text x="20" y="200" fill="#5c6570" font-size="12" font-family="Calibri,Arial">Т-1, 11.08.2026 · 5 потоков · порция 50 · ошибки 0</text>
</svg>

<table class="grid">
<tr><th>Метрика</th><th>Значение</th></tr>
<tr><td>Документов параллельно</td><td>5 028 / создано 5 028 / ошибок 0</td></tr>
<tr><td>Порций</td><td>101 × 50 (потоков 5)</td></tr>
<tr><td>Время параллели</td><td>332,0 с · 15,14 док/с</td></tr>
<tr><td>Хвост последовательно</td><td>24 док · 7,5 с · 3,21 док/с</td></tr>
<tr><td>Обе платежки</td><td>Успешно обработаны</td></tr>
<tr><td>Ранний замер (45 док., оригинал)</td><td>~14 с на 45 ≈ 3,2 док/с — согласуется с хвостом</td></tr>
</table>

<!-- ========== 5 ========== -->
<h2 id="s5">5. Регресс снимков</h2>
<p>Сравнение «было» (исходные поступления на Т-1) vs «стало» (пересозданные через выписку оптимизированными обработками) показывает отличия полей, в первую очередь:</p>
<ul>
  <li><b>ДоговорКонтрагента:</b> ЕБС_* → ЕРС_*</li>
  <li><b>СчетКонтрагента:</b> был единый брокерский счёт → в новом пусто / по правилам выписки</li>
  <li><b>НазначениеПлатежа:</b> добавлен фрагмент «по распоряжению от 11.08.2026» (текст выписки)</li>
</ul>
<div class="box warn">
<strong>Это не регрессия параллельного создания.</strong> Оптимизация не меняет состав заполнения реквизитов поступления:
договор по-прежнему берётся <b>из поручения</b>, назначение — <b>из выписки</b>.
Отличия отражают смену <b>пути создания</b> (Оплата КЗ → выписка) и текущие данные поручений. Разбор — в разделе 6.
</div>

<!-- ========== 6 ========== -->
<h2 id="s6">6. Уточнение по ЕБС/ЕРС и Оплате ВУК</h2>
<p>В исходном плане стояло «!! уточнить!!» на примере МИИ733 (ЕБС→ЕРС, счёт контрагента, назначение).</p>

<h3>6.1. Наше предположение (подтверждено разбором и кодом)</h3>
<table class="grid">
<tr><th></th><th>Путь A — выписка</th><th>Путь B — Оплата КЗ</th></tr>
<tr><td>Когда</td><td>«Зачисления на р/с Розничного ДУ»</td><td>«Сформировать поступление…» в ОплатаКЗ</td></tr>
<tr><td>Типичный комментарий поручения</td><td>Перевод ДС при расторжении</td><td>Оплата ВУК / Оплата НДФЛ</td></tr>
<tr><td>ДоговорКонтрагента в поступлении</td><td>Из <b>поручения</b> (часто ЕРС)</td><td>Из аналитического счёта плательщика (часто <b>ЕБС</b>)</td></tr>
<tr><td>Назначение</td><td>Текст выписки (+ «по распоряжению от…»)</td><td>Шаблон обработки, без текста выписки</td></tr>
<tr><td>Ответственный</td><td>Пусто</td><td>Текущий пользователь</td></tr>
</table>
<p>На ПРОД сейчас поступления по <b>Оплате ВУК</b> в основном создаются путём B (Оплата КЗ) — отсюда «ЕБС» в эталонном снимке.
При пересоздании на Т-1 через выписку срабатывает путь A → в поступление уходит договор <b>как в поручении</b> (ЕРС) и текст выписки.</p>

<h3>6.2. Что сказал бизнес (Кукушкин В.Ю.) — переписка «RE: вопрос по поступлению…»</h3>
<div class="box good">
<ul style="margin:0;">
  <li><b>Сейчас</b> поступления по Оплате ВУК действительно делаются из <b>Оплаты КЗ</b>.</li>
  <li><b>План:</b> поступления по Оплате ВУК будут создавать из <b>банковской выписки</b> (наша обработка «Поступления… Розничное ДУ»).</li>
  <li><b>Причина ЕРС в поручении ВУК</b> — ошибка формирования поручения (вендор / оплата КЗ). Будет задача: в поручении ставить <b>корректный договор брокерского счёта (ЕБС)</b> вместо расчётного (ЕРС).</li>
  <li>Править следствие в нашей обработке «насильно» не нужно — «бороться с причиной, а не с последствием». Если вендор не справится — помощь по доработке возможна.</li>
  <li>На Т-1 можно ставить нашу оптимизацию для проверки (подтверждение в переписке 24.08.2026).</li>
</ul>
</div>

<h3>6.3. Как читать отличия регресса после уточнения</h3>
<ol>
  <li>Расхождение ЕБС→ЕРС на Т-1 при пересоздании через выписку — <b>ожидаемо</b> при текущих (ещё не исправленных) поручениях ВУК с ЕРС.</li>
  <li>После исправления поручений вендором путь A начнёт подставлять уже <b>правильный ЕБС</b> из поручения — целевая модель совпадёт с бизнесом.</li>
  <li>Для приёмки IMDEV-9202 (ускорение): критерий — совпадение нового поступления с правилами <b>заполнения из поручения/выписки</b>, 0 ошибок, обе платежки, скорость; не «байт-в-байт» с эталоном, созданным путём ОплатаКЗ.</li>
</ol>

<!-- ========== 7 ========== -->
<h2 id="s7">7. Критерии приёмки</h2>
<table class="grid">
<tr><th>Критерий</th><th>Результат на Т-1</th></tr>
<tr><td>Обе платежки Перевод обработаны</td><td class="good" style="background:#eaf7ec;">Да</td></tr>
<tr><td>Создано без ошибок</td><td class="good" style="background:#eaf7ec;">5 028 + 24, ошибок 0</td></tr>
<tr><td>Параллельный режим работает (SafeMode=Нет)</td><td class="good" style="background:#eaf7ec;">Да, 15,14 док/с</td></tr>
<tr><td>Fallback последовательно не ломает создание</td><td class="good" style="background:#eaf7ec;">Хвост 24 док. создан</td></tr>
<tr><td>Прирост скорости vs последовательный темп</td><td class="good" style="background:#eaf7ec;">~4,7×</td></tr>
<tr><td>Отличия ЕБС/ЕРС в регрессе</td><td>Не блокер ускорения; зафиксировано уточнение с бизнесом (раздел 6)</td></tr>
</table>

</div>

<div class="footer">
  Источники: <code>План тестирования 9202 на Т_1.docx</code>;
  прогон Т-1 21.08.2026 (день 11.08.2026);
  переписка <code>RE вопрос по поступлению на расчетный счет.msg</code> (Чмыхалов / Кукушкин);
  версии к внедрению 6.05 / 1.10.
  Скриншоты встроены в HTML (извлечены из docx).
</div>

</div>
</body>
</html>
"""

# Fix accidental double braces from f-string for CSS - actually I used {{ }} for CSS which is correct
# But in table I wrote {{ВнешниеОбработки...}} which becomes {Внешние...} - good
# In pre I don't need braces

OUT.write_text(html, encoding="utf-8")
print("OK", OUT, "bytes", OUT.stat().st_size)
