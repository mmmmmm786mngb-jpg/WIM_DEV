const pptxgen = require("pptxgenjs");
const pres = new pptxgen();

pres.layout = "LAYOUT_WIDE";
pres.title = "Локальный ИИ на ноутбуке: LM Studio, Qwen2.5-Coder, Cline";
pres.author = "WIM local pilot";
pres.subject = "Как на ноутбуке запущены LM Studio, Qwen2.5-Coder-7B и VS Code с Cline";

const C = {
  ink: "1C2430",
  ink2: "2A3848",
  amber: "C47B2B",
  amberDeep: "8A5414",
  amberSoft: "FBF3E6",
  teal: "1F6F62",
  tealDeep: "144F46",
  tealSoft: "E7F2EF",
  mist: "F4F6F8",
  white: "FFFFFF",
  text: "1C2430",
  muted: "5C6B76",
  codeBg: "1C2430",
  codeTx: "E7EEF3",
};

const FONT = "Calibri";
const SERIF = "Cambria";
const MONO = "Courier New";

function shadow() {
  return { type: "outer", color: "1C2430", blur: 16, opacity: 0.1, offset: 4, angle: 90 };
}

function title(slide, text, dark) {
  slide.addText(text, {
    x: 0.55, y: 0.36, w: 12.2, h: 0.58,
    fontFace: SERIF, fontSize: 32, bold: true,
    color: dark ? C.white : C.ink,
    margin: 0, isTextBox: true, valign: "middle",
  });
}

function kicker(slide, text, dark) {
  slide.addText(text, {
    x: 0.55, y: 0.98, w: 12.2, h: 0.36,
    fontFace: FONT, fontSize: 16,
    color: dark ? "C9D4DE" : C.muted,
    margin: 0, isTextBox: true,
  });
}

function card(slide, x, y, w, h, fill) {
  slide.addShape("roundRect", {
    x, y, w, h,
    fill: { color: fill },
    rectRadius: 0.12,
    shadow: shadow(),
  });
}

function notes(slide, text) {
  slide.addNotes(text);
}

// ---------------------------------------------------------------------------
// 1. Title
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.ink };
  s.addText("ПИЛОТ НА ОДНОМ НОУТБУКЕ", {
    x: 0.7, y: 1.15, w: 11.5, h: 0.32,
    fontFace: FONT, fontSize: 14, bold: true,
    color: C.amber, margin: 0, isTextBox: true,
    charSpacing: 1.4,
  });
  s.addText("Локальный ИИ, который\nпишет код 1С на этом компьютере", {
    x: 0.7, y: 1.6, w: 11.2, h: 1.9,
    fontFace: SERIF, fontSize: 40, bold: true,
    color: C.white, margin: 0, isTextBox: true,
  });
  s.addText("LM Studio держит модель Qwen2.5-Coder-7B.\nVS Code с расширением Cline превращает ответы в правки.\nАдрес сервера: 127.0.0.1, порт 1234.", {
    x: 0.7, y: 3.7, w: 10.5, h: 1.25,
    fontFace: FONT, fontSize: 18,
    color: "D5DEE6", margin: 0, isTextBox: true,
  });

  const pills = [
    ["LM Studio", "локальный сервер"],
    ["Qwen2.5-Coder-7B", "файл 4,68 ГБ, Q4"],
    ["Cline в VS Code", "агент в редакторе"],
  ];
  pills.forEach((p, i) => {
    const x = 0.7 + i * 4.05;
    s.addShape("roundRect", {
      x, y: 5.45, w: 3.8, h: 1.15,
      fill: { color: C.ink2 },
      rectRadius: 0.1,
    });
    s.addText(p[0], {
      x: x + 0.22, y: 5.58, w: 3.36, h: 0.42,
      fontFace: SERIF, fontSize: 18, bold: true,
      color: C.white, margin: 0, isTextBox: true,
    });
    s.addText(p[1], {
      x: x + 0.22, y: 6.04, w: 3.36, h: 0.34,
      fontFace: FONT, fontSize: 14,
      color: "C9D4DE", margin: 0, isTextBox: true,
    });
  });
  notes(s, "Коротко: это не облако и не сервер отдела. На ноутбуке три части. LM Studio считает модель, Cline сидит в VS Code, между ними HTTP на localhost. Снимок живого диалога сделан 4 ноября 2026.");
}

