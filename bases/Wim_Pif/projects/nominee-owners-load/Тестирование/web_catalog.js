const cat = await navigateLink('Справочник.ДополнительныеОтчетыИОбработки');
console.log(JSON.stringify({
  title: cat.title,
  errorModal: cat.errorModal || null,
  table: cat.table || null,
  buttons: (cat.buttons || []).map(b => b.name || b.title || b).slice(0, 20)
}, null, 2));

let rows = [];
try {
  rows = await readTable();
} catch (e) {
  console.log('readTable: ' + e);
}
const names = JSON.stringify(rows).toLowerCase();
const found = names.indexOf('владельц') >= 0 || names.indexOf('nominee') >= 0 || names.indexOf('заполнение') >= 0;
console.log('WEB_CATALOG_FOUND=' + found);
console.log('ROWS=' + JSON.stringify(rows).slice(0, 2000));
