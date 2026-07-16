# Comparison: etalon vs XBRL_Orticon (1C)

- Etalon: `0420431_409_январь_2026_конвертер.xlsx` (1749006 bytes)
- Ours: `XBRL_Orticon.xlsx` (1888563 bytes)
- Sheets etalon: **43**, ours: **20**
- Exact name matches: **19**
- Only etalon: **24**, only ours: **1**

## TOC / generator
- Etalon TOC rows: 54
- Ours Generator: внВыгрузкаXBRLОртиконВXLSX v1.2.2 (1C only)

## Sheets only in etalon (no exact name in ours)
- `0420431 Раздел 1 Сведения об _1`: rows=13, cols=77, data~4 (from r10)
- `0420431 Раздел 2 Сведения о пор`: rows=10, cols=13, data~1 (from r10)
- `0420431 Раздел 3 Сведения о п_1`: rows=10, cols=11, data~1 (from r10)
- `0420431 Раздел 3 Сведения о п_3`: rows=10, cols=11, data~1 (from r10)
- `0420431 Раздел 3 Сведения о пор`: rows=10, cols=11, data~1 (from r10)
- `0420431 Раздел 4 Сведения о пор`: rows=10, cols=12, data~1 (from r10)
- `0420431 Раздел 5 Сведения о пор`: rows=10, cols=11, data~1 (from r10)
- `0420431 Раздел 6 Сведения о пор`: rows=9, cols=20, data~0 (from r11)
- `0420431 Раздел 7 Сведения о п_1`: rows=10, cols=13, data~1 (from r10)
- `0420431 Раздел 7 Сведения о п_2`: rows=9, cols=17, data~0 (from r11)
- `0420431 Раздел 7 Сведения о п_3`: rows=9, cols=11, data~0 (from r11)
- `0420431 Раздел 7 Сведения о пор`: rows=9, cols=15, data~0 (from r11)
- `0420431 Раздел 8 Сведения о п_1`: rows=9, cols=21, data~0 (from r11)
- `0420431 Раздел 8 Сведения о пор`: rows=9, cols=21, data~0 (from r11)
- `0420431 Раздел 9 Сведения о п_1`: rows=10, cols=11, data~1 (from r10)
- `0420431 Раздел 9 Сведения о пор`: rows=10, cols=11, data~1 (from r10)
- `0420458 Сведения о маржинальн_1`: rows=10, cols=15, data~1 (from r10)
- `0420458 Сведения о маржинальн_2`: rows=11, cols=17, data~2 (from r10)
- `0420458 Сведения о маржинальн_3`: rows=9, cols=10, data~0 (from r11)
- `0420458 Сведения о маржинальн_4`: rows=11, cols=21, data~2 (from r10)
- `0420458 Сведения о маржинальных`: rows=13, cols=36, data~3 (from r11)
- `0420459 Раздел 1 Сведения о ц_1`: rows=8, cols=18, data~0 (from r11)
- `0420459 Раздел 2 Сведения о циф`: rows=8, cols=11, data~0 (from r11)
- `_dropDownSheet` — service sheet of converter UI, ignore

## Sheets only in ours
- `0420431 Раздел 1 Договоры ДУ`: rows=1153, cols=13, data=1152

## Volume compare on exact name matches
| Status | Sheet | Etalon data~ | Ours data | Delta | E cols | O cols |
|---|---|---:|---:|---:|---:|---:|
| CLOSE | `0420409 Раздел 1 Сведения о бан` | 4209 | 4209 | +0 | 18 | 15 |
| CLOSE | `0420409 Раздел 2 Сведения о ден` | 5 | 5 | +0 | 13 | 12 |
| DIFF | `0420414 Раздел 1 Выданные займы` | 2 | 1 | -1 | 16 | 11 |
| CLOSE | `0420414 Раздел 2 Полученные зай` | 1 | 1 | +0 | 16 | 3 |
| OURS_MUCH_LESS | `0420431 Раздел 1 Сведения об _2` | 722 | 307 | -415 | 77 | 13 |
| OURS_MUCH_MORE | `0420431 Раздел 1 Сведения об _3` | 301 | 939 | +638 | 153 | 13 |
| CLOSE | `0420431 Раздел 1 Сведения об ос` | 53 | 53 | +0 | 7 | 8 |
| CLOSE | `0420431 Раздел 2 Сведения о п_1` | 1380 | 1379 | -1 | 13 | 16 |
| NEAR | `0420431 Раздел 3 Сведения о п_2` | 16 | 15 | -1 | 11 | 14 |
| CLOSE | `0420431 Раздел 4 Сведения о п_1` | 17037 | 17036 | -1 | 12 | 15 |
| NEAR | `0420431 Раздел 5 Сведения о п_1` | 8 | 7 | -1 | 11 | 14 |
| CLOSE | `0420431 Раздел 6 Сведения о п_1` | 2 | 2 | +0 | 20 | 19 |
| CLOSE | `0420431 Раздел 7 Сведения о п_4` | 1591 | 1590 | -1 | 13 | 16 |
| CLOSE | `0420431 Раздел 7 Сведения о п_5` | 595 | 595 | +0 | 17 | 19 |
| CLOSE | `0420459 Раздел 1 Сведения о цен` | 542 | 542 | +0 | 26 | 14 |
| OURS_MUCH_LESS | `TOC` | 49 | 23 | -26 | 3 | 3 |
| OURS_ONLY_DATA | `Информация о документах включен` | 0 | 1 | +1 | 5 | 5 |
| CLOSE | `Сопроводительная информация к о` | 4 | 4 | +0 | 7 | 7 |
| CLOSE | `Сопроводительная информация об` | 1 | 1 | +0 | 11 | 11 |

