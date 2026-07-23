#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate IMDEV-9153 HTML test report with embedded images."""

import base64
import os

img_dir = r"C:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-9153 ВУК РДУ\Оптимизация\Документация\test_plan_images"
out_path = r"C:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-9153 ВУК РДУ\Оптимизация\Документация\IMDEV-9153_test_plan_results.html"


def img_src(name):
    with open(os.path.join(img_dir, name), "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")


def main():
    i1 = img_src("image1.png")
    i2 = img_src("image2.png")
    i3 = img_src("image3.png")
    i4 = img_src("image4.png")

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IMDEV-9153 — План и результаты ИТ-тестирования</title>
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
  table {{ border-collapse: collapse; width: 100%; margin: 14px 0; }}
  th, td {{ border: 1px solid #d5dbe0; padding: 8px 10px; text-align: left; vertical-align: top; }}
  th {{ background: #2c3e50; color: #fff; }}
  tr:nth-child(even) td {{ background: #f7f9fb; }}
  .shot {{ margin: 14px 0; text-align: center; }}
  .shot img {{ max-width: 100%; height: auto; border: 1px solid #cfd6dc; border-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .caption {{ font-size: 12px; color: #666; margin-top: 6px; }}
  ul, ol {{ margin: 8px 0 8px 22px; }}
  li {{ margin: 4px 0; }}
  code {{ background: #f0f2f4; padding: 1px 5px; border-radius: 3px; font-family: Consolas, monospace; font-size: 13px; }}
  .toc a {{ color: #17a2b8; text-decoration: none; }}
  .toc a:hover {{ text-decoration: underline; }}
  .verdict {{ font-size: 17px; padding: 14px 18px; background: #e8f5e9; border-left: 5px solid #28a745; margin: 18px 0; }}
</style>
</head>
<body>
<div class="wrap">

<h1>IMDEV-9153. План и результаты ИТ-тестирования</h1>
<div class="meta">
  Задача: <a href="https://jira/browse/IMDEV-9153">https://jira/browse/IMDEV-9153</a><br>
  Объект: внешняя обработка <code>внНачислениеВознаграждения_РозничноеДУ</code><br>
  База: WIM_DU &nbsp;|&nbsp; Дата тестирования: 23.07.2026 &nbsp;|&nbsp; Версии: 2.01 / 2.02 (новая), 1.09 (старая)
</div>

<div class="toc box">
  <b>Содержание</b>
  <ol>
    <li><a href="#tz">Постановка задачи</a></li>
    <li><a href="#plan">План тестирования</a></li>
    <li><a href="#t1">Тест 1. Проверка запуска (параллельно, малый объём)</a></li>
    <li><a href="#t2">Тест 2. Сравнение ~1000 договоров: по-старому / по-новому</a></li>
    <li><a href="#stats">Сводная статистика</a></li>
    <li><a href="#concl">Выводы</a></li>
  </ol>
</div>

<h2 id="tz">1. Постановка задачи</h2>
<p>
  Ускорить массовое начисление вознаграждения за управление (ВУК) по договорам розничного ДУ
  и обеспечить автоматический запуск по расписанию 4 раза в год.
  Бизнес-логику расчёта сумм и формирования PDF не менять.
</p>

<div class="box">
  <b>Что реализовать</b>
  <ol>
    <li><b>Параллельное начисление</b> (кнопка «Начислить», кроме режима расторжения):
      договоры разбиваются на пачки (фиксированно по 100), каждая пачка — в фоновом задании;
      одновременно не больше потоков, чем в константе <code>МаксимальноеКоличествоПараллельныхПотоков</code>.
      В фоне: создание начисления + формирование PDF.</li>
    <li><b>Последовательное удаление обязательств</b> (после всех фонов):
      снятие движений регистра <code>ОбязательстваПоДС</code> и удаление документа <code>ОперацияБух</code>
      — в один поток (параллельная запись в регистр / удаление регистратора вызывает блокировки).</li>
    <li><b>Регламентная команда</b> в этой же обработке (вызов серверного метода), расписание 4 раза в год в 00:15:
      1 января, 1 апреля, 1 июля, 1 октября.</li>
    <li><b>Краткое письмо об итогах</b>: договоры, пачки, ошибки начисления, удаление ОперацияБух, затраченное время.
      Настройки рассылки — на форме настроек.</li>
  </ol>
</div>

<p><b>Две фазы выполнения:</b></p>
<table>
  <tr><th>Фаза</th><th>Что</th><th>Как</th></tr>
  <tr><td>Фаза 1</td><td>Начисление + PDF</td><td><b>Параллельно</b> (пачки / фоновые задания)</td></tr>
  <tr><td>Фаза 2</td><td>Снятие движений + удаление ОперацияБух</td><td><b>Последовательно</b> (один поток)</td></tr>
</table>

<h2 id="plan">2. План тестирования</h2>
<table>
  <tr><th>#</th><th>Сценарий</th><th>Критерий успеха</th></tr>
  <tr>
    <td>1</td>
    <td>Проверка запуска: «Выбрать» → «Начислить» на малой выборке (параллельный режим)</td>
    <td>Все начисления и PDF созданы; ошибок 0; ОперацияБух удалены; сводка корректна</td>
  </tr>
  <tr>
    <td>2</td>
    <td>Сравнение ~1000 договоров: старая версия (последовательно) vs новая (параллельно)</td>
    <td>Новая версия отрабатывает без ошибок и заметно быстрее; письмо об итогах приходит</td>
  </tr>
</table>

<h2 id="t1">3. Тест 1. Проверка запуска</h2>
<div class="result">
  <b>Статус:</b> <span class="ok">ПРОЙДЕН</span><br>
  Версия: <b>2.01</b> &nbsp;|&nbsp; Дата начисления: 30.09.2026 &nbsp;|&nbsp; Режим расторжения: выкл<br>
  Договоров: <b>20</b> &nbsp;|&nbsp; Пачек: <b>5</b> &nbsp;|&nbsp; Ошибок начисления: <b>0</b><br>
  Удалено ОперацияБух: <b>20 из 20</b> &nbsp;|&nbsp; Ошибок удаления: <b>0</b><br>
  Затрачено времени: <b>0 ч 0 мин 21 сек</b>
</div>

<div class="shot">
  <img src="{i1}" alt="Тест 1: параллельное начисление 20 договоров, версия 2.01">
  <div class="caption">Рис. 1. Форма обработки v2.01 после «Начислить»: сводка — 20 договоров, 5 пачек, 0 ошибок, 21 сек.</div>
</div>

<h2 id="t2">4. Тест 2. Сравнение ~1000 договоров</h2>
<p>Запуск сравнения на объёме порядка 1000 объектов: сначала по-старому, затем по-новому.</p>

<h3>4.1. По-старому (версия 1.09, последовательно)</h3>
<div class="old">
  <b>Версия:</b> 1.09<br>
  Старт: <b>11:02</b> (23.07.2026)<br>
  Финиш: <b>23.07.2026 11:36:47</b><br>
  Результат: <b>34 минуты</b> на <b>750</b> договоров
</div>

<div class="shot">
  <img src="{i2}" alt="Старая версия 1.09 — табличная часть для массового начисления">
  <div class="caption">Рис. 2. Форма обработки v1.09 (последовательный режим) — подготовка массового начисления.</div>
</div>

<h3>4.2. По-новому (версия 2.02, параллельно)</h3>
<div class="result">
  <b>Статус:</b> <span class="ok">ПРОЙДЕН</span><br>
  Версия: <b>2.02</b> &nbsp;|&nbsp; Дата начисления: 30.09.2026<br>
  Договоров: <b>1001</b> &nbsp;|&nbsp; Пачек: <b>11</b> &nbsp;|&nbsp; Ошибок начисления: <b>0</b><br>
  Удалено ОперацияБух: <b>1001 из 1001</b> &nbsp;|&nbsp; Ошибок удаления: <b>0</b><br>
  Затрачено времени: <b>0 ч 11 мин 56 сек</b><br>
  Письмо: <b>«Авто-начисление ВУК РДУ за 30.09.2026»</b> — получено (от svc_avancore_mail)
</div>

<div class="shot">
  <img src="{i3}" alt="Новая версия 2.02 — форма после выбора договоров">
  <div class="caption">Рис. 3. Форма обработки v2.02 — выборка договоров для параллельного начисления.</div>
</div>

<div class="shot">
  <img src="{i4}" alt="Письмо об итогах авто-начисления ВУК РДУ">
  <div class="caption">Рис. 4. Письмо об итогах: 1001 договор, 11 пачек, 0 ошибок, 11 мин 56 сек.</div>
</div>

<h2 id="stats">5. Сводная статистика</h2>
<table>
  <tr>
    <th>Показатель</th>
    <th>Старая (v1.09)</th>
    <th>Новая (v2.02)</th>
  </tr>
  <tr>
    <td>Режим</td>
    <td>Последовательно</td>
    <td>Параллельно (пачки по 100) + последовательное удаление</td>
  </tr>
  <tr>
    <td>Договоров</td>
    <td>750</td>
    <td>1001</td>
  </tr>
  <tr>
    <td>Время</td>
    <td>34 мин</td>
    <td>11 мин 56 сек</td>
  </tr>
  <tr>
    <td>Среднее на договор</td>
    <td>~2,7 сек</td>
    <td>~0,7 сек</td>
  </tr>
  <tr>
    <td>Ошибки начисления / удаления</td>
    <td>—</td>
    <td><span class="ok">0 / 0</span></td>
  </tr>
  <tr>
    <td>Письмо об итогах</td>
    <td>нет</td>
    <td><span class="ok">да</span></td>
  </tr>
</table>

<div class="note">
  При сопоставимой нагрузке новая версия отрабатывает примерно в <b>3–4 раза быстрее</b>
  (оценка по среднему времени на договор: ~2,7 сек → ~0,7 сек).
  На малой выборке (20 договоров) полный цикл занял 21 секунду без ошибок.
</div>

<h2 id="concl">6. Выводы</h2>
<div class="verdict">
  ИТ-тестирование по IMDEV-9153 <span class="ok">пройдено успешно</span>.
  Параллельное начисление, последовательное удаление ОперацияБух и рассылка итогового письма работают штатно.
</div>
<ul>
  <li>Проверка запуска на 20 договорах — без ошибок, сводка корректна.</li>
  <li>Массовый прогон ~1000 договоров — 0 ошибок начисления, 1001/1001 удалений ОперацияБух, время ~12 мин.</li>
  <li>Ускорение относительно последовательной версии 1.09 — существенное (ориентировочно в 3–4 раза).</li>
  <li>Письмо об итогах доставляется и содержит краткие счётчики + время выполнения.</li>
</ul>

<div class="meta" style="margin-top:28px; border-top:1px solid #e1e6ea; padding-top:12px;">
  Источник плана: файл «ПланИТТестировани 9153.docx». Скриншоты встроены в отчёт (можно открыть без внешних файлов).
</div>

</div>
</body>
</html>
"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    for name in os.listdir(img_dir):
        if name.endswith(".b64.txt"):
            os.remove(os.path.join(img_dir, name))

    print("OK", out_path)
    print("size_kb", round(os.path.getsize(out_path) / 1024, 1))


if __name__ == "__main__":
    main()
