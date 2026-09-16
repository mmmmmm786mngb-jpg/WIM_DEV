const EPF = 'C:\\1c\\Cursor_1c\\WIM_DEV\\bases\\Wim_Pif\\projects\\nominee-owners-load\\build\\NomineeOwnersLoad.epf';
await openFile(EPF);
await clickElement('Сопоставить');
const state = await getFormState();
console.log(JSON.stringify({
  modal: state.modal || false,
  errorModal: state.errorModal || null,
  title: state.title,
  texts: state.texts || null
}, null, 2));
console.log('WEB_EMPTY_MATCH_CHECKED=true');
