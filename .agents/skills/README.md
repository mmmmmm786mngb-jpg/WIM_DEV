# Слой B — скиллы из Desko77/cursor-1c-skills

Cursor читает этот каталог отдельно от `.cursor/skills/`.

| Скилл | Назначение |
|---|---|
| `composing-1c-queries` | язык запросов 1С |
| `1c-query-optimization` | оптимизация запросов |
| `v8unpack-cf` | распаковка/сборка CF, CFE, EPF без платформы (`pip install v8unpack`) |

Правило слоя B лежит в `.cursor/rules/1c-form-reserved-names.mdc` (уникальное имя, проектные правила не затирает).

Обновление белого списка:

```powershell
powershell.exe -NoProfile -File tools\sync-cursor-1c-extras.ps1
```

Скрипт не пишет в `.cursor/skills/` и не удаляет чужие папки. Кэш исходника: `tools/cursor-1c-skills/` (не в git).
