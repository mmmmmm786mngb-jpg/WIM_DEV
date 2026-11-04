// Сборка отчета о тестировании IMDEV-9746 на Т-1 (docx).
// Запуск: node build_t1_report_docx.js "<каталог PNG из build_t1_report_charts.py>" "<путь к docx>"
// Пакет docx берется из NODE_PATH. Цифры - из логов теста Т-1 от 04.11.2026 (обычный ФО 07:52, розница 07:47).
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType, AlignmentType,
  HeadingLevel, BorderStyle, LevelFormat, Footer, PageNumber, ImageRun,
} = require("docx");

const CHARTS = process.argv[2];
const OUT = process.argv[3];
const FONT = "Calibri";
const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };
const GREEN = "E6F4EA";
const GRAY = "F2F2F2";
const BLUE = "1C5CAB";

function runs(text, size = 21) {
  return (Array.isArray(text) ? text : [text]).map((t) =>
    typeof t === "string" ? new TextRun({ text: t, font: FONT, size }) : new TextRun({ font: FONT, size, ...t }));
}
function p(text, opts = {}) {
  return new Paragraph({ children: runs(text), spacing: { after: 100, line: 276 }, ...opts });
}
function h(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, keepNext: true, children: [new TextRun({ text, font: FONT })],
    spacing: { before: 240, after: 110 } });
}
function bullet(text) {
  return p(text, { numbering: { reference: "bullets", level: 0 }, spacing: { after: 50, line: 276 } });
}
function numbered(text) {
  return p(text, { numbering: { reference: "steps", level: 0 }, spacing: { after: 50, line: 276 } });
}
function caption(text) {
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 },
    children: [new TextRun({ text, font: FONT, size: 18, italics: true, color: "52514E" })] });
}
function image(name, widthPx) {
  const buf = fs.readFileSync(path.join(CHARTS, name));
  const w = buf.readUInt32BE(16);
  const hgt = buf.readUInt32BE(20);
  return new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 80, after: 40 },
    children: [new ImageRun({ type: "png", data: buf, transformation: { width: widthPx, height: Math.round(widthPx * hgt / w) } })] });
}
function table(widths, rows, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const t = new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((row, i) => new TableRow({
      tableHeader: i === 0,
      cantSplit: true,
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
  return [t, new Paragraph({ spacing: { after: 60 }, children: [] })];
}
function tiles(items) {
  const w = 3212;
  return [new Table({
    width: { size: w * items.length, type: WidthType.DXA },
    columnWidths: items.map(() => w),
    rows: [new TableRow({ children: items.map(([big, small]) => new TableCell({
      borders, width: { size: w, type: WidthType.DXA },
      shading: { fill: GREEN, type: ShadingType.CLEAR, color: "auto" },
      margins: { top: 120, bottom: 120, left: 120, right: 120 },
      children: [
        new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: big, font: FONT, size: 34, bold: true, color: BLUE })] }),
        new Paragraph({ spacing: { after: 0 }, children: [new TextRun({ text: small, font: FONT, size: 19 })] }),
      ],
    })) })],
  }), new Paragraph({ spacing: { after: 80 }, children: [] })];
}

const children = [];
children.push(new Paragraph({ spacing: { after: 60 },
  children: [new TextRun({ text: "Отчет о тестировании на копии Т-1", font: FONT, size: 36, bold: true })] }));
children.push(p([{ text: "IMDEV-9746. Ускорение установки лимитов новым клиентам: обработка \"Распространение правил с одного клиента на список клиентов\" 1.17", size: 24 }]));
children.push(p([{ text: "Дата тестирования: 04.11.2026. Базы: копии ПРОД (Т-1) ФО и ФО розница, конфигурация 1.4.9.5. Сравнивались рабочая версия обработки 1.16 и новая 1.17.", color: "52514E" }]));

children.push(h("1. Итог"));
children.push(...tiles([
  ["в 7,3 раза", "ФО: установка лимитов новому клиенту 22,7 с против 3,1 с"],
  ["в 1,4 раза", "ФО розница: запуск с двумя клиентами 7,7 с против 5,4 с"],
  ["0 расхождений", "у 9 клиентов результат 1.17 совпал с 1.16 и с исходным состоянием"],
]));
children.push(...table([2400, 1700, 5538], [
  ["Проверка", "Результат", "Основание"],
  ["Регресс", "Пройден", "9 реальных клиентов (3 в ФО, 6 в рознице), каждый обработан обеими версиями: установки лимитов, пороги и сведения после 1.16 и после 1.17 одинаковые и совпадают с состоянием до теста. Ошибок нет ни в одном из 18 запусков"],
  ["Скорость, ФО", "в 7,3 раза быстрее", "Медиана по 3 запускам: 22,7 с в 1.16 и 3,1 с в 1.17. Прогноз по стенду - в 7,7 раза"],
  ["Скорость, ФО розница", "в 1,4 раза быстрее", "Медиана по 3 запускам: 7,7 с в 1.16 и 5,4 с в 1.17. Прогноз по стенду - в 1,35 раза"],
  ["Фоновая запись версий лимитов, ФО розница", "в 2,2 раза быстрее", "14 с в 1.16 и 6-7 с в 1.17; на время обмена не влияет"],
  ["Письма", "Без ошибок", "Отправлены на тестовые адреса, ошибок отправки в журнале регистрации нет. 1.17 отправляет одно итоговое письмо на класс лимитов вместо письма по каждому клиенту"],
], { fill: (i, j) => (j === 1 ? GREEN : null) }));

