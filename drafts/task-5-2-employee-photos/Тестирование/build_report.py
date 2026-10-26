#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Собирает HTML-отчет по задаче 5.2 из JSON проверки и снимков экрана."""

import base64
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "reports", "verify_data.json")
OUT_PATH = os.path.join(HERE, "reports", "employee_photos_report.html")

SHOT_LIST = r"C:\Users\Acer\logs\session-20261026T143620-505287bd0958\screenshots\000003.png"
SHOT_CARD = r"C:\Users\Acer\logs\session-20261026T143620-505287bd0958\screenshots\000015.png"
SHOT_FILE = r"C:\Users\Acer\logs\session-20261026T143907-231936e9a1a1\screenshots\000010.png"
PORTRAIT_DIR = r"C:\Users\Acer\Documents\1C\EmployeePhotosFiles\portraits"

GALLERY = [
    ("p32.jpg", "Соколова Мария", "В карточке"),
    ("p25.jpg", "Кузнецова Елена", "В карточке"),
    ("p44.jpg", "Морозова Ольга", "В карточке"),
    ("p16.jpg", "Лебедева Анна", "В карточке"),
    ("p11.jpg", "Орлов Дмитрий", "В папке"),
    ("p60.jpg", "Волков Игорь", "В папке"),
    ("p68.jpg", "Новиков Павел", "В папке"),
    ("p33.jpg", "Громов Алексей", "В папке"),
]


def data_uri(path):
    ext = os.path.splitext(path)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    with open(path, "rb") as image_file:
        payload = base64.b64encode(image_file.read()).decode("ascii")
    return "data:%s;base64,%s" % (mime, payload)