### Status counts: CLOSE=12, OURS_MUCH_LESS=2, NEAR=2, DIFF=1, OURS_MUCH_MORE=1, OURS_ONLY_DATA=1

## Interpretation of etalon-only sheets
Etalon often splits broker/DU (and margin forms) into separate sheets; ours currently keeps mainly DU / primary bucket sheets.

- `0420431 Раздел 1 Сведения об _1` data~4
- `0420431 Раздел 2 Сведения о пор` data~1
- `0420431 Раздел 3 Сведения о п_1` data~1
- `0420431 Раздел 3 Сведения о п_3` data~1
- `0420431 Раздел 3 Сведения о пор` data~1
- `0420431 Раздел 4 Сведения о пор` data~1
- `0420431 Раздел 5 Сведения о пор` data~1
- `0420431 Раздел 6 Сведения о пор` data~0
- `0420431 Раздел 7 Сведения о п_1` data~1
- `0420431 Раздел 7 Сведения о п_2` data~0
- `0420431 Раздел 7 Сведения о п_3` data~0
- `0420431 Раздел 7 Сведения о пор` data~0
- `0420431 Раздел 8 Сведения о п_1` data~0
- `0420431 Раздел 8 Сведения о пор` data~0
- `0420431 Раздел 9 Сведения о п_1` data~1
- `0420431 Раздел 9 Сведения о пор` data~1
- `0420458 Сведения о маржинальн_1` data~1
- `0420458 Сведения о маржинальн_2` data~2
- `0420458 Сведения о маржинальн_3` data~0
- `0420458 Сведения о маржинальн_4` data~2
- `0420458 Сведения о маржинальных` data~3
- `0420459 Раздел 1 Сведения о ц_1` data~0
- `0420459 Раздел 2 Сведения о циф` data~0

## Key sheets detail
### `0420409 Раздел 1 Сведения о бан`
- Etalon: max_row=4219, data_start=11, data~4209, cols=18
- Ours: max_row=4210, data=4209, cols=15
- Etalon header labels (sample): ['1', '2', '3', '4', '5', '6', '7', '8']
- Ours headers (concept names): ['Rek_kred_org_i_scheta', 'Nom_schet', 'INN_TIN', 'SokrNaim', 'OKSM_Kred_Org_Enumerator', 'Vid_scheta_v_kreditnoj_organizaczii_Enumerator', 'Dat_otkr_schet', 'Kod_valEnumerator', 'Vozm_isp_den_sred_naxod_na_schete_v_sobst_interesaxEnumerator', 'Dat_zakryt_schet']
- Row ratio ours/etalon: 1.000

### `0420431 Раздел 1 Сведения об ос`
- Etalon: max_row=62, data_start=10, data~53, cols=7
- Ours: max_row=54, data=53, cols=8
- Etalon header labels (sample): ['1', '2', '3', '4', '5', '6']
- Ours headers (concept names): ['Period', 'ID_strateg', 'Naim_strategii_Inf_ob_inv_strateg', 'TipStrategEnumerator', 'AktStoim', 'DoxInStr', 'KolichestvoKlientov', 'VremGor']
- Row ratio ours/etalon: 1.000

### `0420431 Раздел 4 Сведения о п_1`
- Etalon: max_row=17046, data_start=10, data~17037, cols=12
- Ours: max_row=17037, data=17036, cols=15
- Etalon header labels (sample): []
- Ours headers (concept names): ['Period', 'ID_strateg', 'ID_CzennojBumagi', 'Vid_Deyatelnosti', 'Uroven_riska', 'Tip_i_status_klienta', 'PriznakIIS', 'Tip_imushhestva', 'Kvalificzirovannost_investora', 'Kod_OKATO_KodOKSM']
- Row ratio ours/etalon: 1.000

