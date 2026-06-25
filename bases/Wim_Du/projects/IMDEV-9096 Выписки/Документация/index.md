# IMDEV-Выписки — документация

| Файл | Описание |
|------|----------|
| [optimization_plan.html](optimization_plan.html) | **План работ:** блок 1 (Прочитать: 3 SQL + 1 цикл) + блок 2 (Разобрать: параллельность) |
| [statement_loading_optimization.html](statement_loading_optimization.html) | Полный анализ и замеры отладчика, пересмотренные приоритеты OPT-* |
| [mass_load_parallel_background_spec.html](mass_load_parallel_background_spec.html) | ТЗ: фоновая массовая загрузка «Разобрать отмеченные» (группы по счёту/договору, пул N), приложение с кодом |

## Контекст

- База: **Wim_Du**
- EPF: **внЗагрузкаВыписокДУ** (`ЗагрузкаВыписок`)
- Конфигурация: **Обработка.КлиентБанк**, **Справочник.НаборыПравилРазбораБанковскойВыписки**

Исходники EPF (оптимизация): `bases/Wim_Du/projects/IMDEV-9096 Выписки/erf_Оптимизация/внЗагрузкаВыписокДУ_epf/`  
Исходники CF: `C:\1c\Cursor_1c\WORK\Wim_Du\SRC\CF\`  
Замеры: `bases/Wim_Du/projects/IMDEV-9096 Выписки/замерОтладчика_было.docx`
