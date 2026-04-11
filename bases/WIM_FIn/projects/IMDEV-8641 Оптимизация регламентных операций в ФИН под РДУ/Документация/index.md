# Documentation

Specifications and notes for this project.

- [imdev8641_brief_development_tz.html](imdev8641_brief_development_tz.html) — краткое ТЗ на разработку (цели, границы, принципы, приёмка, свод по запросам BSL).
- [imdev8641_final_development_tz.html](imdev8641_final_development_tz.html) — окончательное ТЗ (статус RduPF, алгоритм по ТЗ на модуль менеджера РС, пошаговая разработка, новая блок-схема).
- [work_plan_imdev8641.md](work_plan_imdev8641.md) — календарный план работ (анализ базы, разбор операций, код, тесты, расширение Аванкор).
- [plan_reg_oper_du_group_closure_chain.md](plan_reg_oper_du_group_closure_chain.md) — аналитика цепочки `ПланРегламентныхОперацийДУ` и `ГрупповоеВыполнениеЗакрытияПериодов` (код базы WIM_FIn).
- [imdev8641_development_brief.md](imdev8641_development_brief.md) — постановка на разработку (бизнес + технические вставки, пример запроса, критерии приёмки).
- [filter_plan_regl_operations_table_integration.md](filter_plan_regl_operations_table_integration.md) — встраивание фильтра таблицы плана в `ВыполнитьМногопоточноеЗакрытиеПериодовПортфелей`, колонки и типы `ПланРеглОпераций`.
- [tz_subordinate_docs_analytics_plan_reg_oper_du.md](tz_subordinate_docs_analytics_plan_reg_oper_du.md) — ТЗ: внешняя обработка, проверка наличия документа по виду операции в разрезе пула портфелей.
- [operation_closure_procedure_document_map.html](operation_closure_procedure_document_map.html) — соответствие операций закрытия, процедур и типов документов; перечень видов для фильтра плана — регистр сведений **`ВидыОптимизируемыхРегламентныхОперацийДУ`** со ссылками на `ВидыОперацийЗакрытияПериода` (см. `filter_plan_regl_operations_table_integration.md`).
- [operation_closure_data_sources.md](operation_closure_data_sources.md) — источники данных и условия пустого результата (нет проведения / нет новой записи) по тем же процедурам.
