# Тестирование IMDEV-9302

## Обработка сравнения результатов

| Путь | Назначение |
|------|------------|
| `внСравнениеРезультатовРаспределенияДоходовЦБ_epf/` | Исходники EPF |
| Описание сценария | `../Документация/regression_compare_tool.html` |

Сборка (из корня WIM_DEV, база Wim_Du):

```powershell
powershell.exe -NoProfile -File ".cursor/skills/epf-build/scripts/epf-build.ps1" `
  -ProcessorName "внСравнениеРезультатовРаспределенияДоходовЦБ" `
  -SrcDir "bases/Wim_Du/projects/IMDEV-9302 Распред доходов по ЦБ (Кукушкни 020926)/Тестирование/внСравнениеРезультатовРаспределенияДоходовЦБ_epf" `
  -OutDir "bases/Wim_Du/projects/IMDEV-9302 Распред доходов по ЦБ (Кукушкни 020926)/Тестирование"
```
