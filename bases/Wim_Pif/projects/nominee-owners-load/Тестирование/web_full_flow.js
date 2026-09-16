const seedPath = 'C:\\1c\\Cursor_1c\\WIM_DEV\\bases\\Wim_Pif\\projects\\nominee-owners-load\\Тестирование\\reports\\web_seed.json';
const seed = JSON.parse(readFileSync(seedPath, 'utf8'));
const EPF = seed.epf || 'C:\\1c\\Cursor_1c\\WIM_DEV\\bases\\Wim_Pif\\projects\\nominee-owners-load\\build\\NomineeOwnersLoad.epf';

function names(items) {
  return (items || []).map(x => (typeof x === 'string' ? x : (x.name || x.title || x.label || '')));
}

const form = await openFile(EPF);
const buttons = names(form.buttons);
const fields = names(form.fields);
const hasRead = buttons.some(b => String(b).indexOf('Прочитать') >= 0);
const hasMatch = buttons.some(b => String(b).indexOf('Сопоставить') >= 0);
const hasFund = fields.some(f => String(f).indexOf('Фонд') >= 0);
console.log('OPEN title=' + form.title + ' formCount=' + form.formCount);
console.log('BUTTONS=' + JSON.stringify(buttons));
console.log('FIELDS=' + JSON.stringify(fields));
console.log('WEB_FORM_OK=' + (hasRead && hasMatch && hasFund));

let emptyOk = false;
try {
  const st = await clickElement('Сопоставить');
  const msg = JSON.stringify(st.errorModal || st.modal || st.texts || st);
  emptyOk = msg.indexOf('прочитайте') >= 0 || msg.indexOf('Прочитайте') >= 0 || msg.indexOf('файл') >= 0;
  console.log('EMPTY_MATCH=' + msg.slice(0, 800));
} catch (e) {
  const t = String(e);
  emptyOk = t.indexOf('прочитайте') >= 0 || t.indexOf('файл') >= 0;
  console.log('EMPTY_MATCH_ERR=' + t.slice(0, 800));
}
console.log('WEB_EMPTY_MATCH_OK=' + emptyOk);

try {
  await selectValue('Фонд', seed.fund);
  console.log('FUND_OK=' + seed.fund);
} catch (e) {
  console.log('FUND_ERR=' + e);
}

try {
  await selectValue('Номинальный держатель', seed.nominee);
  console.log('NOMINEE_OK=' + seed.nominee);
} catch (e) {
  console.log('NOMINEE_ERR=' + e);
}

const page = getPage();
let fileOk = false;
try {
  const chooserP = page.waitForEvent('filechooser', { timeout: 20000 });
  await clickElement('Выбрать файл');
  const dlg = await page.waitForSelector('#fileSelectDialogOk', { timeout: 8000 }).catch(() => null);
  if (dlg) {
    try {
      await page.click('a.underline.pointer');
    } catch (e) {
      console.log('DISK_LINK: ' + e);
    }
  }
  const chooser = await chooserP;
  await chooser.setFiles(seed.xlsx);
  await wait(1);
  if (dlg) {
    await page.click('#fileSelectDialogOk');
  }
  await wait(4);
  fileOk = true;
  console.log('FILE_DIALOG_OK');
} catch (e) {
  console.log('FILE_DIALOG_ERR=' + e);
}

let afterRead = await getFormState();
let table = null;
try {
  table = await readTable();
} catch (e) {
  console.log('readTable after file: ' + e);
}
console.log('AFTER_FILE title=' + afterRead.title + ' totals=' + JSON.stringify(afterRead.texts || null));
console.log('ROWS_AFTER_FILE=' + JSON.stringify(table).slice(0, 2500));
const rowCount = (table && (table.total || (table.rows || []).length)) || 0;
console.log('WEB_READ_OK=' + (rowCount >= 1));

if (rowCount >= 1) {
  try {
    await clickElement('Сопоставить');
    await wait(4);
  } catch (e) {
    console.log('MATCH_CLICK=' + e);
  }
}

const afterMatch = await getFormState();
const fieldVals = (afterMatch.fields || []).map(f => ({
  name: f.name || f.label,
  value: f.value
}));
console.log('AFTER_MATCH_FIELDS=' + JSON.stringify(fieldVals));
console.log('AFTER_MATCH_TABS=' + JSON.stringify(afterMatch.tabs));

try {
  await clickElement('Строки файла');
  await wait(1);
} catch (e) {
  console.log('ROWS_TAB=' + e);
}

let rowsAfter = null;
try {
  rowsAfter = await readTable({ table: 'СтрокиФайла' });
} catch (e) {
  try {
    rowsAfter = await readTable();
  } catch (e2) {
    console.log('readTable rows: ' + e2);
  }
}
console.log('ROWS_AFTER_MATCH=' + JSON.stringify(rowsAfter).slice(0, 3000));

const row0 = (rowsAfter && rowsAfter.rows && rowsAfter.rows[0]) || {};
const way = String(row0['Способ'] || '');
const card = String(row0['Карточка'] || '');
const nrdCol = String(row0['НРД id файла'] || '');
const matchOk = way.indexOf('НРД') >= 0 && card.length > 0;
console.log('WEB_MATCH_WAY=' + way);
console.log('WEB_MATCH_CARD=' + card);
console.log('WEB_MATCH_OK=' + matchOk);
console.log('WEB_SEED_NRD=' + seed.nrd + ' FILE_NRD=' + nrdCol);

try {
  await clickElement('Протокол');
  await wait(1);
  const proto = await readTable();
  console.log('PROTO=' + JSON.stringify(proto).slice(0, 1500));
} catch (e) {
  console.log('PROTO_TAB=' + e);
}
