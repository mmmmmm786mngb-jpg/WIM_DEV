# WIM_DEV

Репозиторий для разработки на 1С 8.3. Несколько базовых конфигураций; под каждой — папка **projects**, в ней создаются проекты.

- **Правила** (структура репозитория, проекты 1С): [.cursor/rules/](.cursor/rules/)
- **Skill по коду 1С (BSL):** [.cursor/skills/1c-bsl-coding/](.cursor/skills/1c-bsl-coding/) — применяется ко всему проекту при работе с 1С

## Папки верхнего уровня

| Папка | Назначение |
|-------|------------|
| [bases/](bases/) | Базовые конфигурации и проекты (по одной или нескольким базам) |
| [drafts/](drafts/) | Черновики, наброски, незавершённые материалы |
| [code-review/](code-review/) | Отчёты и материалы ревью кода |

## Базы и исходники

Реальные базы в **C:\\1c\\Cursor_1c\\WORK** (SBB_Broker, SBB_Depo, Wim_Du, WIM_FIn, Wim_Mo). В репозиторий не копируются.

В каждой базе в [bases/](bases/):
- **source-path.txt** — путь к каталогу с исходниками (для скриптов и проектов)
- **projects/** — папка для проектов на этой базе

**Shared-проекты** (несколько баз): [bases/shared/projects/](bases/shared/projects/). Пути к базам — в папках баз, файл source-path.txt; в проекте можно указать список баз в **bases.txt**.

## Создание проектов

- **Одна база:** создавайте в **bases/<база>/projects/**. Шаблон: [bases/SBB_Broker/projects/example/](bases/SBB_Broker/projects/example/).
- **Несколько баз:** создавайте в **bases/shared/projects/**. Шаблон: [bases/shared/projects/example/](bases/shared/projects/example/).

В проекте: Расширения, Документация, Тестирование, Скрипты. Путь к коду базы — в **source-path.txt** папки базы (для shared — ../../<база>/source-path.txt).
