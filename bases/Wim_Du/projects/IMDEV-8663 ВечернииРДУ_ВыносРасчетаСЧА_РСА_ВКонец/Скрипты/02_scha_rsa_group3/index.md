# Скрипты доработки 2 (СЧА/РСА, группа 3)

Выходные файлы пишутся в `Документация/02_scha_rsa_group3/`.

| Скрипт / папка | Назначение |
|---|---|
| `build_presentation_pptx.py` | Сборка `presentation_scha_rsa.pptx` |
| `export_presentation_pdf.py` | Экспорт `presentation_scha_rsa.pdf` из HTML |
| `check_pptx_render.py` | Экспорт слайдов PPTX в PNG для проверки вёрстки |
| `epf_move_scha_rsa_group3/` | Исходники внешней обработки для поддержки: группа 3 и перенос пяти операций (создаётся по ревизии промпта) |

Запуск из этой папки (пример):

```text
python build_presentation_pptx.py
python export_presentation_pdf.py
```
