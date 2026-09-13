# Тестирование ОУ партионный учет

| Файл | Назначение |
|------|------------|
| `test_ou_batch_scenarios.py` | COM-прогон функциональных сценариев |
| `test_ou_perf_expense.py` | Замер времени проведения РН (N строк ТЧ) |
| `seed_web_report_data.py` | Тестовые документы сентября для отчетов |
| `web_test_reports.js` | Автотест отчетов в веб-клиенте |
| `perf_test_plan.md` | План нагрузочного тестирования |
| `reports/` | HTML/JSON/PNG отчеты прогонов |

## Функциональные тесты

```powershell
$env:PYTHONIOENCODING = "utf-8"
python ".\Тестирование\test_ou_batch_scenarios.py"
```

## Производительность расхода

```powershell
python ".\Тестирование\test_ou_perf_expense.py" before 50,100,200,500
python ".\Тестирование\test_ou_perf_expense.py" after 50,100,200,500
```

Сравнительный отчет: `Документация/ou_perf_expense_report.html`.

ИБ: OU_Training, пользователь Admin / 1.
