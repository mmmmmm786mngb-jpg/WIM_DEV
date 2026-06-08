# Query console - report 0420431 tabular sections

Document: `Документ.РО_XBRL7_1_0420431_СведенияОДеятельностиПоУправлениюЦБ_7119У`

Filled by external processor `внЗаполнениеРеглОтчетаПоДоговорамДУ_0420431_71`.

## Usage

1. Open query console in WIM_DU.
2. Run `00_find_document.txt`, copy `Документ` ref into parameter `&Документ`.
3. Run `00_row_counts_all_sections.txt` for quick row count check.
4. Run any `01_...` - `10_...` file to export one tabular section.
5. Export result to Excel/CSV from query console.

## Notes

- Queries do **not** select `НомерСтроки` / line number.
- Sort order is by **all business fields** of the tabular section (stable for diff).
- One combined data query for all sections is not practical (different column sets).
- `00_row_counts_all_sections.txt` is the single combined query for overview.

## Files

| File | Tabular section |
|------|-----------------|
| `01_razdel1_podrazdel1_1.txt` | `Раздел1_Подраздел1_1` |
| `02_razdel1_podrazdel1_2.txt` | `Раздел1_Подраздел1_2` |
| `03_razdel1_podrazdel1_3.txt` | `Раздел1_Подраздел1_3` |
| `04_razdel2.txt` | `Раздел2` |
| `05_razdel3.txt` | `Раздел3` |
| `06_razdel4.txt` | `Раздел4` |
| `07_razdel5.txt` | `Раздел5` |
| `08_razdel6.txt` | `Раздел6` |
| `09_razdel7.txt` | `Раздел7` |
| `10_reestr_cb.txt` | `РеестрЦенныхБумаг` |
| `00_row_counts_all_sections.txt` | counts for all sections (incl. Раздел10) |
| `00_find_document.txt` | find document ref |
