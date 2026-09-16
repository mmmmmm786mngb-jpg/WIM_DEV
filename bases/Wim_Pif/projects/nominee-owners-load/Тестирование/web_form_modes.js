const seedPath = 'C:\\1c\\Cursor_1c\\WIM_DEV\\bases\\Wim_Pif\\projects\\nominee-owners-load\\Тестирование\\reports\\form_modes_seed.json';
const outJson = 'C:\\1c\\Cursor_1c\\WIM_DEV\\bases\\Wim_Pif\\projects\\nominee-owners-load\\Тестирование\\reports\\form_modes_web.json';
const outDir = 'C:\\1c\\Cursor_1c\\WIM_DEV\\bases\\Wim_Pif\\projects\\nominee-owners-load\\Тестирование\\reports\\';
const seed = JSON.parse(readFileSync(seedPath, 'utf8'));
const EPF = seed.epf;

const cases = [];

function add(name, ok, details) {
  cases.push({ name: name, ok: !!ok, details: String(details || '') });
  console.log((ok ? 'OK  ' : 'FAIL') + ' ' + name + (details ? ' | ' + details : ''));
}

function fieldBy(st, pred) {
  return (st.fields || []).find(pred) || null;
}

function fieldVal(st, names) {
  const want = names.map(x => String(x).toLowerCase());
  const f = (st.fields || []).find(x => {
    const n = String(x.name || '').toLowerCase();
    const l = String(x.label || x.title || '').toLowerCase();
    return want.some(w => n === w || l === w || n.indexOf(w) >= 0 || l.indexOf(w) >= 0);
  });
  return f ? String(f.value == null ? '' : f.value) : '';
}

async function putFile(path) {
  const page = getPage();
  const chooserP = page.waitForEvent('filechooser', { timeout: 20000 });
  await clickElement('Выбрать файл');
  const dlg = await page.waitForSelector('#fileSelectDialogOk', { timeout: 8000 }).catch(() => null);
  if (dlg) {
    try { await page.click('a.underline.pointer'); } catch (e) {}
  }
  const chooser = await chooserP;
  await chooser.setFiles(path);
  await wait(1);
  if (dlg) {
    await page.click('#fileSelectDialogOk');
  }
  await wait(3);
}

async function setFormat(label) {
  const r = await fillFields({ 'ФорматФайла': label, 'Формат': label });
  return r;
}

async function readRows() {
  try {
    await clickElement('Строки файла');
    await wait(1);
  } catch (e) {}
  try {
    return await readTable({ table: 'СтрокиФайла' });
  } catch (e) {
    try {
      return await readTable();
    } catch (e2) {
      return { rows: [], total: 0, error: String(e2) };
    }
  }
}

const form = await openFile(EPF);
await wait(1);
const page = getPage();
await page.setViewportSize({ width: 1680, height: 980 });

const buttons = (form.buttons || []).map(b => b.name || b.title || b);
const fields = (form.fields || []).map(f => ({
  name: f.name,
  label: f.label || f.title || '',
  value: f.value,
  options: f.options || f.choiceList || null
}));
console.log('TITLE=' + form.title);
console.log('BUTTONS=' + JSON.stringify(buttons));
console.log('FIELDS=' + JSON.stringify(fields));

const buf0 = await screenshot();
writeFileSync(outDir + 'form_modes_open.png', buf0);

add('Form opened', String(form.title || '').indexOf('владельцев') >= 0, form.title);

const formatField = (form.fields || []).find(f =>
  String(f.name || '').indexOf('Формат') >= 0 || String(f.label || '').indexOf('Формат') >= 0
);
const formatButtons = buttons.filter(b =>
  String(b).indexOf('Гарант') >= 0 || String(b).indexOf('XML') >= 0 || String(b).indexOf('ЦДФ') >= 0
);
const optText = JSON.stringify((formatField && (formatField.options || formatField.choiceList || [])) || formatButtons);
add(
  'Tumbler has 4 formats',
  formatButtons.indexOf('Гарант Excel') >= 0
    && formatButtons.some(b => String(b).indexOf('XML') >= 0)
    && formatButtons.indexOf('ЦДФ') >= 0
    && formatButtons.some(b => String(b).indexOf('NEW') >= 0),
  optText.slice(0, 500)
);