// ---------------------------------------------------------------------------
// 2. Three roles
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  title(s, "Три программы, одна цепочка");
  kicker(s, "Модель считает. Редактор действует. Сеть за пределы компьютера не нужна.");

  const items = [
    [C.tealSoft, C.tealDeep, "01", "LM Studio", "Программа-сервер. Загружает файл весов в память и открывает HTTP на 127.0.0.1:1234. Пока сервер остановлен, чату в редакторе некуда отправить задачу."],
    [C.amberSoft, C.amberDeep, "02", "Qwen2.5-Coder-7B", "Открытая модель Alibaba под лицензией Apache 2.0, сборка для кода. На диске лежит квантованный файл Q4_K_M, 4,68 ГБ. Считает на процессоре ноутбука."],
    [C.mist, C.ink, "03", "Cline в VS Code", "Открытое расширение. Собирает задачу, правила проекта и открытые файлы, отправляет их модели и показывает ответ. Запись файла видна кнопкой View Changes."],
  ];
  items.forEach((it, i) => {
    const x = 0.55 + i * 4.2;
    card(s, x, 1.7, 3.85, 4.55, it[0]);
    s.addText(it[2], {
      x: x + 0.28, y: 1.95, w: 3.4, h: 0.4,
      fontFace: SERIF, fontSize: 20, bold: true,
      color: it[1], margin: 0, isTextBox: true,
    });
    s.addText(it[3], {
      x: x + 0.28, y: 2.42, w: 3.4, h: 0.48,
      fontFace: SERIF, fontSize: 24, bold: true,
      color: C.ink, margin: 0, isTextBox: true,
    });
    s.addText(it[4], {
      x: x + 0.28, y: 3.05, w: 3.4, h: 2.85,
      fontFace: FONT, fontSize: 16,
      color: C.text, margin: 0, isTextBox: true,
    });
  });
  notes(s, "Развести роли. Cline сам код не пишет: он клиент. Ум находится в файле модели внутри LM Studio. Это важно, потому что коллеги часто думают, что расширение уже содержит ИИ.");
}

// ---------------------------------------------------------------------------
// 3. How a message travels
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  title(s, "Путь одного сообщения");
  kicker(s, "Cline говорит с LM Studio тем же HTTP-форматом, что и клиенты OpenAI. Адрес локальный.");

  const nodes = [
    [C.teal, "VS Code + Cline", "Чат, правила .clinerules и навыки .cline/skills остаются на ноутбуке. Cline решает, что приложить к запросу."],
    [C.amber, "127.0.0.1:1234", "POST в формате chat completions. В ответе поток токенов. Проверка сервера: GET /v1/models."],
    [C.ink, "LM Studio + Qwen", "Файл весов уже в памяти. Расчет идет на CPU. В логе сервера виден каждый завершенный ответ."],
  ];
  nodes.forEach((n, i) => {
    const x = 0.55 + i * 4.2;
    card(s, x, 1.65, 3.85, 3.15, C.white);
    s.addShape("ellipse", {
      x: x + 0.28, y: 1.88, w: 0.42, h: 0.42,
      fill: { color: n[0] },
    });
    s.addText(String(i + 1), {
      x: x + 0.28, y: 1.88, w: 0.42, h: 0.42,
      fontFace: FONT, fontSize: 16, bold: true, color: C.white,
      align: "center", valign: "middle", margin: 0, isTextBox: true,
    });
    s.addText(n[1], {
      x: x + 0.84, y: 1.9, w: 2.75, h: 0.42,
      fontFace: SERIF, fontSize: 18, bold: true, color: C.ink,
      margin: 0, isTextBox: true, valign: "middle",
    });
    s.addText(n[2], {
      x: x + 0.28, y: 2.55, w: 3.3, h: 1.95,
      fontFace: FONT, fontSize: 15, color: C.text,
      margin: 0, isTextBox: true,
    });
    if (i < 2) {
      s.addShape("rightArrow", {
        x: x + 3.9, y: 2.95, w: 0.28, h: 0.22,
        fill: { color: "C5CED6" },
      });
    }
  });

  const steps = [
    ["Чат", "задача по-русски"],
    ["Контекст", "правила и файлы"],
    ["POST", "localhost:1234"],
    ["Токены", "ответ с CPU"],
    ["Дифф", "кнопка View Changes"],
  ];
  steps.forEach((st, i) => {
    const x = 0.55 + i * 2.5;
    s.addShape("roundRect", {
      x, y: 5.15, w: 2.2, h: 1.45,
      fill: { color: i === 2 ? C.tealSoft : C.mist },
      rectRadius: 0.1,
    });
    s.addText(st[0], {
      x: x + 0.16, y: 5.32, w: 2.06, h: 0.4,
      fontFace: SERIF, fontSize: 18, bold: true, color: C.ink,
      margin: 0, isTextBox: true,
    });
    s.addText(st[1], {
      x: x + 0.16, y: 5.8, w: 2.06, h: 0.55,
      fontFace: FONT, fontSize: 14, color: C.muted,
      margin: 0, isTextBox: true,
    });
  });
  notes(s, "Пройти пальцем слева направо. Единственный сетевой шаг - HTTP на localhost. MCP и навыки, если они нужны, Cline запускает локальными процессами, это отдельный разговор с моделью, не выход в интернет.");
}

