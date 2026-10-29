const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType, AlignmentType,
  HeadingLevel, ImageRun, BorderStyle, LevelFormat, Footer, PageNumber,
} = require("docx");

const OUT = process.argv[2];
const CHART = path.join(__dirname, "chart.png");
const FONT = "Calibri";
const W = 9638; // A4 с полями 2 см
const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };

function p(text, opts = {}) {
  const runs = (Array.isArray(text) ? text : [text]).map((t) =>
    typeof t === "string" ? new TextRun({ text: t, font: FONT, size: 22 }) : new TextRun({ font: FONT, size: 22, ...t }));
  return new Paragraph({ children: runs, spacing: { after: 100, line: 276 }, ...opts });
}
function h(text, level) {
  return new Paragraph({ heading: level, children: [new TextRun({ text, font: FONT })], spacing: { before: 240, after: 120 } });
}
function bullet(text) {
  return p(text, { numbering: { reference: "bullets", level: 0 }, spacing: { after: 60, line: 276 } });
}
function cell(text, width, opts = {}) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA },
    shading: opts.head ? { fill: "E6EDF5", type: ShadingType.CLEAR, color: "auto" }
      : opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({
      alignment: opts.right ? AlignmentType.RIGHT : AlignmentType.LEFT,
      children: [new TextRun({ text, font: FONT, size: 20, bold: !!(opts.head || opts.bold) })],
    })],
  });
}
function table(widths, rows, rightCols = []) {
  return new Table({
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((r, i) => new TableRow({
      tableHeader: i === 0,
      children: r.map((t, j) => cell(String(t), widths[j], { head: i === 0, right: i > 0 && rightCols.includes(j) })),
    })),
  });
}