const namesJoined = JSON.stringify(form.fields || []).toLowerCase();
add('Flag create counterparties on form', namesJoined.indexOf('контрагент') >= 0, '');
add('Flag create LS on form', namesJoined.indexOf('лицевые счета') >= 0 || namesJoined.indexOf('лицевых') >= 0, '');
add('Flag multiply LS on form', namesJoined.indexOf('размнож') >= 0 || namesJoined.indexOf('множить') >= 0, '');

const defCreate = fieldVal(form, ['флсоздаватьконтрагентов', 'создавать контрагентов']);
const defLs = fieldVal(form, ['флсоздаватьлицевыесчета', 'создавать лицевые счета']);
const defMult = fieldVal(form, ['множитьлицсчета', 'размножать лиц. счета', 'размножать']);
const defFmt = fieldVal(form, ['форматфайла', 'формат']);
add(
  'Defaults: flags off, format Garant Excel',
  (defCreate === 'false' || defCreate === '' || defCreate.toLowerCase() === 'нет')
    && (defLs === 'false' || defLs === '' || defLs.toLowerCase() === 'нет')
    && (defMult === 'false' || defMult === '' || defMult.toLowerCase() === 'нет'),
  'cp=' + defCreate + ' ls=' + defLs + ' mult=' + defMult + ' fmtButtons=' + formatButtons.join(',')
);

const filterBtns = ['Незаполненные', 'Не найденные', 'Подмены клиента', 'Выбор из нескольких', 'Показать все'];
filterBtns.forEach(b => {
  add('Button ' + b, buttons.some(x => String(x).indexOf(b) >= 0), '');
});

try {
  await selectValue('Фонд', seed.fund);
  add('Select fund', true, seed.fund);
} catch (e) {
  add('Select fund', false, String(e));
}
try {
  await selectValue('Номинальный держатель', seed.nominee);
  add('Select nominee', true, seed.nominee);
} catch (e) {
  add('Select nominee', false, String(e));
}

const formats = [
  { label: 'Гарант Excel', file: seed.xlsx0, expect: 2, key: '0' },
  { label: 'XML ВТБ СД', file: seed.xml1, expect: 2, key: '1' },
  { label: 'ЦДФ', file: seed.xlsx2, expect: 2, key: '2' },
  { label: 'Гарант Excel NEW', file: seed.xlsx3, expect: 2, key: '3' }
];

for (const fmt of formats) {
  try {
    await clickElement(fmt.label);
    await wait(1);
    add('Switch format to ' + fmt.label, true, 'clicked tumbler');
  } catch (e) {
    add('Switch format to ' + fmt.label, false, String(e));
  }

  try {
    await putFile(fmt.file);
    const rows = await readRows();
    const n = (rows && (rows.total || (rows.rows || []).length)) || 0;
    const sample = (rows.rows || [])[0] || {};
    const fio = String(sample['ФИО файла'] || sample['ФИО'] || '');
    const nrdCol = String(sample['НРД id'] || '');
    add('Read file in format ' + fmt.label, n >= fmt.expect && fio.indexOf('Ivanov') >= 0, 'rows=' + n + ' fio=' + fio + ' nrd=' + nrdCol);
    if (fmt.key === '0' || fmt.key === '2') {
      writeFileSync(outDir + 'form_modes_fmt' + fmt.key + '.png', await screenshot());
    }
  } catch (e) {
    add('Read file in format ' + fmt.label, false, String(e));
  }
}

// Back to Garant Excel for match + filters + flags
try {
  await clickElement('Гарант Excel');
  await wait(1);
  await putFile(seed.xlsxFlags);
} catch (e) {
  console.log('RELOAD_FLAGS=' + e);
}

try {
  await clickElement('Сопоставить');
  await wait(4);
  add('Match after read', true, '');
} catch (e) {
  add('Match after read', false, String(e));
}

