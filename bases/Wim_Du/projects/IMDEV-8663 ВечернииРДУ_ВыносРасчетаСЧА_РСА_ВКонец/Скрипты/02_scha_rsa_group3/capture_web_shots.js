// Capture 1C web-client screenshots for IM86632 test report.
// Globals: screenshot, navigateLink, filterList, clickElement, getFormState,
// closeForm, highlight, unhighlight, showCaption, hideCaption, wait,
// writeFileSync, readFileSync, readTable.

const SHOT_DIR = "bases/Wim_Du/projects/IMDEV-8663 ВечернииРДУ_ВыносРасчетаСЧА_РСА_ВКонец/Тестирование/reports/web_shots";
const TARGETS_PATH = SHOT_DIR + "/targets.json";

function loadTargets() {
  const raw = readFileSync(TARGETS_PATH, "utf8");
  return JSON.parse(raw);
}

async function saveShot(name) {
  const png = await screenshot();
  const path = SHOT_DIR + "/" + name + ".png";
  writeFileSync(path, png);
  console.log("SHOT " + name + " bytes=" + png.length);
  return path;
}

async function tryClose() {
  try {
    await closeForm();
  } catch (e) {
    console.log("closeForm skip: " + e.message);
  }
}

async function caption(text) {
  await showCaption(text, { position: "top", fontSize: 20, speech: false });
}

const targets = loadTargets();
console.log("targets keys=" + Object.keys(targets).join(","));

// 1. Groups 2 and 3 in operation kinds
await navigateLink("Справочник.ВидыОперацийЗакрытияПериода");
await wait(1);
try {
  await filterList('2. "Вечерние"');
} catch (e) {
  console.log("filter group2: " + e.message);
  try { await filterList("Вечерние"); } catch (e2) { console.log("filter evening: " + e2.message); }
}
await wait(1);
await caption('Группа 2. "Вечерние" операции в видах операций закрытия периода');
await saveShot("01_group2_kinds");
await hideCaption();
try { await unfilterList(); } catch (e) { console.log("unfilter: " + e.message); }
try {
  await filterList("Расчет СЧА");
} catch (e) {
  console.log("filter group3: " + e.message);
}
await wait(1);
await caption('Группа 3. "Расчет СЧА/РСА" в видах операций закрытия периода');
await saveShot("02_group3_kinds");
await hideCaption();
await tryClose();

// 2. Plans list for test date
await navigateLink("Документ.ПланРегламентныхОперацийДУ");
await wait(1);
try {
  await filterList("15.03.2027");
} catch (e) {
  console.log("filter plans date: " + e.message);
}
await wait(1);
const listState = await getFormState();
console.log("plans list title=" + listState.title + " rows=" + (listState.table && listState.table.rowCount));
await caption("Список планов регламентных операций за тестовую дату 15.03.2027");
await saveShot("03_plans_list_20270315");
await hideCaption();

// 3. Open group 3 plan
if (targets.plan_g3 && targets.plan_g3.nav) {
  await navigateLink(targets.plan_g3.nav);
  await wait(1.5);
} else {
  try {
    await clickElement({ row: 0, column: "Номер" }, { dblclick: true });
  } catch (e) {
    console.log("open plan row0: " + e.message);
  }
  await wait(1.5);
}
let form = await getFormState();
console.log("plan form title=" + form.title);
console.log("plan fields=" + JSON.stringify((form.fields || []).map(f => ({ n: f.name, l: f.label, v: f.value }))));
try {
  await highlight("План вечерних операций");
} catch (e) {
  console.log("highlight evening: " + e.message);
}
await caption("План группы 3: реквизит «План вечерних операций» заполнен из группы 2");
await saveShot("04_plan_group3_evening_link");
await hideCaption();
try { await unhighlight(); } catch (e) {}
await tryClose();

// 4. Open group 2 plan if available
if (targets.plan_g2 && targets.plan_g2.nav) {
  await navigateLink(targets.plan_g2.nav);
  await wait(1.5);
  form = await getFormState();
  console.log("plan2 title=" + form.title);
  await caption("План группы 2. Вечерние операции — основание для связки с группой 3");
  await saveShot("05_plan_group2");
  await hideCaption();
  await tryClose();
}

// 5. SCHA document
if (targets.scha && targets.scha.nav) {
  await navigateLink(targets.scha.nav);
} else {
  await navigateLink("Документ.РасчетСЧА_РСА");
  await wait(1);
  try { await filterList("15.03.2027"); } catch (e) { console.log("filter scha: " + e.message); }
  await wait(1);
  try { await clickElement({ row: 0, column: "Номер" }, { dblclick: true }); } catch (e) { console.log("open scha: " + e.message); }
}
await wait(1.5);
form = await getFormState();
console.log("scha title=" + form.title);
console.log("scha fields=" + JSON.stringify((form.fields || []).map(f => ({ n: f.name, l: f.label, v: f.value }))));
try { await highlight("План вечерних операций"); } catch (e) { console.log("highlight scha evening: " + e.message); }
await caption("Документ «Расчет СЧА/РСА»: план вечерних операций с основания группы 3");
await saveShot("06_scha_evening_plan");
await hideCaption();
try { await unhighlight(); } catch (e) {}
await tryClose();

// 6. Period form
if (targets.period && targets.period.nav) {
  await navigateLink(targets.period.nav);
} else {
  await navigateLink("Справочник.РегламентныеПериоды");
  await wait(1);
  try { await filterList("15.03.2027"); } catch (e) { console.log("filter period: " + e.message); }
  await wait(1);
  try { await clickElement({ row: 0 }, { dblclick: true }); } catch (e) { console.log("open period: " + e.message); }
}
await wait(1.5);
form = await getFormState();
console.log("period title=" + form.title);
console.log("period fields=" + JSON.stringify((form.fields || []).map(f => ({ n: f.name, l: f.label, v: f.value }))));
console.log("period buttons=" + JSON.stringify((form.buttons || []).map(b => b.name || b.title || b)));
await caption("Регламентный период 15.03.2027. Отмена гасит родителя, порции IM8663_ дорабатывают договор");
await saveShot("07_period_form");
await hideCaption();
await tryClose();

console.log("DONE");