const children = [
  new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun({ text: "Отчет о тестировании", font: FONT })] }),
  p({ text: "Ускорение веб-сервиса депозитов базы ПИФ: расширение ПИФ_ДепозитыОдноЧтение 1.0.0.1", bold: true, size: 26 }),
  p("Дата тестирования: 29.10.2026. Среда: копия ПРОД Т-1 (база ПИФ AVC_PP_PIF, вызов из базы ФО Розница AVC_PP_Retail_FO)."),

  h("1. Итог", HeadingLevel.HEADING_1),
  table([3400, 6238], [
    ["Проверка", "Результат"],
    ["Регресс ответа getDeposits", "Нет: 72 строки из 72 совпали по всем 11 полям, контрольная сумма ответа одна и та же"],
    ["Время ответа, среднее по 2 вызовам", "223,3 с до установки, 111,4 с после установки"],
    ["Ускорение", "в 2,0 раза (минус 111,8 с, или 50%, на каждый вызов)"],
    ["Стабильность", "Ответы двух вызовов внутри каждого прогона совпали; первый вызов после установки расширения медленнее второго на 1,9 с"],
  ]),
  p(""),
  p("Расширение можно передавать на установку в ПИФ ПРОД (или вендору Аванкор для внесения в базовую конфигурацию): ответ сервиса не изменился, время ответа сократилось вдвое."),

  h("2. Что проверялось", HeadingLevel.HEADING_1),
  p("Операция getDeposits веб-сервиса deposits базы ПИФ. Ее каждое утро в 05:00 вызывают обе базы Фронт-офиса при загрузке депозитов. Расширение меняет функцию ТаблицаДепозитов модуля веб-сервиса: движения выдачи депозитов (виртуальная таблица ДвиженияССубконто регистра Управленческий) читаются один раз во временную таблицу, вместо двух одинаковых чтений за всю историю. Состав и формат ответа не меняются."),

  h("3. Условия теста", HeadingLevel.HEADING_1),
  bullet("Тестовая обработка ТестСервисаДепозитовПИФ запускалась в ФО Розница Т-1 и вызывала getDeposits так же, как ежедневная загрузка депозитов: тот же сервис, та же учетная запись, ответ разбирается полностью."),
  bullet("Прогон \"до\": 29.10.2026, начат в 06:17, ПИФ без расширения. Прогон \"после\": 29.10.2026, начат в 06:28, в ПИФ установлено расширение ПИФ_ДепозитыОдноЧтение 1.0.0.1."),
  bullet("Оба прогона на одной копии Т-1, с одной датой запроса (29.10.2026), по 2 вызова подряд, к одному и тому же сервису (отпечаток адреса совпадает)."),
  bullet("Ответ сравнивался по каждому полю каждой строки и по контрольным суммам строк и всего ответа."),

  h("4. Замеры", HeadingLevel.HEADING_1),
  table([2600, 2346, 2346, 2346], [
    ["Вызов", "До, с", "После, с", "Ускорение"],
    ["1", "231,6", "112,4", "в 2,06 раза"],
    ["2", "215,0", "110,5", "в 1,95 раза"],
    ["Среднее", "223,3", "111,4", "в 2,00 раза"],
    ["Минимум", "215,0", "110,5", "в 1,95 раза"],
    ["Получение описания сервиса", "1,4", "1,6", "-"],
  ], [1, 2]),
  p(""),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({
    type: "png", data: fs.readFileSync(CHART), transformation: { width: 600, height: 342 },
    altText: { title: "Ускорение getDeposits", description: "Время ответа getDeposits до и после установки расширения по вызовам и в среднем", name: "chart" },
  })] }),
  p({ text: "Рисунок 1. Время ответа getDeposits до и после установки расширения", italics: true, size: 20 }, { alignment: AlignmentType.CENTER }),

  h("5. Регресс", HeadingLevel.HEADING_1),
  table([4800, 2419, 2419], [
    ["Сравнение", "До", "После"],
    ["Строк в ответе", "72", "72"],
    ["Строк, совпавших по всем полям", "72 из 72", "72 из 72"],
    ["Контрольная сумма ответа", "4A78C299B5D6D9AC", "4A78C299B5D6D9AC"],
    ["Ответ второго вызова совпадает с первым", "Да", "Да"],
    ["Итоги по числовым полям ответа", "совпадают", "совпадают"],
  ]),
  p(""),
  p("Поля ответа, сверенные построчно: идентификатор, источник, наименование (по контрольной сумме), рыночная стоимость, проценты за день, начальная сумма, текущая сумма, валюта, дата открытия, дата погашения, ставка. Расхождений нет ни в одном поле."),
  bullet("Валюты депозитов в ответе: рубли - 67 строк, юани - 5 строк; источник во всех строках - AVC_PP_PIF."),
  bullet("Один идентификатор депозита встречается в ответе 6 раз в обоих прогонах. Это особенность данных ПИФ, расширение ее не затрагивает."),

  h("6. Ожидаемый эффект на ПРОД", HeadingLevel.HEADING_1),
  p("28.10.2026 сервис депозитов ПИФ ПРОД (вызов из Фронт-офиса по адресу из настроек загрузки депозитов) отвечал 685-692 с, то есть втрое дольше, чем ПИФ Т-1 до установки расширения. Расширение убирает одно из двух одинаковых чтений истории проводок, поэтому на ПРОД ожидается сокращение того же порядка: ответ около 5,5-6 минут вместо 11,5. Сервис вызывают обе базы Фронт-офиса, поэтому сервер ПИФ ПРОД освобождается примерно на 11 минут каждое утро. Точное значение покажет первый запуск загрузки депозитов после установки на ПРОД."),

  h("7. Ограничения", HeadingLevel.HEADING_1),
  bullet("Тест выполнен на Т-1: сервер, нагрузка и объем данных отличаются от ПРОД, абсолютное время на ПРОД будет другим."),
  bullet("По 2 вызова в каждом прогоне, один день данных. Разброс времени внутри прогона - до 8% до установки и до 2% после."),
  bullet("Проверялся ответ на одну дату запроса (29.10.2026)."),
];

const doc = new Document({
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", run: { size: 40, bold: true, font: FONT, color: "1F3864" }, paragraph: { spacing: { after: 120 } } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, font: FONT, color: "2F5D8A" }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: "7F7F7F" })] })] }) },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("ok", OUT); });
