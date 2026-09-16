const SHOT_DIR = 'bases/Wim_Pif/projects/nominee-owners-load/Тестирование/reports/form_open';

function dumpForm(prefix, form) {
  const buttons = (form.buttons || []).map(b => b.name || b.title || b);
  const fields = (form.fields || []).map(f => f.label || f.name);
  const payload = {
    title: form.title,
    formCount: form.formCount,
    buttons: buttons,
    fields: fields,
    tabs: form.tabs,
    errorModal: form.errorModal || null,
    confirmation: form.confirmation || null,
    errors: form.errors || null
  };
  console.log(prefix + '=' + JSON.stringify(payload));
  const hasRead = buttons.some(b => String(b).indexOf('Прочитать') >= 0);
  const hasMatch = buttons.some(b => String(b).indexOf('Сопоставить') >= 0);
  const hasFund = fields.some(f => String(f).indexOf('Фонд') >= 0);
  const ok = hasRead && hasMatch && hasFund && !form.errorModal;
  console.log(prefix + '_OK=' + ok);
  return ok;
}

async function shot(name) {
  const buf = await screenshot();
  writeFileSync(SHOT_DIR + '/' + name + '.png', buf);
  console.log('SHOT=' + name + '.png');
}

async function logErrors(tag) {
  const st = await getFormState();
  if (st.errorModal) {
    console.log(tag + '_ERR=' + JSON.stringify(st.errorModal));
  }
  if (st.errors) {
    console.log(tag + '_ERRORS=' + JSON.stringify(st.errors));
  }
  if (st.confirmation) {
    console.log(tag + '_CONFIRM=' + JSON.stringify(st.confirmation));
  }
  return st;
}

let cat = await navigateLink('Справочник.ДополнительныеОтчетыИОбработки');
console.log('LIST title=' + cat.title + ' formCount=' + cat.formCount);
if (String(cat.title || '').indexOf('Дополнительная обработка') >= 0
    && String(cat.title || '').indexOf('Дополнительные отчеты') < 0) {
  cat = await closeForm({ save: false });
  console.log('CLOSED_CARD title=' + cat.title);
}

try { await filterList('владельцев НД'); console.log('FILTERED'); } catch (e) { console.log('FILTER: ' + e); }
try { await clickElement('Заполнение списка владельцев НД (тонкий клиент)'); console.log('SELECTED'); }
catch (e) {
  console.log('SELECT: ' + e);
  try { await clickElement('Заполнение списка владельцев'); console.log('SELECTED_SHORT'); }
  catch (e2) { console.log('SELECT2: ' + e2); }
}
await shot('05_before_commands');

let st;
try {
  st = await clickElement('Список команд');
  console.log('AFTER_CMD_BTN title=' + st.title + ' formCount=' + st.formCount + ' submenu=' + JSON.stringify(st.submenu || []));
  console.log('AFTER_CMD_ERR=' + JSON.stringify(st.errorModal || st.errors || null));
} catch (e) {
  console.log('CMD_EX=' + e);
  st = await logErrors('CMD_EX');
}

await wait(2);
st = await logErrors('CMDFORM');
try {
  const tbl = await readTable({ maxRows: 20 });
  console.log('CMD_TABLE=' + JSON.stringify(tbl));
} catch (e) {
  console.log('CMD_TABLE_EX=' + e);
}
await shot('06_commands_form');

const cmdName = 'Заполнение списка владельцев НД (тонкий клиент)';
try {
  st = await clickElement(cmdName);
  console.log('CMD_ROW title=' + st.title + ' formCount=' + st.formCount);
} catch (e) {
  console.log('CMD_ROW: ' + e);
}

try {
  st = await clickElement('Выполнить');
  console.log('EXECUTE title=' + st.title + ' formCount=' + st.formCount);
} catch (e2) {
  console.log('EXECUTE: ' + e2);
}

await wait(3);
st = await logErrors('AFTER_RUN');
const ok = dumpForm('CATALOG2', st);
await shot('07_after_catalog_launch');
console.log('SUMMARY_CATALOG_OK=' + ok);
