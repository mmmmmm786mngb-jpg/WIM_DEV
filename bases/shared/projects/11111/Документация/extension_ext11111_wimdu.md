# Extension Ext11111_WimDu (Wim_Du)

## Purpose

Configuration extension for Wim_Du with one SKD report: balances of accounting register **Khozraschetny** (`РегистрБухгалтерии.Хозрасчетный`) split by **ДоговорДУ** (and **Валюта**), filtered by user-selected **account** from chart **Хозрасчетный**.

## Reports

- `Ext11111_ОстаткиДоговорДуПоСчету` — синоним в интерфейсе: «Остатки по договору ДУ по счету (дополнительный отчет)». Имя метаданных выбрано без суффикса `ДУДоп`, чтобы избежать конфликтов в справочнике **Идентификаторы объектов метаданных** после смены состава расширения.

### Logic

- Query uses virtual table: `РегистрБухгалтерии.Хозрасчетный.Остатки(&ДатаОкончания, ...)` where `ДатаОкончания` is tied to SKD parameter **Период** (StandardPeriod, end of period).
- User parameters **Период** and **Счет** use QuickAccess on the report form.

## Parameters

| Parameter (Russian UI) | Role in query |
|------------------------|---------------|
| Период                 | Standard period; balance date = end of period (`ДатаОкончания`) |
| Счет                   | Account filter (hierarchy) |

## Role

`Ext11111_ОсновнаяРоль` grants **Use** and **View** on the report. Data access follows base configuration RLS and register rights.

## Source layout

- Extension root: `bases/shared/projects/11111/Расширения/Ext11111_WimDu`
- SKD JSON source (optional edits): `_skd_ostatki.json` — regenerate `Template.xml` via `skd-compile` (path: `Reports/Ext11111_ОстаткиДоговорДуПоСчету/Templates/ОсновнаяСхемаКомпоновкиДанных/Ext/Template.xml`).

## Troubleshooting

If opening the report fails with missing identifier in `ИдентификаторыОбъектовМетаданных`, run auxiliary data update — see [troubleshooting_metadata_identifiers.md](troubleshooting_metadata_identifiers.md).

## index

See `index.md` in this folder.
