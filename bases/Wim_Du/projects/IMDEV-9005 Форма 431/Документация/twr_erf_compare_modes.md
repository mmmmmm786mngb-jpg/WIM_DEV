# Сравнение режимов TWR: два ERF для базы МО

Для A/B-замеров в базе **WIM_MO** без COM и без изменения конфигурации используются два внешних отчёта:

| ERF | Режим | Логика | Соответствие обработке 0420431 |
|-----|-------|--------|--------------------------------|
| `внVTBAM_TWR_MANDATE_STRATEGY.erf` | **MANDATE_STRATEGY** (batch) | Один вызов `TWR` на все мандаты | `epf_Оптимизиция` (opt.1) |
| `внVTBAM_TWR_MANDATE.erf` | **MANDATE** (per-strategy) | Цикл: один `TWR` на стратегию | `NEW_Оптимизация` (текущая обработка) |

## Исходники

```
Отчеты/
  внVTBAM_TWR_MANDATE_STRATEGY.xml
  внVTBAM_TWR_MANDATE.xml
```

## Сборка (WIM_MO)

```powershell
powershell.exe -NoProfile -File .cursor/skills/epf-build/scripts/epf-build.ps1 `
  -InfoBaseServer "localhost" -InfoBaseRef "WIM_MO" `
  -SourceFile "bases/Wim_Du/projects/IMDEV-9005 Форма 431/Отчеты/внVTBAM_TWR_MANDATE.xml" `
  -OutputFile "bases/Wim_Du/projects/IMDEV-9005 Форма 431/Отчеты/внVTBAM_TWR_MANDATE.erf"
```

## Сценарий сравнения

1. Одинаковый период и флаги пассивов на обеих формах.
2. **MANDATE_STRATEGY** — одна строка в журнале `IMDEV-9005.TWR`, суммарное время одного вызова.
3. **MANDATE** — таблица «Замеры по стратегиям» + суммарное время N вызовов в строке статуса.
4. Сравнить: общее время, число вызовов, детализацию по стратегиям.

## Журнал регистрации

Событие: `IMDEV-9005.TWR`

- batch: `TWR MANDATE_STRATEGY: мандатов=..., сек=...`
- per-strategy: `TWR MANDATE per-strategy: вызовов=..., сек=...`
