# IMDEV-Выписки — документация

| Файл | Описание |
|------|----------|
| [may_regression_report.html](may_regression_report.html) | **Регресс за май (18-31.05):** XLSX-сверка было/стало, ПП 8835=8835, примеры ЕРС 21.05 / ДУ 9957 / 10076 |
| [imdev-9096_optimization_regression_report.html](imdev-9096_optimization_regression_report.html) | **Итоговый отчет регрессии (01-05.06):** оригинал vs ispr5, OPT-02/05/17/18, скорость 8.9x, MXL/ПП/лог |
| [optimization_plan.html](optimization_plan.html) | **План работ:** блок 1 (Прочитать: 3 SQL + 1 цикл) + блок 2 (Разобрать: параллельность) |
| [optimization_read_results.html](optimization_read_results.html) | **Результаты оптимизации «Прочитать»:** замеры было/стало (617→237 с) + регресс MXL 1106 |
| [statement_loading_optimization.html](statement_loading_optimization.html) | Полный анализ и замеры отладчика, статус OPT-* (раздел 0), регрессия MXL (раздел 0.1) |
| [mass_load_parallel_background_spec_v2.html](mass_load_parallel_background_spec_v2.html) | **ТЗ v2.0 (актуальное):** фоновая параллельная загрузка «Разобрать отмеченные» — сверено с кодом+API, упрощено через `ОперацияВыполнена`, КлиентБанк на выписку, примеры кода |
| [mass_load_parallel_background_spec.html](mass_load_parallel_background_spec.html) | ТЗ 1.0 (исходное): фоновая массовая загрузка (группы по счёту/договору, пул N) |

## Контекст

- База: **Wim_Du**
- EPF: **внЗагрузкаВыписокДУ** (`ЗагрузкаВыписок`)
- Конфигурация: **Обработка.КлиентБанк**, **Справочник.НаборыПравилРазбораБанковскойВыписки**

**Baseline EPF (замеры «было»):** `bases/Wim_Du/projects/IMDEV-9096 Выписки/erf_Оптимизация/внЗагрузкаВыписокДУ_epf/`  
**Рабочая ветка (оптимизации):** `bases/Wim_Du/projects/IMDEV-9096 Выписки/erf_Оптимизация_Тест1/внЗагрузкаВыписокДУ_epf/`  
Исходники CF: `C:\1c\Cursor_1c\WORK\Wim_Du\SRC\CF\`  
Замеры: `bases/Wim_Du/projects/IMDEV-9096 Выписки/замерОтладчика_было.docx`

## Сборка EPF

- **База сборки (без авторизации):** `Srvr="localhost";Ref="WIM_Du"`
- **Не путать с WIM_MO** — это другая конфигурация.
- Скрипт: `Скрипты/build_epf_zagruzka_vypisok.ps1`
- Результат Test1: `erf_Оптимизация_Тест1/внЗагрузкаВыписокДУ.epf`

```powershell
powershell.exe -NoProfile -File "bases/Wim_Du/projects/IMDEV-9096 Выписки/Скрипты/build_epf_zagruzka_vypisok.ps1"
```

## Статус реализации (Test1)

| ID | Статус | Описание |
|----|--------|----------|
| OPT-02 | Выполнено | Пакетный кэш `ДоговорДУПоСчету` в `ПрочитатьОбъекты` |
| OPT-17 | Выполнено | Ленивый кэш `ЕРС_ДоговорДУ_ПоСчетуИСчетуДепо` (разбивка на 3 функции) |
| OPT-05 | Выполнено | Кэш `ЕРС_ДоговорДУ_ПоПлатежномуПоручению` (`ПолучитьПлатежныеПорученияОкна`) |
| OPT-18 | Выполнено | Индекс префиксов для `ЕРС_ДоговорДУ_ПоСчетуИНазначению` |

**Регрессия MXL:** Запрос1 — 629/629 (7 позиционных diff, перестановка ЕРС); 1106 — 387/387, 0 diff. См. [optimization_read_results.html](optimization_read_results.html).

**Замер «Прочитать» (Test1, v5.90):** 617 с → 237 с (~2.6x). Источник: `ОптимизацияЧтения_БылоСталоРегресс.docx`.
