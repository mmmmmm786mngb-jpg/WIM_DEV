// Сборка отчета о тестировании IMDEV-9744 на Т-1 (docx).
// Запуск: node build_t1_report_docx.js "<каталог PNG из build_t1_report_charts.py>" "<путь к docx>"
// Пакет docx берется из NODE_PATH. Цифры - из лога обработки замеров Т-1 от 30.10.2026 14:07 и логов выгрузки.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType, AlignmentType,
  HeadingLevel, BorderStyle, LevelFormat, Footer, PageNumber, ImageRun,
} = require("docx");

const CHARTS = process.argv[2];
const OUT = process.argv[3];
const FONT = "Calibri";
const W = 9638; // A4 книжная, поля 2 см
const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };
const GREEN = "E6F4EA";
const GRAY = "F2F2F2";

function runs(text, size = 21) {
  return (Array.isArray(text) ? text : [text]).map((t) =>
    typeof t === "string" ? new TextRun({ text: t, font: FONT, size }) : new TextRun({ font: FONT, size, ...t }));
}
function p(text, opts = {}) {
  return new Paragraph({ children: runs(text), spacing: { after: 100, line: 276 }, ...opts });
}
function h(text, level = HeadingLevel.HEADING_1) {
  return new Paragraph({ heading: level, keepNext: true, children: [new TextRun({ text, font: FONT })], spacing: { before: 240, after: 110 } });
}
function bullet(text) {
  return p(text, { numbering: { reference: "bullets", level: 0 }, spacing: { after: 50, line: 276 } });
}
function caption(text) {
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 },
    children: [new TextRun({ text, font: FONT, size: 18, italics: true, color: "52514E" })] });
}
function pngSize(file) {
  const buf = fs.readFileSync(file);
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20), data: buf };
}
function image(name, widthPx = 620) {
  const png = pngSize(path.join(CHARTS, name));
  return new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 80, after: 40 },
    children: [new ImageRun({ type: "png", data: png.data,
      transformation: { width: widthPx, height: Math.round(widthPx * png.height / png.width) } })] });
}
function table(widths, rows, opts = {}) {
  return [tableOnly(widths, rows, opts), new Paragraph({ spacing: { after: 60 }, children: [] })];
}
function tableOnly(widths, rows, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((row, i) => new TableRow({
      tableHeader: i === 0,
      children: row.map((value, j) => {
        const head = i === 0;
        const fill = head ? GRAY : (opts.fill && opts.fill(i, j)) || null;
        return new TableCell({
          borders, width: { size: widths[j], type: WidthType.DXA },
          shading: fill ? { fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
          margins: { top: 50, bottom: 50, left: 90, right: 90 },
          children: String(value).split("\n").map((line) => new Paragraph({
            alignment: j > 0 && opts.numeric && opts.numeric(j) ? AlignmentType.RIGHT : AlignmentType.LEFT,
            spacing: { after: 20 },
            children: [new TextRun({ text: line, font: FONT, size: 19, bold: head })],
          })),
        });
      }),
    })),
  });
}

const children = [];
children.push(new Paragraph({ spacing: { after: 60 },
  children: [new TextRun({ text: "Отчет о тестировании на копии Т-1", font: FONT, size: 36, bold: true })] }));
children.push(p([{ text: "IMDEV-9744. Ускорение передачи блокировок ДС из МО Розница в ФО Розница: обработка выгрузки остатков 1.43", size: 24 }]));
children.push(p([{ text: "Дата тестирования: 30.10.2026. Базы: копия ПРОД (Т-1) МО Розница и ФО Розница.", color: "52514E" }]));

children.push(h("1. Итог"));
children.push(...table([2600, 1500, 5538], [
  ["Проверка", "Результат", "Основание"],
  ["Регресс", "Пройден", "8 прогонов выгрузки по 200 мандатам (обе версии): все мандаты выгружены, ошибок нет. 3 800 поручений-блокировок отправлено в ФО: ошибок, незагруженных поручений и сбоев вызова нет"],
  ["Скорость без блокировок", "Не изменилась", "Парные прогоны: 1.42 - 182 с, 1.43 - 184 с (+1%). Один прогон 1.43 (256 с) пришелся на нагрузку сервера: в нем вдвое замедлилось и чтение данных МО, которое в версиях одинаково"],
  ["Скорость с блокировками", "Лучше", "Выгрузка 200 мандатов с блокировками: 305 с в 1.42 и 264 с в 1.43 (-13%). Отправка одной блокировки: -37% для нового поручения, -44% для существующего"],
  ["Оценка на объеме 21-28.10", "~ -16 мин", "19 399 блокировок, 5 потоков: отправка блокировок ~44 мин в 1.42 и ~28 мин в 1.43"],
], { fill: (i, j) => (j === 1 ? GREEN : null) }));

