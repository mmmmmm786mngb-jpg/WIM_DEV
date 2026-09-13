#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка HTML-свода по скиллам, правилам и MCP для 1С."""

from pathlib import Path

OUT = Path(__file__).with_name("ai_1c_skills_rules_mcp_report_2026-09-13.html")

html = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Свод по ИИ-инструментам 1С — 13.09.2026</title>
<style>
:root {
  --bg: #f4f7fb;
  --card: #ffffff;
  --text: #1f2d3d;
  --muted: #6b7b8c;
  --ok: #28a745;
  --warn: #d39e00;
  --error: #dc3545;
  --info: #17a2b8;
  --violet: #6f42c1;
  --border: #dbe4ef;
  --shadow: 0 4px 14px rgba(15, 42, 71, 0.08);
}
* { box-sizing: border-box; }
body { margin: 0; font-family: Arial, sans-serif; background: var(--bg); color: var(--text); line-height: 1.45; }
.container { max-width: 1280px; margin: 0 auto; padding: 24px; }
.header { background: linear-gradient(120deg, #1d4e89, #0f7ca5); color: #fff; border-radius: 14px; padding: 28px; box-shadow: var(--shadow); }
.header h1 { margin: 0 0 8px 0; font-size: 28px; }
.header p { margin: 6px 0; color: #e7f4ff; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 18px; }
.stat { background: rgba(255,255,255,0.14); border-radius: 10px; padding: 14px 16px; }
.stat .n { font-size: 28px; font-weight: bold; }
.stat .l { font-size: 13px; color: #d7ecf8; }
.section { margin-top: 22px; background: var(--card); border-radius: 14px; padding: 20px; border: 1px solid var(--border); box-shadow: var(--shadow); }
.section h2 { margin: 0 0 12px 0; font-size: 22px; }
.section h3 { margin: 18px 0 8px 0; font-size: 17px; color: #1d4e89; }
.note { background: #eef9ff; border-left: 5px solid var(--info); border-radius: 10px; padding: 12px 14px; margin: 10px 0; }
.note.ok { background: #eefaf1; border-left-color: var(--ok); }
.note.warn { background: #fff8e6; border-left-color: var(--warn); }
.note.violet { background: #f6f0ff; border-left-color: var(--violet); }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { border-bottom: 1px solid var(--border); padding: 8px 10px; text-align: left; vertical-align: top; }
th { background: #f0f5fa; color: #35506a; }
tr:hover td { background: #f8fbff; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; font-weight: bold; }
.badge-ok { background: #d4edda; color: #155724; }
.badge-off { background: #f8d7da; color: #721c24; }
.badge-info { background: #d1ecf1; color: #0c5460; }
.badge-warn { background: #fff3cd; color: #856404; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
.card { border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; background: #fbfdff; }
.card h4 { margin: 0 0 6px 0; }
.muted { color: var(--muted); }
code { background: #eef3f8; padding: 1px 5px; border-radius: 4px; font-size: 13px; }
.toc a { color: #1d4e89; text-decoration: none; }
.toc a:hover { text-decoration: underline; }
.toc li { margin: 4px 0; }
footer { margin: 24px 0 8px; color: var(--muted); font-size: 13px; text-align: center; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Свод по ИИ-инструментам разработки 1С</h1>
    <p>Состояние на 13 сентября 2026. Контур WIM_DEV: скиллы, правила агента и MCP-серверы.</p>
    <p>Назначение: понять, чем агент реально пользуется при написании кода 1С, и чего ещё не хватает.</p>
    <div class="stats">
      <div class="stat"><div class="n">79</div><div class="l">скиллов Широкова (слой A)</div></div>
      <div class="stat"><div class="n">3</div><div class="l">доп. скилла (слой B)</div></div>
      <div class="stat"><div class="n">4 + 11</div><div class="l">правил проекта и пользователя</div></div>
      <div class="stat"><div class="n">1 / 5</div><div class="l">MCP именно для 1С / всего MCP</div></div>
    </div>
  </div>

  <div class="section">
    <h2>Содержание</h2>
    <ol class="toc">
      <li><a href="#intro">1. Что это даёт на практике</a></li>
      <li><a href="#stack">2. Текущий контур</a></li>
      <li><a href="#skills">3. Скиллы 1С</a></li>
      <li><a href="#rules">4. Правила</a></li>
      <li><a href="#mcp">5. MCP-серверы</a></li>
      <li><a href="#gaps">6. Чего нет и что не ставить</a></li>
      <li><a href="#out">7. Выводы</a></li>
    </ol>
  </div>

  <div class="section" id="intro">
    <h2>1. Что это даёт на практике</h2>
    <div class="grid">
      <div class="card">
        <h4>Скиллы</h4>
        <p>Пошаговые инструкции, как собрать форму, расширение, обработку, загрузить XML в базу, прогнать синтаксический контроль. Это «руки» агента в конфигураторе и в выгрузке.</p>
      </div>
      <div class="card">
        <h4>Правила</h4>
        <p>Постоянный стиль: куда класть проекты, как писать BSL, как не ломать формы, как оформлять документацию для бизнеса. Работают на каждой задаче, скилл вызывать не нужно.</p>
      </div>
      <div class="card">
        <h4>MCP</h4>
        <p>Живые инструменты снаружи репозитория. Сейчас для 1С подключён синтакс-помощник платформы: агент смотрит реальные методы и конструкторы, а не угадывает API.</p>
      </div>
    </div>
    <div class="note ok">
      <b>Как это стыкуется.</b> Правила задают стиль. Скиллы собирают XML и грузят в базу. MCP-синтакс-помощник отвечает на вопрос «есть ли такой метод у Массива / какой конструктор у Даты». Финальная проверка кода — синтаксический контроль конфигуратора (скилл управления расширениями).
    </div>
  </div>

  <div class="section" id="stack">
    <h2>2. Текущий контур</h2>
    <table>
      <thead><tr><th>Слой</th><th>Источник</th><th>Статус</th><th>Комментарий</th></tr></thead>
      <tbody>
        <tr>
          <td>Скиллы, слой A</td>
          <td>набор Николая Широкова (cc-1c-skills), порт под Cursor</td>
          <td><span class="badge badge-ok">подключен</span></td>
          <td>79 навыков: конфигурации, расширения, формы, СКД, базы, веб. Обновляется из git, чужие скиллы сюда не подмешивать.</td>
        </tr>
        <tr>
          <td>Скиллы, слой B</td>
          <td>белый список из набора Desko77</td>
          <td><span class="badge badge-ok">подключен</span></td>
          <td>3 навыка: язык запросов, оптимизация запросов, распаковка CF/CFE/EPF.</td>
        </tr>
        <tr>
          <td>Скилл стиля BSL</td>
          <td>внутренний 1c-bsl-coding</td>
          <td><span class="badge badge-info">справочный</span></td>
          <td>Текстовые стандарты кода. Сам BSL Language Server как MCP не запущен.</td>
        </tr>
        <tr>
          <td>Правила проекта</td>
          <td>четыре правила репозитория</td>
          <td><span class="badge badge-ok">всегда / по маске</span></td>
          <td>Структура bases, документация для бизнеса, соглашения проектов, запрет резервных имён в формах.</td>
        </tr>
        <tr>
          <td>Правила пользователя</td>
          <td>глобальные правила Cursor</td>
          <td><span class="badge badge-ok">включены</span></td>
          <td>COM через Python, комментарии BSL, кодировка, запрет HTML-сущностей в коде 1С и др.</td>
        </tr>
        <tr>
          <td>MCP 1С</td>
          <td>alkoleft, синтакс-помощник платформы 8.3.27</td>
          <td><span class="badge badge-ok">работает</span></td>
          <td>Поставлен 13.09.2026 вместо сломанного MCP к живой базе WIM_FIN.</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="section" id="skills">
    <h2>3. Скиллы 1С</h2>
    <p class="muted">Слой A — полный цикл XML и конфигуратора. Слой B — запросы и разбор бинарников. Имена ниже — как их вызывает агент.</p>

    <h3>Слой A. Конфигурация и расширения — 9</h3>
    <table>
      <thead><tr><th>Скилл</th><th>Зачем</th></tr></thead>
      <tbody>
        <tr><td><code>cf-init / cf-info / cf-edit / cf-validate</code></td><td>Создать, просмотреть, точечно править и проверить конфигурацию.</td></tr>
        <tr><td><code>cfe-init / cfe-borrow / cfe-patch-method / cfe-diff / cfe-validate</code></td><td>Расширения: scaffold, заимствование, перехват методов, состав, валидация.</td></tr>
      </tbody>
    </table>

    <h3>Слой A. Информационные базы — 13</h3>
    <table>
      <thead><tr><th>Скилл</th><th>Зачем</th></tr></thead>
      <tbody>
        <tr><td><code>db-create / db-list / db-run / db-update</code></td><td>Создать ИБ, реестр баз, запуск предприятия, обновление БД.</td></tr>
        <tr><td><code>db-dump-xml / db-load-xml / db-load-git</code></td><td>Выгрузка и загрузка XML, частичная загрузка из git.</td></tr>
        <tr><td><code>db-dump-cf / db-load-cf / db-dump-dt / db-load-dt</code></td><td>CF и DT: бэкап и восстановление конфигурации / всей базы.</td></tr>
        <tr><td><code>db-repo</code></td><td>Хранилище конфигурации: захват, помещение, получение.</td></tr>
        <tr><td><code>db-cfe-admin</code></td><td>Расширения в живой базе: применимость и синтаксический контроль модулей.</td></tr>
      </tbody>
    </table>

    <h3>Слой A. Обработки и отчёты — 10</h3>
    <table>
      <thead><tr><th>Скилл</th><th>Зачем</th></tr></thead>
      <tbody>
        <tr><td><code>epf-init / epf-dump / epf-build / epf-validate</code></td><td>Внешние обработки: создать, разобрать, собрать EPF, проверить.</td></tr>
        <tr><td><code>epf-bsp-init / epf-bsp-add-command</code></td><td>Регистрация в БСП «Дополнительные отчёты и обработки».</td></tr>
        <tr><td><code>erf-init / erf-dump / erf-build / erf-validate</code></td><td>То же для внешних отчётов ERF.</td></tr>
      </tbody>
    </table>

    <h3>Слой A. Формы, метаданные, СКД, макеты — 27</h3>
    <table>
      <thead><tr><th>Группа</th><th>Скиллы</th><th>Зачем</th></tr></thead>
      <tbody>
        <tr><td>Формы</td><td><code>form-add, compile, decompile, edit, info, patterns, remove, validate</code></td><td>Управляемые формы из XML/JSON, паттерны компоновки.</td></tr>
        <tr><td>Метаданные</td><td><code>meta-compile, decompile, edit, info, remove, validate</code></td><td>Справочники, документы, регистры, общие модули.</td></tr>
        <tr><td>СКД</td><td><code>skd-compile, decompile, edit, info, validate</code></td><td>Схемы компоновки отчётов.</td></tr>
        <tr><td>MXL</td><td><code>mxl-compile, decompile, info, validate</code></td><td>Печатные формы и табличные документы.</td></tr>
        <tr><td>Макеты объекта</td><td><code>template-add / template-remove</code></td><td>Пустой макет у объекта.</td></tr>
      </tbody>
    </table>

    <h3>Слой A. Роли, подсистемы, XDTO, веб — 20</h3>
    <table>
      <thead><tr><th>Группа</th><th>Скиллы</th><th>Зачем</th></tr></thead>
      <tbody>
        <tr><td>Роли</td><td><code>role-compile / role-info / role-validate</code></td><td>Права, RLS, аудит роли.</td></tr>
        <tr><td>Подсистемы</td><td><code>subsystem-compile / edit / info / validate</code></td><td>Разделы командного интерфейса.</td></tr>
        <tr><td>Интерфейс</td><td><code>interface-edit / interface-validate</code></td><td>Видимость и порядок команд.</td></tr>
        <tr><td>XDTO</td><td><code>xdto-compile / decompile / edit / info / validate</code></td><td>Пакеты обмена и XML-схемы.</td></tr>
        <tr><td>Веб</td><td><code>web-info / publish / unpublish / stop / test</code></td><td>Apache, публикация, проверка в веб-клиенте.</td></tr>
        <tr><td>Прочее</td><td><code>help-add, support-edit, img-grid</code></td><td>Справка объекта, снятие с поддержки, сетка на скриншоте макета.</td></tr>
      </tbody>
    </table>

    <h3>Слой B. Дополнения — 3</h3>
    <table>
      <thead><tr><th>Скилл</th><th>Зачем</th></tr></thead>
      <tbody>
        <tr><td><code>composing-1c-queries</code></td><td>Язык запросов 1С: синтаксис, виртуальные таблицы, типовые ошибки.</td></tr>
        <tr><td><code>1c-query-optimization</code></td><td>Медленные запросы: временные таблицы, соединения, агрегаты, СКД.</td></tr>
        <tr><td><code>v8unpack-cf</code></td><td>Распаковка и сборка CF / CFE / EPF без конфигуратора.</td></tr>
      </tbody>
    </table>

    <div class="note">
      Скиллы хорошо закрывают <b>сборку объектов и выгрузку/загрузку</b>. Они не заменяют синтакс-помощник платформы и не являются линтером BSL: несуществующий метод массива скилл сам не поймает.
    </div>
  </div>

  <div class="section" id="rules">
    <h2>4. Правила</h2>

    <h3>Правила репозитория (всегда или по маске файлов)</h3>
    <table>
      <thead><tr><th>Правило</th><th>Когда</th><th>Суть</th></tr></thead>
      <tbody>
        <tr><td>Структура репозитория</td><td>всегда</td><td>Проекты в bases/&lt;база&gt;/projects, не копировать исходники базы, скиллы слоя A не затирать.</td></tr>
        <tr><td>Аудитория документации</td><td>всегда</td><td>В папке Документация нет локальных путей, Cursor, скиллов и MCP — это для бизнеса.</td></tr>
        <tr><td>Соглашения проектов 1С</td><td>файлы в bases/</td><td>Путь к базе из source-path.txt; в проекте Расширения / Документация / Тестирование / Скрипты.</td></tr>
        <tr><td>Резервные имена форм</td><td>модули *.bsl</td><td>Не называть переменные Параметры, Вид, НастройкиОтчета и т.п. — платформа путает их с реквизитами формы.</td></tr>
      </tbody>
    </table>

    <h3>Пользовательские правила, важные для кода 1С</h3>
    <table>
      <thead><tr><th>Правило</th><th>Суть</th></tr></thead>
      <tbody>
        <tr><td>Разработка 1С</td><td>PascalCase, ключевые слова 1С в каноническом регистре, клиент/сервер, параметры вместо констант, запросы только через параметры.</td></tr>
        <tr><td>Комментарии BSL</td><td>Документирующие блоки у экспортных процедур: Описание, Параметры, Возвращаемое значение.</td></tr>
        <tr><td>Семантический разбор ошибок</td><td>Ловить намерение, а не буквальный синтаксис (Новый Массив(1,2,3) — это не список; Дата — год, месяц, день).</td></tr>
        <tr><td>Python + COM</td><td>Как подключаться к базе, создавать объекты, выполнять запросы, вызывать модули и обработки.</td></tr>
        <tr><td>Без HTML-сущностей в коде</td><td>В запросах 1С писать &amp;Параметр как есть, не &amp;amp;Параметр.</td></tr>
        <tr><td>Кодировка и отчёты</td><td>UTF-8, ASCII в консоли, HTML-отчёты о тестах 1С через Python.</td></tr>
        <tr><td>Куда класть файлы</td><td>Документация / Тестирование / Скрипты — по назначению, имена файлов латиницей.</td></tr>
      </tbody>
    </table>
  </div>

  <div class="section" id="mcp">
    <h2>5. MCP-серверы</h2>
    <p>Подключены в Cursor глобально. Для разработки 1С сейчас важен один.</p>

    <h3>Для 1С</h3>
    <table>
      <thead><tr><th>Сервер</th><th>Статус</th><th>Что делает</th><th>Инструменты</th></tr></thead>
      <tbody>
        <tr>
          <td>1c-platform<br><span class="muted">alkoleft / mcp-bsl-platform-context 0.3.2</span></td>
          <td><span class="badge badge-ok">работает</span></td>
          <td>Синтакс-помощник платформы 8.3.27. Поиск методов, свойств, типов, конструкторов. Не ходит в данные учёта.</td>
          <td>search, info, getMember, getMembers, getConstructors</td>
        </tr>
        <tr>
          <td>1c-server<br><span class="muted">прокси к HTTP-сервису живой базы</span></td>
          <td><span class="badge badge-off">отключён 13.09.2026</span></td>
          <td>Был сломан (Cursor не видел инструменты). Вел на одну базу WIM_FIN. Заменён синтакс-помощником.</td>
          <td>—</td>
        </tr>
      </tbody>
    </table>

    <h3>Прочие MCP (не про код 1С)</h3>
    <table>
      <thead><tr><th>Сервер</th><th>Статус</th><th>Назначение</th></tr></thead>
      <tbody>
        <tr><td>word</td><td><span class="badge badge-ok">включён</span></td><td>Документы Word.</td></tr>
        <tr><td>excel</td><td><span class="badge badge-ok">включён</span></td><td>Таблицы Excel.</td></tr>
        <tr><td>puppeteer</td><td><span class="badge badge-ok">включён</span></td><td>Браузерная автоматизация.</td></tr>
        <tr><td>filesystem</td><td><span class="badge badge-info">узкий каталог</span></td><td>Файлы отдельного рабочего каталога MCP, не исходники конфигураций.</td></tr>
      </tbody>
    </table>

    <div class="note violet">
      <b>Что даёт 1c-platform.</b> Агент может спросить: какие методы у типа Массив, как создать Дату, есть ли ДобавитьВКонец. Это закрывает класс ошибок «модель выдумала API платформы». Это не проверка вашего прикладного кода и не доступ к справочникам базы.
    </div>
  </div>

  <div class="section" id="gaps">
    <h2>6. Чего нет и что не ставить</h2>
    <table>
      <thead><tr><th>Инструмент</th><th>Статус</th><th>Зачем был бы нужен</th><th>Решение сейчас</th></tr></thead>
      <tbody>
        <tr>
          <td>BSL Language Server (линтер BSL)</td>
          <td><span class="badge badge-warn">не подключён</span></td>
          <td>~180 проверок по файлам: запрос в цикле, пустой Исключение, транзакции, устаревшие методы.</td>
          <td>Опционально следующим шагом. Не заменяет конфигуратор.</td>
        </tr>
        <tr>
          <td>MCP к живой базе (запросы, выполнение кода)</td>
          <td><span class="badge badge-off">снят</span></td>
          <td>Прогон запроса на реальных метаданных конкретной ИБ.</td>
          <td>Не ставить второй, пока нет стабильного сервиса. Есть XML-выгрузки и COM-тесты.</td>
        </tr>
        <tr>
          <td>1С:Напарник</td>
          <td><span class="badge badge-info">не ставим</span></td>
          <td>Ревью специализированной моделью 1С.</td>
          <td>Нужен ИТС и токен code.1c.ai. Не линтер и не синтакс-помощник.</td>
        </tr>
        <tr>
          <td>EDT-MCP</td>
          <td><span class="badge badge-info">не нужен</span></td>
          <td>Глубокая интеграция с EDT.</td>
          <td>Рабочий контур — конфигуратор и XML, не EDT.</td>
        </tr>
        <tr>
          <td>OData MCP (данные учёта)</td>
          <td><span class="badge badge-info">не про разработку</span></td>
          <td>Вопросы «покажи долги / продажи».</td>
          <td>Не уменьшает ошибки в BSL.</td>
        </tr>
      </tbody>
    </table>
    <div class="note warn">
      Не смешивать в одном проекте полный набор правил comol и скиллы Широкова: агент начнёт дергать оба контура сразу, контекст распухнет. Слой B — только белый список из трёх скиллов.
    </div>
  </div>

  <div class="section" id="out">
    <h2>7. Выводы</h2>
    <ol>
      <li>Для разработки 1С контур уже рабочий: 82 скилла (79 + 3) закрывают XML, расширения, формы, загрузку в базу и веб-проверки.</li>
      <li>Правила держат структуру репозитория, стиль BSL и запрет опасных имён в модулях форм.</li>
      <li>С 13.09.2026 у агента есть синтакс-помощник платформы. Это главный MCP именно для качества кода 1С.</li>
      <li>Сломанный MCP живой базы отключён специально: он не помогал писать код и мешал.</li>
      <li>Единственный осмысленный следующий MCP — линтер BSL Language Server. Остальные 1С-MCP (OData, EDT, Напарник) сейчас не закрывают дыру в качестве кода.</li>
    </ol>
    <div class="note ok">
      Практическая проверка MCP: в чате агента «покажи методы типа Массив» или «как устроен конструктор Дата». Если отвечают инструменты search / getMembers — синтакс-помощник живой.
    </div>
  </div>

  <footer>Свод на 13.09.2026. Внутренний материал по ИИ-контуру разработки 1С, не документация для заказчика.</footer>
</div>
</body>
</html>
"""

OUT.write_text(html, encoding="utf-8")
print("Wrote", OUT)
print("Bytes", OUT.stat().st_size)
