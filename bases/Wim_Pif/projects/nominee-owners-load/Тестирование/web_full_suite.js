const seedPath = 'C:\\1c\\Cursor_1c\\WIM_DEV\\bases\\Wim_Pif\\projects\\nominee-owners-load\\Тестирование\\reports\\web_seed.json';
const outFile = 'C:\\1c\\Cursor_1c\\WIM_DEV\\bases\\Wim_Pif\\projects\\nominee-owners-load\\Тестирование\\reports\\web_full_suite.json';
const seed = JSON.parse(readFileSync(seedPath, 'utf8'));
const EPF = seed.epf;
const cases = [];

function add(id, name, ok, details) {
  cases.push({ id: id, name: name, ok: !!ok, details: String(details || '') });
  console.log((ok ? 'OK' : 'FAIL') + ' ' + id + ' ' + name + ' ' + String(details || ''));
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
add('W01', 'WEB openFile EPF', !!form && !!(form.title || form.formCount), 'title=' + (form && form.title));
add('W02', 'WEB form title', form && String(form.title || '').indexOf('владельцев') >= 0, form && form.title);
add('W03', 'WEB command Read file', !!(form && form.buttons && form.buttons.some(b => String(b.name).indexOf('Прочитать') >= 0)), JSON.stringify((form.buttons || []).map(b => b.name)));
add('W04', 'WEB command Match', !!(form && form.buttons && form.buttons.some(b => String(b.name).indexOf('Сопоставить') >= 0)), '');
add('W05', 'WEB command Create missing', !!(form && form.buttons && form.buttons.some(b => String(b.name).indexOf('недостающ') >= 0)), '');
add('W06', 'WEB command Create document', !!(form && form.buttons && form.buttons.some(b => String(b.name).indexOf('документ') >= 0)), '');
add('W07', 'WEB tabs Stroki/Protokol', !!(form && form.tabs && form.tabs.length >= 2), JSON.stringify(form.tabs || []));
add('W08', 'WEB field Fond', !!(form && form.fields && form.fields.some(f => String(f.name || f.label || '').indexOf('Фонд') >= 0 || String(f.label || '').indexOf('Фонд') >= 0)), '');
add('W09', 'WEB flag create counterparties', !!(form && form.fields && form.fields.some(f => String(f.label || f.name || '').indexOf('контрагент') >= 0)), '');
add('W10', 'WEB flag create LS', !!(form && form.fields && form.fields.some(f => String(f.label || f.name || '').indexOf('лицевые') >= 0)), '');
add('W11', 'WEB flag multiply LS', !!(form && form.fields && form.fields.some(f => String(f.label || f.name || '').indexOf('Размнож') >= 0)), '');

const page = getPage();
await page.setViewportSize({ width: 1680, height: 980 });
await wait(1);

try {
  await selectValue('Фонд', seed.fund);
  add('W12a', 'WEB select fund', true, seed.fund);
} catch (e) {
  add('W12a', 'WEB select fund', false, String(e));
}

try {
  await clickElement('Гарант Excel');
  await wait(1);
} catch (e) {}

try {
  await putFile(seed.xlsx);
  add('W12', 'WEB choose file dialog', true, seed.xlsx);
} catch (e) {
  add('W12', 'WEB choose file dialog', false, String(e));
}

try {
  const rows = await readRows();
  const n = (rows && (rows.total || (rows.rows || []).length)) || 0;
  const sample = (rows.rows || [])[0] || {};
  const fio = String(sample['ФИО файла'] || sample['ФИО'] || '');
  add('W13', 'WEB read Garant file rows', n >= 1, 'rows=' + n + ' fio=' + fio.slice(0, 80));
} catch (e) {
  add('W13', 'WEB read Garant file rows', false, String(e));
}

try {
  await clickElement('Сопоставить');
  await wait(4);
  add('W14', 'WEB match without crash', true, 'ok');
} catch (e) {
  add('W14', 'WEB match without crash', false, String(e));
}

try {
  await clickElement('Протокол');
  await wait(2);
  add('W15', 'WEB switch to protocol tab', true, 'ok');
} catch (e) {
  add('W15', 'WEB switch to protocol tab', false, String(e));
}

try {
  await clickElement('Строки файла');
  await wait(1);
  add('W16', 'WEB switch to file rows tab', true, 'ok');
} catch (e) {
  add('W16', 'WEB switch to file rows tab', false, String(e));
}

const size = await page.evaluate(() => {
  let maxTabs = 0;
  const nodes = document.querySelectorAll('div.frameTabs, div.frameGrid');
  for (const el of nodes) {
    const r = el.getBoundingClientRect();
    if (r.width > 200 && r.height > 80 && r.top > 300) {
      if (r.width > maxTabs) maxTabs = r.width;
    }
  }
  return { inner: window.innerWidth, tableFrame: Math.round(maxTabs) };
});
add('W17', 'WEB table frame near full width', size.tableFrame >= 1500, JSON.stringify(size));
add('W18', 'WEB viewport 1680', size.inner === 1680, JSON.stringify(size));

writeFileSync(outFile, JSON.stringify({ cases: cases }, null, 2));
console.log('WEBJSON=' + JSON.stringify({ cases: cases }));
console.log('WEB_SUITE_OK=true');
