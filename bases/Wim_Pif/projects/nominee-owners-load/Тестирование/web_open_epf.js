const EPF = 'C:\\1c\\Cursor_1c\\WIM_DEV\\bases\\Wim_Pif\\projects\\nominee-owners-load\\build\\NomineeOwnersLoad.epf';

const form = await openFile(EPF);
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
