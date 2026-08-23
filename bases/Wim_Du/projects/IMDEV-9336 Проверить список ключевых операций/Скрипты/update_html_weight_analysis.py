#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Update HTML analysis block with weight-aware stats."""

from pathlib import Path

HTML_PATH = Path(__file__).resolve().parents[1] / "Документация" / "imdev_9336_three_objects_overview.html"

TAIL = r'''    <!-- Statistics from prod -->
    <div class="card">
        <h2>Анализ продовых замеров (июль–август 2026)</h2>
        <p style="color:var(--muted); font-size:0.92rem;">
            Источник: <code>Замеры_СверкаСделокСОтчетомБрокера.xlsx</code> (281 запись),
            <code>Замеры_СверкаЦБ.xlsx</code> (59 записей).
            Плановый порог из IMDEV-8927: <strong>1800 с</strong> (0,5 ч) на ключевую операцию.
        </p>
        <div class="verdict-info">
            <strong>Методика с весом:</strong>
            абсолютное время само по себе некорректно сравнивать при разном объёме.
            Для сверки с брокером <strong>вес = число сделок из SQL</strong> (<code>СделокИзSQL</code>).
            Нормировка: <code>с/сделку = время / вес</code>, <code>сделок/с = вес / время</code>.
            Итоговая оценка — по абсолютному времени <em>и</em> по удельным показателям.
        </div>

        <h3 style="font-size:1.05rem; margin-top:18px;">1. Сверка с отчетом брокера</h3>
        <p>
            Вес замера = <code>СделокИзSQL</code> (обычно 6–11 тыс., разброс 134–18 509).<br>
            РЗ 9336: <code>ДУ.Сверка.СделокСОтчетомБрокера.ФоновоеВыполнение</code>
        </p>
        <table>
            <tr>
                <th>Показатель</th>
                <th>ФоновоеВыполнение (РЗ)</th>
                <th>ФоновоеПроведение (флаг)</th>
            </tr>
            <tr><td>Записей</td><td class="num-col">75</td><td class="num-col">25</td></tr>
            <tr><td>Время: медиана / среднее / P95 / max</td>
                <td class="num-col">100 с / 110 с / 187 с / 345 с</td>
                <td class="num-col">851 с / 791 с / 1257 с / 2793 с</td></tr>
            <tr><td>Вес (сделок): медиана / среднее / max</td>
                <td class="num-col">8 388 / 7 172 / 18 509</td>
                <td class="num-col">8 381 / 6 772 / 11 793</td></tr>
            <tr><td>Удельно: медиана с/сделку</td>
                <td class="num-col stat-good">0,01 с</td>
                <td class="num-col stat-warn">0,11 с</td></tr>
            <tr><td>Удельно: взвеш. среднее с/сделку</td>
                <td class="num-col stat-good">0,015 с</td>
                <td class="num-col stat-warn">0,117 с</td></tr>
            <tr><td>Удельно: медиана сделок/с</td>
                <td class="num-col stat-good">70</td>
                <td class="num-col stat-warn">9</td></tr>
            <tr><td>Удельно: взвеш. среднее сделок/с</td>
                <td class="num-col stat-good">65</td>
                <td class="num-col stat-warn">8,6</td></tr>
            <tr><td>Превышений порога 1800 с</td>
                <td class="num-col stat-good">0</td>
                <td class="num-col stat-warn">1 (46 мин при весе 10 210)</td></tr>
            <tr><td>FAIL / WARN</td>
                <td class="num-col">4 / 75</td>
                <td class="num-col">1 / 25</td></tr>
        </table>
        <p style="font-size:0.92rem; color:var(--muted);">
            Сравнение команд при похожем медианном весе (~8,4 тыс. сделок):
            <code>ФоновоеВыполнение</code> ~100 с (~70 сделок/с),
            <code>ФоновоеПроведение</code> ~851 с (~9 сделок/с) —
            <strong>~8× медленнее на сделку</strong> из-за цикла
            <code>ПолучитьОбъект</code> + <code>Записать(Проведение)</code>.
            Выброс 46 мин при весе 10 210: 0,27 с/сделку (в ~18× хуже типичной сверки без записи).
            Дни с малым весом (134 сделки) дают «плохую» удельную скорость из-за фиксированных накладных
            (SQL, запрос, рассылка) — это не признак деградации алгоритма.
        </p>
        <div class="verdict-ok">
            <strong>Вывод по п.1 (ФоновоеВыполнение):</strong> оптимизация <strong>не требуется</strong>.
            При типичном весе ~8 тыс. сделок медиана ~100 с (0,01 с/сделку, ~70 сделок/с).
            Даже при max весе 18 509 время 345 с — далеко от порога 30 мин.
            Рост времени объясняется объёмом, а не деградацией.
        </div>
        <div class="verdict-warn">
            <strong>Замечание (вне основного РЗ 9336):</strong>
            <code>ФоновоеПроведение</code> при том же весе работает ~8× медленнее на сделку
            (медиана 0,11 с/сделку vs 0,01). Узкое место — массовая запись/перепроведение документов,
            а не сама сверка SQL. Кандидат на оптимизацию только если включать эту команду в scope.
        </div>

        <h3 style="font-size:1.05rem; margin-top:24px;">2. Сверка остатков ЦБ с депозитарием</h3>
        <p>
            РЗ: <code>ДУ.СверкаЦБ.Сверка.ФоновоеВыполнение</code>.<br>
            <strong>Вес в коде всегда = 1</strong> (замер не масштабируется по числу договоров/ЦБ).
            Поэтому «с/единицу» = абсолютное время; сравнивать throughput по весу нельзя —
            это ограничение качества замера, не показатель нагрузки.
        </p>
        <table>
            <tr>
                <th>Показатель</th>
                <th>ФоновоеВыполнение (РЗ)</th>
                <th>Ручной</th>
            </tr>
            <tr><td>Записей</td><td class="num-col">18</td><td class="num-col">41</td></tr>
            <tr><td>Вес замера</td><td class="num-col">всегда 1</td><td class="num-col">всегда 1</td></tr>
            <tr><td>Время = с/вес: медиана / среднее / P95 / max</td>
                <td class="num-col">217 / 219 / 268 / 286 с</td>
                <td class="num-col">175 / 215 / 449 / 724 с</td></tr>
            <tr><td>Превышений порога 1800 с</td>
                <td class="num-col stat-good">0</td>
                <td class="num-col stat-good">0</td></tr>
            <tr><td>FAIL / WARN</td>
                <td class="num-col">0 / 18</td>
                <td class="num-col">0 / 41</td></tr>
        </table>
        <div class="verdict-ok">
            <strong>Вывод по п.2:</strong> по абсолютному времени оптимизация <strong>не требуется</strong>
            (РЗ стабильно 2,8–4,8 мин, намного меньше 30 мин).
            Но вес=1 не даёт понять, растёт ли время с объёмом портфеля.
            Рекомендация на будущее: в замер ставить вес = число строк сверки / договоров —
            тогда можно будет оценивать удельную производительность.
        </div>

        <h3 style="font-size:1.05rem; margin-top:24px;">3. Отрицательные остатки на р/с (IMDEV-8274)</h3>
        <div class="verdict-info">
            Замеры с прода пока не предоставлены. В EPF нет блока <code>ОценкаПроизводительности</code>.
            После деплоя: вставить замер с весом = число найденных минусовых строк (или договоров в выборке).
        </div>
    </div>

    <!-- Summary -->
    <div class="card">
        <h2>Итоговая сводка для IMDEV-9336</h2>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Операция (в 9336)</th>
                    <th>Объект / КО</th>
                    <th>Медиана времени / вес</th>
                    <th>Удельно</th>
                    <th>Нужна оптимизация?</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>1</td>
                    <td>Сверка с отчетом брокера</td>
                    <td><code>...ФоновоеВыполнение</code></td>
                    <td class="num-col">~100 с / вес ~8 400</td>
                    <td class="num-col">~0,01 с/сделку<br>~70 сделок/с</td>
                    <td class="stat-good">Нет</td>
                </tr>
                <tr>
                    <td>2</td>
                    <td>Сверка остатков ЦБ</td>
                    <td><code>...ФоновоеВыполнение</code></td>
                    <td class="num-col">~217 с / вес = 1</td>
                    <td class="num-col">вес не информативен</td>
                    <td class="stat-good">Нет</td>
                </tr>
                <tr>
                    <td>3</td>
                    <td>Отриц. остатки р/с РДУ</td>
                    <td><code>внОтрицательныеОстаткиНаАналитическомСчете</code></td>
                    <td class="num-col">—</td>
                    <td class="num-col">—</td>
                    <td class="stat-warn">Нет данных</td>
                </tr>
            </tbody>
        </table>
        <div class="verdict-ok" style="margin-top:14px;">
            <strong>Общий вывод (с учётом веса):</strong>
            основная сверка с брокером масштабируется нормально (~65–70 сделок/с) —
            <strong>оптимизация не нужна</strong>.
            Сверка ЦБ по абсолютному времени тоже в норме, но вес=1 мешает оценивать масштаб.
            Единственный удельно «тяжёлый» контур — <code>ФоновоеПроведение</code>
            (~8–9 сделок/с, в ~8× медленнее сверки) из-за массовой записи документов;
            в список 9336 как основной объект не входит.
        </div>
    </div>

    <div class="sources">
        Источники: IMDEV-9336.doc; IMDEV-8274.doc;
        BSS/IMDEV-8927 (объекты 1–2);
        продовые замеры: <code>Замеры_СверкаСделокСОтчетомБрокера.xlsx</code>,
        <code>Замеры_СверкаЦБ.xlsx</code>;
        исходники: <code>ОРИГИНАЛЫ/</code>,
        <code>C:\1c\Cursor_1c\WORK\Wim_Du\SRC\epf\</code>.
    </div>

</div>
</body>
</html>
'''


def main():
    text = HTML_PATH.read_text(encoding="utf-8")
    marker = "    <!-- Statistics from prod -->"
    idx = text.find(marker)
    if idx < 0:
        raise SystemExit("marker not found")
    HTML_PATH.write_text(text[:idx] + TAIL, encoding="utf-8")
    print("OK", HTML_PATH)


if __name__ == "__main__":
    main()
