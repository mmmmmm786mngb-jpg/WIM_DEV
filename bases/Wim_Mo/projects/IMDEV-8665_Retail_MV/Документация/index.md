# IMDEV-8665: документация



| Документ | Описание |

| --- | --- |

| [imdev_8665_retail_mv_task.html](imdev_8665_retail_mv_task.html) | Постановка задачи, разбор алгоритма обработки `внРасчетMVиWAP`, команды RETAIL, план работ |

| [mv_wap_current_flow.html](mv_wap_current_flow.html) | Детальная текущая схема вызовов обработки `внРасчетMVиWAP`, с фокусом на `ВыполнитьКомандуПересчет_MV_и_WAP` и нижележащие вызовы |

| [mv_document_calculation_flow.html](mv_document_calculation_flow.html) | Детальный разбор внутренней логики документа `РасчетРыночнойСтоимости`: `ЗаполнитьДокумент()`, источники данных, пересчет ТЧ и `ОбработкаПроведения()` с перечнем записываемых регистров |

| [wap_document_calculation_flow.html](wap_document_calculation_flow.html) | Детальный разбор внутренней логики документа `РасчетСредневзвешеннойСтоимости`: `ЗаполнитьДокумент()`, источники данных расчета WAP и `ОбработкаПроведения()` с перечнем записываемых полей регистра |

| [wap_calculation_optimization_wishlist_draft.md](../Черновики_8665/wap_calculation_optimization_wishlist_draft.md) | Черновик пожеланий по оптимизации: `ВТ_СчетаМандатов`, массив мандатов в пакете, `ВТ_МаксПериод`, риски и следующие шаги (папка `Черновики_8665`) |

| [parallel_external_processing_methods_guide.html](parallel_external_processing_methods_guide.html) | Методика фоновых и параллельных вызовов методов модуля объекта `внРасчетMVиWAP` через `ДополнительныеОтчетыИОбработки` и адаптер (не править типовой `ДлительныеОперации`) |

| [measurements_table_IMDEV-8665.html](measurements_table_IMDEV-8665.html) | Таблица замеров проблемных участков (до оптимизации) |

| [measurements_table_IMDEV-8665_jira.txt](measurements_table_IMDEV-8665_jira.txt) | То же для вставки в Jira (wiki markup) |

| [jira_comment_IMDEV-8665_final_8_13.txt](jira_comment_IMDEV-8665_final_8_13.txt) | Краткий комментарий в Jira 8.13: итог теста, улучшения, регресс |

| [Инструкция_запуск_пересчета_MV_и_WAP_база_T1.html](Инструкция_запуск_пересчета_MV_и_WAP_база_T1.html) | Инструкция для бизнес-заказчика: как на базе T-1 вручную запустить регламентное задание пересчета MV/WAP (без полного теста) |

| [changes_tree_IMDEV-8665.html](changes_tree_IMDEV-8665.html) | Дерево изменений по задаче |



## Связанные файлы в репозитории



- Выгрузка Jira: `docs/8665_задача` (корень репозитория WIM_DEV).

- HTML-отчет финального теста: `bases/Wim_Mo/projects/IMDEV-8665 Тесты/Тестирование/reports/imdev_8665_final_test_report.html`.

- Сводка по РДУ и контексту собрания: `ДимаХ/Переход_01_04_2026/КСобранию_2026_04_28/common_task_mo_rdu_summary_2026_04_28.html`.



Исходники обработки в каталоге базы Wim_Mo: `SRC/epf/внРасчетMVиWAP_epf/` (см. `bases/Wim_Mo/source-path.txt`).