// ---------------------------------------------------------------------------
// 4. LM Studio
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  title(s, "LM Studio: сервер на localhost");
  kicker(s, "Вкладка Developer, пункт Local Server. На снимке 4 ноября статус был Running и Reachable.");

  card(s, 0.55, 1.6, 6.15, 5.15, C.mist);
  s.addText("Что было включено", {
    x: 0.82, y: 1.82, w: 5.6, h: 0.4,
    fontFace: SERIF, fontSize: 22, bold: true, color: C.ink,
    margin: 0, isTextBox: true,
  });
  const leftRows = [
    ["Статус", "Running, Reachable"],
    ["Модель в памяти", "qwen2.5-coder-7b-instruct"],
    ["Адрес", "http://127.0.0.1:1234"],
    ["Идентификатор API", "qwen2.5-coder-7b-instruct"],
    ["Контекст в карточке", "128K, на CPU лучше 16-32K"],
    ["Квантование", "Q4_K_M, 4,68 ГБ, домен code"],
  ];
  leftRows.forEach((r, i) => {
    const y = 2.42 + i * 0.66;
    s.addText(r[0], {
      x: 0.82, y, w: 2.15, h: 0.5,
      fontFace: FONT, fontSize: 14, color: C.muted,
      margin: 0, isTextBox: true, valign: "middle",
    });
    s.addText(r[1], {
      x: 3.0, y, w: 3.35, h: 0.5,
      fontFace: FONT, fontSize: 15, bold: true, color: C.ink,
      margin: 0, isTextBox: true, valign: "middle",
    });
  });

  card(s, 7.05, 1.6, 5.7, 5.15, C.ink);
  s.addText("Как убедиться, что сервер жив", {
    x: 7.22, y: 1.82, w: 5.25, h: 0.7,
    fontFace: SERIF, fontSize: 22, bold: true, color: C.white,
    margin: 0, isTextBox: true,
  });
  s.addText("В PowerShell, после Load и Start Server:", {
    x: 7.22, y: 2.65, w: 5.25, h: 0.4,
    fontFace: FONT, fontSize: 15, color: "D5DEE6",
    margin: 0, isTextBox: true,
  });
  s.addShape("roundRect", {
    x: 7.22, y: 3.2, w: 5.25, h: 1.15,
    fill: { color: "141C26" },
    rectRadius: 0.08,
  });
  s.addText("curl http://127.0.0.1:1234/v1/models", {
    x: 7.4, y: 3.4, w: 4.95, h: 0.75,
    fontFace: MONO, fontSize: 14, color: C.codeTx,
    margin: 0, isTextBox: true, valign: "middle",
  });
  s.addText("В ответе должно быть имя загруженной модели. Если соединение отклонено, Cline отвечать не начнет: клиент есть, сервера нет.", {
    x: 7.22, y: 4.55, w: 5.25, h: 1.8,
    fontFace: FONT, fontSize: 16, color: "D5DEE6",
    margin: 0, isTextBox: true,
  });
  notes(s, "Показать два состояния: модель скачана и модель загружена в память. Start Server без Load дает пустой список. Контекст 128K в карточке - это возможность файла. На CPU его лучше урезать, иначе каждый ответ раздувается по времени.");
}

