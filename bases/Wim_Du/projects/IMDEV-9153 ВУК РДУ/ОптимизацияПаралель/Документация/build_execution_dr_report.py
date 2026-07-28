#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IMDEV-9153: HTML report on implementation and DR testing."""

import base64
from pathlib import Path

base = Path(__file__).resolve().parent
img_dir = base / "test_dr_images"
out_path = base / "IMDEV-9153_execution_and_DR_test_report.html"


def img_src(name: str) -> str:
    data = (img_dir / name).read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def main() -> None:
    i1 = img_src("image1.png")
    i2 = img_src("image2.png")
    i3 = img_src("image3.png")
    i4 = img_src("image4.png")
    i5 = img_src("image5.png")
    i6 = img_src("image6.png")
    i7 = img_src("image7.png")

    old_sec = 9 * 3600 + 52 * 60 + 44
    new_sec = 1 * 3600 + 4 * 60 + 34
    speedup = round(old_sec / new_sec, 1)
    saved_sec = old_sec - new_sec
    saved_h = saved_sec // 3600
    saved_m = (saved_sec % 3600) // 60
    saved_s = saved_sec % 60

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IMDEV-9153 — Отчёт о выполнении и тестировании (DR 30.09.2026)</title>
<style>
  body {{ font-family: Calibri, Arial, sans-serif; font-size: 15px; color: #222; line-height: 1.55; margin: 0; background: #f0f3f6; }}
  .wrap {{ max-width: 1100px; margin: 20px auto; background: #fff; padding: 28px 36px 40px; border: 1px solid #d8dee4; border-radius: 8px; }}
  h1 {{ font-size: 24px; color: #17a2b8; border-bottom: 2px solid #17a2b8; padding-bottom: 10px; margin-top: 0; }}
  h2 {{ font-size: 19px; color: #2c3e50; margin-top: 32px; border-left: 4px solid #17a2b8; padding-left: 10px; }}
  h3 {{ font-size: 16px; color: #34495e; margin-top: 22px; }}
  .meta {{ color: #666; font-size: 13px; margin-bottom: 18px; }}
  .meta a {{ color: #17a2b8; }}
  .ok {{ color: #28a745; font-weight: 700; }}
  .box {{ background: #eef6f8; border: 1px solid #cfe6ec; border-radius: 6px; padding: 12px 16px; margin: 12px 0; }}
  .note {{ background: #fff8e1; border: 1px solid #ffe08a; border-radius: 6px; padding: 10px 14px; margin: 12px 0; }}
  .result {{ background: #e8f5e9; border: 1px solid #a5d6a7; border-radius: 6px; padding: 12px 16px; margin: 12px 0; }}
  .old {{ background: #f5f5f5; border: 1px solid #ccc; border-radius: 6px; padding: 12px 16px; margin: 12px 0; }}
  .verdict {{ font-size: 17px; padding: 14px 18px; background: #e8f5e9; border-left: 5px solid #28a745; margin: 18px 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 14px 0; }}
  th, td {{ border: 1px solid #d5dbe0; padding: 8px 10px; text-align: left; vertical-align: top; }}
  th {{ background: #2c3e50; color: #fff; }}
  tr:nth-child(even) td {{ background: #f7f9fb; }}
  .num {{ text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }}
  .shot {{ margin: 14px 0; text-align: center; }}
  .shot img {{ max-width: 100%; height: auto; border: 1px solid #cfd6dc; border-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .caption {{ font-size: 12px; color: #666; margin-top: 6px; }}
  ul, ol {{ margin: 8px 0 8px 22px; }}
  li {{ margin: 4px 0; }}
  code {{ background: #f0f2f4; padding: 1px 5px; border-radius: 3px; font-family: Consolas, monospace; font-size: 13px; }}
  pre {{ background: #f4f6f8; border: 1px solid #dce3ea; border-radius: 6px; padding: 12px 14px; white-space: pre-wrap; font-family: Consolas, monospace; font-size: 13px; }}
  .toc a {{ color: #17a2b8; text-decoration: none; }}
  .toc a:hover {{ text-decoration: underline; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; color: #fff; }}
  .badge-ok {{ background: #28a745; }}
  .badge-info {{ background: #17a2b8; }}
</style>
</head>
<body>
<div class="wrap">

<h1>IMDEV-9153. Отчёт о выполнении и тестировании</h1>
<div class="meta">
  Задача: <a href="https://jira/browse/IMDEV-9153">https://jira/browse/IMDEV-9153</a> —
  Оптимизация начисления ВУК РДУ в регламентные даты<br>
  Объект: внешняя обработка <code>внНачислениеВознаграждения_РозничноеДУ</code>
  (папка <code>ОптимизацияПаралель</code>, версия <b>2.19</b>)<br>
  ТЗ: <code>IMDEV-9153.doc</code> &nbsp;|&nbsp;
  План/результаты DR: <code>ТестDR_30092026.docx</code><br>
  Контур тестирования: DR / AVC_UAT_RDU_PERFTEST &nbsp;|&nbsp;
  Период начисления: <b>30.09.2026</b> &nbsp;|&nbsp;
  Дата прогона: 27–28.07.2026
</div>

<div class="verdict">
  <span class="badge badge-ok">ИТОГ</span>
  На DR за 30.09.2026 параллельная обработка ускорила начисление примерно в
  <b>{speedup} раз</b> (с 9 ч 52 мин до 1 ч 04 мин) при <b>0 ошибок</b>.
  Письма об итогах с префиксом <code>{{OK}}</code> отправляются успешно.
</div>

<div class="toc box">
  <b>Содержание</b>
  <ol>
    <li><a href="#intro">Введение</a></li>
    <li><a href="#tz">Соответствие ТЗ — что сделано</a></li>
    <li><a href="#tech">Технология решения</a></li>
    <li><a href="#stats">Статистика DR-теста (30.09.2026)</a></li>
    <li><a href="#t-old">Тест A. По-старому (оригинал 1.10)</a></li>
    <li><a href="#t-new">Тест B. По-новому (параллель 2.19)</a></li>
    <li><a href="#t-mail">Тест C. Письмо об итогах</a></li>
    <li><a href="#concl">Выводы</a></li>
  </ol>
</div>

<h2 id="intro">1. Введение</h2>
<p>
  Цель задачи — ускорить массовое начисление вознаграждения за управление (ВУК) по договорам
  розничного ДУ и обеспечить регламентный запуск 4 раза в год с уведомлением по почте.
  Бизнес-логика начисления (суммы, PDF-справки, режим расторжения) сохранена.
</p>
<p>
  На контуре DR выполнен полный прогон за дату <b>30.09.2026</b>: сначала исходная
  последовательная обработка (оригинал с замером времени), после перезагрузки базы —
  оптимизированная параллельная версия. Результаты зафиксированы в
  <code>ТестDR_30092026.docx</code> и приведены ниже со скриншотами.
</p>

<h2 id="tz">2. Соответствие ТЗ — что сделано</h2>
<table>
  <tr>
    <th style="width:28%">Требование ТЗ</th>
    <th>Реализация в ОптимизацияПаралель (v2.19)</th>
    <th style="width:12%">Статус</th>
  </tr>
  <tr>
    <td>Многопоточное начисление: пачки по 100, лимит потоков из константы</td>
    <td>Дирижёр <code>СоздатьНачисления</code>: пачки 100, пул ФЗ через
      <code>ДлительныеОперации.ВыполнитьВФоне</code>, лимит
      <code>МаксимальноеКоличествоПараллельныхПотоков</code></td>
    <td><span class="ok">OK</span></td>
  </tr>
  <tr>
    <td>В пачке: начисление + PDF + работа с обязательствами</td>
    <td><code>ОбработатьПачкуНачислений</code>: начисление, справка-расчёт PDF,
      удаление <code>ОперацияБух</code> / движений <code>ОбязательстваПоДС</code></td>
    <td><span class="ok">OK</span></td>
  </tr>
  <tr>
    <td>Корректное удаление <code>ОперацияБух</code> без взаимоблокировок</td>
    <td>Одна фаза внутри пачки: очистка набора РН + <code>Удалить()</code> с
      <code>ОбменДанными.Загрузка</code> (вместо двухфазной схемы ТЗ — проверено на DR)</td>
    <td><span class="ok">OK*</span></td>
  </tr>
  <tr>
    <td>Регламентная команда 01.01 / 01.04 / 01.07 / 01.10</td>
    <td>Команда <code>НачислениеВУКРегламентноеФоновое</code>; дата документов =
      предыдущий день 23:55; проверка регламентной даты / флаг игнора</td>
    <td><span class="ok">OK</span></td>
  </tr>
  <tr>
    <td>Письмо об итогах (счётчики, время), настройки на форме</td>
    <td><code>ОтправитьПисьмоОбИтогах</code>: договоры / ошибки / время / пример ошибки;
      тема <code>{{OK|WARN|FAIL}}</code> + <code>{{r9153, ib: ...}}</code>; ТЧ СписокРассылки</td>
    <td><span class="ok">OK</span></td>
  </tr>
  <tr>
    <td>Fallback последовательный режим; расторжение без параллели</td>
    <td>При лимите потоков &le; 1 или без ссылки доп.обработки / расторжение —
      <code>НачислитьПоследовательно</code></td>
    <td><span class="ok">OK</span></td>
  </tr>
  <tr>
    <td>Замеры производительности (APDEX)</td>
    <td>Ключ <code>ДУ.НачислениеВознагражденияРДУ.Начисление.&lt;Контур&gt;</code>;
      комментарий с договорами/пачками/ошибками/параллельностью</td>
    <td><span class="ok">OK</span></td>
  </tr>
</table>
<div class="note">
  * В исходном ТЗ предлагались две фазы удаления (параллельно снять движения, затем
  последовательно удалить документы). В рабочей версии удаление выполняется в пачке
  с <code>ОбменДанными.Загрузка</code> — на полном объёме DR блокировок и ошибок не выявлено.
</div>

<h2 id="tech">3. Технология решения</h2>
<div class="box">
  <ul>
    <li><b>Платформа:</b> 1С:Предприятие 8.3, управляемое приложение, фоновые задания БСП.</li>
    <li><b>Пул:</b> волны ФЗ по лимиту константы; опрос статуса
      <code>ДлительныеОперации.ОперацияВыполнена</code>.</li>
    <li><b>Передача параметров/результатов:</b>
      <code>XMLСтрока(ХранилищеЗначения(...))</code> во временном хранилище.</li>
    <li><b>Мерж в ТЧ родителя:</b> из результата пачки возвращаются ссылки
      <code>НачислениеВознаграждения</code> / удержания при расторжении.</li>
    <li><b>Каталоги PDF:</b> автосоздание корня и каталога кабинета ДУ при отсутствии.</li>
    <li><b>Сравнение baseline:</b> оригинал v1.10 с сводкой времени
      («Режим: последовательно (оригинал)») для честного бенчмарка.</li>
  </ul>
</div>

<h2 id="stats">4. Статистика DR-теста (30.09.2026)</h2>
<table>
  <tr>
    <th>Показатель</th>
    <th>По-старому (оригинал 1.10)</th>
    <th>По-новому (параллель 2.19)</th>
    <th>Дельта</th>
  </tr>
  <tr>
    <td>Обработано договоров</td>
    <td class="num">20&nbsp;482</td>
    <td class="num">20&nbsp;467</td>
    <td class="num">−15*</td>
  </tr>
  <tr>
    <td>Ошибок</td>
    <td class="num"><span class="ok">0</span></td>
    <td class="num"><span class="ok">0</span></td>
    <td class="num">0</td>
  </tr>
  <tr>
    <td>Время выполнения (сводка)</td>
    <td class="num">9 ч 52 мин 44 сек</td>
    <td class="num">1 ч 04 мин 34 сек</td>
    <td class="num"><span class="ok">−{saved_h} ч {saved_m:02d} мин {saved_s:02d} сек</span></td>
  </tr>
  <tr>
    <td>Окно по часам стенда</td>
    <td class="num">13:20 → 23:12</td>
    <td class="num">11:07 → 12:22</td>
    <td class="num">~1 ч 15 мин wall-clock</td>
  </tr>
  <tr>
    <td>Ускорение</td>
    <td class="num" colspan="2">в <b>{speedup}×</b> (по сводке: {old_sec} с / {new_sec} с)</td>
    <td class="num"><span class="ok">PASS</span></td>
  </tr>
</table>
<div class="note">
  * Разница в 15 договоров объясняется перезагрузкой базы DR между прогонами
  («Попросим перегрузить базу DR»). Состав выборки после reload слегка изменился;
  оба прогона завершились без ошибок.
</div>

<div class="result">
  <b>Критерий сравнения:</b> одинаковый смысл операции
  (начисление + PDF + удаление обязательств), сопоставимый объём (~20,5 тыс.),
  0 ошибок, время у параллели существенно меньше.
</div>

<h2 id="t-old">5. Тест A. По-старому (оригинал 1.10)</h2>
<p>
  <span class="badge badge-info">Шаги</span>
  Заполнение ТЧ за 30.09.2026 → кнопка «Начислить» на оригинале со сводкой времени.
</p>

<div class="old">
  <b>Фактический результат (сообщение пользователю / ЖР):</b>
<pre>Выполнено начисление вознаграждения за управление (розничное ДУ).
Режим: последовательно (оригинал).
По каждому договору: создано начисление, сформирована справка-расчет (PDF), удалено обязательство по денежным средствам.
Обработано договоров: 20482.
Ошибок: 0.
Время выполнения: 9 ч 52 мин 44 сек.</pre>
</div>

<div class="shot">
  <img src="{i1}" alt="Форма оригинала v1.10, дата 30.09.2026">
  <div class="caption">Рис. A1. Форма оригинала (версия 1.10), дата начисления 30.09.2026, каталоги PDF.</div>
</div>

<div class="shot">
  <img src="{i2}" alt="ЖР завершение оригинала 23:12:53">
  <div class="caption">Рис. A2. Журнал регистрации: завершение прогона оригинала
    (событие <code>IMDEV-9153...Оригинал</code>, 27.07.2026 23:12:53).</div>
</div>

<p><span class="ok">Результат теста A: PASS</span> — полный объём отработан, ошибок нет, время зафиксировано для baseline.</p>

<h2 id="t-new">6. Тест B. По-новому (параллель 2.19)</h2>
<p>
  <span class="badge badge-info">Шаги</span>
  Перезагрузка DR → запуск оптимизированной обработки → контроль фоновых заданий →
  проверка сводки и PDF.
</p>

<div class="result">
  <b>Фактический результат (сообщение):</b>
<pre>Выполнено начисление вознаграждения за управление (розничное ДУ).
По каждому договору: создано начисление, сформирована справка-расчет (PDF), удалено обязательство по денежным средствам.
Обработано договоров: 20467.
Ошибок: 0.
Время выполнения: 1 ч 04 мин 34 сек.</pre>
</div>

<div class="shot">
  <img src="{i3}" alt="Старт регламентного/фонового запуска 11:07">
  <div class="caption">Рис. B1. Монитор заданий: родительский запуск выполняется
    (старт 28.07.2026 11:07:08).</div>
</div>

<div class="shot">
  <img src="{i4}" alt="Параллельные ФЗ IMDEV-9153">
  <div class="caption">Рис. B2. Параллельные фоновые задания
    <code>IMDEV-9153 Начисление РДУ пачка …</code> (одновременно ~12 потоков,
    сервер SMSK02MG138:8560).</div>
</div>

<div class="shot">
  <img src="{i5}" alt="Завершение заданий 12:12">
  <div class="caption">Рис. B3. Завершение: пачка ФЗ ~3–4 мин; родительский запуск
    11:07:08 → 12:12:22 (статус «Задание выполнено»).</div>
</div>

<div class="shot">
  <img src="{i6}" alt="PDF справки-расчёт">
  <div class="caption">Рис. B4. Каталог PDF: справки-расчёты
    <code>AM…-ДУ МИ….pdf</code> формируются в процессе параллельного прогона
    (28.07.2026, интервал ~11:09–12:05).</div>
</div>

<p><span class="ok">Результат теста B: PASS</span> — параллельный пул отработал, 0 ошибок,
время ~в {speedup} раз лучше baseline.</p>

<h2 id="t-mail">7. Тест C. Письмо об итогах</h2>
<p>
  Отдельная проверка рассылки: тестовая учётная запись почты;
  расчёт от <b>01.01.2027</b> (т.к. 01.10.2026 уже был выполнен на контуре).
</p>

<div class="shot">
  <img src="{i7}" alt="Письмо OK Авто-начисление ВУК РДУ">
  <div class="caption">Рис. C1. Письмо:
    тема <code>{{OK}} Авто-начисление ВУК РДУ за 31.12.2026 {{r9153, ib: AVC_UAT_RDU_PERFTEST}}</code>;
    в теле — старт 01.01.2027 00:15:00, документов 31.12.2026,
    договоров 14&nbsp;221, ошибок 0, время 0 ч 37 мин 58 сек.</div>
</div>

<div class="result">
  По плану тестирования: <b>«Письма успешно отправляются.»</b>
  Префикс статуса в теме соответствует корпоративному правилу
  <code>{{OK}}</code> / <code>{{WARN}}</code> / <code>{{FAIL}}</code>.
</div>
<p><span class="ok">Результат теста C: PASS</span></p>

<h2 id="concl">8. Выводы</h2>
<ol>
  <li>Требования ТЗ IMDEV-9153 по параллельному начислению, регламенту, письму и замерам
    реализованы в обработке версии <b>2.19</b> (папка <code>ОптимизацияПаралель</code>).</li>
  <li>На полном объёме DR (~20,5 тыс. договоров за 30.09.2026) параллельная версия
    дала ускорение порядка <b>{speedup}×</b> при нуле ошибок.</li>
  <li>Удаление обязательств/операций в пачках с <code>ОбменДанными.Загрузка</code>
    на боевом объёме подтверждено (блокировок/сбоев не зафиксировано).</li>
  <li>Почтовые уведомления с префиксом статуса и пропиской рассылки работают
    (проверено на регламентной дате 01.01.2027).</li>
  <li><span class="ok">Рекомендация:</span> считать функционал готовым к выкладке на прод
    после установки доп.обработки, настройки регламентного задания и списка рассылки
    (см. <code>support_install_prod.html</code>).</li>
</ol>

<div class="box">
  <b>Источники отчёта</b>
  <ul>
    <li>ТЗ: <code>bases/Wim_Du/projects/IMDEV-9153 ВУК РДУ/IMDEV-9153.doc</code></li>
    <li>План/факты DR: <code>…/ТестDR_30092026.docx</code></li>
    <li>Исходники: <code>…/ОптимизацияПаралель/внНачислениеВознаграждения_РозничноеДУ_epf/</code></li>
    <li>Baseline: <code>…/ОРИГИНАЛ_с_Замером/</code> (v1.10)</li>
  </ul>
</div>

<p class="meta" style="margin-top:28px">
  Отчёт сформирован 28.07.2026. HTML: UTF-8.
</p>

</div>
</body>
</html>
"""

    out_path.write_text(html, encoding="utf-8")
    print("OK", out_path)
    print("size_kb", round(out_path.stat().st_size / 1024, 1))
    print("speedup", speedup)


if __name__ == "__main__":
    main()
