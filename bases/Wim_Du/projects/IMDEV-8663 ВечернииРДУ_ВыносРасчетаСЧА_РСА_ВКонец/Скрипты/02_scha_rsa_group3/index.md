# Скрипты доработки 2 (СЧА/РСА, группа 3)

Выходные файлы презентации пишутся в `Документация/02_scha_rsa_group3/`.

| Скрипт / папка | Назначение |
|---|---|
| `build_presentation_pptx.py` | Сборка `presentation_scha_rsa.pptx` |
| `export_presentation_pdf.py` | Экспорт `presentation_scha_rsa.pdf` из HTML |
| `check_pptx_render.py` | Экспорт слайдов PPTX в PNG для проверки вёрстки |
| `epf_move_scha_rsa_group3/` | Исходники внешней обработки для поддержки: группа 3, перенос пяти операций и возврат в вечерние |
| `epf_compare_scha_rsa_docs/` | Тестовая обработка: снимок документов СЧА/РСА за день, пометка планов в потоках, сверка двух JSON |
| `run_com_test_cancel_group3.py` | COM-прогон отмены порций и связки групп 2/3 на WIM_DU (~500 договоров). HTML-отчёт пишет в документацию; при наличии PNG в `Тестирование/reports/web_shots` встраивает скриншоты |
| `dump_web_shot_targets.py` | Выгрузка навигационных ссылок тестовых документов IM86632_COMTEST для веб-клиента |
| `capture_web_shots.js` | Сценарий веб-клиента: открыть формы и сохранить PNG |

Запуск из этой папки (пример):

```text
python build_presentation_pptx.py
python export_presentation_pdf.py
```