// ---------------------------------------------------------------------------
// 5. Model numbers
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  title(s, "Модель, которая была в памяти");
  kicker(s, "Qwen2.5-Coder-7B-Instruct. Цифры скорости сняты с лога LM Studio 4 ноября 2026, около 12:50.");

  const stats = [
    ["7B", "параметров", "сборка Instruct, код"],
    ["4,68 ГБ", "файл на диске", "квантование Q4_K_M"],
    ["2,4", "токена в секунду", "72 токена, 475 мс на токен"],
    ["128K", "контекст файла", "на CPU держать 16-32K"],
  ];
  stats.forEach((st, i) => {
    const x = 0.55 + (i % 4) * 3.15;
    card(s, x, 1.6, 3.0, 2.55, i === 2 ? C.amberSoft : C.mist);
    s.addText(st[0], {
      x: x + 0.2, y: 1.78, w: 2.6, h: 0.7,
      fontFace: SERIF, fontSize: 32, bold: true, color: i === 2 ? C.amberDeep : C.ink,
      margin: 0, isTextBox: true,
    });
    s.addText(st[1], {
      x: x + 0.2, y: 2.5, w: 2.6, h: 0.4,
      fontFace: FONT, fontSize: 15, bold: true, color: C.ink,
      margin: 0, isTextBox: true,
    });
    s.addText(st[2], {
      x: x + 0.2, y: 3.0, w: 2.6, h: 0.8,
      fontFace: FONT, fontSize: 14, color: C.muted,
      margin: 0, isTextBox: true,
    });
  });

  card(s, 0.55, 4.4, 12.2, 2.25, C.tealSoft);
  s.addText("Что это значит на практике", {
    x: 0.82, y: 4.58, w: 11.6, h: 0.4,
    fontFace: SERIF, fontSize: 20, bold: true, color: C.tealDeep,
    margin: 0, isTextBox: true,
  });
  s.addText("Короткий ответ занимает десятки секунд, правка на несколько абзацев - минуты. Для показа схемы этого хватает. Для ежедневной разработки на таком CPU модель 7B тесная: она теряет нить задачи и называет методы, которых в платформе нет. Лицензия весов Qwen2.5-Coder - Apache 2.0. В карточке LM Studio архитектура файла указана как llama: так GGUF помечает семейство Qwen2.", {
    x: 0.82, y: 5.08, w: 11.6, h: 1.35,
    fontFace: FONT, fontSize: 16, color: C.text,
    margin: 0, isTextBox: true,
  });
  notes(s, "Задержаться на 2,4 токена в секунду. Это честный замер с этого ноутбука, не паспорт видеокарты. Отсюда все дальнейшие оговорки про качество диалога.");
}

