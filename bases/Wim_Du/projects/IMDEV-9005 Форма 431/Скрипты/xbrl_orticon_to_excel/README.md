# XBRL Orticon -> Excel

Конвертер instance XBRL ОРТИКОН (НСО ПУРЦБ) в multi-sheet `.xlsx`.

## Требования

- Python 3.10+
- `pip install openpyxl`

## Запуск

```text
python convert_xbrl_orticon_to_excel.py "C:\path\to\file.xbrl" -o "C:\path\to\out.xlsx"
```

Также поддерживается `.zip` с одним `.xbrl` внутри.

## Обработка 1С

`внВыгрузкаXBRLОртиконВXLSX` вызывает этот скрипт. Нужны:

- Python на машине, где выполняется код сервера/клиента (запуск приложения);
- `БезопасныйРежим = Ложь` при регистрации обработки.

## Эталон

Сверка: `ОРТИКОН/0420431_409_январь_2026_конвертер.xlsx`
