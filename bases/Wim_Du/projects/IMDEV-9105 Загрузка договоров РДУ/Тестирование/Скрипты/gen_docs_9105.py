#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Генерация двух HTML-документов IMDEV-9105 с встроенными (base64) картинками.

Док 1: постановка проблемы (БЫЛО -> ГИПОТЕЗА -> СТАЛО -> выводы).
ТЗ Аванкору (imdev9105_ts_avankor_index.html) оформлено как IMDEV-9095
и поддерживается отдельно — этот скрипт его не перезаписывает.
"""

import base64
from pathlib import Path

BASE = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-9105 "
    r"Загрузка договоров РДУ\Тестирование"
)
REPORTS = BASE / "reports"
IMG_BEFORE = BASE / "Тест_100ДоговоровДУ.png"
IMG_AFTER = BASE / "Тест_100ДоговоровДУ_ПослеИндексирования.png"


def data_uri(path: Path) -> str:
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


CSS = """
* { box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    line-height: 1.55; color: #1a202c; background: #f0f2f5; margin: 0; padding: 24px;
}
.container { max-width: 100%; margin: 0 auto; }
.hero { background: #1a365d; color: #fff; border-radius: 10px; padding: 22px 26px; margin-bottom: 16px; }
.hero h1 { margin: 0 0 6px; font-size: 1.28rem; font-weight: 600; }
.hero p { margin: 0; opacity: 0.9; font-size: 0.95rem; }
.meta { margin-top: 10px; font-size: 0.82rem; opacity: 0.85; }
.card { background: #fff; border-radius: 10px; padding: 18px 22px; margin-bottom: 14px; border: 1px solid #e2e8f0; }
h2 { color: #1a365d; font-size: 1.05rem; margin: 0 0 12px; padding-bottom: 8px; border-bottom: 2px solid #e2e8f0; }
h3 { color: #2d3748; font-size: 0.95rem; margin: 16px 0 8px; }
.problem { background: #fff5f5; border-left: 4px solid #e53e3e; padding: 12px 14px; border-radius: 0 8px 8px 0; margin-bottom: 12px; }
.hypo { background: #fffaf0; border-left: 4px solid #dd6b20; padding: 12px 14px; border-radius: 0 8px 8px 0; margin-bottom: 12px; }
.verdict { background: #f0fff4; border-left: 4px solid #28a745; padding: 12px 14px; border-radius: 0 8px 8px 0; margin-bottom: 12px; }
.solution { background: #ebf8ff; border-left: 4px solid #3182ce; padding: 12px 14px; border-radius: 0 8px 8px 0; margin-bottom: 12px; }
.kpi { display: flex; flex-wrap: wrap; gap: 10px; margin: 10px 0; }
.kpi div { flex: 1 1 140px; background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; }
.kpi .v { font-size: 1.25rem; font-weight: 700; color: #2c5282; }
.kpi .v.good { color: #276749; }
.kpi .l { font-size: 0.8rem; color: #718096; }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; margin: 10px 0; }
th, td { border: 1px solid #e2e8f0; padding: 8px 10px; vertical-align: top; }
th { background: #f7fafc; text-align: left; font-weight: 600; }
.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.hot { background: #fff5f5; }
.ok-row { background: #f0fff4; }
.muted { color: #718096; font-size: 0.85rem; }
code { background: #edf2f7; padding: 1px 5px; border-radius: 3px; font-size: 0.86em; }
pre { background: #2d3748; color: #e2e8f0; padding: 12px 14px; border-radius: 8px; overflow-x: auto; font-size: 0.82rem; line-height: 1.45; }
ol, ul { margin: 8px 0 4px 18px; padding: 0; }
li { margin: 6px 0; }
figure { margin: 12px 0; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: #f7fafc; }
figure .cap { padding: 8px 10px; font-size: 0.85rem; font-weight: 600; border-bottom: 1px solid #e2e8f0; background: #edf2f7; }
figure img { display: block; width: 100%; height: auto; }
.delta-down { color: #276749; font-weight: 600; }
.delta-flat { color: #718096; }
.footer { text-align: center; color: #718096; font-size: 0.82rem; margin-top: 18px; }
.tag { display: inline-block; background: #edf2f7; border: 1px solid #cbd5e0; border-radius: 12px; padding: 1px 9px; font-size: 0.78rem; margin: 0 4px 4px 0; }
"""


def doc1(img_before: str, img_after: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IMDEV-9105: постановка проблемы и результат оптимизации</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">

<div class="hero">
    <h1>IMDEV-9105: производительность загрузки договоров РДУ</h1>
    <p>Постановка проблемы, гипотеза и результат после индексации</p>
    <div class="meta">База WIM_DU &middot; обработка <code style="background:rgba(255,255,255,.15);color:#fff">внТестЗагрузкаДоговоровРДУ</code> &middot; прогоны 14.07.2026 (14:30 и 15:41)</div>
</div>

<div class="card">
    <h2>1. Постановка проблемы</h2>
    <div class="problem">
        Загрузка розничных договоров ДУ (сценарий как в <code>СинхронизацияНСИ</code>) работает
        <strong>медленно</strong>: на пакете 100 договоров прогон занимает <strong>~5 минут</strong>
        (~3 с на договор). Нужно найти узкое место и подтвердить его замерами.
    </div>
    <p><strong>Условия замера</strong> (одинаковы во всех прогонах):</p>
    <span class="tag">100 образцов</span>
    <span class="tag">пул «Розничное ДУ»</span>
    <span class="tag">без Документооборота</span>
    <span class="tag">без ПП</span>
    <span class="tag">откат транзакции = Да</span>
    <p class="muted" style="margin-top:10px">
        Тест берёт 100 существующих РДУ, имитирует загрузку и проходит путь
        «СоздатьНСИ &rarr; аналитика &rarr; поручение на перевод», затем откатывает транзакцию
        (чистый замер, в базу ничего не фиксируется, в ДО ничего не отправляется).
    </p>
</div>

<div class="card">
    <h2>2. Замер БЫЛО (без индекса)</h2>
    <div class="kpi">
        <div><div class="v">311.5 с</div><div class="l">ИТОГО (~5 мин)</div></div>
        <div><div class="v">303 с</div><div class="l">блок 2 (97%)</div></div>
        <div><div class="v">3.03 с</div><div class="l">на 1 договор</div></div>
        <div><div class="v">0.33</div><div class="l">договоров/с</div></div>
    </div>
    <figure>
        <div class="cap">Скриншот прогона БЫЛО &middot; 14:30 &middot; ИТОГО 311.5 с</div>
        <img src="{img_before}" alt="Замер до индексации, ИТОГО 311.5 с">
    </figure>
    <table>
        <thead><tr><th>Блок</th><th class="num">Время</th><th class="num">Доля</th></tr></thead>
        <tbody>
            <tr><td>1. Генерация ТЧ из существующих РДУ</td><td class="num">6.5 с</td><td class="num">2%</td></tr>
            <tr class="hot"><td><strong>2. СоздатьНСИ + аналитика + поручение</strong></td><td class="num"><strong>303.3 с</strong></td><td class="num"><strong>97%</strong></td></tr>
            <tr><td>ИТОГО</td><td class="num">311.5 с</td><td class="num">100%</td></tr>
        </tbody>
    </table>
</div>

<div class="card">
    <h2>3. Гипотеза</h2>
    <div class="hypo">
        По профилю отладчика <strong>две самые медленные строки</strong> (41.6% и 14.1% всего прогона)
        приходятся на <strong>один и тот же запрос</strong> к справочнику
        <code>ДоговорыКонтрагентов</code> с отбором по реквизитам
        <code>ДоговорДУ</code> и <code>РольДоговора</code>, у которых
        <strong>отключено индексирование</strong> (<code>DontIndex</code> в конфигурации).
        Запрос вызывается ~500 раз на 100 договоров и почти всегда возвращает пусто
        (объекты ещё создаются), но каждый пустой поиск стоит ~0.3–0.4 с.
    </div>
    <table>
        <thead><tr><th>Строка профиля (тот же SELECT)</th><th class="num">self, с</th><th class="num">Вызовов</th><th class="num">Доля*</th></tr></thead>
        <tbody>
            <tr class="hot"><td>L3335 &middot; функция <code>ДоговорКонтрагента</code></td><td class="num">128.4</td><td class="num">400</td><td class="num"><strong>41.6%</strong></td></tr>
            <tr class="hot"><td>L3199 &middot; торговый код / ЕБС</td><td class="num">43.6</td><td class="num">100</td><td class="num"><strong>14.1%</strong></td></tr>
            <tr><td><strong>Сумма</strong></td><td class="num"><strong>172.0</strong></td><td class="num">500</td><td class="num"><strong>55.7%</strong></td></tr>
        </tbody>
    </table>
    <p class="muted">* доля от полного прогона ~308.7 с по отладчику.</p>
<pre>ВЫБРАТЬ ДоговорыКонтрагентов.Ссылка
ИЗ Справочник.ДоговорыКонтрагентов
ГДЕ Владелец = &amp;Владелец
  И ДоговорДУ = &amp;ДоговорДУ          // DontIndex
  И РольДоговора = &amp;РольДоговора    // DontIndex</pre>
    <p><strong>Проверяемое предположение:</strong> включение индекса на этих реквизитах
    уберёт ~172 с и заметно сократит общий прогон.</p>
</div>

<div class="card">
    <h2>4. Замер СТАЛО (после индексации)</h2>
    <div class="kpi">
        <div><div class="v good">132.4 с</div><div class="l">ИТОГО (~2.2 мин)</div></div>
        <div><div class="v good">124 с</div><div class="l">блок 2 (94%)</div></div>
        <div><div class="v good">1.24 с</div><div class="l">на 1 договор</div></div>
        <div><div class="v good">0.81</div><div class="l">договоров/с</div></div>
    </div>
    <figure>
        <div class="cap">Скриншот прогона СТАЛО &middot; 15:41 &middot; ИТОГО 132.4 с</div>
        <img src="{img_after}" alt="Замер после индексации, ИТОГО 132.4 с">
    </figure>
    <table>
        <thead><tr><th>Строка профиля (тот же SELECT)</th><th class="num">Было self</th><th class="num">Стало self</th><th class="num">Ускорение</th></tr></thead>
        <tbody>
            <tr class="ok-row"><td>L3335 (N=400)</td><td class="num">128.4 с</td><td class="num"><strong>0.96 с</strong></td><td class="num delta-down">&times;133</td></tr>
            <tr class="ok-row"><td>L3199 (N=100)</td><td class="num">43.6 с</td><td class="num"><strong>0.24 с</strong></td><td class="num delta-down">&times;184</td></tr>
            <tr class="ok-row"><td><strong>Сумма TOP-2</strong></td><td class="num">172.0 с</td><td class="num"><strong>1.20 с</strong></td><td class="num delta-down">&minus;171 с</td></tr>
        </tbody>
    </table>
</div>

<div class="card">
    <h2>5. Выводы</h2>
    <div class="verdict">
        Гипотеза <strong>подтверждена численно</strong>: индекс на <code>ДоговорДУ</code> /
        <code>РольДоговора</code> убрал главный тормоз. Экономия по ИТОГО (&minus;179 с)
        практически равна исчезновению двух горячих строк (&minus;171 с).
    </div>
    <table>
        <thead><tr><th>Показатель</th><th class="num">Было</th><th class="num">Стало</th><th class="num">Эффект</th></tr></thead>
        <tbody>
            <tr><td>ИТОГО прогона</td><td class="num">311.5 с</td><td class="num">132.4 с</td><td class="num delta-down">&minus;58%, &times;2.35</td></tr>
            <tr><td>Блок 2</td><td class="num">303.3 с</td><td class="num">123.9 с</td><td class="num delta-down">&minus;59%</td></tr>
            <tr><td>На 1 договор</td><td class="num">3.03 с</td><td class="num">1.24 с</td><td class="num delta-down">&minus;59%</td></tr>
            <tr><td>Горячий SELECT</td><td class="num">172 с</td><td class="num">1.2 с</td><td class="num delta-down">&minus;99%</td></tr>
        </tbody>
    </table>
    <p><strong>Дальше</strong> (вторичный слой, уже без этого запроса): подписка выгрузки CSV
    (~10 с), запрос L3380 «АналитическийПризнакиБрокерскогоСчета» (~8.6 с),
    проведения документов УП/поручений. Приоритет ниже — сначала закрепить индекс в базовой конфигурации
    (см. отдельное ТЗ Аванкору).</p>
</div>

<div class="footer">IMDEV-9105 &middot; постановка проблемы и результат &middot; 14.07.2026</div>

</div>
</body>
</html>
"""


def doc2() -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ТЗ Аванкору: индексы Справочник.ДоговорыКонтрагентов (IMDEV-9105)</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">

<div class="hero">
    <h1>ТЗ на доработку: индексы справочника «ДоговорыКонтрагентов»</h1>
    <p>Для вендора базовой конфигурации (Аванкор) &middot; задача IMDEV-9105</p>
    <div class="meta">Конфигурация: базовая (WIM/ДУ) &middot; объект: <code style="background:rgba(255,255,255,.15);color:#fff">Справочник.ДоговорыКонтрагентов</code></div>
</div>

<div class="card">
    <h2>1. Цель</h2>
    <div class="solution">
        Ускорить массовую загрузку/синхронизацию договоров РДУ за счёт индексирования
        реквизитов справочника <code>ДоговорыКонтрагентов</code>, участвующих в частом
        поиске по договору ДУ и роли. Изменение должно войти в <strong>базовую конфигурацию</strong>,
        чтобы сохраняться при обновлениях (не «на поддержке» у клиента).
    </div>
</div>

<div class="card">
    <h2>2. Обоснование (замеры)</h2>
    <p>На пакете 100 договоров один и тот же SELECT к <code>ДоговорыКонтрагентов</code>
    давал <strong>55.7%</strong> времени прогона. После включения индекса на тестовом
    стенде общий прогон сократился <strong>с 311.5 с до 132.4 с (&minus;58%, &times;2.35)</strong>,
    сам запрос — со <strong>172 с до 1.2 с</strong>.</p>
    <table>
        <thead><tr><th>Показатель</th><th class="num">Без индекса</th><th class="num">С индексом</th></tr></thead>
        <tbody>
            <tr><td>ИТОГО (100 договоров)</td><td class="num">311.5 с</td><td class="num">132.4 с</td></tr>
            <tr><td>Горячий SELECT (self)</td><td class="num">172 с</td><td class="num">1.2 с</td></tr>
        </tbody>
    </table>
    <p class="muted">Подробности и скриншоты — в документе «постановка проблемы и результат».</p>
</div>

<div class="card">
    <h2>3. Текущее состояние объекта</h2>
    <table>
        <thead><tr><th>Реквизит</th><th>Тип</th><th>Индексирование сейчас</th></tr></thead>
        <tbody>
            <tr><td>Владелец</td><td>CatalogRef.Контрагенты (владелец справочника)</td><td>индексируется платформой как владелец</td></tr>
            <tr class="hot"><td><code>ДоговорДУ</code></td><td>CatalogRef.ДоговорДУ</td><td><strong>DontIndex</strong></td></tr>
            <tr class="hot"><td><code>РольДоговора</code></td><td>EnumRef.РолиДоговоровКонтрагента</td><td><strong>DontIndex</strong></td></tr>
        </tbody>
    </table>
    <p class="muted">Справочник подчинён владельцу <code>Catalog.Контрагенты</code>
    (<code>SubordinationUse = ToItems</code>).</p>
    <p><strong>Типовой запрос (место возникновения нагрузки):</strong></p>
<pre>ВЫБРАТЬ ДоговорыКонтрагентов.Ссылка
ИЗ Справочник.ДоговорыКонтрагентов
ГДЕ Владелец = &amp;Владелец
  И ДоговорДУ = &amp;ДоговорДУ
  И РольДоговора = &amp;РольДоговора</pre>
</div>

<div class="card">
    <h2>4. Требуемое изменение</h2>
    <table>
        <thead><tr><th>Реквизит</th><th>Было</th><th>Стало</th><th>Приоритет</th></tr></thead>
        <tbody>
            <tr class="ok-row">
                <td><code>ДоговорДУ</code></td>
                <td>Indexing = DontIndex</td>
                <td><strong>Indexing = Index</strong> (Индексировать)</td>
                <td>Обязательно (основной эффект)</td>
            </tr>
            <tr>
                <td><code>РольДоговора</code></td>
                <td>Indexing = DontIndex</td>
                <td>Indexing = Index (Индексировать)</td>
                <td>Желательно (дополнение к отбору)</td>
            </tr>
        </tbody>
    </table>
    <div class="solution">
        <strong>Ключевой реквизит — <code>ДоговорДУ</code></strong>: он высокоселективен
        (на один договор ДУ приходится немного строк), и именно его индекс дал измеренный эффект.
        <code>РольДоговора</code> — перечисление низкой селективности; индекс на нём полезен как
        дополнение к отбору и практически безвреден, но при ограничениях можно ограничиться только
        <code>ДоговорДУ</code>.
    </div>
    <p class="muted">
        В терминах платформы для ссылочных реквизитов достаточно значения «Индексировать».
        «Индексировать с доп. упорядочиванием» не требуется — сортировка по этим полям в сценарии не используется.
    </p>
</div>

<div class="card">
    <h2>5. Порядок применения</h2>
    <ol>
        <li>Внести изменение свойства <code>Индексирование = Индексировать</code> для указанных
            реквизитов в базовой конфигурации.</li>
        <li>Обновить конфигурацию базы данных (реструктуризация построит индексы).
            Операция затрагивает таблицу справочника <code>ДоговорыКонтрагентов</code>.</li>
        <li>Провести на тестовом стенде повторный замер загрузки 100 договоров РДУ
            (обработка <code>внТестЗагрузкаДоговоровРДУ</code>) и сверить с эталоном ~132 с.</li>
    </ol>
</div>

<div class="card">
    <h2>6. Риски и влияние</h2>
    <ul>
        <li><strong>Реструктуризация БД</strong>: при обновлении структуры потребуется монопольный
            доступ / окно; на больших объёмах справочника построение индекса займёт время (разово).</li>
        <li><strong>Запись объектов</strong>: индекс незначительно удорожает вставку/изменение строк
            справочника (обычно доли процента) — на фоне выигрыша в поиске несущественно.</li>
        <li><strong>Размер БД</strong>: небольшой прирост под индексные структуры.</li>
        <li><strong>Совместимость</strong>: изменение чисто метаданное, кода не требует,
            обратная совместимость полная.</li>
    </ul>
</div>

<div class="card">
    <h2>7. Критерий приёмки</h2>
    <div class="verdict">
        На тестовом стенде прогон загрузки 100 договоров РДУ занимает
        <strong>&le; ~140 с</strong> (против ~311 с без индекса), а доля запроса к
        <code>ДоговорыКонтрагентов</code> в профиле отладчика — <strong>единицы процентов</strong>
        вместо ~56%.
    </div>
</div>

<div class="footer">IMDEV-9105 &middot; ТЗ на индексацию для базовой конфигурации &middot; 14.07.2026</div>

</div>
</body>
</html>
"""


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    img_b = data_uri(IMG_BEFORE)
    img_a = data_uri(IMG_AFTER)

    d1 = REPORTS / "imdev9105_problem_and_result.html"
    d1.write_text(doc1(img_b, img_a), encoding="utf-8")
    print("OK doc1", d1, d1.stat().st_size)
    print("SKIP doc2 (TZ Avankor styled as 9095, edit HTML directly)")


if __name__ == "__main__":
    main()