// ---------------------------------------------------------------------------
// 6. Cline settings
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  title(s, "Настройки Cline");
  kicker(s, "Слева то, что записано в инструкции пилота. Справа то, что видно на снимке экрана.");

  card(s, 0.55, 1.55, 6.15, 4.55, C.mist);
  s.addText("Инструкция пилота", {
    x: 0.8, y: 1.74, w: 5.7, h: 0.4,
    fontFace: SERIF, fontSize: 20, bold: true, color: C.ink,
    margin: 0, isTextBox: true,
  });
  const guide = [
    ["API Provider", "LM Studio"],
    ["Base URL", "http://localhost:1234"],
    ["OpenAI Compatible", "http://localhost:1234/v1"],
    ["Context Window", "32768"],
    ["Enable Skills", "включено"],
    ["Compact Prompt", "включено, ради скорости"],
  ];
  guide.forEach((r, i) => {
    const y = 2.28 + i * 0.58;
    s.addText(r[0], {
      x: 0.8, y, w: 2.35, h: 0.46,
      fontFace: FONT, fontSize: 14, color: C.muted,
      margin: 0, isTextBox: true, valign: "middle",
    });
    s.addText(r[1], {
      x: 3.15, y, w: 3.25, h: 0.46,
      fontFace: FONT, fontSize: 15, bold: true, color: C.ink,
      margin: 0, isTextBox: true, valign: "middle",
    });
  });

  card(s, 7.05, 1.55, 5.7, 4.55, C.tealSoft);
  s.addText("На экране 4 ноября", {
    x: 7.2, y: 1.74, w: 5.3, h: 0.4,
    fontFace: SERIF, fontSize: 20, bold: true, color: C.tealDeep,
    margin: 0, isTextBox: true,
  });
  const seen = [
    ["Строка статуса", "wimfo @ qwen2.5-coder-7b-instruct"],
    ["Окно контекста", "128.0k, занято 3.0k"],
    ["Auto-approve", "Read, Edit, WebFetch, MCP"],
    ["После ответа", "кнопка View Changes"],
    ["Папка", "WIM_DEV"],
  ];
  seen.forEach((r, i) => {
    const y = 2.32 + i * 0.68;
    s.addText(r[0], {
      x: 7.2, y, w: 5.3, h: 0.26,
      fontFace: FONT, fontSize: 13, color: C.tealDeep,
      margin: 0, isTextBox: true,
    });
    s.addText(r[1], {
      x: 7.2, y: y + 0.26, w: 5.3, h: 0.32,
      fontFace: FONT, fontSize: 15, bold: true, color: C.ink,
      margin: 0, isTextBox: true,
    });
  });

  s.addText("Compact Prompt укорачивает системный текст и ускоряет 7B. Для проверки MCP его выключают: иначе инструкции инструментов могут не попасть в запрос. Телеметрию расширения в пилоте держат выключенной.", {
    x: 0.55, y: 6.28, w: 12.2, h: 0.75,
    fontFace: FONT, fontSize: 15, color: C.muted,
    margin: 0, isTextBox: true,
  });
  notes(s, "Честно сказать, что инструкция и снимок расходятся по контексту: в гайде 32K, на экране модель показывала 128K и занятые 3K. Auto-approve на пилоте был включен для чтения, правок, WebFetch и MCP. Для демонстрации коллегам автоподтверждение правок лучше выключить, чтобы было видно каждый шаг.");
}