children.push(h("2. Что изменено в версии 1.43"));
children.push(p("Обработка выгрузки остатков МО - ФО передает блокировки денежных средств в ФО поручениями-блокировками. В версии 1.42 блокировки каждого мандата уходят отдельным вызовом веб-сервиса ФО, в версии 1.43 - одним вызовом на пакет мандатов (50 мандатов, как в настройке узла выгрузки). Если ответ ФО на пакет содержит ошибку, 1.43 повторяет отправку пакета по мандатам, чтобы ошибка относилась к своему мандату, как в 1.42."));
children.push(p("Выгрузка мандатов без блокировок в 1.42 и 1.43 выполняется одинаково: в обеих версиях вызов передачи блокировок не делается, если у мандатов пакета блокировок нет."));

children.push(h("3. Условия тестирования"));
[
  "Копия ПРОД (Т-1) от 30.10.2026: МО Розница и ФО Розница, веб-сервис ФО Т-1.",
  "Сравнение версий: обработка замеров выполняет выгрузку (заполнение и отправку в ФО) версиями 1.42 и 1.43 на одной и той же выборке из 200 мандатов, одним потоком, пакетами по 50 мандатов. Порядок прогонов чередуется: без блокировок 1.42 - 1.43 - 1.43 - 1.42, с блокировками 1.43 - 1.42 - 1.42 - 1.43, чтобы ни одна версия не получала преимущества от прогрева ФО.",
  "Блокировки взяты на 28.10.2026 - последний день, когда в МО было 19 399 блокировок \"Вознаграждение\" (к 29.10 они сняты). Для теста они отправлены поручениями с тестовыми кодами, которые в конце помечены на удаление.",
  "Отдельно замерена отправка одной блокировки: по 100 мандатам, по мандату и пакетами по 10 и 50, для новых и для уже существующих поручений, а также частота ошибок ответа ФО на 10 пакетах по 50 мандатов.",
].forEach((t) => children.push(bullet(t)));

children.push(h("4. Регресс"));
children.push(...table([4200, 2200, 3238], [
  ["Проверка", "1.42", "1.43"],
  ["Выгрузка 200 мандатов без блокировок, 2 прогона на версию", "200 из 200 успешно, ошибок нет", "200 из 200 успешно, ошибок нет"],
  ["Выгрузка 200 мандатов с блокировками, 2 прогона на версию", "200 из 200 успешно, ошибок нет", "200 из 200 успешно, ошибок нет"],
  ["Поручения-блокировки в ФО: ошибки ответа, незагруженные поручения, сбои вызова", "0 / 0 / 0", "0 / 0 / 0"],
  ["Ответ ФО на пакет с ошибкой (повторная отправка по мандатам)", "-", "На Т-1 ошибок нет (0 из 10 пакетов); ветка проверена на стенде разработки"],
  ["Стенд разработки, 28.10: создание, перезапись, ошибка в пакете, без блокировок, длинный код счета", "Эталон", "Ответ ФО и состав поручений совпадают с 1.42"],
], { fill: (i, j) => (i > 0 && j > 0 ? GREEN : null) }));
children.push(p("Всего за тестирование в ФО Т-1 отправлено 3 800 поручений-блокировок (создание, повтор, пометка удаления) - без единой ошибки."));

children.push(h("5. Скорость без блокировок"));
children.push(image("01_versions.png", 640));
children.push(caption("Рисунок 1. Время отправки в ФО (Опубликовать) по прогонам, 200 мандатов"));
children.push(p("Без блокировок обе версии делают одно и то же: передают позиции, флаги и пересчет РСА, вызова передачи блокировок нет. В первой паре прогонов разница 1% (182 и 184 с), во второй паре прогоны 1.42 - 170 с и 1.43 - 256 с."));
children.push(p("Прогон 1.43 в 256 с пришелся на нагрузку сервера Т-1: в нем вдвое дольше обычного шло и чтение данных МО (Заполнить), код которого в 1.42 и 1.43 одинаков и к ФО не обращается (рисунок 2). Без этого прогона среднее время: 1.42 - 176 с, 1.43 - 184 с, в пределах разброса между двумя прогонами одной версии 1.42 (170 и 182 с)."));
children.push(image("03_fill.png", 470));
children.push(caption("Рисунок 2. Чтение данных МО (Заполнить) в прогонах без блокировок"));

