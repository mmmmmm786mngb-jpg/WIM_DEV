#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Собирает HTML-страницу про справочник без объекта Справочник."""

import base64
from pathlib import Path

from PIL import Image

SHOTS = Path(r"C:\Users\Acer\logs\session-20261026T154447-49d7b9c0a56a\screenshots")
OUT = Path(__file__).resolve().parents[1] / "Документация" / "catalog-without-catalog.html"

FILES = {
    "NAV": SHOTS / "000010.png",
    "LIST": SHOTS / "000013.png",
    "CARD": SHOTS / "000014.png",
    "REGION": SHOTS / "000016.png",
    "CHOICE": SHOTS / "000024.png",
    "EMPLOYEE": SHOTS / "000027.png",
}


def png_data_uri(path, crop_bottom=0):
    image = Image.open(path).convert("RGB")
    if crop_bottom:
        width, height = image.size
        image = image.crop((0, 0, width, height - crop_bottom))
    temp = path.with_name(path.stem + "-ad.jpg")
    image.save(temp, "JPEG", quality=82, optimize=True)
    payload = base64.b64encode(temp.read_bytes()).decode("ascii")
    temp.unlink()
    return "data:image/jpeg;base64," + payload


def main():
    images = {key: png_data_uri(path) for key, path in FILES.items()}
    # Нижняя строка карточки показывает каталог снимков. Для страницы она не нужна.
    images["EMPLOYEE"] = png_data_uri(FILES["EMPLOYEE"], crop_bottom=118)
    html = TEMPLATE
    for key, uri in images.items():
        html = html.replace("{{" + key + "}}", uri)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print("bytes", OUT.stat().st_size)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Справочник без справочника</title>