// ---------------------------------------------------------------------------
// 7. Rules and skills
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  title(s, "Правила проекта и навыки");
  kicker(s, "Пустая модель не знает, как у нас принято писать 1С. Это дописывается файлами рядом с репозиторием.");

  card(s, 0.55, 1.58, 6.15, 5.15, C.amberSoft);
  s.addText(".clinerules", {
    x: 0.82, y: 1.78, w: 5.6, h: 0.32,
    fontFace: FONT, fontSize: 14, bold: true, color: C.amberDeep,
    margin: 0, isTextBox: true,
  });
  s.addText("Файл 01-pilot-local.md", {
    x: 0.82, y: 2.12, w: 5.6, h: 0.42,
    fontFace: SERIF, fontSize: 22, bold: true, color: C.ink,
    margin: 0, isTextBox: true,
  });
  const rules = [
    "Модель только локальная, порт 1234.",
    "Код остается на машине, во внешний API его не отправлять.",
    "Сигнатуры платформы сверять через MCP 1c-platform.",
    "Поиск по выгрузкам конфигураций - через code-index.",
    "BSL: PascalCase, ключевые слова Если, Тогда, КонецЕсли.",
  ];
  rules.forEach((line, i) => {
    const y = 2.75 + i * 0.72;
    s.addShape("ellipse", {
      x: 0.86, y: y + 0.06, w: 0.28, h: 0.28,
      fill: { color: C.amber },
    });
    s.addText(String(i + 1), {
      x: 0.86, y: y + 0.06, w: 0.28, h: 0.28,
      fontFace: FONT, fontSize: 11, bold: true, color: C.white,
      align: "center", valign: "middle", margin: 0, isTextBox: true,
    });
    s.addText(line, {
      x: 1.3, y, w: 5.05, h: 0.58,
      fontFace: FONT, fontSize: 15, color: C.text,
      margin: 0, isTextBox: true,
    });
  });

  card(s, 7.05, 1.58, 5.7, 5.15, C.mist);
  s.addText(".cline/skills", {
    x: 7.22, y: 1.78, w: 5.25, h: 0.32,
    fontFace: FONT, fontSize: 14, bold: true, color: C.tealDeep,
    margin: 0, isTextBox: true,
  });
  s.addText("Навыки, разложенные в репозитории", {
    x: 7.22, y: 2.12, w: 5.25, h: 0.7,
    fontFace: SERIF, fontSize: 22, bold: true, color: C.ink,
    margin: 0, isTextBox: true,
  });
  const skills = [
    ["epf-build, epf-validate", "сборка и проверка обработок"],
    ["form-info, form-validate", "формы"],
    ["meta-info", "состав объекта метаданных"],
    ["composing-1c-queries", "текст запроса"],
    ["1c-query-optimization", "разбор тяжелого запроса"],
  ];
  skills.forEach((sk, i) => {
    const y = 3.0 + i * 0.66;
    s.addText(sk[0], {
      x: 7.22, y, w: 5.25, h: 0.3,
      fontFace: FONT, fontSize: 15, bold: true, color: C.ink,
      margin: 0, isTextBox: true,
    });
    s.addText(sk[1], {
      x: 7.22, y: y + 0.28, w: 5.25, h: 0.28,
      fontFace: FONT, fontSize: 14, color: C.muted,
      margin: 0, isTextBox: true,
    });
  });
  notes(s, "Навык - это папка с SKILL.md. Cline подхватывает его, когда задача совпадает, и не кладет все инструкции в каждый запрос. На этом репозитории в .cline/skills лежат семь навыков по 1С. В диалоге со снимка модель до навыков и MCP по сути не дошла.");
}

// ---------------------------------------------------------------------------
// 8. Dialogue
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  title(s, "Диалог со снимка 4 ноября");
  kicker(s, "Один живой обмен в чате Cline. Модель qwen2.5-coder-7b-instruct, контекст на экране 128K, занято 3K.");

  const bubbles = [
    [C.tealSoft, C.tealDeep, "Вы", "Ты можешь использовать MCP сервера 1С?"],
    [C.mist, C.ink, "Модель", "Ушла в английский план: создать файл скрипта и сохранить его в каталог. На вопрос про MCP прямо не ответила."],
    [C.tealSoft, C.tealDeep, "Вы", "Отвечай по-русски, так что у нас получилось?"],
    [C.amberSoft, C.amberDeep, "Модель, статус COMPLETED", "Запрос понят. Создает простую внешнюю обработку, которая выводит в консоль строку \"Привет, мир\"."],
  ];
  bubbles.forEach((b, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.5 + col * 6.4;
    const y = 1.58 + row * 2.6;
    card(s, x, y, 6.05, 2.4, b[0]);
    s.addText(b[2], {
      x: x + 0.28, y: y + 0.22, w: 5.6, h: 0.36,
      fontFace: FONT, fontSize: 14, bold: true, color: b[1],
      margin: 0, isTextBox: true,
    });
    s.addText(b[3], {
      x: x + 0.28, y: y + 0.7, w: 5.6, h: 1.4,
      fontFace: FONT, fontSize: 18, color: C.text,
      margin: 0, isTextBox: true,
    });
  });
  notes(s, "Читать по порядку: вопрос, мимо, уточнение, ответ про обработку. Это сильная сторона слайда: видно и то, что цепочка живая, и то, что 7B на первом вопросе про MCP не справилась. Не приукрашивать.");
}