children.push(h("6. Скорость с блокировками"));
children.push(image("02_averages.png", 560));
children.push(caption("Рисунок 3. Среднее время отправки в ФО по версиям и режимам"));
children.push(p("С блокировками на каждом из 200 мандатов выгрузка в 1.43 в среднем на 13% быстрее: 264 с против 305 с. Добавка от блокировок к выгрузке без блокировок в 1.42 - около 128 с (0,64 с на блокировку), в 1.43 - около 80 с (0,40 с на блокировку)."));
children.push(image("04_per_block.png", 560));
children.push(caption("Рисунок 4. Время отправки одной блокировки, мс"));
children.push(...table([3400, 2000, 2000, 2238], [
  ["Отправка блокировки", "По мандату (1.42)", "Пакет 50 (1.43)", "Пакет 10"],
  ["Новое поручение", "676 мс", "427 мс", "404 мс"],
  ["Существующее поручение", "736 мс", "413 мс", "-"],
], { numeric: () => true }));
children.push(p("Пакет убирает накладные расходы отдельного вызова веб-сервиса - около 0,3 с на мандат. Оставшиеся ~0,4 с на поручение - запись и проведение поручения в ФО, от размера пакета они почти не зависят (пакеты 10 и 50 дают одинаковый результат)."));

children.push(h("7. Оценка для объема блокировок 21-28.10"));
children.push(image("05_estimate.png", 600));
children.push(caption("Рисунок 5. Оценка утренней выгрузки при 19 399 блокировках, 5 потоков"));
children.push(p("При 19 399 блокировках и 5 потоках, как на ПРОД, отправка блокировок оценивается в ~44 мин для 1.42 и ~28 мин для 1.43: утренняя выгрузка короче примерно на 16 минут. Оценка получена из времени одной блокировки на Т-1 и не учитывает конкуренцию потоков за ФО; на ПРОД 21-28.10 блокировки добавляли к выгрузке около 53 минут."));

children.push(h("8. Полные выгрузки 30.10 на Т-1"));
children.push(p("30.10 полная выгрузка по узлу на Т-1 выполнялась трижды: 05:29 - 40 мин, 10:18 (1.43) - 75 мин, 11:44 (1.42) - 37 мин. В этот день в МО оставалось 19 блокировок: их отправка занимает около 13 секунд в любой версии, поэтому разница между прогонами вызвана не версией обработки, а состоянием Т-1 в рабочее время - так же, как в прогоне 1.43 из раздела 5."));

children.push(h("9. Тестовые данные"));
children.push(p("Поручения-блокировки с кодами LOCK:T9744... в ФО Т-1 отправлены с пометкой удаления и удаляются ночным обновлением копии. Позиции 200 мандатов выборки выгружены в ФО Т-1 так же, как при утренней выгрузке; рассылки не было."));

children.push(h("10. Вывод"));
children.push(p("Версия 1.43 обработки выгрузки остатков МО - ФО прошла регресс без ошибок, не замедляет выгрузку без блокировок и ускоряет передачу блокировок ДС: на 13% на выборке, где блокировка есть у каждого мандата, и на 37-44% в расчете на одну блокировку. Версию 1.43 можно передавать на ПРОД; эффект на ПРОД проявится при следующем появлении массовых блокировок."));

const doc = new Document({
  styles: {
    default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: FONT, color: "1C5CAB" }, paragraph: { spacing: { before: 240, after: 110 }, outlineLevel: 0 } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ font: FONT, size: 18, color: "7F7F7F", children: ["IMDEV-9744. Тестирование на Т-1. Стр. ", PageNumber.CURRENT] })] })] }) },
    children,
  }],
});

Packer.toBuffer(doc).then((buffer) => { fs.writeFileSync(OUT, buffer); console.log("ok", OUT); });
