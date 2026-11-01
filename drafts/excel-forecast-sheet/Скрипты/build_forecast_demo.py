#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Демонстрационная книга: лист прогноза Excel по месячному спросу.

История вымышленная. Каркас листа (заголовки и диаграмма) создает
Workbook.CreateForecastSheet - тот же механизм, что лента
«Данные - Прогноз - Лист прогноза». Горизонт на 12 месяцев заполняется
формулами FORECAST.ETS и FORECAST.ETS.CONFINT: именно их записывает
эта команда, когда в окне задана дата окончания.
"""

import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pythoncom
import win32com.client


OUT_PATH = Path(__file__).resolve().parents[1] / "forecast_sheet_demo.xlsx"
EXCEL_EPOCH = datetime(1899, 12, 30)
HISTORY_END = datetime(2026, 10, 1)
FORECAST_MONTHS = 12

XL_SRC_RANGE = 1
XL_YES = 1
XL_CONTINUOUS = 1
XL_OPENXML_WORKBOOK = 51
XL_NOT_PLOTTED = 1
XL_CATEGORY = 1
XL_VALUE = 2
XL_LEGEND_BOTTOM = -4107
XL_CENTER = -4108

COLOR_TITLE = 0x794E1F
COLOR_SECTION = 0xF0E3D6
COLOR_NOTE = 0xCCF2FF
COLOR_HEADER = 0x794E1F
COLOR_WHITE = 0xFFFFFF
COLOR_ZEBRA = 0xF7F4EE
COLOR_INPUT = 0xE8F0FA
COLOR_FUTURE = 0xE0F3FF


def to_serial(moment):
    """Целая дата Excel без времени: COM иначе сдвигает полночь на часовой пояс."""
    return (moment - EXCEL_EPOCH).days


def add_months(moment, count):
    month_index = moment.month - 1 + count
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    return datetime(year, month, 1)


def build_history():
    """Помесячный спрос, январь 2023 - октябрь 2026: тренд и годовая сезонность."""
    seasonal = {
        1: 0.82,
        2: 0.88,
        3: 0.97,
        4: 1.05,
        5: 1.02,
        6: 0.96,
        7: 0.90,
        8: 0.94,
        9: 1.08,
        10: 1.15,
        11: 1.32,
        12: 1.48,
    }
    rows = []
    year, month, step = 2023, 1, 0
    while (year, month) <= (HISTORY_END.year, HISTORY_END.month):
        step += 1
        level = 4200 + 55 * step
        wobble = 40 * math.sin(step / 3.0)
        value = int(round(level * seasonal[month] + wobble))
        rows.append((datetime(year, month, 1), value))
        month += 1
        if month == 13:
            month = 1
            year += 1
    if len(rows) != 46 or rows[0][0] != datetime(2023, 1, 1) or rows[-1][0] != HISTORY_END:
        raise RuntimeError("unexpected history bounds")
    if any(value <= 0 for _, value in rows):
        raise RuntimeError("demand must stay positive")
    return rows


def sheet_names(wb):
    return [wb.Worksheets(index).Name for index in range(1, wb.Worksheets.Count + 1)]


def write_history(ws, rows):
    ws.Name = "История спроса"
    ws.Cells(1, 1).Value = "Дата"
    ws.Cells(1, 2).Value = "Объем спроса, шт"
    for index, (moment, value) in enumerate(rows, start=2):
        ws.Cells(index, 1).Value = to_serial(moment)
        ws.Cells(index, 2).Value = value

    last_row = 1 + len(rows)
    body = ws.Range(ws.Cells(2, 1), ws.Cells(last_row, 2))
    body.Font.Name = "Arial"
    body.Font.Size = 11
    ws.Range(ws.Cells(2, 1), ws.Cells(last_row, 1)).NumberFormat = "DD.MM.YYYY"
    ws.Range(ws.Cells(2, 2), ws.Cells(last_row, 2)).NumberFormat = "#,##0"

    table = ws.ListObjects.Add(XL_SRC_RANGE, ws.Range(ws.Cells(1, 1), ws.Cells(last_row, 2)), None, XL_YES)
    table.Name = "DemandHistory"
    table.TableStyle = "TableStyleMedium2"

    note_row = last_row + 2
    note = ws.Range(ws.Cells(note_row, 1), ws.Cells(note_row, 2))
    note.Merge()
    ws.Cells(note_row, 1).Value = (
        "Примечание: цифры вымышленные. В ряде есть ежемесячный рост и годовая сезонность "
        "(спад в январе-феврале, пик в ноябре-декабре). Пропусков и повторных дат нет, "
        "шаг - первое число месяца. Лист прогноза ссылается на эту таблицу: "
        "если изменить объем, прогноз пересчитается."
    )
    ws.Cells(note_row, 1).Font.Name = "Arial"
    ws.Cells(note_row, 1).Font.Size = 10
    ws.Cells(note_row, 1).WrapText = True
    ws.Cells(note_row, 1).Interior.Color = COLOR_NOTE
    ws.Rows(note_row).RowHeight = 58

    hints = (
        "Как построить такой лист кнопкой",
        "1. Выделите любую ячейку таблицы.",
        "2. Лента: Данные - Прогноз - Лист прогноза.",
        "3. Окончание прогноза: 01.10.2027.",
        "4. Доверительный интервал: 95%. Диаграмма: линия.",
        "5. Нажмите Создать. Образец уже есть на листе «Лист прогноза».",
    )
    for offset, text in enumerate(hints):
        cell = ws.Cells(1 + offset, 4)
        cell.Value = text
        cell.Font.Name = "Arial"
        cell.Font.Size = 10
        cell.WrapText = True
        if offset == 0:
            cell.Font.Bold = True
            cell.Font.Color = COLOR_WHITE
            cell.Interior.Color = COLOR_HEADER
        else:
            cell.Interior.Color = COLOR_INPUT

    ws.Columns(1).ColumnWidth = 16
    ws.Columns(2).ColumnWidth = 22
    ws.Columns(3).ColumnWidth = 3
    ws.Columns(4).ColumnWidth = 68
    ws.Range("A2").Select()
    ws.Application.ActiveWindow.FreezePanes = True
    ws.PageSetup.Orientation = 2
    ws.PageSetup.FitToPagesWide = 1
    ws.PageSetup.FitToPagesTall = 1
    ws.Tab.Color = 0xC0C0C0
    return last_row


def create_forecast_sheet(wb, ws, last_row):
    before = sheet_names(wb)
    # Только числа, без заголовка: временная шкала должна быть датой.
    wb.CreateForecastSheet(
        ws.Range(ws.Cells(2, 1), ws.Cells(last_row, 1)),
        ws.Range(ws.Cells(2, 2), ws.Cells(last_row, 2)),
    )
    created = [name for name in sheet_names(wb) if name not in before]
    if len(created) != 1:
        raise RuntimeError("CreateForecastSheet sheets: %s" % created)
    forecast = wb.Worksheets(created[0])
    forecast.Name = "Лист прогноза"
    return forecast


def extend_forecast(forecast, last_hist):
    """12 месяцев вперед формулами, которые пишет команда «Лист прогноза»."""
    history_dates = "$A$2:$A$%d" % last_hist
    history_values = "$B$2:$B$%d" % last_hist

    for row_index in range(2, last_hist + 1):
        source_row = row_index
        forecast.Cells(row_index, 1).Formula = "='История спроса'!A%d" % source_row
        forecast.Cells(row_index, 2).Formula = "='История спроса'!B%d" % source_row

    # Последняя точка факта соединяет линии факта и прогноза, как в окне команды.
    forecast.Cells(last_hist, 3).Formula = "=B%d" % last_hist
    forecast.Cells(last_hist, 4).Formula = "=B%d" % last_hist
    forecast.Cells(last_hist, 5).Formula = "=B%d" % last_hist

    for offset in range(1, FORECAST_MONTHS + 1):
        row_index = last_hist + offset
        moment = add_months(HISTORY_END, offset)
        forecast.Cells(row_index, 1).Value = to_serial(moment)
        target = "A%d" % row_index
        point = "C%d" % row_index
        forecast.Cells(row_index, 3).Formula = "=FORECAST.ETS(%s,%s,%s,1,1)" % (
            target,
            history_values,
            history_dates,
        )
        confint = "FORECAST.ETS.CONFINT(%s,%s,%s,0.95,1,1)" % (
            target,
            history_values,
            history_dates,
        )
        forecast.Cells(row_index, 4).Formula = "=%s-%s" % (point, confint)
        forecast.Cells(row_index, 5).Formula = "=%s+%s" % (point, confint)
        forecast.Range(forecast.Cells(row_index, 1), forecast.Cells(row_index, 5)).Interior.Color = COLOR_FUTURE

    last_row = last_hist + FORECAST_MONTHS
    forecast.Range(forecast.Cells(2, 1), forecast.Cells(last_row, 1)).NumberFormat = "DD.MM.YYYY"
    forecast.Range(forecast.Cells(2, 2), forecast.Cells(last_row, 5)).NumberFormat = "#,##0"
    return last_row


def write_stats(forecast, last_hist, last_row):
    if forecast.ListObjects.Count:
        forecast.ListObjects(1).Resize(forecast.Range("A1:E%d" % last_row))
    origin = last_row + 2
    forecast.Cells(origin, 1).Value = "Статистика модели ETS"
    forecast.Range(forecast.Cells(origin, 1), forecast.Cells(origin, 2)).Merge()
    title = forecast.Cells(origin, 1)
    title.Font.Name = "Arial"
    title.Font.Bold = True
    title.Font.Size = 12
    title.Font.Color = COLOR_WHITE
    forecast.Range(forecast.Cells(origin, 1), forecast.Cells(origin, 2)).Interior.Color = COLOR_HEADER

    values = "$B$2:$B$%d" % last_hist
    timeline = "$A$2:$A$%d" % last_hist
    rows = (
        ("Длина сезона, месяцев", "=FORECAST.ETS.SEASONALITY(%s,%s)" % (values, timeline), "0"),
        ("Альфа (уровень)", "=FORECAST.ETS.STAT(%s,%s,1,1,1)" % (values, timeline), "0,000"),
        ("Бета (тренд)", "=FORECAST.ETS.STAT(%s,%s,2,1,1)" % (values, timeline), "0,000"),
        ("Гамма (сезонность)", "=FORECAST.ETS.STAT(%s,%s,3,1,1)" % (values, timeline), "0,000"),
        ("MASE", "=FORECAST.ETS.STAT(%s,%s,4,1,1)" % (values, timeline), "0,000"),
        ("SMAPE", "=FORECAST.ETS.STAT(%s,%s,5,1,1)" % (values, timeline), "0,000"),
        ("MAE", "=FORECAST.ETS.STAT(%s,%s,6,1,1)" % (values, timeline), "0,00"),
        ("RMSE", "=FORECAST.ETS.STAT(%s,%s,7,1,1)" % (values, timeline), "0,00"),
    )
    header_row = origin + 1
    forecast.Cells(header_row, 1).Value = "Показатель"
    forecast.Cells(header_row, 2).Value = "Значение"
    forecast.Range(forecast.Cells(header_row, 1), forecast.Cells(header_row, 2)).Font.Bold = True
    forecast.Range(forecast.Cells(header_row, 1), forecast.Cells(header_row, 2)).Font.Name = "Arial"
    forecast.Range(forecast.Cells(header_row, 1), forecast.Cells(header_row, 2)).Interior.Color = COLOR_SECTION

    forecast.Range("A1").Select()
    for offset, (label, formula, number_format) in enumerate(rows, start=2):
        row_index = origin + offset
        forecast.Cells(row_index, 1).Value = label
        value_cell = forecast.Cells(row_index, 2)
        try:
            value_cell.NumberFormatLocal = number_format
        except Exception as exc:
            merge = value_cell.MergeArea.Address if value_cell.MergeCells else "none"
            tables = forecast.ListObjects.Count
            raise RuntimeError(
                "format failed row=%s merge=%s tables=%s err=%s" % (row_index, merge, tables, exc)
            ) from exc
        value_cell.Formula = formula
        forecast.Range(forecast.Cells(row_index, 1), forecast.Cells(row_index, 2)).Font.Name = "Arial"
        forecast.Range(forecast.Cells(row_index, 1), forecast.Cells(row_index, 2)).Font.Size = 10

    block = forecast.Range(forecast.Cells(header_row, 1), forecast.Cells(origin + 1 + len(rows), 2))
    block.Borders.LineStyle = XL_CONTINUOUS
    block.Borders.Weight = 2

    note_row = origin + 2 + len(rows) + 1
    forecast.Range(forecast.Cells(note_row, 1), forecast.Cells(note_row, 5)).Merge()
    forecast.Cells(note_row, 1).Value = (
        "Желтые строки - горизонт прогноза, ноябрь 2026 - октябрь 2027. "
        "«Привязка низкой вероятности» и «Привязка высокой вероятности» - "
        "нижняя и верхняя границы доверительного интервала 95%. "
        "Это подписи самой команды «Лист прогноза». "
        "Колонки факта ссылаются на лист «История спроса»."
    )
    forecast.Cells(note_row, 1).Font.Name = "Arial"
    forecast.Cells(note_row, 1).Font.Size = 10
    forecast.Cells(note_row, 1).WrapText = True
    forecast.Cells(note_row, 1).Interior.Color = COLOR_NOTE
    forecast.Rows(note_row).RowHeight = 48
    return origin + 2


def polish_forecast_sheet(forecast, last_row):
    used = forecast.UsedRange
    used.Font.Name = "Arial"
    used.Font.Size = 10

    header = forecast.Range("A1:E1")
    header.Font.Name = "Arial"
    header.Font.Bold = True
    header.Font.Color = COLOR_WHITE
    header.Font.Size = 10
    header.Interior.Color = COLOR_HEADER
    header.WrapText = True
    header.HorizontalAlignment = XL_CENTER
    header.VerticalAlignment = XL_CENTER
    forecast.Rows(1).RowHeight = 36

    forecast.Columns(1).ColumnWidth = 18
    forecast.Columns(2).ColumnWidth = 22
    forecast.Columns(3).ColumnWidth = 16
    forecast.Columns(4).ColumnWidth = 32
    forecast.Columns(5).ColumnWidth = 34

    charts = forecast.ChartObjects()
    if charts.Count != 1:
        raise RuntimeError("expected one forecast chart, got %s" % charts.Count)
    chart_object = charts.Item(1)
    chart_object.Left = forecast.Cells(1, 7).Left
    chart_object.Top = forecast.Cells(2, 7).Top
    chart_object.Width = 680
    chart_object.Height = 340

    chart = chart_object.Chart
    if chart.SeriesCollection().Count != 4:
        raise RuntimeError("expected 4 chart series")
    dates = forecast.Range(forecast.Cells(2, 1), forecast.Cells(last_row, 1))
    for index, column in enumerate((2, 3, 4, 5), start=1):
        series = chart.SeriesCollection(index)
        series.XValues = dates
        series.Values = forecast.Range(forecast.Cells(2, column), forecast.Cells(last_row, column))
    chart.DisplayBlanksAs = XL_NOT_PLOTTED
    chart.HasTitle = True
    chart.ChartTitle.Text = "Прогноз спроса, шт"
    chart.ChartTitle.Font.Name = "Arial"
    chart.ChartTitle.Font.Size = 14
    chart.HasLegend = True
    chart.Legend.Position = XL_LEGEND_BOTTOM
    chart.Legend.Font.Name = "Arial"
    chart.Legend.Font.Size = 9
    chart.Axes(XL_CATEGORY).TickLabels.NumberFormat = "MMM YYYY"
    chart.Axes(XL_CATEGORY).TickLabels.Font.Name = "Arial"
    chart.Axes(XL_CATEGORY).TickLabels.Font.Size = 9
    chart.Axes(XL_VALUE).TickLabels.NumberFormat = "#,##0"
    chart.Axes(XL_VALUE).TickLabels.Font.Name = "Arial"
    chart.Axes(XL_VALUE).HasTitle = True
    chart.Axes(XL_VALUE).AxisTitle.Text = "шт"
    chart.Axes(XL_VALUE).AxisTitle.Font.Name = "Arial"

    forecast.Range("A2").Select()
    forecast.Application.ActiveWindow.FreezePanes = True
    forecast.PageSetup.Orientation = 2
    forecast.PageSetup.FitToPagesWide = 1
    forecast.PageSetup.FitToPagesTall = 1
    forecast.PageSetup.LeftMargin = 28
    forecast.PageSetup.RightMargin = 28
    forecast.Tab.Color = 0x50B050


def write_guide(wb):
    guide = wb.Worksheets.Add(Before=wb.Worksheets(1))
    guide.Name = "Как пользоваться"

    guide.Range("A1:B1").Merge()
    guide.Cells(1, 1).Value = "Лист прогноза Excel: пример на месячном спросе"
    guide.Cells(1, 1).Font.Name = "Arial"
    guide.Cells(1, 1).Font.Size = 18
    guide.Cells(1, 1).Font.Bold = True
    guide.Cells(1, 1).Font.Color = COLOR_WHITE
    guide.Range("A1:B1").Interior.Color = COLOR_TITLE
    guide.Rows(1).RowHeight = 32

    sections = (
        (3, "Что уже сделано"),
        (10, "Параметры расчета"),
        (20, "Что смотреть на листе прогноза"),
        (27, "Как построить такой лист самостоятельно"),
        (34, "Ограничение"),
    )
    for row_index, title in sections:
        guide.Range(guide.Cells(row_index, 1), guide.Cells(row_index, 2)).Merge()
        guide.Cells(row_index, 1).Value = title
        guide.Cells(row_index, 1).Font.Name = "Arial"
        guide.Cells(row_index, 1).Font.Bold = True
        guide.Cells(row_index, 1).Font.Size = 13
        guide.Cells(row_index, 1).Font.Color = COLOR_TITLE
        guide.Range(guide.Cells(row_index, 1), guide.Cells(row_index, 2)).Interior.Color = COLOR_SECTION
        guide.Rows(row_index).RowHeight = 22

    paragraphs = {
        4: "Лист «Лист прогноза» - результат встроенной команды Excel «Лист прогноза» (лента «Данные», группа «Прогноз»). Это не надстройка.",
        5: "Расчет идет алгоритмом экспоненциального сглаживания ETS, версия AAA. Сезонность Excel определяет сам. Доверительный интервал - 95%.",
        6: "Факт на листе прогноза ссылается на таблицу «История спроса». Измените объем в истории - прогноз и границы пересчитаются.",
        7: "Желтым отмечен горизонт: ноябрь 2026 - октябрь 2027. В этих строках формулы ПРЕДСКАЗ.ETS и ПРЕДСКАЗ.ETS.ДОВИНТЕРВАЛ - те же, что записывает команда.",
        21: "Синяя линия - факт до октября 2026. Оранжевая линия прогноза начинается от последнего факта и идет до октября 2027.",
        22: "Серые линии - нижняя и верхняя границы 95%. Для запаса ориентир - верхняя граница, не одна точка прогноза.",
        23: "Под таблицей - статистика ETS: длина сезона и ошибки на истории (MASE, SMAPE, MAE, RMSE). Длина сезона в этом примере - 12 месяцев.",
        28: "1. Откройте «История спроса» и выделите любую ячейку таблицы.",
        29: "2. Данные - Прогноз - Лист прогноза.",
        30: "3. Окончание: 01.10.2027, интервал 95%, линейная диаграмма. При желании включите статистику прогноза.",
        31: "4. Нажмите «Создать». Excel добавит новый лист с таблицей и графиком.",
        35: "Кнопка «Лист прогноза» есть в настольном Excel для Windows, начиная с Excel 2016 (2019, 2021 и Microsoft 365).",
        36: "В Excel для Mac и в Excel в браузере этой кнопки нет. Функции ПРЕДСКАЗ.ETS есть в настольном Excel для Mac и нет в браузерной версии.",
        37: "Данные примера вымышленные. На реальном спросе перед прогнозом уберите пропуски шага, разовые всплески акций и нули там, где товар еще не продавался.",
    }
    for row_index, text in paragraphs.items():
        guide.Range(guide.Cells(row_index, 1), guide.Cells(row_index, 2)).Merge()
        cell = guide.Cells(row_index, 1)
        cell.Value = text
        cell.Font.Name = "Arial"
        cell.Font.Size = 11
        cell.WrapText = True
        guide.Rows(row_index).RowHeight = 34
    guide.Rows(6).RowHeight = 34
    guide.Rows(22).RowHeight = 34
    guide.Rows(37).RowHeight = 48

    guide.Cells(11, 1).Value = "Параметр"
    guide.Cells(11, 2).Value = "Значение"
    values = (
        ("Факт", "01.01.2023 - 01.10.2026, 46 месяцев"),
        ("Шаг ряда", "1 месяц, первое число месяца"),
        ("Прогноз", "01.11.2026 - 01.10.2027"),
        ("Доверительный интервал", "95%"),
        ("Сезонность", "автоматически, в примере 12 месяцев"),
        ("Пропуски", "интерполяция соседних точек"),
        ("Повторы дат", "усреднение (в примере повторов нет)"),
        ("Диаграмма", "линия"),
    )
    for offset, pair in enumerate(values):
        guide.Cells(12 + offset, 1).Value = pair[0]
        guide.Cells(12 + offset, 2).Value = pair[1]

    table = guide.Range("A11:B19")
    table.Font.Name = "Arial"
    table.Font.Size = 11
    table.Borders.LineStyle = XL_CONTINUOUS
    table.Borders.Weight = 2
    header_row = guide.Range("A11:B11")
    header_row.Font.Bold = True
    header_row.Font.Color = COLOR_WHITE
    header_row.Interior.Color = COLOR_HEADER
    for row_index in range(12, 20):
        guide.Rows(row_index).RowHeight = 20
        if row_index % 2 == 0:
            guide.Range(guide.Cells(row_index, 1), guide.Cells(row_index, 2)).Interior.Color = COLOR_ZEBRA

    guide.Columns(1).ColumnWidth = 42
    guide.Columns(2).ColumnWidth = 78
    guide.Range("A1").Select()
    guide.PageSetup.Orientation = 1
    guide.PageSetup.FitToPagesWide = 1
    guide.PageSetup.FitToPagesTall = 1
    guide.Tab.Color = COLOR_TITLE


def _as_date(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 30000:
        return EXCEL_EPOCH + timedelta(days=int(round(value)))
    return None


def verify(forecast, log_path):
    lines = []
    lines.append("used=%s" % forecast.UsedRange.Address)
    lines.append("charts=%s" % forecast.ChartObjects().Count)
    by_date = {}
    row_index = 2
    while True:
        moment = _as_date(forecast.Cells(row_index, 1).Value)
        if moment is None:
            break
        point = forecast.Cells(row_index, 3).Value
        lower = forecast.Cells(row_index, 4).Value
        upper = forecast.Cells(row_index, 5).Value
        formula = forecast.Cells(row_index, 3).Formula
        if moment >= datetime(2026, 11, 1):
            if not all(isinstance(item, (int, float)) for item in (point, lower, upper)):
                raise RuntimeError("non-numeric forecast at %s" % moment.strftime("%Y-%m-%d"))
            if not (lower <= point <= upper):
                raise RuntimeError("bounds broken at %s" % moment.strftime("%Y-%m-%d"))
            if lower <= 0:
                raise RuntimeError("lower bound is not positive at %s" % moment.strftime("%Y-%m-%d"))
            if not (isinstance(formula, str) and formula.startswith("=FORECAST.ETS(")):
                raise RuntimeError("missing ETS formula at row %s" % row_index)
            by_date[moment] = point
            lines.append(
                "%s point=%.1f low=%.1f high=%.1f" % (moment.strftime("%Y-%m-%d"), point, lower, upper)
            )
        row_index += 1
        if row_index > 200:
            raise RuntimeError("forecast date column did not end")

    if len(by_date) != FORECAST_MONTHS:
        raise RuntimeError("expected %s forecast months, got %s" % (FORECAST_MONTHS, len(by_date)))

    december = by_date[datetime(2026, 12, 1)]
    january = by_date[datetime(2027, 1, 1)]
    july = by_date[datetime(2027, 7, 1)]
    if not (december > january and december > july):
        raise RuntimeError("seasonal peak was not reproduced: dec=%.1f jan=%.1f jul=%.1f" % (december, january, july))

    season_cell = None
    for scan in range(1, 90):
        if forecast.Cells(scan, 1).Value == "Длина сезона, месяцев":
            season_cell = forecast.Cells(scan, 2).Value
            break
    if season_cell != 12:
        raise RuntimeError("season length is %s, expected 12" % season_cell)
    lines.append("season=%s" % season_cell)
    log_path.write_text("\n".join(lines), encoding="utf-8")
    return len(by_date)


def main():
    pythoncom.CoInitialize()
    excel = None
    wb = None
    try:
        rows = build_history()
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        if OUT_PATH.exists():
            OUT_PATH.unlink()

        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        excel.AskToUpdateLinks = False
        excel.ScreenUpdating = False

        wb = excel.Workbooks.Add()
        while wb.Worksheets.Count > 1:
            wb.Worksheets(wb.Worksheets.Count).Delete()

        history = wb.Worksheets(1)
        last_hist_source = write_history(history, rows)
        forecast = create_forecast_sheet(wb, history, last_hist_source)
        # Команда копирует 46 точек под заголовок: последняя строка факта = 47.
        last_hist = 1 + len(rows)
        if forecast.Cells(last_hist, 2).Value in (None, ""):
            raise RuntimeError("forecast sheet did not receive history")
        last_row = extend_forecast(forecast, last_hist)
        write_stats(forecast, last_hist, last_row)
        excel.CalculateFull()
        polish_forecast_sheet(forecast, last_row)
        write_guide(wb)

        forecast.Move(Before=wb.Worksheets(1))
        history.Move(After=forecast)
        forecast.Activate()
        excel.ActiveWindow.Zoom = 100

        future_rows = verify(forecast, OUT_PATH.with_suffix(".verify.txt"))
        wb.SaveAs(str(OUT_PATH), FileFormat=XL_OPENXML_WORKBOOK)
        print("OK file=%s forecast_months=%s" % (OUT_PATH, future_rows))
        return 0
    finally:
        if wb is not None:
            wb.Close(SaveChanges=False)
        if excel is not None:
            excel.Quit()
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    sys.exit(main())