// ---------------------------------------------------------------------------
// 9. Code
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  title(s, "Что модель показала в чате");
  kicker(s, "Текст процедуры со снимка. Рядом - что с ним не так, если сверить с платформой.");

  s.addShape("roundRect", {
    x: 0.55, y: 1.58, w: 6.3, h: 5.15,
    fill: { color: C.codeBg },
    rectRadius: 0.12,
  });
  s.addText("Процедура из ответа", {
    x: 0.82, y: 1.78, w: 5.8, h: 0.36,
    fontFace: FONT, fontSize: 14, color: "9FB0BE",
    margin: 0, isTextBox: true,
  });
  s.addText("Процедура Запуск(Отчет)\n    Отчет.ДобавитьСтроку(\"Привет, мир!\");\nКонецПроцедуры", {
    x: 0.82, y: 2.4, w: 5.75, h: 2.2,
    fontFace: MONO, fontSize: 16, color: C.codeTx,
    margin: 0, isTextBox: true,
  });
  s.addText("Дальше в том же ответе модель напечатала XML внешней обработки с именем ПриветМир и предложила сохранить файл в каталог обработок вручную.", {
    x: 0.82, y: 4.55, w: 5.75, h: 1.8,
    fontFace: FONT, fontSize: 15, color: "C5D2DC",
    margin: 0, isTextBox: true,
  });

  const remarks = [
    ["Похоже на BSL", "Скобки, КонецПроцедуры и строка в кавычках выглядят узнаваемо. Для показа новичку этого уже достаточно, чтобы увидеть формат."],
    ["Метод выдуман", "У объекта отчета нет ДобавитьСтроку. Сообщение пользователю в платформе пишется через Сообщить()."],
    ["Файл не собран", "XML ушел текстом в чат. Кнопка View Changes на экране была, но готовой обработки из этого ответа не получилось."],
  ];
  remarks.forEach((r, i) => {
    const y = 1.58 + i * 1.78;
    card(s, 7.05, y, 5.7, 1.48, i === 1 ? C.amberSoft : C.mist);
    s.addText(r[0], {
      x: 7.28, y: y + 0.16, w: 5.25, h: 0.36,
      fontFace: SERIF, fontSize: 18, bold: true, color: C.ink,
      margin: 0, isTextBox: true,
    });
    s.addText(r[1], {
      x: 7.28, y: y + 0.56, w: 5.25, h: 0.9,
      fontFace: FONT, fontSize: 14, color: C.text,
      margin: 0, isTextBox: true,
    });
  });
  notes(s, "Это главный учебный момент. Модель 7B имитирует синтаксис и спокойно называет несуществующий метод. Отсюда правило пилота: сигнатуры сверять через синтакс-помощник, а не принимать ответ как есть. Сообщить() - правильная замена для этой задачи.");
}

// ---------------------------------------------------------------------------
// 10. Screenshot
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  title(s, "Экран в момент этого ответа");
  kicker(s, "Слева VS Code с чатом Cline, справа LM Studio со статусом Running. Тот же диалог, что на предыдущих слайдах.");

  const imgH = 5.35;
  const imgW = imgH * (1910 / 1027);
  const imgX = (13.3 - imgW) / 2;
  s.addImage({
    path: "c:/1c/Cursor_1c/WIM_DEV/drafts/local_llm_cline/ПримерРаботыНаНоуте.png",
    x: imgX, y: 1.52, w: imgW, h: imgH,
  });
  notes(s, "Дать людям несколько секунд посмотреть снимок. Слева зеленый блок COMPLETED и кнопка View Changes. Справа Loaded Models: qwen2.5-coder-7b-instruct, адрес 127.0.0.1:1234, в логе Finished streaming. Если текст на проекторе мелкий, предыдущие два слайда уже содержат расшифровку.");
}

