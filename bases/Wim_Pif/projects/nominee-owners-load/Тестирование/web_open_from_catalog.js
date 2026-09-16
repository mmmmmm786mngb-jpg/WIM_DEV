const start = await getFormState();
console.log('START title=' + start.title + ' formCount=' + start.formCount);

try {
  const pageState = await getPageState();
  console.log('SECTIONS=' + JSON.stringify(pageState));
} catch (e) {
  console.log('PAGE_STATE: ' + e);
}

try {
  const cmds = await getCommands();
  console.log('COMMANDS=' + JSON.stringify(cmds));
} catch (e) {
  console.log('COMMANDS: ' + e);
}

const cat = await navigateLink('Справочник.ДополнительныеОтчетыИОбработки');
console.log('CAT title=' + cat.title + ' formCount=' + cat.formCount);

let st = await getFormState();
if (String(st.title || '').indexOf('Дополнительная обработка') >= 0 && String(st.title || '').indexOf('Дополнительные отчеты') < 0) {
  try {
    st = await closeForm();
    console.log('CLOSED_CARD title=' + st.title);
  } catch (e) {
    console.log('CLOSE: ' + e);
  }
}

st = await getFormState();
console.log('LIST title=' + st.title + ' buttons=' + JSON.stringify((st.buttons || []).map(b => b.name || b.title || b)));

try {
  await clickElement('Заполнение списка владельцев НД (тонкий клиент)');
  console.log('SELECTED');
} catch (e) {
  console.log('SELECT: ' + e);
}

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
}

const form = await getFormState();
const buttons = (form.buttons || []).map(b => b.name || b.title || b);
const fields = (form.fields || []).map(f => f.label || f.name);
console.log(JSON.stringify({
  title: form.title,
  buttons: buttons,
  fields: fields,
  tabs: form.tabs,
  errorModal: form.errorModal || null,
  formCount: form.formCount
}, null, 2));

const hasRead = buttons.some(b => String(b).indexOf('Прочитать') >= 0);
const hasMatch = buttons.some(b => String(b).indexOf('Сопоставить') >= 0);
const hasFund = fields.some(f => String(f).indexOf('Фонд') >= 0);
console.log('WEB_FORM_OK=' + (hasRead && hasMatch && hasFund));
