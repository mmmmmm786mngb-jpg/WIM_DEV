# Доработка 2 — вынос СЧА/РСА в группу 3

Задача: **IMDEV-8663**, часть 2 из 2.

## Суть

Сейчас операции расчета СЧА/РСА (1000) и связанные контрольные (1010–1030) входят в группу `2. "Вечерние" операции` и вызываются **по каждому договору** в цикле.

Предлагается:

1. Создать группу `3. "Расчет СЧА/РСА"` и перенести туда эти операции.
2. Запускать группу 3 **после** полного завершения вечерних операций по всем договорам отбора.
3. Считать показатели **пакетно** по группам договоров с одинаковой сигнатурой параметров (вариант A+D1).

## Документы

| Файл | Назначение |
|---|---|
| [prompt_imdev8663_2_extension.html](prompt_imdev8663_2_extension.html) | **Промпт на реализацию**: новое расширение IM86632 над базой после переноса 8663.1 вендором |
| [proposal_scha_rsa_batch_calculation.html](proposal_scha_rsa_batch_calculation.html) | Полное предложение для бизнеса и разработки |
| [presentation_scha_rsa.html](presentation_scha_rsa.html) | Презентация 16:9 (HTML) |
| [presentation_scha_rsa.pdf](presentation_scha_rsa.pdf) | PDF |
| [presentation_scha_rsa.pptx](presentation_scha_rsa.pptx) | PPTX |
| [vim_logo.png](vim_logo.png) | Логотип для HTML/PPTX |
| proposal_scha_rsa_batch_calculation.rar | Архив предложения (если нужен для рассылки) |

## Скрипты пересборки

`Скрипты/02_scha_rsa_group3/`:

- `build_presentation_pptx.py` — сборка PPTX
- `export_presentation_pdf.py` — PDF из HTML (Playwright / Edge)
- `check_pptx_render.py` — визуальная проверка слайдов PPTX

## Связанная доработка

Фоновые задания: [../01_background_jobs/index.md](../01_background_jobs/index.md)