<style>
  :root {
    --ink: #1b2430;
    --paper: #fff8ee;
    --sun: #ffd23f;
    --coral: #ff5d4a;
    --mint: #1f9d78;
    --sky: #2f6fed;
    --lilac: #7a4de0;
    --card: #fffdf8;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    color: var(--ink);
    font-family: "Segoe UI", Tahoma, sans-serif;
    background:
      radial-gradient(circle at 8% 12%, #ffe08a 0 140px, transparent 142px),
      radial-gradient(circle at 92% 8%, #ffb4a8 0 120px, transparent 122px),
      radial-gradient(circle at 80% 70%, #b7f0dc 0 160px, transparent 162px),
      radial-gradient(circle at 10% 88%, #c9d7ff 0 150px, transparent 152px),
      var(--paper);
    line-height: 1.45;
  }
  .wrap { max-width: 1080px; margin: 0 auto; padding: 28px 20px 64px; }
  .hero {
    background: var(--ink);
    color: white;
    border-radius: 28px;
    padding: 36px 36px 28px;
    position: relative;
    overflow: hidden;
    box-shadow: 10px 10px 0 #ffd23f;
  }
  .hero:before {
    content: "";
    position: absolute;
    width: 220px; height: 220px;
    right: -40px; top: -60px;
    background: var(--coral);
    border-radius: 50%;
  }
  .hero:after {
    content: "";
    position: absolute;
    width: 140px; height: 140px;
    right: 120px; bottom: -50px;
    background: var(--mint);
    border-radius: 50%;
  }
  .kicker {
    display: inline-block;
    background: var(--sun);
    color: var(--ink);
    font-weight: 800;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    font-size: 13px;
    padding: 6px 12px;
    border-radius: 999px;
    position: relative;
    z-index: 1;
  }
  h1 {
    position: relative;
    z-index: 1;
    font-size: 46px;
    line-height: 1.05;
    margin: 16px 0 10px;
    max-width: 16ch;
  }
  .lead {
    position: relative;
    z-index: 1;
    max-width: 62ch;
    font-size: 18px;
    color: #f4efe6;
    margin: 0;
  }
  h2 { font-size: 30px; margin: 42px 0 12px; }
  h3 { margin: 0 0 8px; font-size: 20px; }
  p { margin: 0 0 12px; }
  .grid3, .grid2 { display: grid; gap: 16px; }
  .grid3 { grid-template-columns: repeat(3, 1fr); }
  .grid2 { grid-template-columns: 1.1fr 0.9fr; }
  .tile, .note, .shot, .step {
    background: var(--card);
    border: 3px solid var(--ink);
    border-radius: 18px;
    box-shadow: 6px 6px 0 var(--ink);
  }
  .tile { padding: 18px 18px 8px; }
  .tile .num {
    display: inline-block;
    min-width: 36px;
    text-align: center;
    font-weight: 800;
    background: var(--sun);
    border-radius: 10px;
    padding: 2px 8px;
    margin-bottom: 8px;
  }
  .tile.coral .num { background: var(--coral); color: white; }
  .tile.mint .num { background: var(--mint); color: white; }
  .tile.sky .num { background: var(--sky); color: white; }
  .flow {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: center;
    margin-top: 8px;
  }
  .box {
    border: 3px solid var(--ink);
    border-radius: 14px;
    padding: 10px 12px;
    background: white;
    min-width: 140px;
    box-shadow: 4px 4px 0 var(--sun);
  }
  .box b { display: block; }
  .box small { color: #5c6570; }
  .arrow { font-weight: 800; color: var(--coral); }
  .shot { padding: 12px; margin: 18px 0 8px; background: white; }
  .shot img { width: 100%; height: auto; display: block; border-radius: 10px; background: #f3f0ea; }
  .cap {
    display: flex;
    gap: 10px;
    align-items: baseline;
    margin: 8px 4px 0;
    font-size: 15px;
  }
  .tag {
    flex: none;
    font-weight: 800;
    background: var(--lilac);
    color: white;
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 13px;
  }
  .tag.sun { background: var(--sun); color: var(--ink); }
  .tag.mint { background: var(--mint); }
  .tag.coral { background: var(--coral); }
  .tag.sky { background: var(--sky); }
  .steps { counter-reset: step; display: grid; gap: 12px; }
  .step { padding: 14px 16px 6px 16px; }
  .step h3:before {
    counter-increment: step;
    content: counter(step);
    display: inline-block;
    width: 28px; height: 28px;
    line-height: 28px;
    text-align: center;
    margin-right: 8px;
    border-radius: 50%;
    background: var(--coral);
    color: white;
    font-size: 15px;
  }
  pre {
    background: #14202b;
    color: #f6f1e7;
    border-radius: 14px;
    padding: 14px 16px;
    overflow: auto;
    font-size: 14px;
    line-height: 1.4;
  }
  .two { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .yes { background: #e7fff4; }
  .no { background: #fff1ee; }
  ul { margin: 8px 0 14px; padding-left: 18px; }
  li { margin: 0 0 6px; }
  .finale {
    margin-top: 28px;
    background: var(--sun);
    border: 3px solid var(--ink);
    border-radius: 22px;
    padding: 22px 24px;
    box-shadow: 8px 8px 0 var(--coral);
    font-size: 22px;
    font-weight: 750;
  }
  @media (max-width: 800px) {
    h1 { font-size: 34px; }
    .grid3, .grid2, .two { grid-template-columns: 1fr; }
    .hero { box-shadow: 6px 6px 0 #ffd23f; }
  }
</style>
</head>
<body>
<div class="wrap">

  <header class="hero">
    <div class="kicker">Для технического архитектора</div>
    <h1>Справочник, которого нет в метаданных</h1>
    <p class="lead">Платформа не даст ссылку на таблицу из хранилища настроек. Пользователю ссылка не нужна. Ему нужны список, карточка и кнопка выбора. Это можно собрать самим, и снаружи оно ведет себя как справочник.</p>
  </header>

  <h2>Коротко, в чем прием</h2>
  <div class="grid3">
    <article class="tile">
      <div class="num">1</div>
      <h3>Данные не в справочнике</h3>
      <p>Строки лежат в хранилище общих настроек: одна структура на всех, внутри две таблицы значений. Места и регионы России.</p>
    </article>
    <article class="tile coral">
      <div class="num">2</div>
      <h3>У сотрудника не ссылка</h3>
      <p>В реквизите хранится строка из 36 символов, идентификатор строки. На форме ее не показывают. Показывают наименование.</p>
    </article>
    <article class="tile mint">
      <div class="num">3</div>
      <h3>Выбор перехватывается</h3>
      <p>Кнопка выбора у поля отменяет стандартную обработку и открывает свою форму. Форма закрывается и возвращает идентификатор и имя.</p>
    </article>
  </div>

  <h2>Куда смотрит каждая стрелка</h2>
  <div class="flow">
    <div class="box"><b>Сотрудник</b><small>реквизит-строка, не ссылка</small></div>
    <div class="arrow">-></div>
    <div class="box" style="box-shadow: 4px 4px 0 #ff5d4a"><b>Поле на форме</b><small>наименование, кнопка выбора, очистка, карточка</small></div>
    <div class="arrow">-></div>
    <div class="box" style="box-shadow: 4px 4px 0 #2f6fed"><b>Форма списка</b><small>своя таблица, режим выбора</small></div>
    <div class="arrow">-></div>
    <div class="box" style="box-shadow: 4px 4px 0 #1f9d78"><b>Хранилище настроек</b><small>ключи объекта и настройки, имя пользователя "Общие"</small></div>
  </div>
  <p style="margin-top:14px">Из карточки места открывается карточка региона: субъект, код, федеральный округ. Регионы лежат в той же структуре, отдельной таблицей. Это тоже не справочник.</p>

  <h2>Сквозной пример: места рождения</h2>
  <p>Ниже живые экраны. Пользователь проходит тот же маршрут, что и у обычного справочника: раздел, список, карточка, выбор в другом объекте, открытие выбранного элемента.</p>

  <figure class="shot">
    <img alt="Раздел Сотрудники: команды Места рождения и Сотрудники рядом" src="{{NAV}}">
    <figcaption class="cap"><span class="tag sun">Раздел</span><span>В панели раздела команда "Места рождения" стоит рядом со справочником сотрудников. Отдельного объекта метаданных для нее нет, но в меню она выглядит как еще один список.</span></figcaption>
  </figure>

  <figure class="shot">
    <img alt="Список мест рождения с кнопками Создать, Изменить, Удалить" src="{{LIST}}">
    <figcaption class="cap"><span class="tag">Список</span><span>Таблица, поиск, создать, изменить, удалить. Двойной щелчок открывает карточку. Курсор можно поставить на нужную строку, здесь выделена Казань.</span></figcaption>
  </figure>

  <figure class="shot">
    <img alt="Карточка места рождения Казань" src="{{CARD}}">
    <figcaption class="cap"><span class="tag mint">Карточка</span><span>Записать, записать и закрыть, наименование, регион из списка. Так выглядит элемент. Кнопка "Открыть регион" уводит на следующий экран.</span></figcaption>
  </figure>

  <figure class="shot">
    <img alt="Карточка региона Республика Татарстан" src="{{REGION}}">
    <figcaption class="cap"><span class="tag sky">Регион</span><span>Субъект, код 16, Приволжский округ. Для пользователя это такая же карточка связанного элемента, только регион открыт только на просмотр.</span></figcaption>
  </figure>

  <figure class="shot">
    <img alt="Карточка сотрудника, поле Место рождения заполнено Казанью" src="{{EMPLOYEE}}">
    <figcaption class="cap"><span class="tag coral">Как ссылка</span><span>У Волкова Игоря поле "Место рождения" показывает Казань. Справа кнопка выбора, очистка и кнопка "Карточка". "Карточка" открывает ту же форму элемента, что и двойной щелчок в списке.</span></figcaption>
  </figure>

  <figure class="shot">
    <img alt="Форма выбора мест рождения, текущая строка Казань" src="{{CHOICE}}">
    <figcaption class="cap"><span class="tag sun">Повторный выбор</span><span>Кнопка выбора у реквизита открывает тот же список, уже в режиме выбора: появилась команда "Выбрать". Строка не прыгает в начало. Курсор стоит на Казани, потому что у сотрудника выбрана Казань.</span></figcaption>
  </figure>

  <h2>Что происходит по шагам, когда жмут выбор</h2>
  <div class="steps">
    <div class="step">
      <h3>Поле гасит стандартный выбор</h3>
      <p>У строки нет типа ссылки, поэтому платформенную форму выбора открывать нечему. Обработчик начала выбора ставит стандартную обработку в Ложь и открывает общую форму списка.</p>
<pre>СтандартнаяОбработка = Ложь;
ПараметрыФормы = Новый Структура;
ПараметрыФормы.Вставить("РежимВыбора", Истина);
ПараметрыФормы.Вставить("ТекущийИдентификатор", Объект.ИдентификаторМестаРождения);
ОткрытьФорму("ОбщаяФорма.СписокМестРождения", ПараметрыФормы, ...)</pre>
    </div>
    <div class="step">
      <h3>Список сам находит текущую строку</h3>
      <p>Идентификатор приходит параметром. Форма ищет строку своей таблицы и ставит ее текущей. Поэтому при повторном выборе пользователь видит уже выбранное место, а не первую строку.</p>
<pre>НайденныеСтроки = Места.НайтиСтроки(Новый Структура("Идентификатор", Идентификатор));
Элементы.Места.ТекущаяСтрока = НайденныеСтроки[0].ПолучитьИдентификатор();</pre>
    </div>
    <div class="step">
      <h3>Форма возвращает значение, как выбор из справочника</h3>
      <p>Команда "Выбрать" и двойной щелчок закрывают форму со структурой. Оповещение на карточке сотрудника записывает идентификатор в реквизит и наименование в поле.</p>
<pre>Закрыть(Новый Структура("Идентификатор, Наименование", Идентификатор, Наименование));</pre>
    </div>
  </div>

  <h2>Где пользователь не отличит, и где архитектор отличит сразу</h2>
  <div class="two">
    <div class="tile yes">
      <h3>Снаружи это справочник</h3>
      <ul>
        <li>Команда в разделе.</li>
        <li>Список с созданием, изменением и удалением.</li>
        <li>Карточка элемента и запись.</li>
        <li>Поле с выбором, очисткой и открытием карточки.</li>
        <li>Повторный выбор встает на текущее значение.</li>
        <li>Из элемента открывается связанная карточка, здесь это регион.</li>
      </ul>
    </div>
    <div class="tile no">
      <h3>Внутри ссылки нет</h3>
      <ul>
        <li>Тип реквизита - строка, не ссылка справочника. В запросе нельзя написать "место.наименование".</li>
        <li>Платформа не проверит, что строка еще существует.</li>
        <li>Удаление места не очищает сотрудников. Форма только предупреждает, что место уже указано.</li>
        <li>Нет поэлементных прав справочника и нет истории выбора платформы.</li>
        <li>Отчет, который хочет имя места, берет его из той же таблицы, а не через точку от ссылки.</li>
      </ul>
    </div>
  </div>

  <p style="margin-top:18px">На списке нарочно оставлена фраза "это не справочник". Это подпись для примера. Если ее убрать, маршрут пользователя не меняется: раздел, список, карточка, выбор, открытие элемента.</p>

  <div class="finale">Ссылку платформа не даст. Список, карточку и кнопку выбора можно отдать своими формами, и для пользователя это будет тот же справочник.</div>

</div>
</body>
</html>
"""


if __name__ == "__main__":
    main()
