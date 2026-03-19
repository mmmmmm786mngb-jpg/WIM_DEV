# Конфигурация Cursor - Rules & Skills

> Содержимое всех правил (Rules) и навыков (Skills), настроенных в Cursor для проекта WIM_DEV.
> Дата экспорта: 2026-03-19

---

## Rules (Правила)

### Workspace Rules (файлы `.cursor/rules/`)

Правила на уровне проекта, хранятся в `.mdc` файлах:

| # | Файл | Описание | Always Apply |
|---|------|----------|:---:|
| 1 | [project-structure](Rules/Workspace/01-project-structure.md) | Структура репозитория WIM_DEV | Да |
| 2 | [1c-project-conventions](Rules/Workspace/02-1c-project-conventions.md) | Правила для проектов 1С в bases/ | Нет (globs: `bases/**/*`) |

### User Rules (глобальные настройки Cursor)

Правила на уровне пользователя, заданы в настройках Cursor:

| # | Файл | Описание |
|---|------|----------|
| 1 | [no-hieroglyphs](Rules/User/01-no-hieroglyphs.md) | Запрет на иероглифы и спец. Unicode символы |
| 2 | [html-test-reports](Rules/User/02-html-test-reports.md) | Создание HTML отчетов о тестировании 1С через Python |
| 3 | [1c-python-com](Rules/User/03-1c-python-com.md) | Работа с 1С через Python (COM) - полное руководство |
| 4 | [no-html-entities](Rules/User/04-no-html-entities-in-code.md) | Запрет HTML-сущностей в коде 1С/Python/SQL |
| 5 | [1c-commenting](Rules/User/05-1c-commenting-standards.md) | Стандарты комментирования кода 1С (BSL) |
| 6 | [semantic-analysis](Rules/User/06-semantic-error-analysis.md) | Семантический анализ ошибок 1С |
| 7 | [russian-encoding](Rules/User/07-russian-encoding.md) | Работа с русской кодировкой и кракозябрами |
| 8 | [file-creation](Rules/User/08-file-creation-rules.md) | Правила создания файлов (Документация/Тесты/Скрипты) |
| 9 | [office-documents](Rules/User/09-office-documents-encoding.md) | Кодировка и Office документы (Word/Excel) |
| 10 | [effective-ai-work](Rules/User/10-effective-ai-work.md) | Правила эффективной работы с AI в Cursor |
| 11 | [1c-development](Rules/User/11-1c-development-rules.md) | Правила разработки на 1С:Enterprise |

---

## Skills (Навыки)

### 1c-bsl-coding (`.cursor/skills/1c-bsl-coding/`)

Навык для разработки кода 1С (BSL):

| # | Файл | Описание |
|---|------|----------|
| 1 | [SKILL](Skills/1c-bsl-coding/01-SKILL.md) | Основной файл - стиль кода, запросы, архитектура, документирование |
| 2 | [REFERENCE](Skills/1c-bsl-coding/02-REFERENCE.md) | Примеры кода 1С (запросы, массивы, проверки, комментарии) |
| 3 | [STANDARDS-AND-TOOLS](Skills/1c-bsl-coding/03-STANDARDS-AND-TOOLS.md) | Стандарты v8-code-style и BSL Language Server |

---

## User Settings

| Файл | Источник | Описание |
|------|----------|----------|
| [settings.json](settings.json) | `%APPDATA%\Cursor\User\settings.json` | Пользовательские настройки Cursor (редактор, BSL LS, терминал, тема, шрифты) |

---

## Структура папок

```
Private/CursorConfig/
  INDEX.md                          <-- этот файл
  settings.json                     <-- пользовательские настройки Cursor
  Rules/
    Workspace/                      <-- правила проекта (.cursor/rules/)
      01-project-structure.md
      02-1c-project-conventions.md
    User/                           <-- пользовательские правила (Cursor Settings)
      01-no-hieroglyphs.md
      02-html-test-reports.md
      03-1c-python-com.md
      04-no-html-entities-in-code.md
      05-1c-commenting-standards.md
      06-semantic-error-analysis.md
      07-russian-encoding.md
      08-file-creation-rules.md
      09-office-documents-encoding.md
      10-effective-ai-work.md
      11-1c-development-rules.md
  Skills/
    1c-bsl-coding/                  <-- навык разработки 1С (BSL)
      01-SKILL.md
      02-REFERENCE.md
      03-STANDARDS-AND-TOOLS.md
```

## Где хранятся оригиналы

| Тип | Расположение | Как редактировать |
|-----|-------------|-------------------|
| Workspace Rules | `.cursor/rules/*.mdc` | Редактировать файлы `.mdc` напрямую |
| User Rules | Cursor Settings -> Rules for AI | Cursor -> Settings -> Rules for AI |
| Skills | `.cursor/skills/<name>/SKILL.md` | Редактировать файлы в `.cursor/skills/` |