// ---------------------------------------------------------------------------
// 11. What the pilot shows
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  title(s, "Для чего этого пилота хватает");
  kicker(s, "Схема рабочая. Ежедневным инструментом разработчика она на этом железе еще не стала.");

  const cells = [
    [C.tealSoft, C.tealDeep, "Показать цепочку", "Коллега видит, что чат в VS Code ходит в локальный сервер, а сервер отвечает моделью с диска. Облачный ключ для этого не нужен."],
    [C.tealSoft, C.tealDeep, "Поймать слабый ответ", "Диалог про MCP это и показал: модель сменила язык, проигнорировала вопрос и выдумала метод. На 7B так бывает часто."],
    [C.amberSoft, C.amberDeep, "Скорость CPU", "2,4 токена в секунду. Несколько шагов агента - это минуты. Ждать такой темп в обычной задаче утомительно."],
    [C.amberSoft, C.amberDeep, "Граница пилота", "Один ноутбук и одна модель в памяти. Для отдела нужен отдельный разговор: GPU, модель крупнее, общий сервер."],
  ];
  cells.forEach((c, i) => {
    const x = 0.5 + (i % 2) * 6.4;
    const y = 1.58 + Math.floor(i / 2) * 2.65;
    card(s, x, y, 6.05, 2.3, c[0]);
    s.addText(c[2], {
      x: x + 0.28, y: y + 0.22, w: 5.6, h: 0.42,
      fontFace: SERIF, fontSize: 22, bold: true, color: c[1],
      margin: 0, isTextBox: true,
    });
    s.addText(c[3], {
      x: x + 0.28, y: y + 0.78, w: 5.6, h: 1.35,
      fontFace: FONT, fontSize: 16, color: C.text,
      margin: 0, isTextBox: true,
    });
  });
  notes(s, "Не обещать, что 7B заменит Cursor. Пилот доказывает другое: контур собирается на обычном ноутбуке, код остается локально, и качество ответа видно сразу. Дальше разговор про видеокарту и модель крупнее.");
}

// ---------------------------------------------------------------------------
// 12. Repeat
// ---------------------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.ink };
  s.addText("ПОВТОРИТЬ НА ДРУГОМ КОМПЬЮТЕРЕ", {
    x: 0.7, y: 0.42, w: 12, h: 0.3,
    fontFace: FONT, fontSize: 13, bold: true, color: C.amber,
    margin: 0, isTextBox: true, charSpacing: 1.2,
  });
  s.addText("Четыре шага, и чат отвечает локально", {
    x: 0.7, y: 0.82, w: 12, h: 0.55,
    fontFace: SERIF, fontSize: 32, bold: true, color: C.white,
    margin: 0, isTextBox: true,
  });

  const steps = [
    ["1", "LM Studio", "Скачать qwen2.5-coder-7b-instruct в квантовании Q4_K_M. Load, затем Start Server."],
    ["2", "Проверка", "curl http://127.0.0.1:1234/v1/models. В списке должно быть имя модели."],
    ["3", "Cline", "В VS Code провайдер LM Studio, адрес http://localhost:1234, окно контекста 32768."],
    ["4", "Репозиторий", "Открыть WIM_DEV. Правила лежат в .clinerules, навыки в .cline/skills."],
  ];
  steps.forEach((st, i) => {
    const y = 1.65 + i * 1.15;
    s.addShape("ellipse", {
      x: 0.7, y: y + 0.12, w: 0.48, h: 0.48,
      fill: { color: C.amber },
    });
    s.addText(st[0], {
      x: 0.7, y: y + 0.12, w: 0.48, h: 0.48,
      fontFace: FONT, fontSize: 16, bold: true, color: C.ink,
      align: "center", valign: "middle", margin: 0, isTextBox: true,
    });
    s.addText(st[1], {
      x: 1.4, y: y, w: 2.5, h: 0.7,
      fontFace: SERIF, fontSize: 20, bold: true, color: C.white,
      margin: 0, isTextBox: true, valign: "middle",
    });
    s.addText(st[2], {
      x: 4.0, y: y, w: 8.5, h: 0.75,
      fontFace: FONT, fontSize: 16, color: "D5DEE6",
      margin: 0, isTextBox: true, valign: "middle",
    });
  });
  s.addText("Модель считает на этой машине. Запросы остаются на localhost.", {
    x: 0.7, y: 6.45, w: 12, h: 0.4,
    fontFace: SERIF, fontSize: 18, color: C.amber,
    margin: 0, isTextBox: true,
  });
  notes(s, "Откат, если спросят: скрипт uninstall_local_llm_pilot.ps1 снимает LM Studio, модель, Cline и папки .cline и .clinerules пилота. Cursor он не трогает. Завершить фразой: модель считает на этой машине, облако в схеме не участвует.");
}

pres.writeFile({ fileName: "c:/1c/Cursor_1c/WIM_DEV/drafts/local_llm_cline/local_ai_on_laptop.pptx" })
  .then(() => console.log("wrote deck"))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