children.push(h("2. Что изменено в версии 1.17"));
[
  "Временные файлы вложений писем удаляются после отправки (ФО и ФО розница).",
  "В ФО пороги лимитов нового клиента записываются без пересчета истории и настроек лимита на каждый порог, как в рознице. Проверки, которые выполнял при записи учет порогов (подтвержденный лимит, доступ к классу лимита, пометка удаления настройки порогов), обработка выполняет сама. История лимита и настройки лимита обновляются один раз на лимит в фоновом задании после распространения.",
  "Настройки лимита в фоновом задании обновляются только для классов лимитов с расширенным подтверждением: только для них проверка лимитов берет пороги из сохраненных настроек. На копии ПРОД таких классов нет.",
  "Одно итоговое письмо на класс лимитов с порогами всех клиентов запуска вместо письма по каждому клиенту (ФО и ФО розница).",
  "Обработка не ждет окончания фонового задания записи версий лимитов, которое ставит сама (ФО розница).",
  "Фоновое задание записи версий сначала проверяет, созданы ли установки лимитов, и делает паузу, только если их еще нет.",
].forEach((t) => children.push(bullet(t)));

children.push(h("3. Как проверялось"));
[
  "Базы: копии ПРОД (Т-1) ФО и ФО розница от 04.11.2026, конфигурация 1.4.9.5.",
  "Клиенты: реальные клиенты, которым лимиты были установлены автоматически незадолго до теста. ФО - 3 клиента, по одному на запуск (26 порогов у каждого). ФО розница - 6 клиентов, по два на запуск (классы Compliance и Регуляторные, 4 порога у каждого).",
  "Распространение вызывалось так же, как после обмена с МО, под пользователем из списка сервисных - как на ПРОД. Подписки на запись сведений клиента работали как на ПРОД и на время запуска 1.17 обращались к версии 1.17.",
  "Письма отправлялись по настройкам рассылки обработки; на время теста адреса в них заменены на тестовые.",
].forEach((t) => children.push(bullet(t)));
children.push(p([{ text: "Порядок теста в каждой базе", bold: true }], { keepNext: true }));
[
  "Снимок исходного состояния клиентов: установки лимитов (класс и состав лимитов), пороги (лимит и настройка порогов), сведения распространения.",
  "Перед каждым запуском клиент приводится к состоянию нового клиента: снимается проведение его установок лимитов, удаляются его пороги и сведения автоустановки.",
  "Каждый клиент обрабатывается обеими версиями. Порядок версий чередуется: 1.16 и 1.17, затем 1.17 и 1.16, затем снова 1.16 и 1.17, чтобы ни одна версия не получала преимущества от прогрева сервера.",
  "После каждого запуска: ожидание фоновых заданий, замеры времени, снимок состояния клиентов.",
  "Сравнение состояния клиентов после 1.16, после 1.17 и до теста.",
].forEach((t) => children.push(numbered(t)));

children.push(h("4. Регресс"));
children.push(...table([4300, 2600, 2738], [
  ["Проверка", "ФО (3 клиента)", "ФО розница (6 клиентов)"],
  ["Установки лимитов: класс и состав лимитов после 1.16 и после 1.17", "Совпадают", "Совпадают"],
  ["Пороги лимитов: лимит и настройка порогов", "Совпадают (26 у каждого)", "Совпадают (4 у каждого)"],
  ["Сведения клиента: эталонный портфель, даты автоустановки и распространения правил, лимиты заведены", "Совпадают", "Совпадают"],
  ["Результат 1.17 и состояние клиента до теста", "Совпадают", "Совпадают"],
  ["Версии лимитов, записанные за запуск", "26 в обеих версиях", "4 в обеих версиях"],
  ["Ошибки в журнале регистрации (включая отправку писем)", "0", "0"],
], { fill: (i, j) => (i > 0 && j > 0 ? GREEN : null) }));