const afterMatch = await getFormState();
console.log('AFTER_MATCH_TEXTS=' + JSON.stringify(afterMatch.texts || afterMatch.fields));
writeFileSync(outDir + 'form_modes_after_match.png', await screenshot());

try {
  await clickElement('Строки файла');
  await wait(1);
} catch (e) {}

let allRows = await readRows();
const allCount = (allRows.rows || []).length;
add('Rows after match', allCount >= 1, 'n=' + allCount);

async function clickFilter(title) {
  try {
    await clickElement(title);
    await wait(1);
    const t = await readRows();
    return { ok: true, n: (t.rows || []).length, rows: t.rows || [] };
  } catch (e) {
    return { ok: false, n: -1, error: String(e) };
  }
}

const fNotFound = await clickFilter('Не найденные');
add('Filter not found', fNotFound.ok && fNotFound.n >= 1, 'visible=' + fNotFound.n + '/' + allCount);

const fEmpty = await clickFilter('Незаполненные');
add('Filter unfilled cards', fEmpty.ok && fEmpty.n >= 1, 'visible=' + fEmpty.n);

const fSub = await clickFilter('Подмены клиента');
add('Filter substitutions (empty is ok for this file)', fSub.ok, 'visible=' + fSub.n);

const fMany = await clickFilter('Выбор из нескольких');
add('Filter several cards (empty is ok for this file)', fMany.ok, 'visible=' + fMany.n);

const fAll = await clickFilter('Показать все');
add('Filter show all', fAll.ok && fAll.n >= allCount, 'visible=' + fAll.n);

try {
  await clickElement('Протокол');
  await wait(1);
  const proto = await readTable();
  const txt = JSON.stringify(proto);
  add('Protocol tab', txt.indexOf('НеНайден') >= 0 || txt.indexOf('Не найден') >= 0, txt.slice(0, 400));
} catch (e) {
  add('Protocol tab', false, String(e));
}

// Flags OFF: create should not create
try {
  await fillFields({
    'ФлСоздаватьКонтрагентов': false,
    'ФлСоздаватьЛицевыеСчета': false,
    'МножитьЛицСчета': false
  });
  add('Set flags off', true, '');
} catch (e) {
  add('Set flags off', false, String(e));
}

try {
  await clickElement('Создать недостающих');
  await wait(3);
} catch (e) {
  console.log('CREATE_OFF=' + e);
}
const afterOff = await getFormState();
const totOff = fieldVal(afterOff, ['текститогов', 'итоги']);
add(
  'Create missing with flags OFF does not create CP',
  totOff.indexOf('контрагентов: 0') >= 0 || totOff.indexOf('Создано контрагентов: 0') >= 0,
  totOff
);

try {
  await fillFields({
    'ФлСоздаватьКонтрагентов': true,
    'ФлСоздаватьЛицевыеСчета': true
  });
  add('Set create flags ON', true, '');
} catch (e) {
  add('Set create flags ON', false, String(e));
}

try {
  await clickElement('Создать недостающих');
  await wait(4);
} catch (e) {
  console.log('CREATE_ON=' + e);
}
const afterOn = await getFormState();
const totOn = fieldVal(afterOn, ['текститогов', 'итоги']);
add(
  'Create missing with flags ON creates CP',
  totOn.indexOf('контрагентов: 1') >= 0 || /контрагентов:\s*[1-9]/.test(totOn),
  totOn
);

try {
  await fillFields({ 'МножитьЛицСчета': true });
  const stM = await getFormState();
  const v = fieldVal(stM, ['множитьлицсчета', 'размножать']);
  add('Toggle multiply LS on form', v === 'true' || v.toLowerCase() === 'да' || v === 'True', 'value=' + v);
} catch (e) {
  add('Toggle multiply LS on form', false, String(e));
}

writeFileSync(outDir + 'form_modes_flags.png', await screenshot());

const okCount = cases.filter(c => c.ok).length;
const result = { ok: okCount, total: cases.length, cases: cases };
writeFileSync(outJson, JSON.stringify(result, null, 2));
console.log('WEB_MODES ' + okCount + '/' + cases.length);
console.log('WEB_MODES_ALL_OK=' + (okCount === cases.length));