### `0420431 Раздел 2 Сведения о п_1`
- Etalon: max_row=1389, data_start=10, data~1380, cols=13
- Ours: max_row=1380, data=1379, cols=16
- Etalon header labels (sample): []
- Ours headers (concept names): ['Period', 'IDBrokeraKO', 'ID_strateg', 'Vid_Deyatelnosti', 'Tip_i_status_klienta', 'PriznakIIS', 'Tip_imushhestva', 'Kvalificzirovannost_investora', 'Kod_Valyuty', 'Kod_OKATO_KodOKSM']
- Row ratio ours/etalon: 0.999

### `0420431 Раздел 7 Сведения о п_4`
- Etalon: max_row=1600, data_start=10, data~1591, cols=13
- Ours: max_row=1591, data=1590, cols=16
- Etalon header labels (sample): []
- Ours headers (concept names): ['Period', 'ID_strateg', 'ID_Kontragenta', 'Vid_Deyatelnosti', 'Uroven_riska', 'TrebOb', 'Tip_i_status_klienta', 'PriznakIIS', 'Kvalificzirovannost_investora', 'TipTrebOb']
- Row ratio ours/etalon: 0.999

### `0420431 Раздел 7 Сведения о п_5`
- Etalon: max_row=604, data_start=10, data~595, cols=17
- Ours: max_row=596, data=595, cols=19
- Etalon header labels (sample): ['Код по ОКАТО или код по ОКСМ', 'Уровень риска', 'Категория клиента', 'Признак ИИС', 'Инвестиционный профиль', 'Тип клиента', 'Статус клиента', 'Квалификация инвестора']
- Ours headers (concept names): ['Period', 'IDTrebObyaz', 'ID_strateg', 'ID_Kontragenta', 'Uroven_riska', 'TrebOb', 'Vid_Deyatelnosti', 'TipRepo', 'Tip_i_status_klienta', 'PriznakIIS']
- Row ratio ours/etalon: 1.000

### `0420459 Раздел 1 Сведения о цен`
- Etalon: max_row=552, data_start=11, data~542, cols=26
- Ours: max_row=543, data=542, cols=14
- Etalon header labels (sample): ['1', '2', '3', '4', '5', '6', '7', '8']
- Ours headers (concept names): ['Period', 'ID_CzennojBumagi', 'IDCzbvOsnDR', 'Kod_stranEnumerator', 'PolnNaim', 'INN_TIN', 'TipCZenBumVidFIEnumerator', 'ISIN', 'KodCFI', 'Kod_valEnumerator']
- Row ratio ours/etalon: 1.000

### `0420431 Раздел 1 Сведения об _3`
- Etalon: max_row=310, data_start=10, data~301, cols=153
- Ours: max_row=940, data=939, cols=13
- Etalon header labels (sample): ['Код по ОКАТО или код по ОКСМ', 'Тип клиента', 'Статус клиента', 'Квалификация инвестора']
- Ours headers (concept names): ['Period', 'Vid_Deyatelnosti', 'Tip_i_status_klienta', 'Tip_i_status_klienta2', 'RazmSch', 'Kvalificzirovannost_investora', 'Kod_OKATO_KodOKSM', 'KolichestvoKlientov', 'SovObPortfGr', 'SovObPortfGrIIS']
- Row ratio ours/etalon: 3.120

### `0420431 Раздел 1 Сведения об _2`
- Etalon: max_row=731, data_start=10, data~722, cols=77
- Ours: max_row=308, data=307, cols=13
- Etalon header labels (sample): ['Тип имущества - Денежные средства', 'Тип имущества - Ценные бумаги', 'Тип имущества - Прочее']
- Ours headers (concept names): ['Period', 'ID_strateg', 'Vid_Deyatelnosti', 'Tip_i_status_klienta', 'PriznakIIS', 'Tip_imushhestva', 'Kvalificzirovannost_investora', 'Kod_OKATO_KodOKSM', 'InvestProfile', 'Tip_i_status_klienta2']
- Row ratio ours/etalon: 0.425

## Extra ours sheet
- `0420431 Раздел 1 Договоры ДУ`: data=1152 — likely etalon folds this into another section1 sheet or pivot.

## Summary verdict
- Of 19 exact-name sheets: CLOSE/NEAR=14, MUCH_MORE=1, MUCH_LESS=2, DIFF=1
- Structural difference: etalon = multi-row RU headers + taxonomy table layout; ours = flat one-header row with XBRL concept/axis codes.
- Coverage: ours 20 sheets vs etalon 43 (etalon has broker/margin/extra splits).