children.push(h("5. Время запуска"));
children.push(image("01_runs.png", 640));
children.push(caption("Рисунок 1. Время установки лимитов по запускам, секунд"));
children.push(...table([2700, 2300, 2300, 2338], [
  ["База", "1.16, медиана (мин - макс)", "1.17, медиана (мин - макс)", "Быстрее"],
  ["ФО, 1 клиент", "22,7 с (21,6 - 26,5)", "3,1 с (2,8 - 3,4)", "в 7,3 раза"],
  ["ФО розница, 2 клиента", "7,7 с (7,5 - 7,9)", "5,4 с (5,3 - 5,4)", "в 1,4 раза"],
], { numeric: (j) => j > 0 }));
children.push(image("02_steps.png", 640));
children.push(caption("Рисунок 2. Из чего складывается время запуска"));
children.push(p("В ФО время уходило на запись порогов: каждый из 26 порогов пересчитывал историю и настройки лимита по всем клиентам с порогом по этому лимиту. В 1.17 создание установки занимает 2,6 с вместо 22,2 с, итоговое письмо - около 0,3 с."));
children.push(p("В ФО розница 1.17 убирает четыре письма по клиентам (в 1.16 они входят в создание установок) и ожидание 0,8 с после постановки фонового задания. Оставшееся время - запись установок лимитов и сведений клиентов, которые выполняются средствами конфигурации и в этой доработке не менялись."));

children.push(h("6. Фоновые задания"));
children.push(...table([3500, 3000, 3138], [
  ["Задание", "1.16", "1.17"],
  ["Запись версий лимитов, ФО (26 версий)", "нет: версии пишутся при записи каждого порога внутри запуска", "10-11 с после запуска, на время обмена не влияет"],
  ["Запись версий лимитов, ФО розница (4 версии)", "14 с: пауза 2 с на каждую пару клиент и класс плюс запись версий", "6-7 с: без паузы"],
  ["Распространение по записи сведения клиента (подписка)", "до 1 с каждое", "до 1 с каждое"],
]));
children.push(p("Фоновое задание розницы ускорилось в 2,2 раза, а не в 4,6, как на тестовом стенде: на копии ПРОД у лимитов розницы до 28 тысяч портфелей с порогами, и запись одной версии лимита занимает около 1,5 с. Версия 1.17 убирает паузу, саму запись версий она не меняет."));

children.push(h("7. Сравнение с ПРОД"));
children.push(...table([3200, 3200, 3238], [
  ["Показатель", "ПРОД, замеры 16.10-02.11", "Т-1, версия 1.16"],
  ["ФО: на одного клиента", "25,9 с", "22,7 с"],
  ["ФО розница: на пару клиент и класс", "1,5 с", "1,9 с"],
], { numeric: (j) => j > 0 }));
children.push(p("Копия Т-1 по скорости близка к ПРОД, поэтому ожидаемый результат на ПРОД: в ФО около 3-4 с на нового клиента вместо 26 с, в ФО розница - запуск примерно в 1,4 раза быстрее и в несколько раз меньше писем."));

children.push(h("8. Особенности версии 1.17"));
[
  "История и настройки лимита обновляются фоновым заданием через несколько секунд после распространения (в тесте 6-11 с). Проверка лимитов использует сохраненные настройки только для классов с расширенным подтверждением, на ПРОД таких классов нет.",
  "Письма: по классу лимитов приходит одно итоговое письмо с порогами всех клиентов запуска. Признак ошибки или предупреждения в теме письма считается по всем клиентам класса.",
].forEach((t) => children.push(bullet(t)));

children.push(h("9. Тестовые данные"));
children.push(p("Клиенты теста после теста настроены так же, как до него: действующие установки лимитов, пороги и сведения - от последнего запуска 1.17. Исходные установки лимитов этих клиентов остались непроведенными, установки промежуточных запусков помечены на удаление. Рабочей обработке возвращены версия 1.16 и исходные настройки. Копия Т-1 обновляется с ПРОД каждую ночь."));

children.push(h("10. Вывод"));
children.push(p("Версия 1.17 обработки распространения правил прошла регресс на реальных клиентах копии ПРОД без расхождений и ошибок. Установка лимитов новому клиенту в ФО выполняется в 7,3 раза быстрее, в ФО розница - в 1,4 раза быстрее, письма приходят одним итоговым письмом на класс лимитов. Версию 1.17 можно передавать на ПРОД."));

const doc = new Document({
  styles: {
    default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: FONT, color: BLUE }, paragraph: { spacing: { before: 240, after: 110 }, keepNext: true, outlineLevel: 0 } },
    ],
  },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
      alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    { reference: "steps", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
      alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ font: FONT, size: 18, color: "7F7F7F", children: ["IMDEV-9746. Тестирование на Т-1. Стр. ", PageNumber.CURRENT] })] })] }) },
    children,
  }],
});

Packer.toBuffer(doc).then((buffer) => { fs.writeFileSync(OUT, buffer); console.log("ok", OUT); });
