# IMDEV-9005 — Документация

| Файл | Описание |
|------|----------|
| [imdev-9005_measurements_may2026.html](imdev-9005_measurements_may2026.html) | **Замеры** оригинальной обработки, среда т-1 (`AVC_PP_DU`), период май 2026 (1 ч 54 мин) |
| [imdev-9005_measurements_t1_profiler.html](imdev-9005_measurements_t1_profiler.html) | **Замеры т-1 (docx)** — профилировщик + журнал, старый алгоритм, узкие места TWR/НайтиСтроки |
| [imdev-9005_measurements_before_after.html](imdev-9005_measurements_before_after.html) | **БЫЛО / СТАЛО** — сравнение замеров, МО retail, финальный прогон ДУ, регрессия 0420431 |
| [imdev-9005_final_development_report.html](imdev-9005_final_development_report.html) | **Итоговая разработка** — ДУ: стр. 801/2470/2471; МО: индекс MV по Разделитель |
| [imdev-9005_optimizations_v120.html](imdev-9005_optimizations_v120.html) | **v1.20** — две оптимизации (TWR/MANDATE_STRATEGY + раздел 1.2), теория и практика |
| [imdev-9005_optimizations.html](imdev-9005_optimizations.html) | Краткая документация по трем оптимизациям и обоснованию замерами |
| [../IMDEV-9005_parallel_zapolnenie.html](../IMDEV-9005_parallel_zapolnenie.html) | Подробно: параллельное заполнение разделов 2–7 |
| [../Тесты_замеры_9005.docx](../Тесты_замеры_9005.docx) | Исходные замеры производительности |

## Комментарии для Jira 8.13 (wiki markup, panel)

| Файл | Тема |
|------|------|
| [jira/jira_comment_imdev9005_v120.txt](jira/jira_comment_imdev9005_v120.txt) | **v1.20** — обе оптимизации (Jira panel) |
| [jira/jira_comment_opt1_mo_query.txt](jira/jira_comment_opt1_mo_query.txt) | Опт. 1: база МO, TWR |
| [jira/jira_comment_opt2_section12_findrows.txt](jira/jira_comment_opt2_section12_findrows.txt) | Опт. 2: НайтиСтроки раздел 1.2 |
| [jira/jira_comment_opt3_parallel_sections.txt](jira/jira_comment_opt3_parallel_sections.txt) | Опт. 3: параллель разделов 2–7 |
| [jira/jira_comment_compare_0420431.txt](jira/jira_comment_compare_0420431.txt) | Обработка {{внСравнение0420431}} — сравнение двух документов 0420431 |
| [jira/jira_comment_imdev9005_final.txt](jira/jira_comment_imdev9005_final.txt) | **Итоговая разработка** — Jira 8.13: замеры, доработки, регрессия |
| [twr_erf_compare_modes.md](twr_erf_compare_modes.md) | Два ERF для сравнения TWR: MANDATE_STRATEGY vs MANDATE (per-strategy) |