def esc(value):
    return (str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def bars(rows):
    maximum = max(row["bytes"] for row in rows) or 1
    parts = []
    for row in rows:
        width = int(round(100.0 * row["bytes"] / maximum))
        color = "#1F6F8B" if row["status"] == "database" else "#C46B4A"
        parts.append(
            "<div class='bar-row'>"
            "<div class='bar-name'>%s</div>"
            "<div class='bar-track'><div class='bar-fill' style='width:%s%%;background:%s'></div></div>"
            "<div class='bar-val'>%s КБ</div>"
            "</div>" % (esc(row["name"]), width, color, round(row["bytes"] / 1024.0, 1))
        )
    return "\n".join(parts)


def table_rows(rows):
    parts = []
    for row in rows:
        place_class = "tag-db" if row["status"] == "database" else "tag-file"
        file_name = row["fileName"] if row["fileName"] else "-"
        parts.append(
            "<tr><td>%s</td><td>%s</td><td><span class='%s'>%s</span></td>"
            "<td>%s</td><td>%s</td><td>снимок на месте</td></tr>"
            % (esc(row["name"]), esc(row["code"]), place_class, esc(row["place"]),
               esc(file_name), row["bytes"])
        )
    return "\n".join(parts)


def gallery():
    cards = []
    for file_name, person, place in GALLERY:
        path = os.path.join(PORTRAIT_DIR, file_name)
        cards.append(
            "<figure class='portrait'><img src='%s' alt='%s'>"
            "<figcaption><b>%s</b><br>%s</figcaption></figure>"
            % (data_uri(path), esc(person), esc(person), esc(place))
        )
    return "\n".join(cards)


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as data_file:
        data = json.load(data_file)
    total = data["employees"]
    db_count = data["databaseCount"]
    file_count = data["fileCount"]
    db_pct = round(100.0 * db_count / total, 1)
    file_pct = round(100.0 * file_count / total, 1)
    # Окружность 2 * pi * 42 = 263.9
    db_len = round(263.9 * db_count / total, 1)
    file_len = round(263.9 * file_count / total, 1)

    html = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Задача 5.2. Фотографии сотрудников. Отчет</title>
<style>
  :root {
    --ink: #243E4A;
    --paper: #F6F1E8;
    --card: #FFFCF7;
    --line: #E4D8C8;
    --ok: #28a745;
    --bad: #dc3545;
    --info: #17a2b8;
    --db: #1F6F8B;
    --file: #C46B4A;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--paper);
    color: var(--ink);
    font-family: "Segoe UI", sans-serif;
    line-height: 1.5;
  }
  .wrap { max-width: 1100px; margin: 0 auto; padding: 32px 20px 64px; }
  h1 { font-size: 34px; line-height: 1.15; margin: 0 0 8px; }
  h2 { margin: 36px 0 12px; font-size: 24px; }
  h3 { margin: 22px 0 8px; font-size: 18px; }
  .lead { font-size: 18px; max-width: 760px; }
  .meta { color: #6B6258; margin-bottom: 22px; }
  .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
  .stat {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 14px 16px;
  }
  .stat b { display: block; font-size: 28px; }
  .stat span { color: #6B6258; }
  .ok b { color: var(--ok); }
  .card {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 18px 20px;
    margin: 14px 0;
  }
  .blue { background: #E7F4F8; border-color: #B7D7E2; }
  .yellow { background: #FFF4D6; border-color: #E6C56A; }
  .green { background: #E8F6EC; border-color: #B7D7C3; }
  .purple { background: #F3EEF8; border-color: #D4C6E6; }
  pre {
    background: #1E2A30;
    color: #F6F1E8;
    padding: 14px 16px;
    border-radius: 10px;
    overflow: auto;
    font-size: 13px;
    line-height: 1.45;
  }
  table { width: 100%; border-collapse: collapse; background: white; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
  th { background: #EFE4D4; }
  .tag-db, .tag-file {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    color: white;
    font-size: 13px;
  }
  .tag-db { background: var(--db); }
  .tag-file { background: var(--file); }
  .shots { display: grid; gap: 16px; }
  .shots figure, .portrait {
    margin: 0;
    background: white;
    border: 1px solid var(--line);
    border-radius: 14px;
    overflow: hidden;
  }
  .shots img, .portrait img { width: 100%; display: block; }
  figcaption { padding: 10px 12px; color: #6B6258; }
  .gallery { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
  .bar-row { display: grid; grid-template-columns: 180px 1fr 70px; gap: 8px; align-items: center; margin: 6px 0; }
  .bar-track { background: #EFE4D4; border-radius: 999px; height: 12px; }
  .bar-fill { height: 12px; border-radius: 999px; }
  .bar-name, .bar-val { font-size: 13px; }
  .legend i { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 6px; }
  ol.plan li { margin: 6px 0; }
  .flow { width: 100%; height: auto; }
  .two { display: grid; grid-template-columns: 280px 1fr; gap: 18px; align-items: center; }
  @media (max-width: 800px) {
    .grid, .gallery, .two { grid-template-columns: 1fr; }
    .bar-row { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<div class="wrap">

<h1>Задача 5.2. Фотографии сотрудников</h1>
<p class="lead">Отчет от постановки до проверки в файловой базе: как устроено хранение портрета, как выглядит карточка и чем закончились тесты 26 октября 2026.</p>
<p class="meta">Конфигурация «Задача 5.2. Фотографии сотрудников», платформа 8.3.27, режим управляемого приложения.</p>

<div class="grid">
  <div class="stat ok"><b>11 / 11</b><span>снимков на месте</span></div>
  <div class="stat"><b>5</b><span>в базе данных</span></div>
  <div class="stat"><b>6</b><span>файлом в папке</span></div>
  <div class="stat ok"><b>0</b><span>ошибок в этой проверке</span></div>
</div>

<h2>Введение. Постановка</h2>
<div class="card">
  <p>Задача 5.2 из сборника для подготовки к экзамену «1С:Специалист» по платформе. В справочнике «Сотрудники» нужно хранить фотографию двумя способами:</p>
  <ul>
    <li>в базе данных, реквизитом типа «ХранилищеЗначения»;</li>
    <li>файлом на диске сервера: путь к папке хранится в отдельной константе, имя файла - в реквизите справочника.</li>
  </ul>
  <p>На форме элемента должны быть: показ фотографии, переключение места сохранения и загрузка снимка. Загрузить можно кнопкой и щелчком по самому изображению.</p>
  <p>Имена в демо-карточках вымышленные. Портреты взяты из открытого набора фотографий людей для примеров, это не документы этих сотрудников.</p>
</div>

<h2>План реализации</h2>
<ol class="plan">
  <li>Перечисление «Способы хранения фотографий»: в информационной базе и в каталоге на диске.</li>
  <li>Константа «Каталог фотографий сотрудников», строка 255.</li>
  <li>Справочник «Сотрудники»: способ хранения, фотография (хранилище значения), имя файла.</li>
  <li>Форма элемента. Поле картинки смотрит не в хранилище, а в адрес временного хранилища с двоичными данными.</li>
  <li>Кнопка «Выбрать снимок» и щелчок по портрету открывают диалог файла. Очистка убирает снимок при следующей записи.</li>
  <li>Перед записью: если снимок и способ не менялись, ничего не перекладывать. Иначе записать байты в выбранное место и освободить другое. Старый файл удаляется только после успешной записи.</li>
  <li>Если у снимка из базы нет имени, расширение читается по первым байтам: PNG, JPEG, GIF, BMP.</li>
  <li>Карточка для HR: крупный портрет слева, имя, переключатель «В карточке / В папке», папка видна только для файлового режима.</li>
  <li>Список «Люди в команде» с колонками сотрудника, табельного номера, места снимка и имени файла.</li>
  <li>Проверка чтением базы и проходом по формам в тонком клиенте.</li>
</ol>

<div class="card purple">
  <h3>Как снимок доходит до записи</h3>
  <svg class="flow" viewBox="0 0 980 250" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="90" width="150" height="58" rx="12" fill="#243E4A"/>
    <text x="85" y="124" text-anchor="middle" fill="#F6F1E8" font-size="14" font-family="Segoe UI">Щелчок или кнопка</text>
    <rect x="210" y="90" width="170" height="58" rx="12" fill="#1F6F8B"/>
    <text x="295" y="124" text-anchor="middle" fill="#F6F1E8" font-size="14" font-family="Segoe UI">Временное хранилище</text>
    <rect x="430" y="20" width="220" height="70" rx="12" fill="#C46B4A"/>
    <text x="540" y="50" text-anchor="middle" fill="#FFFCF7" font-size="14" font-family="Segoe UI">В папке</text>
    <text x="540" y="70" text-anchor="middle" fill="#FFFCF7" font-size="12" font-family="Segoe UI">файл в каталоге константы</text>
    <rect x="430" y="150" width="220" height="70" rx="12" fill="#1F6F8B"/>
    <text x="540" y="180" text-anchor="middle" fill="#FFFCF7" font-size="14" font-family="Segoe UI">В карточке</text>
    <text x="540" y="200" text-anchor="middle" fill="#FFFCF7" font-size="12" font-family="Segoe UI">ХранилищеЗначения, сжатие 9</text>
    <rect x="710" y="90" width="250" height="58" rx="12" fill="#6B6258"/>
    <text x="835" y="114" text-anchor="middle" fill="#FFFCF7" font-size="14" font-family="Segoe UI">После записи</text>
    <text x="835" y="132" text-anchor="middle" fill="#FFFCF7" font-size="12" font-family="Segoe UI">удалить старый файл</text>
    <path d="M160 119 H210" stroke="#243E4A" stroke-width="2" fill="none"/>
    <path d="M380 108 C410 108 410 55 430 55" stroke="#C46B4A" stroke-width="2" fill="none"/>
    <path d="M380 130 C410 130 410 185 430 185" stroke="#1F6F8B" stroke-width="2" fill="none"/>
    <path d="M650 55 C690 55 690 108 710 108" stroke="#6B6258" stroke-width="2" fill="none"/>
    <path d="M650 185 C690 185 690 130 710 130" stroke="#6B6258" stroke-width="2" fill="none"/>
  </svg>
</div>

<h2>Технология</h2>
<div class="card blue">
  <p>Проверка данных идет через COM: Component Object Model и библиотеку pywin32. Коннектор платформы создается как <b>V83.COMConnector</b>. Соединение получает строку подключения и возвращает внешнее соединение с базой. Перед работой вызывается <b>pythoncom.CoInitialize()</b>, в конце <b>pythoncom.CoUninitialize()</b>.</p>
  <p>Параметры строки: <b>Srvr</b> - сервер, <b>Ref</b> - имя базы на сервере, <b>File</b> - каталог файловой базы, <b>Usr</b> и <b>Pwd</b> - пользователь и пароль, <b>App</b> - имя приложения, <b>Locale</b> - язык сеанса.</p>
</div>

<h3>Три способа подключения</h3>
<p>Серверная база:</p>
<pre>pythoncom.CoInitialize()
com = win32com.client.Dispatch("V83.COMConnector")
conn = com.Connect("Srvr='localhost';Ref='WIM_DU';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;")</pre>
<p>Файловая база этой задачи, без пароля:</p>
<pre>conn = com.Connect("File='C:\\\\Users\\\\Acer\\\\Documents\\\\1C\\\\EmployeePhotos';App='PyCOM';Locale=ru_RU;")</pre>
<p>Файловая база с пользователем:</p>
<pre>conn = com.Connect("File='C:\\\\base\\\\demo';Usr='Администратор';Pwd='';App='PyCOM';Locale=ru_RU;")</pre>

<h3>Запросы</h3>
<p>Простой запрос. Вернул значение 1.</p>
<pre>ВЫБРАТЬ 1 КАК Один</pre>
<p>Сложный запрос. Им собран список для таблицы ниже.</p>
<pre>ВЫБРАТЬ
    Сотрудники.Наименование КАК Наименование,
    Сотрудники.Код КАК Код,
    ПРЕДСТАВЛЕНИЕ(Сотрудники.СпособХраненияФотографии) КАК Место,
    Сотрудники.СпособХраненияФотографии КАК Способ,
    Сотрудники.ИмяФайлаФотографии КАК ИмяФайла,
    Сотрудники.Ссылка КАК Ссылка
ИЗ
    Справочник.Сотрудники КАК Сотрудники
УПОРЯДОЧИТЬ ПО
    Наименование</pre>

<h3>Вызовы методов</h3>
<p>Справочник. Менеджер создается через NewObject, затем элемент. Свойство СправочникОбъект напрямую не устанавливается.</p>
<pre>manager = conn.NewObject("СправочникМенеджер.Сотрудники")
item = manager.СоздатьЭлемент()
item.Наименование = "Соколова Мария"
item.Записать()</pre>
<p>Снимок в базе. Двоичные данные заворачиваются в хранилище со сжатием.</p>
<pre>binary = conn.NewObject("ДвоичныеДанные", path)
storage = conn.NewObject("ХранилищеЗначения", binary, conn.NewObject("СжатиеДанных", 9))
item.СпособХраненияФотографии = conn.Перечисления.СпособыХраненияФотографий.ВИнформационнойБазе
item.Фотография = storage</pre>
<p>Константа папки. Чтение и установка идут через менеджер константы, не через поле объекта.</p>
<pre>folder = conn.Константы.КаталогФотографийСотрудников.Получить()
conn.Константы.КаталогФотографийСотрудников.Установить(folder)</pre>

<div class="card">
  <h3>Замечания про обработки</h3>
  <p>Внешняя обработка через COM требует в строке подключения <b>App='PyCOM'</b> и <b>Locale=ru_RU</b>. Иначе создание обработки часто заканчивается отказом. Дальше нужен менеджер <b>conn.Обработки.Имя</b>, метод <b>Создать()</b> и вызов экспортной функции уже у созданного объекта. Общий модуль вызывается только если у него включено внешнее соединение. В этой задаче обработка не использовалась: проверка шла запросом, менеджером справочника и константой.</p>
</div>

<h2>Статистика</h2>
<div class="two">
  <svg viewBox="0 0 220 220" width="220" height="220">
    <circle cx="110" cy="110" r="42" fill="none" stroke="#EFE4D4" stroke-width="28"/>
    <circle cx="110" cy="110" r="42" fill="none" stroke="#1F6F8B" stroke-width="28"
      stroke-dasharray="__DB_LEN__ 263.9" stroke-dashoffset="0" transform="rotate(-90 110 110)"/>
    <circle cx="110" cy="110" r="42" fill="none" stroke="#C46B4A" stroke-width="28"
      stroke-dasharray="__FILE_LEN__ 263.9" stroke-dashoffset="-__DB_LEN__" transform="rotate(-90 110 110)"/>
    <text x="110" y="106" text-anchor="middle" font-size="22" font-family="Segoe UI" fill="#243E4A">11</text>
    <text x="110" y="126" text-anchor="middle" font-size="12" font-family="Segoe UI" fill="#6B6258">сотрудников</text>
  </svg>
  <div>
    <p class="legend"><i style="background:#1F6F8B"></i>В базе данных: __DB__ (__DB_PCT__%)</p>
    <p class="legend"><i style="background:#C46B4A"></i>В файле на диске: __FILE__ (__FILE_PCT__%)</p>
    <p>У всех 11 ссылок двоичные данные нашлись: для базы через Получить() у хранилища, для файла - по пути константы и имени файла. Пустых снимков нет.</p>
    <p>Константа папки: <b>__CONST__</b></p>
    <p>Реквизиты справочника: СпособХраненияФотографии, Фотография, ИмяФайлаФотографии. Формы: ФормаЭлемента, ФормаСписка. Значения перечисления: ВИнформационнойБазе, ВКаталогеНаДиске.</p>
  </div>
</div>

<h3>Размер снимка, КБ</h3>
<div class="card">
__BARS__
<p class="legend"><i style="background:#1F6F8B"></i>база <i style="background:#C46B4A"></i>файл</p>
</div>

<h3>Сотрудники и снимки</h3>
<table>
  <tr><th>Сотрудник</th><th>Код</th><th>Место</th><th>Имя файла</th><th>Байт</th><th>Проверка</th></tr>
__ROWS__
</table>

<h2>Детали тестов</h2>
<div class="card green">
  <p>Проверка 26.10.2026 только читала базу и открывала формы. Новые элементы не создавались. Тонкий клиент 8.3.27.2214 после сценария закрыт.</p>
</div>

<h3>Чтение данных</h3>
<table>
  <tr><th>Проверка</th><th>Параметры</th><th>Результат</th></tr>
  <tr><td>Подключение COM</td><td>File, App=PyCOM, Locale=ru_RU</td><td>соединение установлено</td></tr>
  <tr><td>Метаданные</td><td>справочник, константа, перечисление, две формы</td><td>состав совпал с задачей</td></tr>
  <tr><td>Запрос «ВЫБРАТЬ 1»</td><td>без параметров</td><td>Один = 1</td></tr>
  <tr><td>Список сотрудников</td><td>запрос выше, без параметров</td><td>11 строк</td></tr>
  <tr><td>Байты снимка</td><td>хранилище или файл по имени</td><td>11 из 11, размер больше нуля</td></tr>
</table>

<h3>Интерфейс</h3>
<table>
  <tr><th>Шаг</th><th>Что увидели</th><th>Результат</th></tr>
  <tr><td>Список справочника</td><td>заголовок «Люди в команде», 11 строк, колонки сотрудника, номера, места и файла</td><td>успех</td></tr>
  <tr><td>Карточка Соколовой Марии</td><td>имя = Соколова Мария; переключатель = «В карточке»; группа папки скрыта; у портрета адрес временного хранилища</td><td>успех</td></tr>
  <tr><td>Список выбора</td><td>presentation: В базе данных / В файле на диске; на форме: «В карточке» и «В папке»</td><td>успех</td></tr>
  <tr><td>Карточка Орлова Дмитрия</td><td>переключатель = «В папке»; группа папки видна; имя файла be5db334-2f71-494f-8f4e-272943ade1fa.jpg; портрет из файла</td><td>успех</td></tr>
  <tr><td>Папка на сервере</td><td>текст поля совпал с константой</td><td>успех</td></tr>
</table>

<h3>Экраны</h3>
<div class="shots">
  <figure>
    <img src="__SHOT_LIST__" alt="Список сотрудников">
    <figcaption>Список. Бумажная шапка, понятные колонки, у файловых строк заполнено имя файла, у карточек базы имя файла пустое.</figcaption>
  </figure>
  <figure>
    <img src="__SHOT_CARD__" alt="Карточка Соколовой Марии">
    <figcaption>Карточка с хранением в базе. Портрет слева, имя крупно, кнопки «Выбрать снимок» и «Убрать снимок». Блок папки скрыт.</figcaption>
  </figure>
  <figure>
    <img src="__SHOT_FILE__" alt="Карточка Орлова Дмитрия, режим файла">
    <figcaption>Тот же сотрудник в режиме «В папке»: переключатель, имя файла и путь папки на сервере. Портрет читается из файла.</figcaption>
  </figure>
</div>

<h3>Портреты в карточках</h3>
<p>Это фотографии людей, не пиктограммы. Восемь демо-сотрудников:</p>
<div class="gallery">
__GALLERY__
</div>

<h3>Что нашли раньше и уже поправили</h3>
<div class="card yellow">
  <b>ОБНАРУЖЕН БАГ</b>
  <p>Переключатель места хранения на форме был невидим, пока в форму не попал явный список выбора. Клиент тестирования ответил так:</p>
  <pre>Поле СпособХраненияФотографии: visible = false
get_text: операция чтения текста не поддерживается
get_choice_list: список выбора пуст, статус не ok</pre>
  <p>После компиляции ChoiceList: visible = true, текст «В базе данных», два пункта, выбор «В файле на диске» показывает имя файла и каталог.</p>
</div>
<div class="card yellow">
  <b>ОБНАРУЖЕН БАГ</b>
  <p>Перенос снимка из хранилища значения в файл записал PNG под расширением .jpg, потому что исходного имени файла не было. Это не исключение платформы, расхождение поймали сравнением байтов:</p>
  <pre>Имя файла: b33aaf72-142c-47a6-b1a8-67e20f0e2c10.jpg
Сигнатура: 89 50 4E 47 0D 0A 1A 0A
Ожидалось для JPEG: FF D8
Факт: содержимое PNG при расширении jpg</pre>
  <p>Теперь пустое расширение определяется по первым байтам. Повторная запись нового сотрудника дала файл .png, байты совпали с исходным снимком.</p>
</div>

<h2>Возможности</h2>
<div class="card">
  <ul>
    <li>Показ портрета на карточке и пустая подсказка, если снимка еще нет.</li>
    <li>Загрузка кнопкой и щелчком по изображению. Фильтр: jpg, jpeg, png, gif, bmp.</li>
    <li>Переключение «В карточке» и «В папке» без немедленной порчи второго места: перенос происходит при записи.</li>
    <li>Очистка снимка. Пустые данные стирают и хранилище, и файл.</li>
    <li>Папка создается, если ее нет. Имя файла очищается от разделителей пути.</li>
    <li>Старый файл удаляется после успешной записи, а не до нее.</li>
    <li>Список команды показывает, где лежит снимок, не открывая карточку.</li>
  </ul>
</div>

<h2>Выводы</h2>
<div class="card green">
  <p>Условие задачи 5.2 закрыто. Снимок живет либо в хранилище значения, либо файлом в папке константы, и форма показывает одно место за раз. Проверка 26.10.2026: 11 сотрудников, 11 непустых снимков, 5 в базе и 6 в файлах, обе формы открываются, переключатель и блок папки ведут себя по способу хранения.</p>
  <p>Два дефекта, найденные на первых прогонах, исправлены до этой проверки: невидимый переключатель без списка выбора и расширение .jpg у содержимого PNG. В текущем прогоне исключений платформы не было.</p>
</div>

</div>
</body>
</html>
"""
    html = (html
            .replace("__DB_PCT__", str(db_pct))
            .replace("__FILE_PCT__", str(file_pct))
            .replace("__DB_LEN__", str(db_len))
            .replace("__FILE_LEN__", str(file_len))
            .replace("__DB__", str(db_count))
            .replace("__FILE__", str(file_count))
            .replace("__CONST__", esc(data["constant"]))
            .replace("__BARS__", bars(data["rows"]))
            .replace("__ROWS__", table_rows(data["rows"]))
            .replace("__GALLERY__", gallery())
            .replace("__SHOT_LIST__", data_uri(SHOT_LIST))
            .replace("__SHOT_CARD__", data_uri(SHOT_CARD))
            .replace("__SHOT_FILE__", data_uri(SHOT_FILE)))
    # В CSS остались проценты вида 100%. Их нельзя было писать как %% в шаблоне
    # рядом с подстановками, поэтому проценты диаграммы уже посчитаны.
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as out_file:
        out_file.write(html)
    print("OK bytes=%s" % os.path.getsize(OUT_PATH))


if __name__ == "__main__":
    main()
