const EPF = 'C:\\1c\\Cursor_1c\\WIM_DEV\\bases\\Wim_Pif\\projects\\nominee-owners-load\\build\\NomineeOwnersLoad.epf';
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
  const noErr = !form.errorModal;
  const ok = hasRead && hasMatch && hasFund && noErr;
  console.log(prefix + '_OK=' + ok);
  return ok;
}

async function shot(name) {
  try {
    const buf = await screenshot();
    writeFileSync(SHOT_DIR + '/' + name + '.png', buf);
    console.log('SHOT=' + name + '.png');
  } catch (e) {
    console.log('SHOT_FAIL=' + name + ' ' + e);
  }
}

async function dismissIfNeeded() {
  let st = await getFormState();
  if (st.confirmation) {
    try { st = await clickElement('Да'); } catch (e) { console.log('CONFIRM: ' + e); }
  }
  if (st.errorModal || (st.errors && st.errors.modal)) {
    console.log('ERROR_MODAL=' + JSON.stringify(st.errorModal || st.errors));
  }
  return st;
}

console.log('=== FILE_OPEN ===');
let fileOk = false;
try {
  let form = await openFile(EPF);
  form = await dismissIfNeeded();
  await wait(2);
  form = await getFormState();
  fileOk = dumpForm('FILE', form);
  await shot('01_file_open');
} catch (e) {
  console.log('FILE_OPEN_EX=' + e);
  await shot('01_file_open_error');
}

try { await closeForm({ save: false }); } catch (e) { console.log('CLOSE_FILE: ' + e); }
await wait(1);

console.log('=== CATALOG ===');
let catOk = false;
try {
  let cat = await navigateLink('Справочник.ДополнительныеОтчетыИОбработки');
  console.log('CAT_LIST title=' + cat.title + ' formCount=' + cat.formCount);
  await shot('02_catalog_list');

  let st = await getFormState();
  if (String(st.title || '').indexOf('Дополнительная обработка') >= 0
      && String(st.title || '').indexOf('Дополнительные отчеты') < 0) {
    st = await closeForm({ save: false });
    console.log('CLOSED_CARD title=' + st.title);
  }

  try {
    await filterList('владельцев НД');
    console.log('FILTERED');
  } catch (e) {
    console.log('FILTER: ' + e);
  }

  try {
    await clickElement('Заполнение списка владельцев НД (тонкий клиент)');
    console.log('SELECTED_ROW');
  } catch (e) {
    console.log('SELECT_ROW: ' + e);
    try {
      await clickElement('Заполнение списка владельцев');
      console.log('SELECTED_ROW_SHORT');
    } catch (e2) {
      console.log('SELECT_ROW2: ' + e2);
    }
  }

  await shot('03_catalog_selected');

  try {
    st = await clickElement('Список команд');
    console.log('CMD_LIST title=' + st.title + ' submenu=' + JSON.stringify(st.submenu || []) + ' formCount=' + st.formCount);
    const submenu = st.submenu || [];
    const cmd = submenu.find(s => String(s).indexOf('Заполнение') >= 0)
      || submenu.find(s => String(s).indexOf('открыть') >= 0 || String(s).indexOf('Открыть') >= 0)
      || submenu[0];
    if (cmd) {
      st = await clickElement(cmd);
      console.log('CMD_CLICK title=' + st.title + ' formCount=' + st.formCount);
    }
  } catch (e) {
    console.log('CMD_LIST: ' + e);
    try {
      st = await clickElement('Выполнить');
      console.log('EXECUTE title=' + st.title);
    } catch (e2) {
      console.log('EXECUTE: ' + e2);
    }
  }

  await wait(3);
  st = await dismissIfNeeded();
  st = await getFormState();
  catOk = dumpForm('CATALOG', st);
  await shot('04_catalog_open');
} catch (e) {
  console.log('CATALOG_EX=' + e);
  await shot('04_catalog_error');
}

console.log('SUMMARY_FILE_OK=' + fileOk);
console.log('SUMMARY_CATALOG_OK=' + catOk);
console.log('SUMMARY_ANY_OK=' + (fileOk || catOk));
