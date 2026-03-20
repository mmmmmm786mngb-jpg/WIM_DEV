# Report Ext11111: error "ИдентификаторОбъектаМетаданных" / ИОМ

## Symptom

When opening the report `Отчет.Ext11111_ОстаткиДоговорДуПоСчету`, BSP raises an error: no row in catalog `ИдентификаторыОбъектовМетаданных` for this metadata object.

## Cause

BSP (variants, report panel, `ОбщегоНазначения.ИдентификаторОбъектаМетаданных`) expects the auxiliary catalog to be synchronized with the current metadata tree. New objects from a **configuration extension** appear in metadata but the catalog is filled only after auxiliary data update.

## Fix (pick one)

1. **Command line (recommended once after installing the extension)**  
   Start 1C:Enterprise with parameter:
   `/C "ЗапуститьОбновлениеИнформационнойБазы"`  
   Example from repo (PowerShell):
   `db-run.ps1 -InfoBaseServer "localhost" -InfoBaseRef "WIM_DU" -CParam "ЗапуститьОбновлениеИнформационнойБазы"`

2. **In the application**  
   Use the vendor processing **"Инструменты разработчика: Обновление вспомогательных данных"** (or equivalent) if it is included in your delivery.

3. **Catalog list form**  
   Open `Справочник.ИдентификаторыОбъектовМетаданных` (list form) — there is usually an action to **refresh catalog data** (`ОбновитьДанныеСправочника` in Wim_Du).

4. **Configuration version**  
   Raising the **main** configuration version can trigger full IB update handlers on next start; for extensions alone this is less reliable than options 1–3.

## Error: identifier found but maps to another object (e.g. "Событие обмена")

The catalog row for the report name points at the wrong metadata (BSP then compares full name vs stored object and raises an error). Typical after a bad partial sync or duplicate internal ids.

**Fix:**

1. In the extension sources, assign **new UUID** to the report root (`Report uuid="..."` in `Reports/...xml`) and new **TypeId/ValueId** pairs inside `InternalInfo` / `GeneratedType` for `ReportObject` and `ReportManager`.
2. Reload the extension into the database and run `/C "ЗапуститьОбновлениеИнформационнойБазы"` again.
3. If the error persists, in **1С:Предприятие** open `Идентификаторы объектов метаданных`, find elements with **ПолноеИмя** `Отчет.Ext11111_ОстаткиДоговорДуПоСчету` or inconsistent data, remove duplicates / run **Обновить данные справочника** from the list form (Wim_Du).

If the error says the identifier **matches another metadata object** (e.g. `Событие обмена`), the catalog row for the old report name may be corrupted. The extension was renamed to `Отчет.Ext11111_ОстаткиДоговорДуПоСчету` (version **1.0.0.6**) so a fresh catalog binding is created after reload and `/C "ЗапуститьОбновлениеИнформационнойБазы"`.

## After update

Open the report again. The identifier for `Отчет.Ext11111_ОстаткиДоговорДуПоСчету` should exist in `ИдентификаторыОбъектовМетаданных` and match the report metadata.

## index

See [index.md](index.md).
